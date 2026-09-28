"""Input integrity and storage boundaries, using small local fixture archives."""
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import zipfile

import pytest

from wowfs.reproduction import context


def manifest(root, files, *, archive_hash=context.ARCHIVE_SHA256):
    value = {"archive_sha256": archive_hash, "files": {
        name: hashlib.sha256(content).hexdigest() for name, content in files.items()}}
    (root / "INPUT_MANIFEST.json").write_text(json.dumps(value))
    return value


def test_safe_archive_extracts_exact_bytes(tmp_path):
    archive, destination = tmp_path / "safe.zip", tmp_path / "unpacked"
    content = b"exact\x00finite\nresponse\xff"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("nested/response.bin", content)
    context.extract(archive, destination)
    assert (destination / "nested/response.bin").read_bytes() == content


@pytest.mark.parametrize("member", ["../escape.txt", "nested/../../escape.txt",
                                     "/absolute.txt", "nested\\escape.txt"])
def test_archive_rejects_unsafe_paths_before_writing_any_member(tmp_path, member):
    archive, destination = tmp_path / "unsafe.zip", tmp_path / "unpacked"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("would_be_safe.txt", "first entry")
        stream.writestr(member, "must not escape")
    with pytest.raises(ValueError, match="Unsafe archive member"):
        context.extract(archive, destination)
    assert not destination.exists()
    assert not (tmp_path / "escape.txt").exists()


def test_archive_rejects_symlink_members(tmp_path):
    archive, destination = tmp_path / "symlink.zip", tmp_path / "unpacked"
    link = zipfile.ZipInfo("linked-response")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr(link, "../outside")
    with pytest.raises(ValueError, match="Unsafe archive member"):
        context.extract(archive, destination)
    assert not destination.exists()


def test_archive_rejects_duplicate_members_without_silent_overwrite(tmp_path):
    archive, destination = tmp_path / "duplicate.zip", tmp_path / "unpacked"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("response.json", '{"answer":"YES"}')
        with pytest.warns(UserWarning, match="Duplicate name"):
            stream.writestr("response.json", '{"answer":"NO"}')
    with pytest.raises(ValueError, match="Unsafe archive member"):
        context.extract(archive, destination)
    assert not destination.exists()


def test_input_verification_accepts_exact_bytes_and_rejects_tampering(tmp_path):
    payload = b'{"status":"UNKNOWN","denominator":128}\n'
    data = tmp_path / "results.json"
    data.write_bytes(payload)
    expected = manifest(tmp_path, {data.name: payload})
    assert context.verify_inputs(tmp_path) == expected
    data.write_bytes(payload.replace(b"UNKNOWN", b"YES"))
    with pytest.raises(ValueError, match="changed or is missing"):
        context.verify_inputs(tmp_path)


def test_input_verification_rejects_another_archive_identity(tmp_path):
    manifest(tmp_path, {}, archive_hash="0" * 64)
    with pytest.raises(ValueError, match="final v2 audit archive"):
        context.verify_inputs(tmp_path)


@pytest.mark.parametrize("escape_kind", ["relative", "absolute", "symlink"])
def test_input_manifest_cannot_refer_outside_its_tree(tmp_path, escape_kind):
    root = tmp_path / "inputs"
    root.mkdir()
    outside = tmp_path / "outside.json"
    payload = b"valid bytes are insufficient if their path escapes"
    outside.write_bytes(payload)
    if escape_kind == "relative":
        name = "../outside.json"
    elif escape_kind == "absolute":
        name = str(outside.resolve())
    else:
        (root / "link.json").symlink_to(outside)
        name = "link.json"
    manifest(root, {name: payload})
    with pytest.raises(ValueError, match="changed or is missing"):
        context.verify_inputs(root)


def test_external_storage_resolves_symlinks_before_source_tree_check(tmp_path, monkeypatch):
    source, outside = tmp_path / "source", tmp_path / "work"
    source.mkdir()
    outside.mkdir()
    monkeypatch.setattr(context, "SOURCE_ROOT", source.resolve())
    assert context.external(outside / "outputs") == outside / "outputs"
    (outside / "source-alias").symlink_to(source, target_is_directory=True)
    for path in (source, source / "new-output", outside / "source-alias/hidden-output"):
        with pytest.raises(ValueError, match="outside the source repository"):
            context.external(path)


