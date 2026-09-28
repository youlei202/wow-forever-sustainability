"""Runner integrity regressions use synthetic data and never invoke native."""
from __future__ import annotations

from copy import deepcopy
import gzip
import hashlib
import json

import pytest

from wowfs.experiments import oe_runner as runner
from wowfs.paths import canonical_hash


def _cached_cell(tmp_path):
    request = {"request": {"simOptions": {"iterations": 2}}}
    raw = {
        "iterationsDone": 2,
        "raidMetrics": {"parties": [{"players": [{
            "dps": {"allValues": [100.0, 102.0], "avg": 101.0},
            "actions": [{"id": {"spellId": 1},
                         "targets": [{"casts": 2, "damage": 202.0}]}],
            "resources": [], "auras": [],
        }]}]},
    }
    protocol = {"binary_sha256": "synthetic-binary", "source_hashes": {}}
    physical = canonical_hash({"binary": protocol["binary_sha256"], "input": request})
    key = canonical_hash({"physical": physical, "source": {},
                          "observation": runner.OBSERVATION})
    folder = tmp_path / "cache" / runner.STAGE / "native" / key[:2] / key
    folder.mkdir(parents=True)
    raw_bytes = json.dumps(raw).encode()
    (folder / "input.json").write_text(json.dumps(request))
    with gzip.open(folder / "output.json.gz", "wb") as stream:
        stream.write(raw_bytes)
    summary = runner.summarize(raw, request)
    summary.update(cache_key=key, output_sha256=hashlib.sha256(raw_bytes).hexdigest())
    (folder / "summary.json").write_text(json.dumps(summary))
    kwargs = dict(root=tmp_path, run=tmp_path / "run", batch=tmp_path / "batch",
                  protocol=protocol, budget={})
    return {"input": request}, folder, summary, kwargs


def test_valid_cache_is_checked_without_invoking_native(tmp_path, monkeypatch):
    job, _, summary, kwargs = _cached_cell(tmp_path)

    def forbid_native(*args, **kw):
        pytest.fail("A cache integrity test must never launch native")

    monkeypatch.setattr(runner.subprocess, "run", forbid_native)
    result = runner.execute_cell(job, **kwargs)
    assert result["cache_hit"] is True
    assert result["dps_samples"] == summary["dps_samples"]


def test_cache_rejects_changed_raw_output(tmp_path):
    job, folder, _, kwargs = _cached_cell(tmp_path)
    with gzip.open(folder / "output.json.gz", "wb") as stream:
        stream.write(b"corrupt native output")
    with pytest.raises(ValueError, match="output hash mismatch"):
        runner.execute_cell(job, **kwargs)
    assert not list(folder.glob("attempt-*"))


@pytest.mark.parametrize("field,value", [("dps_mean", 999), ("iterations", 999),
                                         ("dps_samples", [99, 103])])
def test_cache_rejects_summary_that_disagrees_with_raw(tmp_path, field, value):
    job, folder, summary, kwargs = _cached_cell(tmp_path)
    summary[field] = value
    (folder / "summary.json").write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="summary differs"):
        runner.execute_cell(job, **kwargs)


def test_cache_rejects_changed_input(tmp_path):
    job, folder, _, kwargs = _cached_cell(tmp_path)
    changed = deepcopy(job["input"])
    changed["request"]["simOptions"]["iterations"] = 1
    (folder / "input.json").write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="input mismatch"):
        runner.execute_cell(job, **kwargs)


def test_campaign_resume_keeps_original_deadline_and_rejects_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.time, "time", lambda: 1000.0)
    first = runner.campaign(tmp_path / "campaign", 1)
    monkeypatch.setattr(runner.time, "time", lambda: 2000.0)
    resumed = runner.campaign(tmp_path / "campaign", 1)
    assert resumed == first
    assert resumed["started_epoch"] == 1000.0
    assert resumed["deadline_epoch"] == 4600.0
    with pytest.raises(ValueError, match="cannot extend"):
        runner.campaign(tmp_path / "campaign", 2)


def test_campaign_budget_includes_environment_audit_time(tmp_path, monkeypatch):
    run = tmp_path / "campaign"
    run.mkdir()
    (run / "ENVIRONMENT.json").write_text(json.dumps({"utc": "1970-01-01T00:16:40+00:00"}))
    monkeypatch.setattr(runner.time, "time", lambda: 2000.0)
    budget = runner.campaign(run, 1)
    assert budget["started_epoch"] == 1000.0
    assert budget["deadline_epoch"] == 4600.0


@pytest.mark.parametrize("target", ["binary", "source"])
def test_resume_rejects_corrupted_frozen_files(tmp_path, monkeypatch, target):
    work = tmp_path / "work"
    source = tmp_path / "source"
    live_binary = work / "envs/r3-go/wowfs-native-variants"
    live_binary.parent.mkdir(parents=True)
    live_binary.write_bytes(b"synthetic binary: no cells will execute")
    live_source = source / "src/probe.py"
    live_source.parent.mkdir(parents=True)
    live_source.write_text("# synthetic frozen source\n")
    monkeypatch.setattr(runner, "SOURCE_ROOT", source)
    monkeypatch.setattr(runner, "setup_paths", lambda: work)
    monkeypatch.setattr(runner, "source_snapshot",
                        lambda: {"src/probe.py": runner.file_hash(live_source)})
    kwargs = dict(run_root=work / "run", batch_id="integrity", phase="audit",
                  workers=1, max_wall_hours=1)
    batch = runner.run_batch([], **kwargs)
    # An intact resume passes before either independent tampering scenario.
    runner.run_batch([], resume=True, **kwargs)
    frozen = batch / ("native.frozen" if target == "binary" else "source/src/probe.py")
    frozen.write_bytes(b"changed after freeze")
    with pytest.raises(ValueError, match="frozen .* hash mismatch"):
        runner.run_batch([], resume=True, **kwargs)
    assert live_binary.read_bytes() == b"synthetic binary: no cells will execute"
    assert live_source.read_text() == "# synthetic frozen source\n"
