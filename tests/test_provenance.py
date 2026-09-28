import json
from pathlib import Path
import pytest
from wowfs.experiments.runner import freeze

def test_native_template_cannot_be_misreported_as_frozen(tmp_path):
    with pytest.raises(RuntimeError, match="Native protocol cannot be frozen"):
        freeze({"scope": "native_forever"}, tmp_path)

def test_frozen_snapshot_detects_tampering(tmp_path):
    cfg = {"scope": "abstract_exact", "split": "development", "horizon": 1, "seeds": [0], "variants": ["pair"]}
    path, original = freeze(cfg, tmp_path)
    file = path / "source_snapshot/wowfs/__init__.py"
    file.write_text(file.read_text() + "\n# changed\n")
    with pytest.raises(RuntimeError, match="snapshot was modified"):
        freeze(cfg, tmp_path)
