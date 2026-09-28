"""Exhaustive target semantics and low-order audit on immutable native events.

No simulator or certificate-query service is imported. Paired-t intervals are
reconstructed from compact moments; a separate publication evaluator compiles
their signs and preserves every failed source. Exact arithmetic is cross-checked
against the independent review oracle. Every post-hoc target stays inside the
original all-row/all-pair event. E is fixed as I minus the published history.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import csv
from pathlib import Path
import time

import numpy as np

from wowfs.paths import canonical_hash
from wowfs.experiments.co_native_analysis import finite_bounds, model_from_moments
from wowfs.experiments.co_native_sensitivity import propagate_tolerance
from wowfs.experiments.co_review_check import load_moments, projection, verify_manifest
from wowfs.experiments.co_review_oracle import ExactMaskOracle


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, separators=(',', ':'), sort_keys=True, allow_nan=False).encode()


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    temporary.replace(path)


def bits(indices):
    return sum(1 << int(i) for i in indices)


def members(mask, names):
    return [name for i, name in enumerate(names) if mask >> i & 1]


def maximal(masks):
    result = []
    for mask in sorted(set(masks), key=lambda x: (-x.bit_count(), x)):
        if not any(mask & other == mask for other in result):
            result.append(mask)
    return result


def make_domain(world, moments, variant):
    left = world['base_candidate_indices'] if variant == 'base' else range(len(world['candidates']))
    right = world['base_partner_indices'] if variant == 'base' else range(len(world['partners']))
    names = [f'a{i:02}' for i in left] + [f'x{j}' for j in right]
    index = {v: i for i, v in enumerate(names)}
    pairs = [(i, j) for i in left for j in right]
    source_pairs = [tuple(p) for p in moments['domain']['pairs']]
    rows = [source_pairs.index(pair) for pair in pairs]
    supports = [bits([index[f'a{i:02}'], index[f'x{j}']]) for i, j in pairs]
    history = bits(index[x] for x in world['history'])
    return names, rows, supports, history


def compile_event(world, moments, bounds, rule, variant):
    """Independent mask construction from rebuilt interval arrays, no service."""
    names, rows, supports, history = make_domain(world, moments, variant)
    hrows = [r for r, support in enumerate(supports) if support & history == support]
    weights = list(map(lambda x: Fraction(str(x)), world['task_weights']))
    q = len(weights)
    enough = lambda threshold: [mask for mask in range(1 << q)
                               if sum(weights[t] for t in range(q) if mask >> t & 1) >= Fraction(threshold)]
    compiled = {}
    for mode, endpoint in [('supported', 'lower'), ('possible', 'upper')]:
        cap = bounds['cap_' + endpoint][:, rows]
        retention = bounds['retention_' + endpoint][:, rows][:, :, rows]
        gain = bounds['gain_' + endpoint][:, rows][:, :, rows]
        compiled[mode] = dict(capbad=bits(r for r in range(len(rows)) if min(cap[:, r]) < 0),
            ret_bad=[[bits(d for d in range(len(rows)) if retention[t, r, d] < 0)
                      for r in range(len(rows))] for t in range(q)],
            gain_good=[bits(r for r in range(len(rows)) if all(gain[t, r, h] >= 0 for h in hrows)) for t in range(q)])
    return dict(items=names, row_indices_in_full_table=rows, support_masks=supports,
                history_mask=history,
                query_masks=[bits(names.index(x) for x in query['required']) for query in world['queries']],
                compiled_masks=compiled, enough_retention_mass_masks=enough(rule['retention_mass']),
                enough_gain_mass_masks=enough(rule['gain_mass']))


def assess(publication, active, data, supports, n, retention_allowed, gain_allowed):
    """Return all failed source obligations, retaining cap and gain separately."""
    task_masks = [0] * n
    for t, bad in enumerate(data['ret_bad']):
        useful_sources = 0
        todo = active
        while todo:
            low = todo & -todo; todo ^= low; r = low.bit_length() - 1
            if not active & bad[r]:
                useful_sources |= supports[r]
        for i in range(n):
            if useful_sources >> i & 1:
                task_masks[i] |= 1 << t
    failed = bits(i for i in range(n) if publication >> i & 1 and task_masks[i] not in retention_allowed)
    cap = bool(active & data['capbad'])
    gain = bits(t for t, good in enumerate(data['gain_good']) if active & good) in gain_allowed
    reason = 'cap' if cap else 'retention' if failed else 'gain' if not gain else 'valid'
    return dict(cap_failed=cap, gain_satisfied=gain, failed_sources=failed, reason=reason)


def enumerate_publications(c):
    names = c['items']; history = c['history_mask']; supports = c['support_masks']
    optional = [i for i in range(len(names)) if not history >> i & 1]
    result = []
    for target_mask in range(1 << len(optional)):
        p = history | bits(optional[k] for k in range(len(optional)) if target_mask >> k & 1)
        active = bits(r for r, support in enumerate(supports) if support & p == support)
        result.append(dict(publication=p, target_mask=target_mask, active_rows=active,
            modes={mode: assess(p, active, data, supports, len(names), set(c['enough_retention_mass_masks']),
                               set(c['enough_gain_mass_masks'])) for mode, data in c['compiled_masks'].items()}))
    initial = {mode: 'cap' if result[0]['modes'][mode]['cap_failed'] else
               'retention' if result[0]['modes'][mode]['failed_sources'] else 'valid'
               for mode in c['compiled_masks']}
    return result, initial


def closure(valid_projections, n):
    family = [False] * (1 << n)
    for mask in valid_projections:
        family[mask] = True
    for i in range(n):
        for mask in range(1 << n):
            if not mask >> i & 1:
                family[mask] |= family[mask | 1 << i]
    return family


def subset_minimum(values, n):
    result = list(values)
    for i in range(n):
        for mask in range(1 << n):
            if mask >> i & 1:
                result[mask] = min(result[mask], result[mask ^ (1 << i)])
    return result


def low_order_analysis(exact, statuses, n, *, exact_initial_valid=True):
    """The empty target is checked, including the no-gaining-publication case."""
    inf = n + 1
    bad = subset_minimum([mask.bit_count() if not ok else inf for mask, ok in enumerate(exact)], n)
    no = subset_minimum([mask.bit_count() if status == 'NO' else inf for mask, status in enumerate(statuses)], n)
    nonyes = subset_minimum([mask.bit_count() if status != 'YES' else inf for mask, status in enumerate(statuses)], n)
    exact_minimal = []
    certified = []
    for mask in range(1 << n):
        predecessors = [mask ^ (1 << i) for i in range(n) if mask >> i & 1]
        if exact_initial_valid and not exact[mask] and all(exact[p] for p in predecessors):
            exact_minimal.append(mask)
        if statuses[mask] == 'NO' and all(statuses[p] == 'YES' for p in predecessors):
            certified.append(mask)
    rows = []
    misses = []
    for r in range(1, n + 1):
        certified_misses = [m for m in range(1 << n) if statuses[m] == 'NO' and nonyes[m] > r]
        # No observed low-order NO refutes these full NOs, but a low-order UNKNOWN
        # prevents certification. These cases are never counted as misses.
        blocked = [m for m in range(1 << n) if statuses[m] == 'NO' and no[m] > r and nonyes[m] <= r]
        unknown_full = [m for m in range(1 << n) if statuses[m] == 'UNKNOWN' and no[m] > r]
        rows.append(dict(order_r=r,
            exact_false_positive_count=sum(not exact[m] and bad[m] > r for m in range(1 << n)) if exact_initial_valid else None,
            certified_false_positive_count=len(certified_misses), unknown_blocked_cases=len(blocked),
            unresolved_full_targets_with_no_low_order_NO=len(unknown_full),
            queried_target_pool_size=1 << n))
        misses += [dict(order_r=r, target_mask=m) for m in certified_misses]
    return exact_minimal, certified, rows, misses


def projected_interface(valid, names, history):
    target_names = [name for i, name in enumerate(names) if not history >> i & 1]
    target_index = {name: i for i, name in enumerate(target_names)}
    project = lambda p: bits(target_index[name] for name in members(p & ~history, names))
    kernels = maximal(valid)
    projected = maximal(project(p) for p in kernels)
    witnesses = []
    for mask in projected:
        preimages = [p for p in kernels if project(p) == mask]
        witness = min(preimages, key=lambda p: (p.bit_count(), p))
        witnesses.append(dict(target_mask=mask, target=members(mask, target_names), publication=members(witness, names),
                              publication_mask=witness, merged_full_maximal_count=len(preimages)))
    k_payload = [members(p, names) for p in kernels]
    a_payload = [members(p, target_names) for p in projected]
    w_payload = [dict(target=w['target'], publication=w['publication']) for w in witnesses]
    return dict(full_maximal_masks=kernels, maximal_target_masks=projected, target_names=target_names,
                witnesses=witnesses, full_maximal_count=len(kernels), target_maximal_count=len(projected),
                projection_merge_count=sum(w['merged_full_maximal_count'] - 1 for w in witnesses),
                serialized_bytes_full=len(encoded(k_payload)), serialized_bytes_targets=len(encoded(a_payload)),
                serialized_bytes_targets_with_witnesses=len(encoded(w_payload)))


def status_from_membership(lower, upper, initial, complete=True):
    if initial['possible'] != 'valid':
        return 'INVALID_INITIAL'
    if initial['supported'] != 'valid':
        return 'UNKNOWN_INITIAL'
    if lower:
        return 'YES'
    if complete and not upper:
        return 'NO'
    return 'UNKNOWN'


def attribution(target_mask, c, publications, target_names, initial):
    names = c['items']; h = c['history_mask']; d = bits(names.index(x) for x in members(target_mask, target_names))
    containing = [row for row in publications if row['publication'] & d == d]
    groups = ('history', 'targets', 'helpers')
    scopes = ['all', 'none', 'drop_cap'] + [prefix + group for group in groups for prefix in ('only_', 'drop_')]
    evidence = {}
    for scope in scopes:
        found = {}; counts = {}; hashes = {}
        for mode in ('supported', 'possible'):
            accepted = []; count = Counter(); trace = hashlib.sha256()
            for row in containing:
                p = row['publication']; data = row['modes'][mode]
                masks = dict(history=h, targets=d, helpers=p & ~(h | d))
                obligations = p if scope in ('all', 'drop_cap') else 0 if scope == 'none' else (
                    masks[scope[5:]] if scope.startswith('only_') else p & ~masks[scope[5:]])
                reason = 'cap' if scope != 'drop_cap' and data['cap_failed'] else 'gain' if not data['gain_satisfied'] else \
                    'retention' if data['failed_sources'] & obligations else 'valid'
                count[reason] += 1; trace.update(f'{p}:{reason}\n'.encode())
                if reason == 'valid':
                    accepted.append(p)
            found[mode] = min(accepted, key=lambda x: (x.bit_count(), x)) if accepted else None
            counts[mode] = dict(count); hashes[mode] = trace.hexdigest()
        evidence[scope] = dict(status=status_from_membership(found['supported'] is not None, found['possible'] is not None, initial),
            witnesses={m: members(p, names) if p is not None else None for m, p in found.items()},
            exhaustive_counts=counts, trace_sha256=hashes)
    labels = []
    for group, label in [('history', 'legacy-history retention'), ('targets', 'target self-retention'), ('helpers', 'helper self-retention')]:
        # A supported feasible relaxed witness establishes necessity of a group;
        # a complete upper exclusion under that group alone plus value YES
        # establishes sufficiency. Both are scoped counterfactual statements.
        if evidence['drop_' + group]['status'] == 'YES' or (
            evidence['none']['status'] == 'YES' and evidence['only_' + group]['status'] == 'NO'):
            labels.append(label)
    pure_cap = all(row['modes']['possible']['cap_failed'] for row in containing)
    if pure_cap or evidence['drop_cap']['status'] == 'YES':
        labels.append('power/composition safety')
    if len(labels) > 1:
        labels.append('mixed/multiple obligations')
    if not labels:
        labels.append('unresolved attribution')
    return dict(labels=labels, scopes=evidence, all_helper_supersets_examined=len(containing),
                expected_helper_supersets=1 << (len(target_names) - target_mask.bit_count()),
                pure_power_exclusion=pure_cap, retention_essential=evidence['none']['status'] == 'YES',
                attribution_scope='Obligation deletion/only-group certificates on same event; categories overlap.')


def audit_contract(world, moments, bounds, rule, variant, saved_certificate, saved_exact, identity):
    c = compile_event(world, moments, bounds, rule, variant)
    if c != saved_certificate['replay_certificate']:
        raise AssertionError('Independently rebuilt replay masks differ from frozen certificate')
    publications, initial = enumerate_publications(c)
    assert initial == saved_certificate['initial']
    assert len(publications) == saved_certificate['examined_publications']
    for mode in ('supported', 'possible'):
        counts = Counter(row['modes'][mode]['reason'] for row in publications)
        assert all(counts[k] == v for k, v in saved_certificate['rejected_or_accepted_counts'][mode].items())
        trace = hashlib.sha256(''.join(f"{row['publication']}:{row['modes'][mode]['reason']}\n" for row in publications).encode()).hexdigest()
        assert trace == saved_certificate['exhaustive_trace_sha256'][mode]
    names = c['items']; history = c['history_mask']
    model = model_from_moments(world, moments, rule, variant)
    oracle = ExactMaskOracle(model)
    if saved_exact is not None:
        assert saved_exact['model_sha256'] == model.digest
    # The review exact oracle uses sorted item names, remap instead of assuming
    # that its bit positions equal the native event's declared item positions.
    exact_valid = [bits(names.index(name) for name in members(p, oracle.names)) for p in oracle.valid]
    valid = {mode: [row['publication'] for row in publications if row['modes'][mode]['reason'] == 'valid']
             for mode in ('supported', 'possible')}
    valid['exact'] = exact_valid
    assert set(valid['supported']) <= set(valid['possible'])
    target_names = [x for i, x in enumerate(names) if not history >> i & 1]
    n = len(target_names)
    target_index = {name: i for i, name in enumerate(target_names)}
    project = lambda p: bits(target_index[name] for name in members(p & ~history, names))
    families = {mode: closure([project(p) for p in masks], n) for mode, masks in valid.items()}
    if initial['supported'] == 'valid' and oracle.initial_valid:
        assert all(not families['supported'][d] or families['exact'][d] for d in range(1 << n))
        assert all(not families['exact'][d] or families['possible'][d] for d in range(1 << n))
    interfaces = {mode: projected_interface(masks, names, history) for mode, masks in valid.items()}
    checks = []
    for mode, interface in interfaces.items():
        # Independent all-valid-publication subset transform vs maximal-target
        # containment scan. Both cover the full powerset, using different paths.
        for d in range(1 << n):
            from_projection = any(d & a == d for a in interface['maximal_target_masks'])
            assert from_projection == families[mode][d]
        checks.append(dict(mode=mode, queries_examined=1 << n, equivalence=True,
                           complete_full_target_powerset=True, full_publications_examined=len(publications)))
    statuses = [status_from_membership(families['supported'][d], families['possible'][d], initial) for d in range(1 << n)]
    registered = []
    for j, query in enumerate(world['queries']):
        d = bits(target_index[x] for x in query['required'] if x in target_index)
        answer = statuses[d]
        assert answer == saved_certificate['queries'][j]['status']
        exact_status = oracle.query(query['required'])['status']
        frozen_exact = saved_exact['queries'][j]['mean_answer']['status'] if saved_exact is not None else 'not_saved'
        if frozen_exact in ('YES', 'NO', 'INVALID_INITIAL'):
            assert exact_status == frozen_exact
        registered.append(dict(query_id=query['query_id'], required=query['required'], frozen_statistical_status=answer,
                               reconstructed_statistical_status=answer, frozen_exact_status=frozen_exact,
                               reconstructed_exact_status=exact_status))
    exact_minimal, certified, low_order, misses = low_order_analysis(families['exact'], statuses, n,
                                                                  exact_initial_valid=oracle.initial_valid)
    item_records = {f'a{i:02}': x for i, x in enumerate(world['candidates'])}
    item_records.update({f'x{i}': x for i, x in enumerate(world['partners'])})
    obstructions = []
    for evidence, masks in [('EXACT FINITE-TABLE RESULT', exact_minimal), ('CERTIFIED NATIVE NO', certified)]:
        for mask in masks:
            target = members(mask, target_names)
            result = dict(target_mask=mask, target=target, order=mask.bit_count(), evidence=evidence,
                          target_items=[dict(source=x, native_item_id=item_records[x].get('native_base_item_id'),
                                             item_name=item_records[x].get('item_name')) for x in target],
                          all_proper_subsets_yes=True)
            if evidence == 'CERTIFIED NATIVE NO':
                result['attribution'] = attribution(mask, c, publications, target_names, initial)
                assert result['attribution']['all_helper_supersets_examined'] == result['attribution']['expected_helper_supersets']
                assert result['attribution']['scopes']['all']['status'] == 'NO'
            obstructions.append(result)
    return dict(**identity, variant=variant, rule=rule, class_name=world['context']['class'], faction=world['context']['faction'],
                world_id=world['world_id'], world_sha256=world['world_sha256'], history=members(history, names), items=names,
                target_universe=target_names, target_universe_rule='E = I minus H, from fixed service query contract; no response selection',
                initial=initial, exact_initial_valid=oracle.initial_valid, interfaces=interfaces,
                checks=checks, registered_queries=registered, statuses=statuses,
                exact_query_statuses=['YES' if value else 'NO' for value in families['exact']] if oracle.initial_valid else
                    ['INVALID_INITIAL'] * (1 << n),
                low_order=low_order, certified_misses=misses, minimal_obstructions=obstructions,
                minimal_obstructions_by_order=dict(Counter(x.bit_count() for x in exact_minimal)),
                certified_obstructions_by_order=dict(Counter(x.bit_count() for x in certified)),
                original_bounds_manifest=bounds['manifest'], additional_alpha=0, native_calls=0,
                replay_certificate=c, publication_exclusion_table=publications,
                assumptions='Fixed-N simultaneous paired-t Bonferroni approximation, not distribution-free; frozen engine/menu/tasks/policy.')


def csv_write(path, rows):
    if not rows:
        Path(path).write_text('no_rows\n'); return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def aggregate(output, results):
    interface_rows = []; ablation = []; obstructions = []; attributions = []; misses = []; negatives = []; equivalence = []
    for result in results:
        key = {k: result[k] for k in ('contract_id', 'stratum', 'world_id', 'variant', 'class_name', 'faction')}
        for mode, interface in result['interfaces'].items():
            interface_rows.append(dict(**key, mode=mode, catalogue_components=len(result['items']), target_universe_size=len(result['target_universe']),
                **{k: interface[k] for k in ('full_maximal_count', 'target_maximal_count', 'projection_merge_count',
                    'serialized_bytes_full', 'serialized_bytes_targets', 'serialized_bytes_targets_with_witnesses')},
                query_answer_equivalence=True, queried_target_pool_size=len(result['statuses']), initial_status=result['initial'],
                minimum_obstruction_order=min((int(k) for k in result['minimal_obstructions_by_order']), default=None),
                maximum_observed_minimal_obstruction_order=max((int(k) for k in result['minimal_obstructions_by_order']), default=None),
                minimal_obstructions_by_order=result['minimal_obstructions_by_order'],
                certified_obstructions_by_order=result['certified_obstructions_by_order']))
        equivalence.append(dict(**key, checks=result['checks'], registered_queries=result['registered_queries'],
                                status_counts=dict(Counter(result['statuses'])), initial=result['initial']))
        ablation += [dict(**key, **row) for row in result['low_order']]
        for row in result['minimal_obstructions']:
            obstructions.append(dict(**key, **row))
            if 'attribution' in row:
                a = row['attribution']
                attributions.append(dict(**key, target=row['target'], native_item_ids=[x['native_item_id'] for x in row['target_items']],
                    order=row['order'], tolerance=result['rule']['tolerance'], categories=a['labels'],
                    all_proper_subsets_certified_YES=True, target_certified_NO=True,
                    **{scope: detail['status'] for scope, detail in a['scopes'].items()},
                    all_helper_supersets_examined=a['all_helper_supersets_examined'],
                    expected_helper_supersets=a['expected_helper_supersets']))
        misses += [dict(**key, **row, target=members(row['target_mask'], result['target_universe'])) for row in result['certified_misses']]
        for status, count in sorted(Counter(result['statuses']).items()):
            if status != 'YES':
                negatives.append(dict(**key, kind='target_query_status', status=status, count=count,
                                      denominator=len(result['statuses']), detail='Exhaustive E powerset; all statuses preserved in checkpoint.'))
        if not result['certified_obstructions_by_order'] or max(map(int, result['certified_obstructions_by_order'])) < 3:
            negatives.append(dict(**key, kind='no_certified_order3_plus', status='negative_result', count=1, denominator=1,
                                   detail='No certified minimal obstruction of order >=3 in this complete fixed universe.'))
        negatives.append(dict(**key, kind='projection_cardinality_compression', status='none_by_contract', count=0, denominator=1,
                              detail='E=I minus H and all publications contain H, so projection is injective.'))
        write(output / 'TARGET_ANTICHAINS' / (result['contract_id'] + '.json'), dict(**key, history=result['history'],
              items=result['items'], target_universe=result['target_universe'], initial=result['initial'], complete=True,
              modes={m: {k: v for k, v in z.items() if k != 'witnesses'} for m, z in result['interfaces'].items()}))
        write(output / 'TARGET_WITNESSES' / (result['contract_id'] + '.json'), dict(**key,
              modes={m: z['witnesses'] for m, z in result['interfaces'].items()},
              possible_witness_warning='Possible publication witnesses satisfy necessary interval tests only; not certified constructions.'))
    csv_write(output / 'TARGET_INTERFACE_AUDIT.csv', interface_rows)
    write(output / 'TARGET_QUERY_EQUIVALENCE.json', dict(status='PASS', contracts=equivalence,
        scope='All target subsets of I minus H in every listed frozen contract. No simulator calls.'))
    csv_write(output / 'LOW_ORDER_ABLATION.csv', ablation)
    csv_write(output / 'CERTIFIED_LOW_ORDER_MISSES.csv', misses)
    csv_write(output / 'OBSTRUCTION_ATTRIBUTION.csv', attributions)
    csv_write(output / 'NEGATIVE_AND_UNRESOLVED.csv', negatives)
    (output / 'MINIMAL_OBSTRUCTIONS.jsonl').write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in obstructions))
    summary = dict(status='PASS', contracts=len(results), strata=dict(Counter(r['stratum'] for r in results)),
        total_target_queries=sum(len(r['statuses']) for r in results),
        registered_queries=sum(len(r['registered_queries']) for r in results),
        projection_merge_count=sum(row['projection_merge_count'] for row in interface_rows),
        exact_obstructions=sum(row['evidence'] == 'EXACT FINITE-TABLE RESULT' for row in obstructions),
        certified_obstructions=len(attributions), attribution_categories=dict(Counter(label for row in attributions for label in row['categories'])),
        strata_summaries={stratum: dict(contracts=sum(r['stratum'] == stratum for r in results),
            target_queries=sum(len(r['statuses']) for r in results if r['stratum'] == stratum),
            query_statuses=dict(Counter(s for r in results if r['stratum'] == stratum for s in r['statuses'])),
            certified_obstruction_orders=dict(Counter(row['order'] for row in obstructions if row['stratum'] == stratum and row['evidence'] == 'CERTIFIED NATIVE NO')),
            low_order={str(order): dict(certified_false_positive_count=sum(row['certified_false_positive_count'] for row in ablation if row['stratum'] == stratum and row['order_r'] == order),
                unknown_blocked_cases=sum(row['unknown_blocked_cases'] for row in ablation if row['stratum'] == stratum and row['order_r'] == order),
                exact_false_positive_count=sum(row['exact_false_positive_count'] or 0 for row in ablation if row['stratum'] == stratum and row['order_r'] == order)) for order in (1, 2, 3)})
            for stratum in sorted({r['stratum'] for r in results})},
        new_native_calls=0, additional_alpha=0,
        inference='Fixed-N simultaneous paired-t Bonferroni approximation; not distribution-free.',
        counting='Contracts in primary expansion, task projection and secondary tolerance are dependent reanalyses; do not pool as independent menus.')
    write(output / 'NATIVE_SUMMARY.json', summary)
    (output / 'PROJECTION_COMPRESSION_SUMMARY.md').write_text(
        '# Projection audit\n\nE was fixed as I minus H from the original arbitrary-in-menu target-query contract, before outcomes. '
        'Every publication contains H, so deleting H preserves inclusion and is injective. Therefore every native contract has '
        'zero projection merges and equal full/target antichain cardinalities. This is a negative compression result.\n\n'
        'Byte counts use UTF-8 compact JSON lists of source names, without repeated contract metadata. Target-plus-witness '
        'bytes use records with target and full publication; witness metadata remains available separately. Shrinking the '
        'repeated history labels is not a structural compression result. No storage-optimality claim is made.\n\n'
        'All exact, supported and possible interfaces were checked against all finite target subsets. A possible witness '
        'is an optimistic interval-test witness, not a certified feasible construction. Initial invalid/unknown contracts '
        'retain their original gate and cannot issue ordinary YES or NO. Empty-target failure remains order zero.\n')
    return summary


def run(bundle, output, resume=False):
    bundle = Path(bundle).resolve(); output = Path(output).resolve()
    if output == bundle or output.is_relative_to(bundle):
        raise ValueError('Output must be outside the immutable bundle')
    manifest = verify_manifest(bundle)
    native = bundle / 'data/native'; analysis = read(native / 'ANALYSIS_MANIFEST.json')
    assert analysis['mode'] == 'confirm'
    registry_path = native / 'CATALOG_REGISTRY.jsonl'
    assert digest(registry_path) == analysis['registry_sha256']
    registry = {w['world_id']: w for w in map(json.loads, registry_path.read_text().splitlines())}
    source_root = Path(__file__).resolve().parents[2]
    sources = ['mi_native.py', 'co_native_analysis.py', 'co_native_sensitivity.py', 'co_review_check.py', 'co_review_oracle.py', 'co_exact.py']
    config = dict(bundle=str(bundle), bundle_manifest_sha256=manifest['manifest_sha256'],
        analysis_sha256=digest(native / 'ANALYSIS_MANIFEST.json'), registry_sha256=digest(registry_path),
        target_universe_rule='E=I minus H; fixed before evaluating responses; arbitrary in-menu service queries',
        strata=['primary_base', 'primary_expanded', 'frozen_task_projection', 'frozen_secondary_tolerance'],
        source_sha256={str(source_root / 'wowfs/experiments' / name): digest(source_root / 'wowfs/experiments' / name) for name in sources},
        workers=1, gpu=0, native_calls=0)
    seal = canonical_hash(config)
    config_path = output / 'NATIVE_RUN_CONFIG.json'
    if config_path.exists():
        if not resume:
            raise ValueError('Output exists; use --resume with matching configuration and source hashes')
        assert read(config_path) == dict(config=config, config_sha256=seal), 'Resume configuration/source mismatch'
        receipt_path = output / 'NATIVE_RUN_RECEIPT.json'
        if receipt_path.exists():
            receipt = read(receipt_path)
            assert receipt['status'] == 'PASS' and receipt['config_sha256'] == seal
            for relative, expected in receipt['output_hashes'].items():
                assert digest(output / relative) == expected, 'Completed output changed: ' + relative
            return read(output / 'NATIVE_SUMMARY.json')
    else:
        output.mkdir(parents=True, exist_ok=True)
        write(config_path, dict(config=config, config_sha256=seal))
    # Register every target universe using registry metadata, before loading moments.
    universe_registration = []
    for world_id in analysis['world_ids']:
        w = registry[world_id]
        definition = dict(w); expected = definition.pop('world_sha256')
        assert canonical_hash(definition) == expected
        for variant in w['universe_variants']:
            left = w['base_candidate_indices'] if variant == 'base' else range(len(w['candidates']))
            right = w['base_partner_indices'] if variant == 'base' else range(len(w['partners']))
            names = [f'a{i:02}' for i in left] + [f'x{i}' for i in right]
            universe_registration.append(dict(world_id=world_id, variant=variant, history=w['history'],
                items=names, target_universe=[x for x in names if x not in w['history']]))
    registration = dict(created_before_response_loading=True, convention=config['target_universe_rule'], contracts=universe_registration)
    regpath = output / 'TARGET_UNIVERSE_REGISTRATION.json'
    if regpath.exists():
        assert read(regpath) == registration
    else:
        write(regpath, registration)
    results = []; started = time.time()
    for world_id in analysis['world_ids']:
        world = registry[world_id]; moments = load_moments(native / world_id, world)
        bounds = finite_bounds(moments, analysis['rule'], analysis['alpha_per_unit'])
        saved_manifest = read(native / world_id / 'BOUNDS_MANIFEST.json')
        for k in ('family_size', 'coefficient_sha256', 'N', 'df', 'alpha'):
            assert saved_manifest[k] == bounds['manifest'][k]
        with np.load(native / world_id / 'BOUNDS.npz', allow_pickle=False) as archive:
            for name in archive.files:
                assert np.allclose(archive[name], bounds[name], rtol=1e-12, atol=1e-10)
        contracts = []
        for variant in world['universe_variants']:
            directory = native / world_id / variant
            contracts.append((world, moments, bounds, analysis['rule'], variant,
                read(directory / 'CONFIDENCE_CERTIFICATES.json'), read(directory / 'EXACT_QUERIES.json'),
                dict(contract_id=world_id + '__' + variant, stratum='primary_' + variant,
                     source_certificate_path=str((directory / 'CONFIDENCE_CERTIFICATES.json').relative_to(bundle)))))
        for path in sorted((bundle / 'data/projection' / world_id).glob('*/CONFIDENCE_CERTIFICATES.json')):
            pw, pm, pb = projection(world, moments, bounds); variant = path.parent.name
            contracts.append((pw, pm, pb, analysis['rule'], variant, read(path), read(path.with_name('EXACT_QUERIES.json')),
                dict(contract_id=world_id + '__projected_tasks__' + variant, stratum='frozen_task_projection',
                     source_certificate_path=str(path.relative_to(bundle)))))
        secondary_path = bundle / 'data/secondary-tolerance' / world_id / 'TOLERANCE_RESULTS.json'
        if secondary_path.exists():
            for record in read(secondary_path)['records']:
                sb, sr = propagate_tolerance(bounds, analysis['rule'], record['multiplier'])
                contracts.append((world, moments, sb, sr, 'base', record['population_answers'], record['mean_table_answers'],
                    dict(contract_id=world_id + '__tolerance_' + record['multiplier'].replace('/', '_'),
                         stratum='frozen_secondary_tolerance', source_certificate_path=str(secondary_path.relative_to(bundle)),
                         tolerance_multiplier=record['multiplier'])))
        for args in contracts:
            checkpoint = output / 'contracts' / (args[-1]['contract_id'] + '.json')
            if checkpoint.exists():
                result = read(checkpoint)
                assert result['run_config_sha256'] == seal
                seal_result = dict(result); recorded_hash = seal_result.pop('checkpoint_sha256')
                assert canonical_hash(seal_result) == recorded_hash, 'Checkpoint hash differs'
            else:
                result = audit_contract(*args)
                result['run_config_sha256'] = seal
                result['checkpoint_sha256'] = canonical_hash(result)
                write(checkpoint, result)
            results.append(result)
            print(json.dumps(dict(contract=result['contract_id'], status='PASS', targets=len(result['statuses']),
                                  initial=result['initial'], certified_orders=result['certified_obstructions_by_order'])), flush=True)
    summary = aggregate(output, results)
    write(output / 'NATIVE_RUN_RECEIPT.json', dict(status='PASS', started_epoch=started, elapsed_seconds=time.time() - started,
        completed_utc=datetime.now(timezone.utc).isoformat(), config_sha256=seal,
        output_hashes={str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'NATIVE_RUN_RECEIPT.json'},
        native_calls=0, additional_alpha=0, contracts=len(results)))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.bundle, args.output, args.resume), indent=2))


if __name__ == '__main__':
    main()
