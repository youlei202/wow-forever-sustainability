#!/usr/bin/env python3
"""Independently count physical native executions, without counting cache reuse.

Read each physical cache receipt once; verify the raw compressed engine result
against its saved hash and iteration count. Bridge battles outside the cache are
an explicit six-invocation ledger. This script never changes the main receipt.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

from wowfs.paths import SOURCE_ROOT, atomic_json, canonical_hash, setup_paths


def sha(data): return hashlib.sha256(data).hexdigest()


def read(path):
    data = path.read_bytes()
    return json.loads(data), sha(data)


def directories(cache):
    command = ['rg', '--files', '-g', 'input.json', str(cache)]
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode not in (0,1): raise RuntimeError(proc.stderr)
    return sorted({str(Path(p).parent) for p in proc.stdout.splitlines()})


def contexts(input_data):
    request = input_data.get('request', input_data)
    return sorted({(str(p.get('class','unknown')), str(p.get('race','unknown')))
                   for party in request['raid']['parties'] for p in party['players']})


def audit_cache(name):
    directory = Path(name)
    record = {'scope':'cache', 'cache_key':directory.name, 'path':name,
              'status':'incomplete', 'verified_physical_battles':0}
    try:
        input_data, record['input_sha256'] = read(directory/'input.json')
        record['requested_physical_battles'] = input_data['request']['simOptions']['iterations']
        record['contexts'] = contexts(input_data)
        if not (directory/'invocation.json').exists():
            record['incomplete_reason'] = 'input saved but no completed invocation receipt'
            return record
        invocation, record['invocation_sha256'] = read(directory/'invocation.json')
        record['returncode'] = invocation['returncode']
        record['binary_sha256'] = invocation['binary_sha256']
        if canonical_hash({'binary':invocation['binary_sha256'],'input':input_data}) != directory.name:
            raise ValueError('input/binary cache-key hash mismatch')
        if invocation['returncode'] != 0:
            record['status'] = 'failed_invocation'
            record['stderr'] = invocation['stderr']
            if (directory/'output.json').exists():
                failed, record['failed_output_sha256'] = read(directory/'output.json')
                record['reported_completed_iterations_in_failure'] = failed.get('iterationsDone')
                record['native_error'] = failed.get('error')
            return record
        if not (directory/'summary.json').exists():
            record['incomplete_reason'] = 'successful process receipt but validation/archiving not finished'
            return record
        summary, record['summary_sha256'] = read(directory/'summary.json')
        with gzip.open(directory/'output.json.gz','rb') as f: raw = f.read()
        record['output_sha256'] = sha(raw)
        if record['output_sha256'] != summary['output_sha256']:
            raise ValueError('raw engine output SHA-256 differs from saved summary')
        output = json.loads(raw)
        count = int(output['iterationsDone'])
        if output.get('error'):
            raise ValueError(f'raw native output error: {output["error"]}')
        if count != record['requested_physical_battles'] or count != summary['iterations']:
            raise ValueError('requested/raw/summary physical iteration counts differ')
        samples = output['raidMetrics']['parties'][0]['players'][0]['dps']['allValues']
        if len(samples) != count:
            raise ValueError('raw per-iteration DPS sample count differs')
        record['verified_physical_battles'] = count
        record['status'] = 'verified_completed'
    except Exception as exc:
        record['status'] = 'audit_error'
        record['audit_error'] = str(exc)
    return record


def audit_bridge(root):
    rows = []
    for group, names in [('native-smoke', ['ordinary','effect','upstream','throughput']),
                         ('mechanism-smoke', ['cd0','cd2'])]:
        for name in names:
            directory = root/'runs/r2-discovery'/group
            input_data, ih = read(directory/f'{name}.input.json')
            output, oh = read(directory/f'{name}.output.json')
            request = input_data.get('request', input_data)
            expected = request['simOptions']['iterations']
            count = output['iterationsDone']
            if count != expected or output.get('error'):
                raise ValueError(f'incomplete bridge battle {group}/{name}')
            rows.append({'scope':'bridge_outside_cache','case':f'{group}/{name}',
                         'status':'verified_completed','input_sha256':ih,'output_sha256':oh,
                         'input_path':str(directory/f'{name}.input.json'),
                         'output_path':str(directory/f'{name}.output.json'),
                         'requested_physical_battles':expected,'verified_physical_battles':count,
                         'contexts':contexts(input_data),
                         'binary_capture_note': 'Initial native wrapper smoke predates a gofmt-only rebuild; original executable bytes were not retained. Upstream CLI and mechanism smoke executable hashes are separately recorded in integration validation.'})
    return rows


def run_snapshots(root):
    result = []
    for path in sorted((root/'runs/r2-discovery').glob('*/PROTOCOL.json')):
        protocol, ph = read(path)
        progress_path = path.parent/'PROGRESS.json'
        progress = read(progress_path)[0] if progress_path.exists() else {'status':'not_yet_reported'}
        row = {'run':path.parent.name,'protocol_sha256':ph,'progress':progress}
        for field in ('logical_cells','requested_physical_battles','binary_sha256'):
            if field in protocol: row[field] = protocol[field]
        results_path = path.parent/'RESULTS.json'
        if results_path.exists():
            results, rh = read(results_path)
            row['results_sha256'] = rh
            row['recorded_errors'] = results.get('errors',[])
            row['logical_rows'] = len(results.get('rows',[]))
            row['missing_logical_rows'] = sum(r is None for r in results.get('rows',[]))
            row['unique_completed_cache_keys'] = len({r['cache_key'] for r in results.get('rows',[]) if r})
        result.append(row)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=16)
    parser.add_argument('--require-complete',action='store_true')
    args = parser.parse_args()
    root = setup_paths(); cache = root/'cache/r2-discovery/native'
    started = datetime.now(timezone.utc)
    audit_dir = root/'runs/r2-discovery'/('native-audit-'+started.strftime('%Y%m%dT%H%M%S%fZ'))
    audit_dir.mkdir(parents=True)
    before = directories(cache)
    state_counts = Counter(); by_context = defaultdict(lambda: {'successful_physical_invocations':0,'physical_battles':0})
    by_binary = defaultdict(lambda: {'successful_physical_invocations':0,'physical_battles':0})
    problems = []; cache_battles = 0
    ledger = audit_dir/'CACHE_LEDGER.jsonl.gz'
    with gzip.open(ledger,'wt') as out, ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(audit_cache,before):
            out.write(json.dumps(row,sort_keys=True)+'\n')
            state_counts[row['status']] += 1
            if row['status'] != 'verified_completed':
                problems.append(row); continue
            cache_battles += row['verified_physical_battles']
            binary = by_binary[row['binary_sha256']]
            binary['successful_physical_invocations'] += 1; binary['physical_battles'] += row['verified_physical_battles']
            for cls,race in row['contexts']:
                c = by_context[(cls,race)]
                c['successful_physical_invocations'] += 1; c['physical_battles'] += row['verified_physical_battles']
    bridge = audit_bridge(root)
    for row in bridge:
        for cls,race in row['contexts']:
            c = by_context[(cls,race)]
            c['successful_physical_invocations'] += 1; c['physical_battles'] += row['verified_physical_battles']
    after = directories(cache)
    snapshots = run_snapshots(root)
    pending_runs = [r['run'] for r in snapshots if r['progress'].get('status') != 'complete']
    recorded_errors = [{'run':r['run'],'errors':r['recorded_errors']} for r in snapshots if r.get('recorded_errors')]
    consistent_complete = before == after and not problems and not pending_runs and not recorded_errors
    context_rows = []
    for (cls,race), counts in sorted(by_context.items()):
        context_rows.append({'class':cls,'race':race,'faction':{'RaceHuman':'Alliance','RaceOrc':'Horde'}.get(race,'unclassified'),
                             **counts,'completed_20_round_sequences':None,
                             'trajectory_status':'not_inferred_from_combat_counts'})
    result = {
        'audit_schema_version':1,'started_utc':started.isoformat(),
        'finished_utc':datetime.now(timezone.utc).isoformat(),
        'snapshot_complete_and_quiescent':consistent_complete,
        'cache_directory_count_at_start':len(before),'cache_directory_count_at_end':len(after),
        'cache_listing_changed':before!=after,'cache_state_counts':dict(state_counts),
        'cache_verified_invocations':state_counts['verified_completed'],
        'cache_verified_physical_battles':cache_battles,
        'bridge_verified_invocations':len(bridge),
        'bridge_verified_physical_battles':sum(r['verified_physical_battles'] for r in bridge),
        'total_verified_successful_native_invocations':state_counts['verified_completed']+len(bridge),
        'total_verified_physical_battles':cache_battles+sum(r['verified_physical_battles'] for r in bridge),
        'failed_invocation_receipts':state_counts['failed_invocation'],
        'incomplete_physical_entries':state_counts['incomplete'],
        'audit_errors':state_counts['audit_error'],'problems':problems,
        'by_cache_binary_sha256':dict(by_binary),'executed_contexts':context_rows,
        'bridge_ledger':bridge,'run_snapshots':snapshots,'pending_runs':pending_runs,
        'recorded_run_errors':recorded_errors,
        'counting_rule':'One verified invocation receipt per distinct binary/input cache key plus six explicit uncached bridge invocations. Logical method decisions, cache hits and resumed references add no battles.',
        'failure_history_limit':'The runner keeps one invocation receipt per cache key; a retry may replace an earlier failed receipt. Frozen run errors are included. This audit does not invent a count for unretained attempts.',
        'context_denominator_note':'All current audited battles have one player. Context rows count only actually executed native combat; sequence completion and breadth targets require separate trajectory analysis.',
        'ledger_path':str(ledger),'ledger_sha256':sha(ledger.read_bytes()),
        'auditor_source_sha256':sha(Path(__file__).read_bytes()),
    }
    atomic_json(audit_dir/'AUDIT.json',result)
    latest = root/'artifacts/r2-discovery/latest/INDEPENDENT_NATIVE_AUDIT.json'
    atomic_json(latest,result)
    print(json.dumps({k:result[k] for k in ('snapshot_complete_and_quiescent','total_verified_successful_native_invocations','total_verified_physical_battles','failed_invocation_receipts','incomplete_physical_entries','audit_errors','pending_runs','ledger_path')},indent=2))
    if args.require_complete and not consistent_complete: raise SystemExit(2)


if __name__ == '__main__': main()
