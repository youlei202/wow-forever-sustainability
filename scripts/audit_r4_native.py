#!/usr/bin/env python3
"""Audit retained R4 receipts and join frozen jobs to results without bulk loads."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import re
import runpy

import yaml
from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash

shared = runpy.run_path(str(SOURCE_ROOT / 'scripts/audit_r2_native.py'))
sha, read, directories, audit_cache = (
    shared[k] for k in ['sha', 'read', 'directories', 'audit_cache'])
STAGE = 'r4-foundational-discovery'
ORIGINS = {STAGE, 'r2-discovery', 'r3-gold'}


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


class JSONStream:
    """Strict JSON container reader; only one array value is materialized."""
    def __init__(self, stream):
        self.stream, self.buffer, self.pos, self.eof = stream, '', 0, False
        self.digest, self.decoder = hashlib.sha256(), json.JSONDecoder()

    def fill(self):
        block = self.stream.read(1 << 20)
        self.digest.update(block.encode('utf-8'))
        self.buffer, self.pos = self.buffer[self.pos:] + block, 0
        self.eof = not block
        if len(self.buffer) > 64 << 20:
            raise ValueError('individual JSON value exceeds 64 MiB audit limit')
        return bool(block)

    def peek(self):
        while True:
            self.pos = re.compile(r'\s*').match(self.buffer, self.pos).end()
            if self.pos < len(self.buffer):
                return self.buffer[self.pos]
            if self.eof or not self.fill():
                return None

    def expect(self, character):
        if self.peek() != character:
            raise ValueError('expected JSON delimiter ' + character)
        self.pos += 1

    def value(self):
        if self.peek() is None:
            raise ValueError('premature JSON EOF')
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.pos)
                # A scalar number may end exactly at a chunk boundary.
                if end == len(self.buffer) and not self.eof:
                    self.fill()
                    continue
                self.pos = end
                return value
            except json.JSONDecodeError:
                if self.eof or not self.fill():
                    raise

    def array(self):
        self.expect('[')
        if self.peek() == ']':
            self.pos += 1
            return
        while True:
            yield self.value()
            if self.peek() == ']':
                self.pos += 1
                return
            self.expect(',')
            if self.peek() == ']':
                raise ValueError('trailing JSON array comma')


def stream_array(path, member=None, metadata=None):
    """Yield root array or named array; return other fields and hash in metadata."""
    metadata = metadata if metadata is not None else {}
    with path.open(encoding='utf-8', newline='') as stream:
        reader = JSONStream(stream)
        if member is None:
            yield from reader.array()
        else:
            reader.expect('{')
            keys = set()
            while reader.peek() != '}':
                key = reader.value()
                if not isinstance(key, str) or key in keys:
                    raise ValueError('invalid or duplicate root JSON key')
                keys.add(key)
                reader.expect(':')
                if key == member:
                    yield from reader.array()
                else:
                    metadata[key] = reader.value()
                if reader.peek() == '}':
                    break
                reader.expect(',')
                if reader.peek() == '}':
                    raise ValueError('trailing JSON object comma')
            reader.expect('}')
            if member not in keys:
                raise ValueError('missing JSON array member ' + member)
        if reader.peek() is not None:
            raise ValueError('trailing data after JSON document')
        metadata['_raw_sha256'] = reader.digest.hexdigest()


def signature(path):
    try:
        stat = path.stat()
        return [stat.st_size, stat.st_mtime_ns, stat.st_ino]
    except FileNotFoundError:
        return None


def receipt_signature(directory):
    return canonical_hash({name: signature(Path(directory) / name) for name in
                           ['input.json', 'invocation.json', 'summary.json',
                            'output.json.gz', 'output.json']})


def audit_receipt(directory):
    before = receipt_signature(directory)
    row = audit_cache(directory)
    row['receipt_signature'] = receipt_signature(directory)
    if before != row['receipt_signature']:
        row.update(status='audit_error', audit_error='receipt files changed while read',
                   verified_physical_battles=0)
    return row


class Issues:
    def __init__(self):
        self.counts, self.examples = Counter(), []

    def add(self, kind, detail=None):
        self.counts[kind] += 1
        if len(self.examples) < 50:
            self.examples.append({'kind': kind, 'detail': detail})

    def require(self, condition, kind, detail=None):
        if not condition:
            self.add(kind, detail)


def provenance_checks(root, run, protocol, issues):
    checks = []
    source_root = (run / 'source').resolve()
    science = protocol.get('science', {})
    mappings = [('protocol.source_hashes', protocol.get('source_hashes', {})),
                ('science.source_hashes', science.get('source_hashes', {}))]
    for label, mapping in mappings:
        for relative, expected in mapping.items():
            path = (source_root / relative).resolve()
            valid = path.is_relative_to(source_root) and path.is_file()
            actual = file_hash(path) if valid else None
            issues.require(actual == expected, 'source_hash_mismatch', label + ':' + relative)
            checks.append({'field': label + ':' + relative, 'path': str(path),
                           'expected': expected, 'actual': actual})
    scalar_sources = {k: science[k] for k in ['source_hash', 'source_sha256', 'driver_sha256']
                      if k in science}
    if scalar_sources:
        archived = {str(p.relative_to(source_root)): file_hash(p)
                    for p in source_root.rglob('*') if p.is_file()}
        for field, expected in scalar_sources.items():
            matches = [p for p, digest in archived.items() if digest == expected]
            issues.require(bool(matches), 'science_source_hash_missing', field)
            checks.append({'field': 'science.' + field, 'expected': expected,
                           'matching_archived_sources': matches})
    baseline = root / 'runs' / STAGE / 'baseline-v1' / 'BASE_ECOSYSTEMS.json'
    hash_paths = {'base_ecosystems_sha256': run / 'BASE_ECOSYSTEMS.json',
                  'measured_ecosystems_sha256': run / 'BASE_ECOSYSTEMS.json',
                  'baseline_ecosystems_sha256': baseline, 'base_domain_sha256': baseline,
                  'reference_domain_sha256': run / 'FULL_REFERENCE_ECOSYSTEMS.json',
                  'configuration_sha256': run / 'CONFIG.yaml'}
    for field, path in hash_paths.items():
        if field not in science:
            continue
        value = (yaml.safe_load(path.read_text()) if path.suffix == '.yaml'
                 else read(path)[0]) if path.is_file() else None
        actual = canonical_hash(value) if value is not None else None
        issues.require(actual == science[field], 'science_content_hash_mismatch', field)
        checks.append({'field': 'science.' + field, 'path': str(path),
                       'expected': science[field], 'actual': actual})
    if 'binary_sha256' in science:
        issues.require(science['binary_sha256'] == protocol.get('binary_sha256'),
                       'science_binary_hash_mismatch')
    for field in ['configuration', 'config']:
        if field in science and (run / 'CONFIG.yaml').is_file():
            issues.require(yaml.safe_load((run / 'CONFIG.yaml').read_text()) == science[field],
                           'science_configuration_mismatch', field)
    known_hashes = set(hash_paths) | set(scalar_sources) | {'source_hashes', 'binary_sha256'}
    unknown = sorted(k for k in science if ('sha256' in k or k.endswith('_hash'))
                     and k not in known_hashes)
    if unknown:
        issues.add('unsupported_science_hash_fields', unknown)
    return checks


def native_snapshot(root, path, protocol, protocol_hash, ledger, external):
    run, issues = path.parent, Issues()
    watched = [path, run / 'PROGRESS.json', run / 'JOBS.json', run / 'RESULTS.json',
               run / 'native.frozen', run / 'BASE_ECOSYSTEMS.json', run / 'CONFIG.yaml',
               run / 'FULL_REFERENCE_ECOSYSTEMS.json']
    watched += [p for p in (run / 'source').rglob('*') if p.is_file()]
    before = {str(p): signature(p) for p in watched}
    row = {'run': run.name, 'protocol_sha256': protocol_hash, 'kind': 'native',
           'binary_sha256': protocol.get('binary_sha256'),
           'logical_cells': protocol.get('logical_cells'),
           'requested_battles': protocol.get('requested_battles')}
    try:
        required = ['binary_sha256', 'jobs_sha256', 'logical_cells', 'requested_battles',
                    'source_hashes', 'science']
        missing = [k for k in required if k not in protocol]
        issues.require(not missing, 'unsupported_native_protocol_schema', missing)
        row['progress'] = read(run / 'PROGRESS.json')[0] if (run / 'PROGRESS.json').exists() else {'status': 'not_yet_reported'}
        issues.require(row['progress'].get('status') == 'complete', 'progress_not_complete', row['progress'])
        issues.require(not row['progress'].get('errors'), 'progress_errors', row['progress'].get('errors'))
        row['provenance_checks'] = provenance_checks(root, run, protocol, issues)
        binary = run / 'native.frozen'
        row['frozen_binary_sha256'] = file_hash(binary) if binary.is_file() else None
        row['frozen_binary_matches'] = row['frozen_binary_sha256'] == protocol.get('binary_sha256') and binary.is_file()
        issues.require(row['frozen_binary_matches'], 'frozen_binary_mismatch')
        jobs_path, results_path = run / 'JOBS.json', run / 'RESULTS.json'
        issues.require(jobs_path.is_file(), 'missing_jobs')
        issues.require(results_path.is_file(), 'missing_results')
        if not jobs_path.is_file() or not results_path.is_file() or missing:
            raise ValueError('native archive is incomplete or schema unsupported')
        job_meta, result_meta = {}, {}
        jobs = stream_array(jobs_path, metadata=job_meta)
        results = stream_array(results_path, 'rows', result_meta)
        absent, digest = object(), hashlib.sha256(b'[')
        job_count = result_count = requested = reported = missing_rows = 0
        keys, origins = set(), Counter()
        for index, (job, result) in enumerate(zip_longest(jobs, results, fillvalue=absent)):
            expected_key = None
            if job is not absent:
                if job_count:
                    digest.update(b',')
                digest.update(json.dumps(job, sort_keys=True, separators=(',', ':')).encode())
                job_count += 1
                iterations = job['input']['request']['simOptions']['iterations']
                requested += iterations
                expected_key = canonical_hash({'binary': protocol['binary_sha256'], 'input': job['input']})
            if result is absent:
                issues.add('result_shorter_than_jobs', index)
                continue
            result_count += 1
            if result is None:
                missing_rows += 1
                issues.add('missing_result_row', index)
                continue
            if job is absent:
                issues.add('result_longer_than_jobs', index)
                continue
            key = result.get('cache_key')
            keys.add(key)
            issues.require(key == expected_key, 'result_job_cache_key_mismatch', index)
            issues.require(all(result.get(k) == v for k, v in job['meta'].items()),
                           'result_job_metadata_mismatch', index)
            count = result.get('iterations', 0)
            reported += count
            issues.require(count == iterations, 'result_iterations_mismatch', index)
            issues.require(len(result.get('dps_samples', [])) == iterations,
                           'result_sample_count_mismatch', index)
            origin = result.get('cache_origin')
            origins[str(origin)] += 1
            if origin not in ORIGINS or not isinstance(key, str) or not re.fullmatch('[0-9a-f]{64}', key):
                issues.add('invalid_cache_origin_or_key', index)
                continue
            expected_directory = (root / 'cache' / origin / 'native' / key[:2] / key).resolve()
            actual_directory = Path(result.get('cache_directory', '')).resolve()
            issues.require(actual_directory == expected_directory, 'cache_directory_mismatch', index)
            cache_path = str(expected_directory)
            if origin == STAGE:
                receipt = ledger.get(cache_path)
            else:
                if cache_path not in external:
                    external[cache_path] = audit_receipt(cache_path)
                receipt = external[cache_path]
            if not receipt or receipt['status'] != 'verified_completed':
                issues.add('cache_receipt_not_verified', {'row': index, 'path': cache_path,
                                                         'status': receipt.get('status') if receipt else 'not_in_ledger'})
                continue
            issues.require(receipt['binary_sha256'] == protocol['binary_sha256'], 'receipt_binary_mismatch', index)
            issues.require(receipt['verified_physical_battles'] == iterations, 'receipt_iterations_mismatch', index)
            issues.require(receipt['output_sha256'] == result.get('output_sha256'), 'result_receipt_output_hash_mismatch', index)
        digest.update(b']')
        row.update(jobs_file_sha256=job_meta.get('_raw_sha256'), results_sha256=result_meta.get('_raw_sha256'),
                   canonical_jobs_sha256=digest.hexdigest(), archived_jobs=job_count, logical_rows=result_count,
                   missing_rows=missing_rows, requested_iterations_from_jobs=requested,
                   logical_iterations_from_results=reported, unique_successful_cache_keys=len(keys),
                   cache_origins=dict(origins), recorded_errors=result_meta.get('errors'))
        issues.require(isinstance(result_meta.get('errors'), list), 'missing_or_invalid_results_errors_field')
        issues.require(not result_meta.get('errors'), 'recorded_run_errors', result_meta.get('errors'))
        issues.require(digest.hexdigest() == protocol['jobs_sha256'], 'jobs_canonical_hash_mismatch')
        issues.require(job_count == result_count == protocol['logical_cells'], 'logical_row_count_mismatch')
        issues.require(requested == reported == protocol['requested_battles'], 'logical_battle_count_mismatch')
    except Exception as exc:
        issues.add('snapshot_exception', str(exc))
    changed = [str(p) for p in watched if signature(p) != before[str(p)]]
    issues.require(not changed, 'run_files_changed_during_snapshot', changed)
    row.update(validation_error_count=sum(issues.counts.values()), validation_error_counts=dict(issues.counts),
               validation_errors=issues.examples, archive_verified=not issues.counts)
    return row


def snapshots(root, ledger, external):
    physical, analyses = [], []
    for path in sorted((root / 'runs' / STAGE).glob('*/PROTOCOL.json')):
        try:
            protocol, protocol_hash = read(path)
            hints = {'jobs_sha256', 'logical_cells', 'requested_battles'} & protocol.keys()
            if 'binary_sha256' not in protocol and not hints and not (path.parent / 'JOBS.json').exists() and not (path.parent / 'native.frozen').exists():
                progress = path.parent / 'PROGRESS.json'
                analyses.append({'run': path.parent.name, 'kind': 'analysis_only',
                                 'protocol_sha256': protocol_hash, 'protocol': protocol,
                                 'progress': read(progress)[0] if progress.exists() else None,
                                 'physical_calls_added': 0, 'physical_battles_added': 0,
                                 'status': 'excluded_from_native_completion_check'})
                continue
            print(json.dumps({'audit_stage': 'archive', 'run': path.parent.name}), flush=True)
            physical.append(native_snapshot(root, path, protocol, protocol_hash, ledger, external))
        except Exception as exc:
            physical.append({'run': path.parent.name, 'kind': 'unclassified_protocol_error',
                             'archive_verified': False, 'validation_error_count': 1,
                             'validation_errors': [{'kind': 'protocol_read_error', 'detail': str(exc)}]})
    return physical, analyses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=24)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    root, started = setup_paths(), datetime.now(timezone.utc)
    folder = root / 'runs' / STAGE / ('audit-' + started.strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir()
    cache = root / 'cache' / STAGE / 'native'
    before = directories(cache)
    protocols_before = sorted(str(p) for p in (root / 'runs' / STAGE).glob('*/PROTOCOL.json'))
    states = Counter()
    contexts, binaries = defaultdict(lambda: {'calls': 0, 'battles': 0}), defaultdict(lambda: {'calls': 0, 'battles': 0})
    problems, retained, external = [], {}, {}
    calls = battles = 0
    ledger = folder / 'CACHE_LEDGER.jsonl.gz'
    with gzip.open(ledger, 'wt') as stream, ProcessPoolExecutor(max_workers=args.workers) as pool:
        for index, row in enumerate(pool.map(audit_receipt, before, chunksize=64), 1):
            stream.write(json.dumps(row, sort_keys=True) + '\n')
            states[row['status']] += 1
            retained[str(Path(row['path']).resolve())] = row
            if row['status'] != 'verified_completed':
                problems.append(row)
                continue
            calls += 1
            count = row['verified_physical_battles']
            battles += count
            binaries[row['binary_sha256']]['calls'] += 1
            binaries[row['binary_sha256']]['battles'] += count
            for cls, race in row['contexts']:
                contexts[cls + '/' + race]['calls'] += 1
                contexts[cls + '/' + race]['battles'] += count
            if index % 10000 == 0:
                print(json.dumps({'audit_stage': 'physical_receipts', 'completed': index,
                                  'total': len(before)}), flush=True)
    runs, analyses = snapshots(root, retained, external)
    external_path = folder / 'EXTERNAL_REUSE_LEDGER.jsonl.gz'
    with gzip.open(external_path, 'wt') as stream:
        for row in external.values():
            stream.write(json.dumps(row, sort_keys=True) + '\n')
    analysis_path = folder / 'ANALYSIS_PROTOCOL_LEDGER.json'
    atomic_json(analysis_path, {'records': analyses, 'scope': 'Analysis bookkeeping; no combat counts or solver-success inference.'})
    changed_receipts = []
    all_receipts = {**retained, **external}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for path, current in zip(all_receipts, pool.map(receipt_signature, all_receipts)):
            if current != all_receipts[path]['receipt_signature']:
                changed_receipts.append(path)
    after = directories(cache)
    protocols_after = sorted(str(p) for p in (root / 'runs' / STAGE).glob('*/PROTOCOL.json'))
    pending = [r['run'] for r in runs if not r.get('archive_verified', False)]
    external_problems = [r for r in external.values() if r['status'] != 'verified_completed']
    complete = (before == after and protocols_before == protocols_after and not changed_receipts
                and not pending and not problems and not external_problems)
    result = {'schema': 2, 'started_utc': started.isoformat(), 'finished_utc': datetime.now(timezone.utc).isoformat(),
              'snapshot_complete_and_quiescent': complete, 'native_calls': calls, 'physical_battles': battles,
              'cache_states': dict(states), 'failed_invocations': states['failed_invocation'],
              'incomplete_invocations': states['incomplete'], 'audit_errors': states['audit_error'],
              'pending_runs': pending, 'cache_listing_changed': before != after,
              'protocol_listing_changed': protocols_before != protocols_after,
              'changed_receipts_after_validation': changed_receipts,
              'problems': problems, 'external_reuse_problems': external_problems, 'run_snapshots': runs,
              'analysis_protocol_count': len(analyses), 'analysis_ledger_path': str(analysis_path),
              'analysis_ledger_sha256': file_hash(analysis_path), 'external_reuse_receipts': len(external),
              'external_reuse_ledger_path': str(external_path), 'external_reuse_ledger_sha256': file_hash(external_path),
              'by_context': dict(contexts), 'by_binary_sha256': dict(binaries), 'ledger_path': str(ledger),
              'ledger_sha256': file_hash(ledger), 'auditor_sha256': file_hash(Path(__file__)),
              'shared_validator_sha256': file_hash(SOURCE_ROOT / 'scripts/audit_r2_native.py'),
              'counting': 'Each distinct verified retained R4 physical binary+full-input cache receipt once. R2/R3 reuse is independently verified in a separate ledger and adds zero R4 calls/battles. Logical pool/method/trajectory incidences and analysis protocols add zero physical battles.',
              'preserved_analysis_failure': 'world-smoke-v1 initially compared Go map action arrays positionally; all7 native calls succeeded. The corrected canonical comparison and diagnosis are retained. This is not a failed engine invocation.',
              'limits': 'Counts retained successful physical receipts, not unrecoverable historical retries: the runner can overwrite earlier failed invocation receipts. Input-file discovery cannot recover orphan/lost attempts. Quiescence checks directory sets and file size/mtime/inode signatures, not a filesystem transaction. Raw output hashes/iteration counts are verified; numerical summary metrics are not independently rederived. Only Human/Orc Warrior coverage; ecological/solver success is separate.'}
    atomic_json(folder / 'AUDIT.json', result)
    atomic_json(root / 'artifacts' / STAGE / 'INDEPENDENT_NATIVE_AUDIT.json', result)
    print(json.dumps({k: result[k] for k in ['snapshot_complete_and_quiescent', 'native_calls',
          'physical_battles', 'failed_invocations', 'incomplete_invocations', 'audit_errors', 'pending_runs']}, indent=2))
    if args.require_complete and not complete:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
