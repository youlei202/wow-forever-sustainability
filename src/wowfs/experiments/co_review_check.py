"""Portable review-v2 checker: compact moments to exact decisions/certificates.

No native executable, raw battles, external catalogue database, network access,
or original server path is used. Statistical claims retain their original
approximate fixed-N paired-t assumptions. Exhaustive finite-model replay is not
a machine-checked theorem proof or a solver-generated formal UNSAT proof.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import numpy as np

from wowfs.experiments.co_exact import Model, evaluate
from wowfs.experiments.co_native_analysis import (
    certify_queries, finite_bounds, model_from_moments,
    verify_replay_publication,
)
from wowfs.experiments.co_review_oracle import exact_queries
from wowfs.paths import canonical_hash


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ensure(condition, message):
    if not condition:
        raise AssertionError(message)


def inside(root, relative):
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError(f'Manifest path is not bundle-relative: {relative}')
    candidate = root / p
    if candidate.is_symlink() or not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Manifest path escapes bundle: {relative}')
    return candidate


def verify_manifest(root, *, allow_unsealed=False):
    path = root / 'REVIEW_MANIFEST.json'
    if not path.exists():
        if allow_unsealed:
            return {'status': 'UNSEALED_DEVELOPMENT_SMOKE', 'checked_files': 0}
        raise ValueError('REVIEW_MANIFEST.json required; --allow-unsealed is only for development smoke checks')
    manifest = read(path); records = manifest['files']
    required_sections = manifest.get('required_sections', [])
    ensure(set(required_sections) <= {'native', 'secondary-tolerance', 'projection', 'obligations', 'sensitivity', 'benchmark'},
           'Unknown required review section')
    for section in required_sections:
        ensure((root / 'data' / section).is_dir(), f'Required review section missing: {section}')
    if isinstance(records, dict):
        records = [dict(path=p, **({'sha256': v} if isinstance(v, str) else v)) for p, v in records.items()]
    seen = set()
    for record in records:
        rel = record['path']
        ensure(rel not in seen, f'Duplicate manifest path: {rel}'); seen.add(rel)
        f = inside(root, rel)
        ensure(f.is_file(), f'Manifest file missing: {rel}')
        ensure(digest(f) == record['sha256'], f'SHA256 mismatch: {rel}')
        if 'bytes' in record:
            ensure(f.stat().st_size == record['bytes'], f'File size mismatch: {rel}')
    # Generated Python bytecode is not a source/input artifact. Every other
    # code/data file must be sealed, so an unlisted replacement cannot be used.
    used_files = {str(p.relative_to(root)) for prefix in ('code', 'data') for p in (root / prefix).rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    ensure(used_files <= seen, f'Unsealed code/data files: {sorted(used_files - seen)[:8]}')
    return {'status': 'PASS', 'checked_files': len(records), 'manifest_sha256': digest(path),
            'required_sections': required_sections,
            'scope': 'Content identity against the supplied manifest; external authenticity requires the separately published ZIP hash.'}


def load_moments(directory, world):
    readable = read(directory / 'MOMENTS_READABLE.json')
    archive = directory / 'MOMENTS.npz'
    ensure(digest(archive) == readable['archive_sha256'], f'Moments archive hash: {world["world_id"]}')
    with np.load(archive, allow_pickle=False) as z:
        means = np.asarray(z['means']); covariance = np.asarray(z['covariance'])
        ensure(np.array_equal(means, np.asarray(readable['means'])), 'Readable/NPZ means differ')
        ensure(np.array_equal(covariance, np.asarray(readable['covariance'])), 'Readable/NPZ covariance differs')
        ensure(int(z['N']) == readable['N'], 'Readable/NPZ N differs')
        ensure(np.array_equal(z['reference_indices'], readable['reference_indices']), 'Reference mapping differs')
    ensure(np.isfinite(means).all() and np.isfinite(covariance).all(), 'Nonfinite compact moments')
    ensure(readable['world_id'] == world['world_id'], 'World identity differs')
    ensure(readable['world_sha256'] == world['world_sha256'], 'World definition differs')
    pairs = [tuple(p) for p in readable['domain']['pairs']]
    expected_pairs = [(i, j) for i in range(len(world['candidates'])) for j in range(len(world['partners']))]
    ensure(pairs == expected_pairs, 'Missing, duplicate, reordered or extra physical pairs')
    ensure(means.shape == (len(world['tasks']), len(pairs)), 'Response task/row shape differs')
    ensure(covariance.shape == (len(world['tasks']), len(pairs), len(pairs)), 'Covariance shape differs')
    ensure(readable['domain']['task_ids'] == [t['task_id'] for t in world['tasks']], 'Task order differs')
    ensure(int(readable['N']) >= 2, 'Insufficient fixed-N observations')
    if 'receipt_index' in readable:
        receipts = readable['receipt_index']
        cells = {(r['candidate_index'], r['partner_index'], r['task_index']) for r in receipts}
        expected = {(i, j, q) for i, j in pairs for q in range(len(world['tasks']))}
        ensure(cells == expected and len(receipts) == len(expected), 'Incomplete/duplicate physical receipt index')
        ensure(all(r['iterations'] == readable['N'] and r['seed_block_id'] == readable['seed_block_id'] for r in receipts), 'Unpaired receipt seed/N identity')
    readable.update(means=means, covariance=covariance)
    readable['domain']['pairs'] = pairs
    return readable


def compare_certificates(saved, actual):
    original_manifest, replay_manifest = saved['bounds_manifest'], actual['bounds_manifest']
    original_event = original_manifest.get('source_manifest', original_manifest)
    replay_event = replay_manifest.get('source_manifest', replay_manifest)
    for field in ('alpha', 'family_size', 'critical', 'N', 'df', 'coefficient_sha256', 'reference_indices'):
        same = abs(original_event[field] - replay_event[field]) < 1e-12 if field == 'critical' else original_event[field] == replay_event[field]
        ensure(same, f'Certificate event identity differs: {field}')
    for field in ('world_id', 'variant', 'initial', 'examined_publications', 'rejected_or_accepted_counts',
                  'exhaustive_trace_sha256', 'replay_certificate'):
        ensure(saved[field] == actual[field], f'Confidence certificate changed: {field}')
    ensure(len(saved['queries']) == len(actual['queries']), 'Confidence query denominator changed')
    for original, replay in zip(saved['queries'], actual['queries']):
        for field in ('query_id', 'required', 'status', 'witness', 'optimistic_completion', 'exhaustive_target_publication_counts'):
            ensure(original[field] == replay[field], f'Confidence query changed: {original["query_id"]}/{field}')
        if original['witness'] is not None:
            ensure(verify_replay_publication(actual, original['witness'])['valid'], 'Saved confidence witness fails replay')


def compare_exact(saved, actual, model):
    ensure(saved['model_sha256'] == model.digest == actual['model_sha256'], 'Exact finite-table identity differs')
    ensure(Model.from_dict(saved['model']).digest == model.digest, 'Saved response model differs from compact means')
    ensure(len(saved['queries']) == len(actual['queries']), 'Exact query denominator changed')
    unresolved = []
    for original, replay in zip(saved['queries'], actual['queries']):
        ensure(original['query_id'] == replay['query_id'] and original['required'] == replay['required'], 'Exact query contract differs')
        for field in ('mean_answer', 'value_only_answer'):
            status, recheck = original[field]['status'], replay[field]['status']
            if status in ('YES', 'NO', 'INVALID_INITIAL'):
                ensure(status == recheck, f'Exact answer mismatch: {original["query_id"]}/{field}: {status} vs {recheck}')
            else:
                unresolved.append({'query_id': original['query_id'], 'field': field, 'frozen': status, 'replay': recheck})
        if original['mean_answer']['status'] == 'YES':
            items = original['mean_answer']['items']
            ensure(set(original['required']) <= set(items), 'Saved mean witness omits target')
            ensure(evaluate(model, items)['valid'], 'Saved exact mean witness invalid')
    return unresolved


def projection(world, moments, bounds):
    """Independent task-array projection; intentionally no co_catalogs import."""
    indices = [0, 3]
    ensure(len(world['tasks']) == 4, 'Projected catalogue was not Q=4')
    w = deepcopy(world); w['tasks'] = [deepcopy(world['tasks'][i]) for i in indices]
    w['task_weights'] = [.5, .5]; w['parent_world_sha256'] = world['world_sha256']
    w['task_projection'] = {'indices': indices, 'weights': ['1/2', '1/2'], 'contract': 'different allowed task distribution; no monotonicity assertion'}
    w.pop('world_sha256'); w['world_sha256'] = canonical_hash(w)
    m = deepcopy(moments); m['world_sha256'] = w['world_sha256']
    m['means'] = m['means'][indices]; m['covariance'] = m['covariance'][indices]
    m['reference_indices'] = [moments['reference_indices'][i] for i in indices]
    m['domain']['task_ids'] = [moments['domain']['task_ids'][i] for i in indices]
    b = {k: v[indices] for k, v in bounds.items() if k != 'manifest'}
    b['manifest'] = deepcopy(bounds['manifest'])
    return w, m, b


def verify_secondary(root, cache):
    directory = root / 'data/secondary-tolerance'
    if not directory.exists():
        return {'status': 'NOT_INCLUDED', 'queries_recomputed': 0}
    from wowfs.experiments.co_native_sensitivity import analyze_catalogue
    paths = sorted(directory.glob('*/TOLERANCE_RESULTS.json'))
    ensure(paths, 'Secondary directory exists without TOLERANCE_RESULTS.json')
    checked = 0
    for path in paths:
        saved = read(path); w, m, b, rule = cache[saved['world_id']]
        replay = analyze_catalogue(w, m, b, rule, include_means=False)
        ensure(saved['protocol'] == replay['protocol'], 'Secondary tolerance protocol differs')
        ensure(len(saved['records']) == len(replay['records']), 'Secondary multiplier denominator differs')
        for a, z in zip(saved['records'], replay['records']):
            ensure(a['multiplier'] == z['multiplier'] and a['tolerance'] == z['tolerance'], 'Secondary threshold differs')
            compare_certificates(a['population_answers'], z['population_answers'])
            if a['mean_table_answers'] is not None:
                new_rule = dict(rule, tolerance=z['tolerance'])
                independent_mean = exact_queries(w, m, new_rule, 'base')
                compare_exact(a['mean_table_answers'], independent_mean, model_from_moments(w, m, new_rule, 'base'))
            checked += len(z['population_answers']['queries'])
    ensure({read(p)['world_id'] for p in paths} == set(cache), 'Secondary panel omitted a primary catalogue')
    return {'status': 'PASS', 'catalogues': len(paths), 'queries_recomputed': checked, 'additional_alpha': 0.}


def verify_projection(root, cache):
    directory = root / 'data/projection'
    if not directory.exists():
        return {'status': 'NOT_INCLUDED', 'queries_recomputed': 0}
    paths = sorted(directory.glob('*/**/CONFIDENCE_CERTIFICATES.json'))
    ensure(paths, 'Projection directory exists without certificates')
    count = 0
    for path in paths:
        saved = read(path); world, moments, bounds, rule = cache[saved['world_id']]
        w, m, b = projection(world, moments, bounds)
        replay = certify_queries(w, m, b, rule, saved['variant'])
        compare_certificates(saved, replay)
        exact = exact_queries(w, m, rule, saved['variant'])
        compare_exact(read(path.with_name('EXACT_QUERIES.json')), exact, model_from_moments(w, m, rule, saved['variant']))
        count += len(saved['queries'])
    expected = sum(len(w['universe_variants']) for w, _, _, _ in cache.values() if len(w['tasks']) == 4)
    ensure(len(paths) == expected, 'Projection catalogue/menu denominator differs')
    return {'status': 'PASS', 'menu_contracts': len(paths), 'queries_recomputed': count, 'additional_alpha': 0.}


def replay_obligations(certificate):
    """Independent complete-publication replay of source-group relaxations."""
    c = certificate['replay_certificate']; names = c['items']; history = c['history_mask']
    rows = c['support_masks']; targets = c['query_masks']
    optional = [i for i in range(len(names)) if not (history >> i) & 1]
    scopes = ('all', 'only_history', 'only_targets', 'only_helpers', 'drop_history', 'drop_targets', 'drop_helpers', 'none')
    modes = ('supported', 'possible')
    qcount = len(c['compiled_masks']['possible']['gain_good'])
    allowed_ret = set(c['enough_retention_mass_masks']); allowed_gain = set(c['enough_gain_mass_masks'])
    counts = [{s: {m: Counter(cap=0, gain=0, retention=0, valid=0) for m in modes} for s in scopes} for _ in targets]
    for optional_mask in range(1 << len(optional)):
        publication = history | sum(1 << i for k, i in enumerate(optional) if (optional_mask >> k) & 1)
        active = sum(1 << r for r, support in enumerate(rows) if support & publication == support)
        for mode in modes:
            data = c['compiled_masks'][mode]
            gain_mask = sum(1 << q for q in range(qcount) if active & data['gain_good'][q])
            common = 'cap' if active & data['capbad'] else 'gain' if gain_mask not in allowed_gain else None
            failed = 0
            if common is None:
                for i in range(len(names)):
                    if not (publication >> i) & 1:
                        continue
                    task_mask = 0
                    for q in range(qcount):
                        if any(active >> r & 1 and support >> i & 1 and not active & data['ret_bad'][q][r]
                               for r, support in enumerate(rows)):
                            task_mask |= 1 << q
                    if task_mask not in allowed_ret:
                        failed |= 1 << i
            for qi, target in enumerate(targets):
                if publication & target != target:
                    continue
                helpers = publication & ~(history | target)
                groups = {'all': publication, 'only_history': publication & history, 'only_targets': publication & target,
                          'only_helpers': helpers, 'drop_history': publication & ~history,
                          'drop_targets': publication & ~target, 'drop_helpers': publication & ~helpers, 'none': 0}
                for scope, obligation in groups.items():
                    reason = common or ('retention' if failed & obligation else 'valid')
                    counts[qi][scope][mode][reason] += 1
    results = []
    for qi, query in enumerate(certificate['queries']):
        statuses = {}
        for scope in scopes:
            if certificate['initial']['possible'] != 'valid':
                status = 'INVALID_INITIAL'
            elif certificate['initial']['supported'] != 'valid':
                status = 'UNKNOWN_INITIAL'
            elif counts[qi][scope]['supported']['valid']:
                status = 'YES'
            elif not counts[qi][scope]['possible']['valid']:
                status = 'NO'
            else:
                status = 'UNKNOWN'
            statuses[scope] = status
        no, value_yes = statuses['all'] == 'NO', statuses['none'] == 'YES'
        labels = {'retention_essential': no and value_yes}
        for label, scope in [('legacy', 'history'), ('targets', 'targets'), ('helpers', 'helpers')]:
            labels[label + '_necessary_for_obstruction'] = no and statuses['drop_' + scope] == 'YES'
            labels[label + '_alone_sufficient'] = value_yes and statuses['only_' + scope] == 'NO'
        results.append({'query_id': query['query_id'], 'statuses': statuses, 'counts': counts[qi], 'labels': labels})
    return results


def verify_obligations(root, cache):
    directory = root / 'data/obligations'
    if not directory.exists():
        return {'status': 'NOT_INCLUDED', 'query_scope_decisions_recomputed': 0}
    paths = sorted(directory.glob('*/**/OBLIGATION_AUDIT.json'))
    ensure(paths, 'Obligation directory exists without audit records')
    checked = 0
    for path in paths:
        saved = read(path); w, m, b, rule = cache[saved['world_id']]
        cert = certify_queries(w, m, b, rule, saved['variant'])
        replay = replay_obligations(cert)
        ensure(len(saved['queries']) == len(replay), 'Obligation query denominator differs')
        for original, actual in zip(saved['queries'], replay):
            ensure(original['query_id'] == actual['query_id'], 'Obligation query identity differs')
            ensure(original['diagnostic_labels'] == actual['labels'], 'Obligation necessity/sufficiency labels differ')
            for scope, status in actual['statuses'].items():
                ensure(original['scopes'][scope]['status'] == status, 'Obligation scope status differs')
                ensure(original['scopes'][scope]['exhaustive_counts'] == actual['counts'][scope], 'Obligation exhaustive counts differ')
                checked += 1
    expected = sum(len(w['universe_variants']) for w, _, _, _ in cache.values())
    ensure(len(paths) == expected, 'Obligation audit omitted a primary catalogue/menu')
    return {'status': 'PASS', 'menu_contracts': len(paths), 'query_scope_decisions_recomputed': checked, 'additional_alpha': 0.}


def check_bundle(root, *, allow_unsealed=False, allow_predictions=False):
    root = Path(root).resolve(); started = time.time()
    identity = verify_manifest(root, allow_unsealed=allow_unsealed)
    native = root / 'data/native'
    manifest = read(native / 'ANALYSIS_MANIFEST.json')
    mode = manifest['mode']
    ensure(mode == 'confirm' or allow_predictions, 'Prediction tables cannot stand in for fresh confirmation; development smoke requires --allow-predictions')
    registry_path = native / 'CATALOG_REGISTRY.jsonl'
    ensure(digest(registry_path) == manifest['registry_sha256'], 'Frozen catalogue registry hash differs')
    worlds = {w['world_id']: w for w in (json.loads(line) for line in registry_path.read_text().splitlines() if line.strip())}
    listed = manifest['world_ids']
    ensure(len(listed) == len(set(listed)), 'Duplicate primary catalogue')
    decisions = read(native / 'NATIVE_DECISIONS.json')
    lookup = {(r['world_id'], r['variant'], r['query_id']): r for r in decisions}
    ensure(len(lookup) == len(decisions), 'Duplicate primary decision row')
    rule = manifest['rule']; alpha = manifest['alpha_per_unit']
    counts = Counter(); examined = 0; queried = 0; observed_keys = set(); cache = {}; unresolved_means = []
    frozen_witnesses = []
    prediction_path = root / 'data/predictions/NATIVE_DECISIONS.json'
    prediction_lookup = ({(r['world_id'], r['variant'], r['query_id']): r for r in read(prediction_path)}
                         if prediction_path.exists() else None)
    for world_id in listed:
        world = worlds[world_id]; definition = dict(world); expected_hash = definition.pop('world_sha256')
        ensure(canonical_hash(definition) == expected_hash, f'Catalogue canonical identity differs: {world_id}')
        moments = load_moments(native / world_id, world)
        bounds = finite_bounds(moments, rule, alpha) if mode == 'confirm' else None
        if bounds is not None:
            cache[world_id] = (world, moments, bounds, rule)
            saved_b = read(native / world_id / 'BOUNDS_MANIFEST.json')
            ensure(saved_b['family_size'] == bounds['manifest']['family_size'], 'Original contrast family count differs')
            ensure(saved_b['coefficient_sha256'] == bounds['manifest']['coefficient_sha256'], 'Original coefficient vectors differ')
            ensure(abs(saved_b['critical'] - bounds['manifest']['critical']) < 1e-12, 'Original t critical differs')
            saved_npz = native / world_id / 'BOUNDS.npz'
            if saved_npz.exists():
                with np.load(saved_npz, allow_pickle=False) as z:
                    for name in z.files:
                        ensure(np.allclose(z[name], bounds[name], rtol=1e-12, atol=1e-10), f'Reconstructed bound differs: {name}')
        for variant in world['universe_variants']:
            directory = native / world_id / variant
            saved_exact = read(directory / 'EXACT_QUERIES.json')
            exact = exact_queries(world, moments, rule, variant)
            model = model_from_moments(world, moments, rule, variant)
            unresolved_means.extend(compare_exact(saved_exact, exact, model))
            cert = certify_queries(world, moments, bounds, rule, variant) if bounds is not None else None
            value = certify_queries(world, moments, bounds, rule, variant, retention=False) if bounds is not None else None
            if cert is not None:
                compare_certificates(read(directory / 'CONFIDENCE_CERTIFICATES.json'), cert)
                compare_certificates(read(directory / 'VALUE_ONLY_CONFIDENCE.json'), value)
                examined += cert['examined_publications'] + value['examined_publications']
            for qi, result in enumerate(exact['queries']):
                frozen_result = saved_exact['queries'][qi]
                key = world_id, variant, result['query_id']; observed_keys.add(key)
                row = lookup[key]
                ensure(row['required'] == result['required'], 'Flattened target differs')
                expected_mean = row['fresh_mean_answer'] if mode == 'confirm' else row['development_prediction']
                ensure(expected_mean == frozen_result['mean_answer']['status'], 'Flattened mean decision differs')
                ensure(row['value_only_mean_answer'] == frozen_result['value_only_answer']['status'], 'Flattened value-only mean differs')
                ensure(row['retention_decision_active_mean'] == (frozen_result['mean_answer']['status'] == 'NO' and frozen_result['value_only_answer']['status'] == 'YES'), 'Mean retention-obstruction indicator differs')
                ensure(row['native_N'] == moments['N'] and row['seed_block_id'] == moments['seed_block_id'], 'Decision sample identity differs')
                if cert is not None:
                    status = cert['queries'][qi]['status']; vstatus = value['queries'][qi]['status']
                    ensure(row['confidence_status'] == status and row['value_only_confidence'] == vstatus, 'Flattened confidence status differs')
                    ensure(row['retention_decision_active_confidence'] == (status == 'NO' and vstatus == 'YES'), 'Retention-obstruction indicator differs')
                    pw = row.get('frozen_prediction_witness')
                    if prediction_lookup is not None:
                        prediction = prediction_lookup[key]
                        ensure(row['development_prediction'] == prediction['development_prediction'], 'Frozen prediction status differs')
                        ensure(pw == prediction.get('frozen_prediction_witness'), 'Frozen prediction witness identity differs')
                    ensure(row['prediction_changed_on_fresh_mean'] == (row['development_prediction'] != row['fresh_mean_answer']), 'Prediction/fresh-mean disagreement flag differs')
                    if pw:
                        ensure(set(row['required']) <= set(pw), 'Frozen prediction witness omits target')
                        replay = verify_replay_publication(cert, pw)
                        ensure(replay == row['prediction_witness_confidence_check'], 'Frozen prediction witness adjudication differs')
                        frozen_witnesses.append(dict(world_id=world_id, variant=variant,
                            query_id=row['query_id'], frozen_witness=pw,
                            fresh_mean_check=evaluate(model, pw), confidence_check=replay,
                            query_confidence_status=status))
                    counts[status] += 1
                else:
                    ensure(row['confidence_status'] == 'NOT_RUN', 'Prediction bundle claims confidence evidence')
                    counts['NOT_RUN'] += 1
                queried += 1
        if world.get('candidate_expansion_registered'):
            for query in world['queries']:
                before = lookup[world_id, 'base', query['query_id']]
                after = lookup[world_id, 'expanded', query['query_id']]
                field = 'fresh_mean_answer' if mode == 'confirm' else 'development_prediction'
                ensure(before[field] != 'YES' or after[field] not in ('NO', 'INVALID_INITIAL'), 'Optional catalogue expansion lost an exact completion')
                if mode == 'confirm':
                    ensure(before['confidence_status'] != 'YES' or after['confidence_status'] == 'YES', 'Shared-event expansion lost a conservative completion')
        print(json.dumps({'rechecked_catalogue': world_id, 'mode': mode}), flush=True)
    ensure(observed_keys == set(lookup), 'Primary decision denominator differs from registered queries/menus')
    witness_path = root / 'provenance/native/FROZEN_WITNESS_RECHECK.json'
    witness_artifact_checked = False
    if witness_path.exists():
        saved_witnesses = read(witness_path)
        key = lambda r: (r['world_id'], r['variant'], r['query_id'])
        ensure(sorted(saved_witnesses, key=key) == sorted(frozen_witnesses, key=key), 'Frozen prediction witness fresh-mean recheck differs')
        witness_artifact_checked = True
    frozen_witness_summary = {}
    for variant in sorted({r['variant'] for r in frozen_witnesses}):
        rows = [r for r in frozen_witnesses if r['variant'] == variant]
        frozen_witness_summary[variant] = dict(witnesses=len(rows),
            fresh_mean_valid=sum(r['fresh_mean_check']['valid'] for r in rows),
            fresh_mean_invalid=sum(not r['fresh_mean_check']['valid'] for r in rows),
            confidence_supported=sum(r['confidence_check']['valid'] for r in rows),
            confidence_unresolved=sum(not r['confidence_check']['valid'] for r in rows))
    secondary = verify_secondary(root, cache) if cache else {'status': 'NOT_RUN_PREDICTION_SMOKE'}
    projected = verify_projection(root, cache) if cache else {'status': 'NOT_RUN_PREDICTION_SMOKE'}
    obligations = verify_obligations(root, cache) if cache else {'status': 'NOT_RUN_PREDICTION_SMOKE'}
    sensitivity = root / 'data/sensitivity'
    if sensitivity.exists():
        from wowfs.experiments.co_sensitivity import verify_bundle
        # The rechecker never changes the review bundle. Temporary computation
        # products respect an externally selected TMPDIR when supplied.
        with tempfile.TemporaryDirectory(prefix='co_review_check_') as td:
            result_path = Path(td) / 'inherited-check.json'
            verify_bundle(sensitivity, result_path)
            inherited = read(result_path)
    else:
        inherited = {'status': 'NOT_INCLUDED'}
    return {'status': 'PASS' if mode == 'confirm' else 'SMOKE_PASS_PREDICTION_TABLES_ONLY',
            'identity': identity, 'primary_catalogues': len(listed), 'primary_query_rows': queried,
            'primary_status_counts': dict(counts), 'confidence_publications_recomputed': examined,
            'exact_mean_unresolved_original_runs': unresolved_means,
            'frozen_prediction_witnesses': {'by_variant': frozen_witness_summary,
                'archived_fresh_mean_checks_verified': witness_artifact_checked,
                'archived_prediction_identity_verified': prediction_lookup is not None,
                'fresh_mean_invalid': [dict(world_id=r['world_id'], variant=r['variant'], query_id=r['query_id'],
                    frozen_witness=r['frozen_witness']) for r in frozen_witnesses if not r['fresh_mean_check']['valid']]},
            'exact_mean_audit_method': 'Independent exact-rational all-publication bitmask oracle; no SAT/CP/MILP imports or rounded response coefficients.',
            'secondary_tolerance': secondary, 'task_projection': projected, 'source_obligation_ablations': obligations,
            'inherited_sensitivity': inherited,
            'new_native_calls': 0, 'new_native_battles': 0, 'additional_alpha': 0,
            'elapsed_seconds': time.time() - started,
            'scope': 'Exact finite-table and exhaustive finite-event consequence replay; approximate paired-t coverage assumptions unchanged. No formal UNSAT proof or proof-assistant theorem verification is claimed.',
            'not_reproduced': ['Raw trajectory generation', 'Battle-level tail diagnostics', 'Elapsed runtime benchmark measurements', 'A new independent catalogue experiment']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-unsealed', action='store_true', help='Development smoke only')
    parser.add_argument('--allow-predictions', action='store_true', help='Development smoke only; never reports fresh confirmation')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.bundle.resolve()):
        parser.error('--output must be outside the immutable review bundle')
    if args.output.exists():
        parser.error('--output already exists; choose a new audit receipt')
    try:
        result = check_bundle(args.bundle, allow_unsealed=args.allow_unsealed, allow_predictions=args.allow_predictions)
    except Exception as exc:
        result = {'status': 'FAIL', 'error_type': type(exc).__name__, 'error': str(exc), 'new_native_calls': 0}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        print(json.dumps(result), file=sys.stderr)
        raise
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'primary_catalogues', 'primary_query_rows', 'confidence_publications_recomputed', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