@pytest.mark.parametrize("output_kind", ["same", "nested", "ancestor"])
def test_context_rejects_overlapping_output_and_immutable_inputs(
        tmp_path, monkeypatch, output_kind):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    output = {"same": inputs, "nested": inputs / "generated", "ancestor": tmp_path}[output_kind]
    monkeypatch.setattr(context, "prepare_inputs", lambda: inputs)
    monkeypatch.setenv("WOWFS_REPRODUCTION_ROOT", str(output))
    with pytest.raises(ValueError, match="immutable input trees must be separate"):
        context.get_context()
    assert not (inputs / "generated").exists()


def test_paper_asset_receipt_seals_staged_evidence_before_reuse(tmp_path, monkeypatch):
    from wowfs.reporting import paper_assets

    # Replace the expensive manuscript generators, but exercise real staging,
    # receipt creation and reuse. Later plotting reads this JSON directly.
    repo, source, output = (tmp_path / name for name in ("repo", "frozen", "output"))
    implementation = repo / "src/wowfs/reporting/paper_assets.py"
    implementation.parent.mkdir(parents=True)
    implementation.write_text("# Isolated test implementation identity\n")
    (source / "tables").mkdir(parents=True)
    (source / "main.tex").write_text("fixture manuscript\n")
    (source / "tables/exact_checks.tex").write_text(r"header\midrule old rows\bottomrule footer")
    relative = "evidence/v2/native-summary/NATIVE_EVIDENCE_SUMMARY.json"
    evidence = source / relative
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps({"obligation_diagnostics": {"base_label_counts": {
        "legacy_alone_sufficient": 42, "targets_alone_sufficient": 39,
        "legacy_necessary_for_obstruction": 28, "targets_necessary_for_obstruction": 16}}}))
    monkeypatch.setattr(paper_assets, "__file__", str(implementation))
    monkeypatch.setattr(paper_assets.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    counts = ["500", "700", "120", "100 / 964", "10 / 55", "1,016", "250", "200", "77"]
    monkeypatch.setattr(paper_assets, "_exact_rows", lambda stage: [["fixture", count] for count in counts])

    assert paper_assets.prepare_paper_assets(source, output, checks=False) == output
    assert not (repo / "paper").exists()
    receipt = json.loads((output / "PAPER_ASSETS.json").read_text())
    assert "maintained_source_sha256" not in receipt
    assert "manuscript/" + relative in receipt["generated_sha256"]
    assert paper_assets.prepare_paper_assets(source, output, checks=False) == output
    staged = output / "manuscript" / relative
    staged.write_text(staged.read_text().replace("42", "420"))
    with pytest.raises(ValueError, match="generated asset changed or is missing"):
        paper_assets.prepare_paper_assets(source, output, checks=False)
    assert json.loads(evidence.read_text())["obligation_diagnostics"]["base_label_counts"]["legacy_alone_sufficient"] == 42


def test_source_package_excludes_manuscripts_and_private_archives(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "scripts/reproduce/package_reproduction.py"
    spec = importlib.util.spec_from_file_location("package_reproduction", script)
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    source, output = tmp_path / "source", tmp_path / "code.zip"
    included = {"README.md": "Code-only fixture\n", "src/example.py": "print('example')\n",
                "notebooks/example.ipynb": '{"cells": [{"outputs": [{"text": ["saved result"]}]}]}'}
    excluded = {"paper/current/main.tex": "private manuscript", "docs/figure.tex": "private figure",
                "scripts/private.zip": "private archive", "src/private.tar.gz": "private archive",
                "docs/manuscript/draft.md": "private manuscript", "docs/private.pdf": "private PDF"}
    for name, content in {**included, **excluded}.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    (source / "src/private.py").symlink_to(source / "paper/current/main.tex")
    monkeypatch.setattr(package, "ROOT", source)
    monkeypatch.setattr(sys, "argv", [str(script), "--output", str(output)])

    # Packaging succeeds without the frozen archive and preserves notebook bytes.
    package.main()
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {"START_HERE.txt", "MANIFEST.json"} | {
            "source/" + name for name in included}
        for name, content in included.items():
            assert archive.read("source/" + name).decode() == content
        checksums = json.loads(archive.read("MANIFEST.json"))
        for name, digest in checksums.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    receipt = json.loads(output.with_suffix(".receipt.json").read_text())
    assert receipt["package_scope"] == "source_code_and_notebooks"
    assert receipt["manuscripts_included"] is False
    assert receipt["private_inputs_included"] is False
