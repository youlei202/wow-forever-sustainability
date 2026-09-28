"""Summarize completed campaign resources and preserved unsuccessful outcomes."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(root):
    root = Path(root)
    status = read(root / 'CAMPAIGN_STATUS.json')
    complete = read(root / 'benchmark/PRIMARY_ALL_COMPLETE.json')
    if complete['status'] != 'COMPLETE':
        raise ValueError('Primary workflows incomplete')
    native = []
    for name in ('dev256', 'dev256-v2', 'predict1024', 'confirm16384'):
        record = read(root / 'batches' / name / 'PROGRESS.json')
        if name == 'dev256':
            native.append({'batch': name, 'infrastructure_attempts': 512, 'actual_native_starts': 0,
                           'completed_battles': 0, 'status': 'PRE_EXECUTION_DEPENDENCY_FAILURE',
                           'original_receipt_preserved': True, 'correction': 'native/DEV256_FAILURE_ERRATUM.json'})
        else:
            native.append({'batch': name, 'actual_native_starts': record['new_calls_this_invocation'],
                           'completed_battles': record['new_battles_this_invocation'],
                           'failed_inputs': record['failed_inputs'], 'cache_hits': record['cache_hits_this_invocation'],
                           'wall_seconds': record['elapsed_seconds_this_invocation'],
                           'system_memory_snapshot_bytes': record['memory_current'], 'status': record['status']})
    benchmark = []
    negative = []
    for name in complete['suites']:
        folder = root / 'benchmark' / name
        index = read(folder / 'JOB_INDEX.json')
        aggregate = read(folder / 'RESULTS_AGGREGATE.json')
        rows = []
        processes = []
        for entry in index:
            directory = folder / entry['job_hash']
            if (directory / 'RESULT.json').exists():
                result = read(directory / 'RESULT.json')
                result_source = directory / 'RESULT.json'
            else:
                missing = next((v for v in aggregate if v['status'] == 'NOT_RUN'
                                and v['instance_id'] == entry['instance_id'] and v['method'] == entry['method']), None)
                if missing is None:
                    raise FileNotFoundError(f'Executed job is missing its result receipt: {directory}')
                result = {**missing, 'solver_seed': entry.get('solver_seed', 0)}
                result_source = folder / 'RESULTS_AGGREGATE.json'
            rows.append(result)
            if (directory / 'PROCESS.json').exists():
                processes.append(read(directory / 'PROCESS.json'))
            if result['status'] not in ('YES', 'NO', 'COMPLETE'):
                negative.append({'evidence': 'exact_computational', 'unit': name + '/' + entry['instance_id'],
                                 'method': entry['method'], 'status': result['status'],
                                 'denominator': len(index), 'reason': result.get('reason', result.get('error', '')),
                                 'detail': str(result_source)})
        benchmark.append({'suite': name, 'registered_jobs': len(rows), 'attempts': sum(r['status'] != 'NOT_RUN' for r in rows),
                          'status_counts': dict(Counter(r['status'] for r in rows)),
                          'primary_seed_zero_attempts': sum(r.get('solver_seed', 0) == 0 and r['status'] != 'NOT_RUN' for r in rows),
                          'measured_method_seconds_sum': sum(r.get('method_elapsed_seconds') or 0 for r in rows),
                          'measured_self_cpu_seconds_sum': sum((r.get('self_user_cpu_seconds') or 0) + (r.get('self_system_cpu_seconds') or 0) for r in rows),
                          'sampled_process_peak_rss_bytes_max': max([r.get('peak_process_tree_rss_bytes', 0) for r in processes] or [0]),
                          'durable_archive_seconds_sum': sum(r.get('durable_archive_seconds', 0) for r in processes),
                          'startup_seconds_sum': sum(r.get('startup_seconds', 0) or 0 for r in processes),
                          'query_records_processed': sum(r.get('queries_answered', 0) for r in rows),
                          'protocol_sha256': sha(folder / 'PROTOCOL_FROZEN.json')})
    for row in read(root / 'native/confirmation-v1/NATIVE_DECISIONS.json'):
        if row['confidence_status'] != 'YES' or (row.get('frozen_prediction_witness') and not row['prediction_witness_confidence_check']['valid']):
            negative.append({'evidence': 'fresh_native', 'unit': row['world_id'] + '/' + row['variant'] + '/' + row['query_id'],
                             'method': 'simultaneous_finite_event', 'status': row['confidence_status'],
                             'denominator': 128 if row['variant'] == 'base' else 64,
                             'reason': 'Supported exclusion or unresolved decision/construction; see separate witness and fresh-mean fields',
                             'detail': 'native/summary-v2/NEGATIVE_AND_UNRESOLVED.csv'})
    negative.extend([
        {'evidence': 'infrastructure', 'unit': 'copied_reference_paper_run_checks', 'method': 'run_checks.sh', 'status': 'SCRIPT_FAILED_AFTER_SCIENTIFIC_CHECKS', 'denominator': 1, 'reason': 'Mathematical/native subchecks passed; full script failed because pdftotext was absent. The full script is not reported as passing.', 'detail': 'provenance/reference-paper/run_checks.log'},
        {'evidence': 'infrastructure', 'unit': 'dev256', 'method': 'native_runner', 'status': 'PRE_EXECUTION_FAILURE', 'denominator': 512, 'reason': 'psutil missing before Popen; zero engine starts, original incorrect labels corrected by retained erratum', 'detail': 'native/DEV256_FAILURE_ERRATUM.json'},
        {'evidence': 'infrastructure', 'unit': 'test-existence-v1', 'method': 'all_methods', 'status': 'WHOLE_SUITE_EXCLUDED', 'denominator': 1080, 'reason': 'Shared filesystem stalls contaminated outer timing; entire frozen suite rerun under isolated method clock', 'detail': 'benchmark/test-existence-v1/INFRASTRUCTURE_CONTAMINATED.json'},
        {'evidence': 'unexecuted_optional', 'unit': '600s_query_3600s_compile_tier', 'method': 'all_methods', 'status': 'NOT_RUN', 'denominator': '', 'reason': 'Primary 60s decisions and 900s whole-history services completed; no heavy-tier or multi-thread speed claim', 'detail': 'REVIEW.md'},
        {'evidence': 'unresolved_native_hypothesis', 'unit': 'task_projection', 'method': 'paired_contract_comparison', 'status': 'NO_JOINTLY_SUPPORTED_FLIP', 'denominator': 32, 'reason': 'Five base mean flips; none with both opposing answers supported', 'detail': 'native/projection-confirmation-v1/NATIVE_TASK_PROJECTION.csv'},
        {'evidence': 'negative_native_hypothesis', 'unit': 'candidate_expansion', 'method': 'all_registered_nested_menus', 'status': 'ZERO_TRANSITIONS', 'denominator': 64, 'reason': 'All mean and confidence states unchanged after measured optional additions', 'detail': 'native/summary-v2/CANDIDATE_EXPANSION_COMPARISONS.csv'},
    ])
    with (root / 'benchmark/report-final-v2/QUERY_HISTORY_RESULTS.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            counts = json.loads(row['query_status_counts'])
            planned = int(row['registered_queries']) if row['registered_queries'] else None
            processed = int(row['processed_queries']) if row['processed_queries'] else 0
            unresolved = sum(v for k, v in counts.items() if k not in ('YES', 'NO'))
            if unresolved or planned is None or processed < planned or row['interface_complete'] == 'False':
                negative.append({'evidence': 'repeated_query_service', 'unit': row['suite'] + '/' + row['instance_id'],
                                 'method': row['method'], 'status': 'PARTIAL_OR_UNRESOLVED', 'denominator': planned,
                                 'reason': json.dumps({'workflow_status': row['status'], 'processed_status_counts': counts,
                                                       'not_processed': None if planned is None else planned - processed,
                                                       'interface_complete': row['interface_complete']}, sort_keys=True),
                                 'detail': 'data/benchmark/QUERY_HISTORY_RESULTS.csv; QUERY_RESULTS.csv.gz contains every processed query'})
    with (root / 'NEGATIVE_AND_UNRESOLVED.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['evidence', 'unit', 'method', 'status', 'denominator', 'reason', 'detail'])
        writer.writeheader(); writer.writerows(negative)
    now = datetime.now(timezone.utc)
    resources = {'recorded_utc': now.isoformat(), 'start_utc': status['start_utc'], 'deadline_utc': status['deadline_utc'],
                 'cumulative_elapsed_seconds_at_ledger': (now - datetime.fromisoformat(status['start_utc'])).total_seconds(),
                 'limits': {'cpu_tokens': 64, 'native_workers': 48, 'native_threads': 1, 'primary_benchmark_workers': 8,
                            'primary_method_threads': 1, 'native_process_rss_limit_gib': 4,
                            'benchmark_process_rss_limit_gib': 8, 'campaign_memory_soft_gib': 128, 'gpus': 0},
                 'native_batches': native, 'completed_native_calls': sum(v['actual_native_starts'] for v in native),
                 'completed_native_battles': sum(v['completed_battles'] for v in native),
                 'benchmark_suites': benchmark,
                 'accounting_scope': 'Native totals are completed calls/battles from the current invocation of each batch (all successful batches ran once without resume). Measured primary computational attempts and only recorded resource values are summed; NOT_RUN is retained separately. Development/audit scripts and excluded infrastructure suites consume campaign elapsed time but are not included in primary CPU sums. Process RSS peaks are sampled, and system memory records are snapshots, not a continuous campaign peak. CPU sums are not aggregate host usage.',
                 'unexecuted': ['optional 600-second decisions', 'optional 3600-second compilation/history tier', 'multi-thread secondary solver timing', 'alternative-policy native validation', 'new independent physical sensitivity confirmation'],
                 'new_alpha': {'main_spent': '.04', 'reserved_unspent': '.01'}, 'paid_api_calls': 0, 'public_pushes': 0}
    write(root / 'RESOURCE_USE.json', resources)
    manifest = {'model': 'finite two-slot unrestricted-helper completion; all activated rows cap-safe; all selected sources retained',
                'single_query_methods': ['reference Python conflict-cover/support deletion', 'direct CP-SAT exact rank model', 'incremental SAT/PB exact threshold chain'],
                'repeated_query_methods': ['reference_fresh', 'reference_cached', 'reference_interface', 'sat_incremental', 'sat_interface', 'sat_maximal_cache'],
                'shared_information': 'Identical full exact rational response tables, history, targets, weights, thresholds and prescribed y where applicable',
                'cost_scope': 'In-memory service: parsing, model build, solve, verification, antichain processing, interface serialization/reload, query recording. Common library preparation and durable NAS archival are measured separately.',
                'query_seconds': 60, 'history_seconds': 900, 'interface_compile_allocation_seconds': 720,
                'compile_allocation_scope': '720 seconds for search/enumeration; measured compilation also includes output postprocessing and may exceed that allowance. All work is charged within the common 900-second history budget.',
                'incomplete_interface': 'Verified kernels may answer YES; absence is UNKNOWN until compilation is complete',
                'sat_seed_semantics': 'Deterministic repeat label; installed Glucose4 has no portable random-seed parameter',
                'cp_sat_seed_semantics': 'Actual CP-SAT random_seed; balanced three-seed subset',
                'primary_source_hashes': {name: read(root / 'benchmark' / name / 'PROTOCOL_FROZEN.json')['source_hashes'] for name in complete['suites']},
                'confirmation_source_hashes': read(root / 'PROTOCOL_FROZEN.json')['source_hashes'],
                'claims_not_supported': ['general specialised-solver superiority', 'always compact maximal interfaces', 'all release orders or bounded-cardinality completion', 'distribution-free paired-t coverage']}
    write(root / 'METHODS_MANIFEST.json', manifest)
    print(json.dumps({'status': 'COMPLETE', 'native_calls': resources['completed_native_calls'], 'native_battles': resources['completed_native_battles'], 'primary_attempts': sum(r['attempts'] for r in benchmark), 'negative_summary_rows': len(negative)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    build(parser.parse_args().run_root)
