"""Candidate figures, tables and review packaging for the minimal-interface audit.

All empirical counts come from exhaustive audit outputs. This does not modify
the manuscript, execute battles, or measure algorithmic speed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile


def read(path):
    return json.loads(Path(path).read_text())


def csv_read(path):
    with Path(path).open(newline='') as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def csv_write(path, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def promote(run):
    sources = {
        'native': ['TARGET_INTERFACE_AUDIT.csv', 'TARGET_QUERY_EQUIVALENCE.json', 'LOW_ORDER_ABLATION.csv',
                   'MINIMAL_OBSTRUCTIONS.jsonl', 'CERTIFIED_LOW_ORDER_MISSES.csv', 'OBSTRUCTION_ATTRIBUTION.csv',
                   'PROJECTION_COMPRESSION_SUMMARY.md', 'NATIVE_SUMMARY.json'],
        'druid': ['DRUID_TRIPLE_RECHECK.json'],
        'theory/v2': ['UNIVERSAL_CONSTRUCTION_CHECKS.json', 'SEMANTIC_MINIMALITY_CHECKS.json', 'SYMBOLIC_VS_ANTICHAIN.csv'],
    }
    for parent, names in sources.items():
        for name in names:
            destination = run / name
            if destination.exists() and sha(destination) != sha(run / parent / name):
                raise ValueError('Would overwrite a different promoted output: ' + name)
            if not destination.exists():
                shutil.copyfile(run / parent / name, destination)
    for name in ['TARGET_ANTICHAINS', 'TARGET_WITNESSES']:
        if not (run / name).exists():
            shutil.copytree(run / 'native' / name, run / name)


def figures(run):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                         'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
                         'axes.spines.top': False, 'axes.spines.right': False})
    out = run / 'figures'; out.mkdir(exist_ok=True)
    rows = csv_read(run / 'LOW_ORDER_ABLATION.csv')
    strata = [('primary_base', '16 registered base menus'), ('primary_expanded', '8 nested expanded menus')]
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 6), layout='constrained')
    colors = ['#155e75', '#b45309', '#64748b']
    for col, (stratum, title) in enumerate(strata):
        subset = [x for x in rows if x['stratum'] == stratum]
        x = list(range(1, 4))
        total = lambda field: [sum(int(z[field]) for z in subset if int(z['order_r']) == r) for r in x]
        misses, blocked, unresolved = map(total, ['certified_false_positive_count', 'unknown_blocked_cases',
                                                'unresolved_full_targets_with_no_low_order_NO'])
        ax = axes[0, col]
        ax.plot(x, misses, 'o-', color=colors[0], label='Certified missed NO decisions')
        for r, value in zip(x, misses):
            ax.annotate(str(value), (r, value), xytext=(4, 6), textcoords='offset points')
        ax.set_title(title)
        ax.set_ylabel('Certified false-positive target decisions')
        ax.set_ylim(bottom=-max(0.1, max(misses, default=0) * .04))
        if stratum == 'primary_base':
            druid = [z for z in subset if z['world_id'] == 'co_druid_passive_resources__validation_02']
            d = [sum(int(z['certified_false_positive_count']) for z in druid if int(z['order_r']) == r) for r in x]
            ax.plot(x, d, 's--', color=colors[1], label='Druid validation-02')
            ax.annotate('2 minimal triples; 3 missed targets', (2, d[1]), xytext=(-106, 26),
                        textcoords='offset points', arrowprops={'arrowstyle': '->', 'color': colors[1]}, color=colors[1])
        ax.legend(fontsize=7, loc='upper right')
        ax = axes[1, col]
        ax.plot(x, blocked, 'o-', color=colors[1], label='Full NO; UNKNOWN subset blocks certification')
        ax.plot(x, unresolved, 's--', color=colors[2], label='Full UNKNOWN; no low-order NO')
        for r, value in zip(x, blocked):
            ax.annotate(str(value), (r, value), xytext=(4, 6), textcoords='offset points', fontsize=8)
        ax.set_ylabel('Unresolved target decisions')
        ax.legend(fontsize=6.6, loc='upper right')
        denominator = sum(int(z['queried_target_pool_size']) for z in subset if int(z['order_r']) == 1)
        ax.set_title(f'Complete target powersets: {denominator:,} queries', fontsize=8)
        for ax in axes[:, col]:
            ax.set_xticks(x); ax.set_xlabel('Retained target order r'); ax.grid(axis='y', alpha=.2)
    fig.suptitle('Low-order information loss on frozen native response events', fontsize=12)
    for extension in ['pdf', 'svg', 'png']:
        fig.savefig(out / f'low_order_ablation.{extension}', dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.1), layout='constrained')
    for ax in axes:
        ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    axes[0].text(.5, .93, 'Abstract construction', ha='center', fontsize=12)
    axes[0].text(.5, .66, 'Every target set of size ≤ r: YES', ha='center', color=colors[0], fontsize=11)
    axes[0].annotate('', xy=(.5, .34), xytext=(.5, .56), arrowprops={'arrowstyle': '->'})
    axes[0].text(.5, .24, 'One minimal obstruction of size r+1: NO', ha='center', color=colors[1], fontsize=10)
    axes[0].text(.5, .08, 'Mathematical construction; no native samples', ha='center', fontsize=8)
    ax = axes[1]
    ax.text(.5, .93, 'Native Druid validation-02', ha='center', fontsize=12)
    pts = np.asarray([[.5, .8], [.16, .26], [.84, .26]])
    for i, j in [(0, 1), (0, 2), (1, 2)]:
        ax.plot(pts[[i, j], 0], pts[[i, j], 1], color=colors[0], lw=1.8)
        mid = (pts[i] + pts[j]) / 2
        ax.text(mid[0], mid[1], 'YES', ha='center', va='center', color=colors[0], bbox={'facecolor': 'white', 'edgecolor': 'none'})
    for label, xy in zip('ABC', pts):
        ax.text(*xy, label, ha='center', va='center', fontsize=12,
                bbox={'boxstyle': 'circle', 'facecolor': 'white', 'edgecolor': colors[0]})
    ax.text(.5, .46, 'ABC\nNO', ha='center', color=colors[1], fontweight='bold')
    ax.text(.5, .08, 'Old-source retention; every physical pair cap-safe', ha='center', fontsize=8)
    for extension in ['pdf', 'svg']:
        fig.savefig(out / f'theory_native_order_gap.{extension}')
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 2.6), layout='constrained'); ax.set_axis_off()
    ax.text(.02, .75, 'Full maximal publications\n{h, x, helper-1}\n{h, x, helper-2}', va='center', fontsize=11)
    ax.annotate('', xy=(.56, .7), xytext=(.36, .7), arrowprops={'arrowstyle': '->'})
    ax.text(.40, .85, 'Project to E={x}', ha='center', fontsize=9)
    ax.text(.63, .7, 'Target antichain\n{{x}}', ha='center', va='center', fontsize=11)
    ax.text(.58, .35, 'Optional witness payload:\n{x} → {h, x, helper-1}', fontsize=10)
    ax.text(.02, .07, 'Abstract semantic illustration. Native E=I\\H gives zero projection merges.', fontsize=9)
    for extension in ['pdf', 'svg']:
        fig.savefig(out / f'target_semantics_witnesses.{extension}')
    plt.close(fig)


def candidate_tables(run):
    out = run / 'tables'; out.mkdir(exist_ok=True)
    rows = csv_read(run / 'OBSTRUCTION_ATTRIBUTION.csv')
    csv_write(out / 'native_minimal_obstruction_inventory_all_contracts.csv', rows)
    primary = [r for r in rows if r['stratum'] in ('primary_base', 'primary_expanded')]
    csv_write(out / 'native_minimal_obstruction_inventory_primary.csv', primary)
    inventory = []
    interfaces = csv_read(run / 'TARGET_INTERFACE_AUDIT.csv')
    for row in interfaces:
        if row['mode'] != 'supported':
            continue
        orders = json.loads(row['certified_obstructions_by_order'])
        inventory.append({k: row[k] for k in ('contract_id', 'stratum', 'world_id', 'variant', 'class_name', 'faction',
                         'target_universe_size', 'full_maximal_count', 'target_maximal_count', 'projection_merge_count',
                         'query_answer_equivalence')} | {
                         'minimum_certified_obstruction_order': min(map(int, orders), default=None),
                         'maximum_certified_obstruction_order': max(map(int, orders), default=None),
                         'certified_obstructions_by_order': row['certified_obstructions_by_order']})
    csv_write(out / 'representation_audit.csv', inventory)
    base = [r for r in inventory if r['stratum'] == 'primary_base']
    lines = ['| Catalogue | Faction | E size | K count = A count (supported) | Certified minimal orders (count) |',
             '|---|---|---:|---:|---|']
    for r in base:
        short = r['world_id'].replace('co_', '').replace('__validation_', ' / ')
        lines.append(f"| {short} | {r['faction']} | {r['target_universe_size']} | {r['full_maximal_count']} | {r['certified_obstructions_by_order']} |")
    return '\n'.join(lines)


def consolidate(run, source):
    """Assemble reporting receipts without changing any component run."""
    import importlib.metadata
    for path in (source / 'docs/minimal-interface-2026-09-27').glob('*.md'):
        shutil.copyfile(path, run / path.name)
    native = read(run / 'native/NATIVE_SUMMARY.json')
    druid = read(run / 'druid/DRUID_TRIPLE_RECHECK.json')
    theory = read(run / 'theory/v2/UNIVERSAL_CONSTRUCTION_CHECKS.json')
    checks = ['FINAL_TESTS.txt', 'INDEPENDENT_NATIVE_REVIEW.json', 'INDEPENDENT_INTEGRATION_REVIEW.json',
              'INDEPENDENT_INTEGRATION_COMPUTATIONS.json', 'HANDOFF_NATIVE_INVENTORY_COMPARISON.json', 'PHASE_D_GATE_REVIEW.json']
    assert native['status'] == druid['status'] == 'PASS'
    assert theory['expected_guarantee_failure_count'] == 0
    assert read(run / 'INPUT_INTEGRITY_AFTER.json')['status'] == 'PASS'
    for name in ['INDEPENDENT_NATIVE_REVIEW.json', 'INDEPENDENT_INTEGRATION_REVIEW.json']:
        assert read(run / 'checks' / name)['status'] == 'PASS'
    gate = {'phase': 'D', 'status': 'not_run', 'activated': False,
            'A_C_correctness_prerequisite': 'PASS_AFTER_PRESERVED_CHECKER_CORRECTION',
            'incremental_prospective_breadth_value_gate_met': False,
            'reason': 'Complete frozen-event ablation, independent original triple reconstruction and additional fixed-tolerance triples address this audit. Additional independent sampling is not justified by a currently necessary evidence gap.',
            'independent_recommendation': 'checks/PHASE_D_GATE_REVIEW.json',
            'prospective_native_outcome': None, 'prospective_selected_catalogues': None,
            'new_native_calls_this_audit': 0, 'new_alpha_this_audit': 0}
    json_write(run / 'PHASE_D_DECISION.json', gate)
    negatives = csv_read(run / 'native/NEGATIVE_AND_UNRESOLVED.csv')
    def negative(kind, status, count, denominator, detail):
        negatives.append(dict(kind=kind, status=status, count=count, denominator=denominator, detail=detail))
    negative('theory_checker_v1', 'FAIL_RETAINED_CORRECTED_V2', 716, 1644,
             '179 malformed random-family inputs from submask enumeration defect; full source/inputs preserved in theory/. Not a theorem counterexample.')
    negative('theory_boundary_eta_at_least_half', 'NO_THEOREM_GUARANTEE', 2, 5,
             'Deterministic corners change family at eta=.50/.51; all five recorded. Uniform draws are separate.')
    proof_rows = druid['saved_two_step_certificate_replay']['comparisons']
    for row in proof_rows:
        if not row['saved_proof_supported']:
            negative('saved_two_step_proof', 'UNRESOLVED_BY_THIS_PROOF', 1, len(proof_rows),
                     f"target={row['target']}; tolerance={row['epsilon']}; original failed sufficient exclusion reproduced; not target YES.")
    negative('unresolved_obligation_attribution', 'UNKNOWN', native['attribution_categories'].get('unresolved attribution', 0),
             native['certified_obstructions'], 'Target answer NO is distinct from unresolved mechanism attribution.')
    negative('missing_inputs_initial_search', 'RESOLVED_BY_USER_SUPPLEMENT', 2, 2,
             'Initial MISSING_ARTIFACTS.json retained; SUPPLEMENTAL_INPUTS.json supersedes missing latest paper/proof status.')
    negative('prospective_native_replication', 'not_run', None, None,
             'Phase D value gate not met. Missing observations are not zero performance.')
    negative('prior_negative_results', 'PRESERVED_IN_FROZEN_INPUT', None, None,
             'Unchanged inputs/review-v2.zip contains NEGATIVE_AND_UNRESOLVED.csv and NATIVE_NEGATIVE_AND_UNRESOLVED.csv, including original solver UNKNOWN and failures.')
    if (run / 'packaging-failures/CANDIDATE_V1_FAILURE.json').exists():
        negative('portable_wrapper_candidate_v1', 'FAIL_RETAINED_CORRECTED_V2', 1, 1,
                 'Compared in-memory integer histogram keys to serialized string keys. Recomputed native summary JSON was byte-identical. Failed wrapper, traceback and archive receipt retained under packaging-failures/.')
    # csv.DictWriter requires a rectangular mapping when keys differ.
    keys = list(dict.fromkeys(k for row in negatives for k in row))
    csv_write(run / 'NEGATIVE_AND_UNRESOLVED.csv', [{k: row.get(k) for k in keys} for row in negatives])
    sources = list((source / 'src/wowfs/experiments').glob('mi_*.py'))
    sources += [source / 'src/wowfs/reporting/mi_report.py']
    sources += [source / 'scripts' / name for name in ['audit_minimal_interface.py', 'recheck_minimal_interface_package.py', 'review_minimal_interface_native.py', 'run_minimal_interface_package_check.sh', 'env.sh']]
    versions = {name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'matplotlib', 'PyYAML', 'pytest']}
    manifest = {'run_id': run.name, 'created_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'Phases A-C deterministic reanalysis; no manuscript edits or new native simulations',
                'preflight': 'PREFLIGHT.json', 'supplement': 'SUPPLEMENTAL_INPUTS.json',
                'input_identity': 'SUPPLEMENTAL_IDENTITY_CHECK.json', 'final_input_integrity': 'INPUT_INTEGRITY_AFTER.json',
                'source_sha256': {str(p.relative_to(source)): sha(p) for p in sources}, 'dependency_versions': versions,
                'phase_configurations': ['native/NATIVE_RUN_CONFIG.json', 'druid/DRUID_RUN_MANIFEST.json', 'theory/v2/CHECKPOINT.json'],
                'phase_D': gate, 'gpu_workers': 0, 'allocated_cpu_equivalents': read(run / 'PREFLIGHT.json')['cpu_allocation'],
                'each_analysis_cpu_workers': 1, 'maximum_concurrent_task_workers': 4, 'native_calls': 0, 'additional_alpha': 0,
                'independent_registered_native_menus': 16, 'primary_contracts': 24, 'posthoc_contracts_counted_separately': 72,
                'complete_target_queries': native['total_target_queries'], 'interface_mode_comparisons': 3 * native['total_target_queries'],
                'frozen_data_policy': 'Original review-v2 and imported paper/proof files unchanged; first failed theory version retained.'}
    json_write(run / 'RUN_MANIFEST.json', manifest)
    receipts = {'status': 'A_C_COMPLETE_WITH_PRESERVED_FAILURES', 'phase_A': 'PASS', 'phase_B': 'PASS',
                'phase_C': 'PASS_CORRECTED_V2', 'phase_C_failed_v1_retained': True, 'phase_D': 'not_run',
                'unit_tests': {'passed': 14, 'output': 'checks/FINAL_TESTS.txt'},
                'component_receipts': ['native/NATIVE_RUN_RECEIPT.json', 'druid/DRUID_RUN_RECEIPTS.json', 'theory/THEORY_RUN_RECEIPT.json'],
                'independent_checks_sha256': {name: sha(run / 'checks' / name) for name in checks},
                'input_integrity': read(run / 'INPUT_INTEGRITY_AFTER.json'),
                'no_new_native_battles': True, 'no_new_alpha': True,
                'actual_archive_recheck': 'Separate immutable sibling ZIP receipt and external PORTABLE_RECHECK.json produced after sealing; see REPRODUCE.md.'}
    json_write(run / 'RUN_RECEIPTS.json', receipts)
    (run / 'requirements-recheck.txt').write_text(''.join(f'{k}=={v}\n' for k, v in versions.items()))


def make_package(run, source):
    """Seal the final review directory and zip it, retaining every failed run."""
    if (run / 'PACKAGE_MANIFEST.json').exists():
        raise FileExistsError('Package already sealed')
    code = run / 'code'; code.mkdir()
    shutil.copytree(source / 'src/wowfs', code / 'wowfs', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (run / 'scripts').mkdir(exist_ok=True)
    for name in ['audit_minimal_interface.py', 'recheck_minimal_interface_package.py', 'review_minimal_interface_native.py', 'run_minimal_interface_package_check.sh', 'env.sh']:
        shutil.copyfile(source / 'scripts' / name, run / 'scripts' / name)
    (run / 'tests').mkdir(exist_ok=True)
    for path in (source / 'tests').glob('*.py'):
        shutil.copyfile(path, run / 'tests' / path.name)
    shutil.copyfile(source / 'pyproject.toml', run / 'pyproject.toml')
    bundle = Path(read(run / 'PREFLIGHT.json')['review_bundle'])
    shutil.copyfile(bundle.with_suffix('.zip'), run / 'inputs/review-v2.zip')
    records = [{'path': str(p.relative_to(run)), 'bytes': p.stat().st_size, 'sha256': sha(p)}
               for p in sorted(run.rglob('*')) if p.is_file()]
    json_write(run / 'PACKAGE_MANIFEST.json', {'files': records, 'scope': 'Content integrity, including failed checks and imported frozen evidence'})
    archive = run.parent / 'WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip'
    if archive.exists():
        raise FileExistsError(archive)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(run.rglob('*')):
            if path.is_file():
                z.write(path, arcname=str(Path(run.name) / path.relative_to(run)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for record in records:
            data = z.read(str(Path(run.name) / record['path']))
            assert hashlib.sha256(data).hexdigest() == record['sha256']
    receipt = {'status': 'PASS', 'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha(archive),
               'files_verified_inside_actual_zip': len(records), 'new_native_battles': 0,
               'finished_utc': datetime.now(timezone.utc).isoformat()}
    json_write(archive.with_suffix('.zip.receipt.json'), receipt)
    print(json.dumps(receipt))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['figures', 'consolidate', 'package'])
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    if args.command == 'figures':
        promote(args.run); figures(args.run)
        (args.run / 'tables/BASE_CATALOGUE_REPRESENTATION.md').parent.mkdir(exist_ok=True)
        (args.run / 'tables/BASE_CATALOGUE_REPRESENTATION.md').write_text(candidate_tables(args.run) + '\n')
    elif args.command == 'consolidate':
        consolidate(args.run, args.source)
    else:
        make_package(args.run, args.source)


if __name__ == '__main__':
    main()
