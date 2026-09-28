"""Build a compact, sealed review archive from completed campaign artifacts.

This is packaging only. It neither runs native simulations nor changes any
frozen result. Large trajectory files and environments stay in the work root.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import zipfile

from wowfs.paths import SOURCE_ROOT


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def assemble(run, benchmark, output):
    run, benchmark, output = map(Path, (run, benchmark, output))
    output.mkdir(parents=True, exist_ok=False)
    copies = []

    def copy(source, target):
        source, target = Path(source), output / target
        if not source.is_file():
            raise FileNotFoundError(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copies.append({'path': str(target.relative_to(output)), 'source': str(source), 'source_sha256': digest(source)})

    def tree(source, target, suffixes=None):
        for path in sorted(Path(source).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and (suffixes is None or path.suffix in suffixes):
                copy(path, Path(target) / path.relative_to(source))

    complete = read(run / 'benchmark/PRIMARY_ALL_COMPLETE.json')
    if complete['status'] != 'COMPLETE':
        raise ValueError('All primary computational workflows must finish before final packaging')
    for name, expected in read(run / 'PROTOCOL_FROZEN.json')['source_hashes'].items():
        if digest(SOURCE_ROOT / name) != expected:
            raise ValueError(f'Frozen confirmation source changed: {name}')
    tree(SOURCE_ROOT / 'src/wowfs', 'code/wowfs', {'.py'})
    for path in sorted((SOURCE_ROOT / 'tests').glob('test_co*.py')):
        copy(path, Path('tests') / path.name)
    for name in ('env.sh', 'review_run_benchmark.py', 'native_completion_panels.py',
                 'native_mechanism_diagnostics.py', 'summarize_native_completion.py',
                 'audit_completion_query_driver.py', 'audit_portable_confirmation.py',
                 'audit_certificate_service.py'):
        copy(SOURCE_ROOT / 'scripts' / name, Path('scripts') / name)
    for name in ('paths.yaml', 'fc_presets.json', 'official_contexts.yaml'):
        copy(SOURCE_ROOT / 'configs' / name, Path('configs') / name)
    tree(SOURCE_ROOT / 'docs/completion-oral-2026-09-26', 'docs', {'.md', '.tex', '.svg'})
    for name in ('REVIEW.md', 'PRIOR_DELTA.md', 'PROOF_AND_ENCODING_AUDIT.md', 'CLAIM_EVIDENCE_MATRIX.md', 'REPRODUCE.md', 'REAL_COMMANDS.md', 'GPT_PRO_REVIEW.md'):
        copy(SOURCE_ROOT / 'docs/completion-oral-2026-09-26' / name, name)
    for name in ('PROTOCOL_FROZEN.json', 'ALPHA_LEDGER.json', 'SEED_OVERLAP.json', 'SECONDARY_TOLERANCE_PROTOCOL.json', 'CAMPAIGN_STATUS.json', 'RESOURCE_USE.json', 'METHODS_MANIFEST.json'):
        copy(run / name, name)
    for name in ('ENVIRONMENT_INITIAL.json', 'RUN_RECEIPTS.jsonl'):
        copy(run / name, Path('provenance') / name)
    tree(run / 'checks', 'checks', {'.json', '.md', '.log'})
    tree(run / 'native/registration', 'data/registration', {'.json', '.jsonl', '.md', '.csv'})
    copy(run / 'native/registration/CATALOG_REGISTRY.jsonl', 'NATIVE_CATALOGUES.jsonl')
    copy(run / 'native/registration/CATALOG_REGISTRY.jsonl', 'data/native/CATALOG_REGISTRY.jsonl')
    tree(run / 'native/confirmation-v1', 'data/native', {'.json', '.npz', '.csv'})
    tree(run / 'audit/certificate-service-v1/interfaces', 'data/certificate-interfaces', {'.json'})
    tree(run / 'native/predictions-v1', 'data/predictions', {'.json', '.npz', '.csv'})
    tree(run / 'native/projection-confirmation-v1', 'data/projection', {'.json', '.csv'})
    tree(run / 'native/obligation-audit-v1', 'data/obligations', {'.json', '.csv'})
    tree(run / 'native/secondary-tolerance-v1', 'data/secondary-tolerance', {'.json', '.csv'})
    tree(run / 'native/summary-v2', 'data/native-summary', {'.json', '.csv'})
    tree(run / 'native/mechanism-diagnostics-v1', 'data/executed-mechanisms', {'.json', '.csv'})
    tree(run / 'sensitivity/propagation-v1', 'data/sensitivity', {'.json', '.jsonl', '.npz', '.csv', '.py'})
    for name in ('INHERITED_EVENT_AUDIT.json', 'THRESHOLD_DERIVATIONS.jsonl', 'SENSITIVITY_GRID.csv', 'CERTIFIED_REGIONS.json'):
        copy(run / 'sensitivity/propagation-v1' / name, name)
    copy(run / 'native/summary-v2/CANDIDATE_EXPANSION_COMPARISONS.csv', 'CATALOG_EXPANSION_RESULTS.csv')
    copy(run / 'native/summary-v2/NEGATIVE_AND_UNRESOLVED.csv', 'NATIVE_NEGATIVE_AND_UNRESOLVED.csv')
    copy(run / 'NEGATIVE_AND_UNRESOLVED.csv', 'NEGATIVE_AND_UNRESOLVED.csv')
    copy(run / 'native/confirmation-v1/NATIVE_DECISIONS.csv', 'NATIVE_DECISIONS.csv')
    predictions = read(run / 'native/predictions-v1/NATIVE_DECISIONS.json')
    (output / 'NATIVE_PREDICTIONS.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in predictions))
    for name in ('DEV256_FAILURE_ERRATUM.json', 'FROZEN_WITNESS_RECHECK.json', 'NATIVE_STAGE_COMPLETION.json', 'NATIVE_REAL_COMMANDS.md'):
        copy(run / 'native' / name, Path('provenance/native') / name)
    copy(run / 'native/development/default-rule/PRECISION_PLANNING_ERRATUM.json',
         'provenance/native/PRECISION_PLANNING_ERRATUM.json')
    copy(run / 'native/projection-predictions-v1/FAILED.json',
         'provenance/native/PROJECTION_PREDICTION_INITIAL_FAILURE.json')
    for folder in ('confirm16384', 'predict1024', 'dev256-v2', 'dev256'):
        directory = run / 'batches' / folder
        for name in ('PROTOCOL.json', 'FREEZE_TIME.json', 'PROGRESS.json', 'OBSERVATION_INDEX.json'):
            if (directory / name).is_file():
                copy(directory / name, Path('provenance/native-batches') / folder / name)
    observations = read(run / 'batches/confirm16384/OBSERVATION_INDEX.json')
    (output / 'OBSERVATION_INDEX.jsonl').write_text(''.join(json.dumps(r, sort_keys=True, separators=(',', ':')) + '\n' for r in observations))
    for name in ('BENCHMARK_INSTANCES.jsonl', 'QUERY_STREAMS.jsonl'):
        (output / name).write_text((run / 'test-registry' / name).read_text() + (run / 'native-test-registry' / name).read_text())
    tree(run / 'test-registry', 'data/benchmark-registry/synthetic', {'.json', '.jsonl'})
    tree(run / 'native-test-registry', 'data/benchmark-registry/native', {'.json', '.jsonl'})
    tree(benchmark, 'data/benchmark', {'.json', '.jsonl', '.csv', '.gz', '.md', '.tex', '.pdf', '.py', '.aux', '.log', '.out', '.txt'})
    for name, expected in read(benchmark / 'REPORT_HASHES.json').items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'Unsafe report path: {name}')
        if digest(output / 'data/benchmark' / relative) != expected:
            raise ValueError(f'Packaged report identity mismatch: {name}')
    for name in ('BENCHMARK_RESULTS.csv', 'COMPILED_INTERFACES.jsonl'):
        copy(benchmark / name, name)
    # Do not duplicate the already-compressed, largest query receipt table.
    # Its canonical path is also the path used by the metric rechecker.
    write(output / 'ARTIFACT_INDEX.json', {'QUERY_RESULTS.csv': 'data/benchmark/QUERY_RESULTS.csv.gz',
        'compression': 'lossless gzip; every processed query retained',
        'benchmark_metric_recheck_directory': 'data/benchmark',
        'all_original_query_streams': 'QUERY_STREAMS.jsonl'})
    for name in complete['suites']:
        for receipt in ('PROTOCOL_FROZEN.json', 'FREEZE_TIME.json', 'COMMON_SERVER_STARTUP.json', 'JOB_INDEX.json'):
            copy(run / 'benchmark' / name / receipt, Path('provenance/benchmark') / name / receipt)
    # Whole-run exclusions and infrastructure failures stay explicitly visible.
    for path in sorted((run / 'benchmark').glob('*.json')):
        copy(path, Path('provenance/benchmark') / path.name)
    for name in ('INFRASTRUCTURE_CONTAMINATED.json', 'INFRASTRUCTURE_INTERRUPTION.json'):
        path = run / 'benchmark/test-existence-v1' / name
        if path.exists():
            copy(path, Path('provenance/benchmark/excluded-test-existence-v1') / name)
    tree(run / 'audit/exact-solvers-v2', 'checks/exact-solvers', {'.json', '.jsonl'})
    copy(run / 'audit/reference-paper-rerun.log', 'provenance/reference-paper/run_checks.log')
    tree(run / 'audit/query-maximal-cache-dev', 'checks/query-maximal-cache-dev', {'.json', '.log'})
    for path in (run / 'audit').glob('*INDEPENDENT*.json'):
        copy(path, Path('checks') / path.name)
    for name in ('native-v2', 'native-expansion-v1'):
        tree(run / 'figures' / name, Path('figures') / name, {'.pdf', '.json'})
    tree(run / 'sensitivity/figures', 'figures/sensitivity', {'.pdf'})
    tree(benchmark / 'figures', 'figures/benchmark', {'.pdf'})
    reference = run.parents[2] / 'inputs/completion-oral-2026-09-26/WoW_Completion_Oral_Experiments_2026_09_26/references'
    for name in ('CURRENT_PAPER.pdf', 'COMPLETION_THEORY.pdf', 'INPUT_HASHES.json'):
        copy(reference / name, Path('references') / name)
    for name in ('START_HERE.md', 'CODEX_EXPERIMENT_PLAN.md', 'PACKAGE_MANIFEST.json'):
        copy(reference.parent / name, Path('references/handoff') / name)
    copy(reference.parent / 'configs/campaign.json', 'references/handoff/campaign-proposal.json')
    environment = {name: version(name) for name in ('numpy', 'scipy', 'PyYAML', 'ortools', 'python-sat', 'pypblib', 'psutil')}
    write(output / 'DEPENDENCIES.json', {'python': __import__('sys').version, 'versions': environment,
        'minimal_recheck': ['numpy', 'scipy', 'PyYAML'], 'solver_reexecution': ['ortools', 'python-sat', 'pypblib', 'psutil']})
    (output / 'requirements-recheck.txt').write_text(''.join(f'{n}=={environment[n]}\n' for n in ('numpy', 'scipy', 'PyYAML')))
    (output / 'requirements-solvers.txt').write_text('-r requirements-recheck.txt\n' + ''.join(f'{n}=={environment[n]}\n' for n in ('ortools', 'python-sat', 'pypblib', 'psutil')))
    write(output / 'provenance/PACKAGING_SOURCE_INDEX.json', copies)
    write(output / 'provenance/ARCHIVE_EXCLUSIONS.json', {
        'excluded': ['raw per-battle trajectories', 'native binary and external engine tree', 'Python/Go environments and caches', 'font binaries', 'old review ZIPs', 'superseded figure previews (final panels and all scientific tables retained)', 'duplicate per-job benchmark model copies'],
        'retained_elsewhere': str(run), 'reason': 'Key finite-table conclusions are recomputed from the included compact sufficient statistics; runtime measurements have compact per-attempt/per-query receipts.',
        'not_reproduced_by_compact_checker': ['native trajectory generation', 'benchmark wall-clock timings', 'higher-moment or tail diagnostics']})
    print(json.dumps({'status': 'ASSEMBLED_NOT_SEALED', 'directory': str(output), 'copied_files': len(copies)}))


def seal(folder):
    folder = Path(folder)
    files = [{'path': str(p.relative_to(folder)), 'sha256': digest(p), 'bytes': p.stat().st_size}
             for p in sorted(folder.rglob('*')) if p.is_file() and p.name != 'REVIEW_MANIFEST.json' and '__pycache__' not in p.parts]
    write(folder / 'REVIEW_MANIFEST.json', {'format': 'wowfs-compact-review-v2',
        'required_sections': ['native', 'secondary-tolerance', 'projection', 'obligations', 'sensitivity', 'benchmark'],
        'sealed_utc': datetime.now(timezone.utc).isoformat(), 'files': files})
    return {'files': len(files), 'uncompressed_bytes': sum(r['bytes'] for r in files), 'manifest_sha256': digest(folder / 'REVIEW_MANIFEST.json')}


def archive(folder, destination):
    folder, destination = Path(folder), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    manifest = read(folder / 'REVIEW_MANIFEST.json')
    for row in manifest['files']:
        if digest(folder / row['path']) != row['sha256']:
            raise ValueError(f'Changed since sealing: {row["path"]}')
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                z.write(p, Path('review-v2') / p.relative_to(folder))
    result = {'archive': str(destination), 'bytes': destination.stat().st_size, 'sha256': digest(destination)}
    write(destination.with_suffix('.zip.receipt.json'), result)
    destination.with_suffix('.zip.sha256').write_text(result['sha256'] + '  ' + destination.name + '\n')
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    a = sub.add_parser('assemble'); a.add_argument('--run', type=Path, required=True); a.add_argument('--benchmark', type=Path, required=True); a.add_argument('--output', type=Path, required=True)
    s = sub.add_parser('seal'); s.add_argument('folder', type=Path)
    z = sub.add_parser('zip'); z.add_argument('folder', type=Path); z.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.operation == 'assemble': assemble(args.run, args.benchmark, args.output)
    elif args.operation == 'seal': print(json.dumps(seal(args.folder)))
    else: archive(args.folder, args.destination)


if __name__ == '__main__':
    main()
