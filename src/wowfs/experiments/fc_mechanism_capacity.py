"""Finite native mechanism transfer: matched spectra, exact order oracle, fresh table.

The oracle is exact only for the frozen finite primary set and admission masks.
No interpolation in event-changing primary parameters or scalar theorem is used.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
from scipy.stats import t as student_t

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash
from wowfs.experiments.fc_native import STAGE, contexts, presets, engine_root, run_jobs
from wowfs.experiments.fc_mechanisms import load_grid, mechanism_input
from wowfs.experiments.r2_native import file_hash

RUN_ID = 'mechanism-capacity-confirmation-v1'
DESIGN_NAME = 'MECHANISM_CAPACITY_DESIGN.json'
CAL_NAME = 'MECHANISM_CALIBRATION.json'
CONFIRM_SEED = 820000001
CONFIRM_N = 512
TOL = 1e-10


def minimum_portfolio(values, frontier, scale, epsilon, weights, coverage):
    """Exact finite set cover over the eight task bits."""
    masks = set()
    for row in values:
        mask = sum(1 << q for q, ok in enumerate(row >= frontier-epsilon*scale-TOL) if ok)
        masks.add(mask)
    costs = {0: 0}
    for mask in masks:
        previous = list(costs.items())
        for covered, cost in previous:
            union = covered | mask
            costs[union] = min(costs.get(union, 10**9), cost+1)
    return min((cost for bits, cost in costs.items()
                if sum(w for q, w in enumerate(weights) if bits & (1 << q)) >= coverage-TOL), default=None)


def finite_oracle(utility, admitted, reference, scale, cfg, require_legacy=True):
    """All finite release orders, retaining every admitted historical cross."""
    utility = np.asarray(utility, dtype=float); admitted = np.asarray(admitted, dtype=bool)
    scale = np.asarray(scale, dtype=float); weights = np.asarray(cfg['task_weights'])
    if not np.isfinite(utility).all() or np.any(scale <= 0):
        raise ValueError('Finite utility and positive frozen scales required')
    candidates = tuple(i for i in range(utility.shape[0]) if i != reference)
    cap = scale*(1+cfg['fixed_headroom'])

    @lru_cache(None)
    def state(mask):
        primaries = [reference]+[p for bit, p in enumerate(candidates) if mask & (1 << bit)]
        pairs = [(p, j) for p in primaries for j in range(utility.shape[1]) if admitted[p, j]]
        values = np.array([utility[p, j] for p, j in pairs])
        if not pairs:
            return {'valid': False, 'frontier': np.zeros(len(scale)), 'checks': {'P': False}}
        frontier = values.max(axis=0)
        power = bool(np.all(values <= cap+TOL))
        use = {}
        for p in primaries:
            available = [utility[a, j] for a, j in pairs if a == p]
            use['primary_'+str(p)] = float(np.sum(weights*(np.max(available, axis=0) >=
                frontier-cfg['legacy_epsilon']*scale-TOL))) if available else 0.
        for j in range(utility.shape[1]):
            available = [utility[p, b] for p, b in pairs if b == j]
            use['partner_'+str(j)] = float(np.sum(weights*(np.max(available, axis=0) >=
                frontier-cfg['legacy_epsilon']*scale-TOL))) if available else 0.
        legacy = min(use.values()) >= cfg['legacy_required_mass']-TOL
        k = minimum_portfolio(values, frontier, scale, cfg['legacy_epsilon'], weights, cfg['portfolio_coverage'])
        complex_ok = k is not None and k <= cfg['portfolio_K']
        checks = {'P': power, 'N_and_L_all_retained_sources': legacy,
                  'H': True, 'C': complex_ok}
        return {'valid': power and (not require_legacy or (legacy and complex_ok)),
                'frontier': frontier, 'checks': checks, 'K': k, 'source_use': use,
                'pairs': pairs, 'worst_source_mass': min(use.values())}

    def transition(mask, bit):
        before, after = state(mask), state(mask | (1 << bit))
        gains = (after['frontier']-before['frontier'])/scale
        mass = float(weights @ (gains >= cfg['meaningful_gain']-TOL))
        return before['valid'] and after['valid'] and mass >= cfg['gain_required_mass']-TOL, gains, mass

    @lru_cache(None)
    def solve(mask):
        if not state(mask)['valid']:
            return ()
        best = ()
        for bit, primary in enumerate(candidates):
            if mask & (1 << bit):
                continue
            ok, _, _ = transition(mask, bit)
            if not ok:
                continue
            path = (primary,)+solve(mask | (1 << bit))
            if len(path) > len(best):
                best = path
        return best

    def inspect(path):
        mask = 0; rows = []; prefix = 0; still_valid = state(0)['valid']
        for primary in path:
            bit = candidates.index(primary)
            if mask & (1 << bit):
                raise ValueError('Cannot release an existing primary alias twice')
            ok, gains, mass = transition(mask, bit)
            mask |= 1 << bit
            after = state(mask)
            still_valid = still_valid and ok
            prefix += int(still_valid)
            rows.append({'primary_index': primary, 'pass': bool(ok), 'normalized_gain': gains.tolist(),
                         'gain_mass': mass, 'checks': after['checks'], 'K': after['K'],
                         'worst_source_mass': after['worst_source_mass'], 'source_use': after['source_use'],
                         'frontier': after['frontier'].tolist(), 'admitted_pairs': after['pairs']})
        return rows, prefix, mask

    path = solve(0)
    rows, prefix, mask = inspect(path)
    blocked = []
    for bit, primary in enumerate(candidates):
        if mask & (1 << bit):
            continue
        ok, gains, mass = transition(mask, bit)
        after = state(mask | (1 << bit))
        blocked.append({'primary_index': primary, 'pass': bool(ok), 'gain_mass': mass,
                        'normalized_gain': gains.tolist(), 'checks': after['checks'],
                        'worst_source_mass': after['worst_source_mass'], 'K': after['K']})
    initial = state(0)
    result = {'capacity': len(path), 'path': list(path), 'path_rows': rows,
              'blocked_after_terminal': blocked, 'states_visited': solve.cache_info().currsize,
              'initial_checks': initial['checks'], 'initial_K': initial.get('K'),
              'initial_source_use': initial.get('source_use'), 'initial_frontier': initial['frontier'].tolist(),
              'require_legacy': require_legacy,
              'scope': 'Exact finite candidate-order oracle on supplied task-vector means and fixed admission mask; not continuous capacity.'}
    return result, inspect


def build_design():
    root = setup_paths(); grid, cfg = load_grid()
    cal_path = root/'artifacts'/STAGE/CAL_NAME
    cal = json.loads(cal_path.read_text())
    task_ids = [t['id'] for t in cfg['tasks']]
    checks = {(c['context_id'], c['task']): c for c in cal['checks']}
    context_map = {c['context_id']: c for c in contexts()}
    designs = []
    for family in grid['families']:
        selected = sorted(c for c in context_map if context_map[c]['class'] == family['class']
                          and context_map[c]['race_label'] in family['races'])
        for cid in selected:
            surfaces = [checks[cid, q] for q in task_ids]
            if not all(c['all_partner_affinity_validated'] and c['all_partner_controls_identical'] for c in surfaces):
                raise ValueError('No validated conditional partner interpolation for '+cid)
            cube = np.stack([np.array(c['mean_dps_grid']) for c in surfaces], axis=2)
            lo, hi = family['partner_values'][0], family['partner_values'][-1]
            slopes = (cube[:, -1, :]-cube[:, 0, :])/(hi-lo)
            reference = family['reference_primary_index']
            scale = cube[reference, -1, :]
            if np.any(slopes[reference] <= 0):
                raise ValueError('Reference completion must have positive slopes')
            width = min(hi-lo, float(np.min(.044*scale/slopes[reference])))
            lower = hi-width
            for ecology, fractions in [('large_gap', [0, 1/440, 2/440, 3/440, 1]),
                                       ('dense', [0, .25, .5, .75, 1])]:
                partners = [lower+width*x for x in fractions]
                # Make the shared endpoint bit-identical to the native calibration endpoint.
                partners[-1] = hi
                utility = np.stack([cube[:, 0, :]+slopes*(y-lo) for y in partners], axis=1)
                admitted = np.all(utility <= (1+cfg['fixed_headroom'])*scale+TOL, axis=2)
                if not np.all(admitted[reference]):
                    raise ValueError('All old-old configurations must be admitted')
                value, _ = finite_oracle(utility, admitted, reference, scale, cfg, True)
                utility_only, _ = finite_oracle(utility, admitted, reference, scale, cfg, False)
                spectra = (utility[reference]-utility[reference, 0])/scale
                gaps = np.max(np.diff(spectra, axis=0), axis=0)
                direct = (utility[:, -1, :]-utility[reference, -1, :])/scale
                designs.append({'design_id': cid+'__'+ecology, 'context': context_map[cid], 'family': family['id'],
                    'ecology': ecology, 'reference_primary_index': reference, 'primary_values': family['primary_values'],
                    'partner_values': partners, 'partner_width': width, 'partner_fractions': fractions,
                    'scale': scale.tolist(), 'cap': ((1+cfg['fixed_headroom'])*scale).tolist(),
                    'prediction_utility': utility.tolist(), 'frozen_admission_mask': admitted.tolist(),
                    'normalized_completion_spectra': spectra.tolist(), 'normalized_taskwise_max_gap': gaps.tolist(),
                    'candidate_direct_increment_vectors': direct.tolist(),
                    'lambda_scope': 'Task-vector increments, possibly signed and nonmonotone; no scalar lambda or Delta/g formula applies.',
                    'predicted_value_legacy': value, 'predicted_utility_only': utility_only,
                    'escapes': {'weaker_direct': 'not_evaluated: all already-calibrated primary choices are included; no validated finer event-parameter grid',
                                'fixed_budget': 'not_evaluated: no justified scalar primary contribution for the signed/nonmonotone event families; no unrelated budget imposed'},
                    'joint_behavior_D': 'not_evaluated; value/legacy capacity does not imply behavioral novelty'})
    return {'schema': 1, 'scope': 'Prospective full finite-table mechanism transfer; no continuous-family capacity claim.',
            'grid_configuration': grid, 'main_protocol': cfg, 'calibration_sha256': file_hash(cal_path),
            'calibration_run': cal['run'], 'confirmation_seed': CONFIRM_SEED, 'confirmation_iterations': CONFIRM_N,
            'admission': 'Every model-cap-safe cross admitted before confirmation. Masks never retuned to confirmation outcomes. Each admitted cross must also pass native power checks.',
            'oracle': 'Complete subset/order dynamic program; all retained primary and five old partner sources must retain required competitive task mass, exact finite portfolio cover.',
            'generic_baseline': 'Generic finite optimizer receives the identical native response table, masks, candidates and source constraints; it is the same oracle, so no algorithmic advantage is claimed.',
            'designs': designs}


def jobs_from_design(design):
    grid = design['grid_configuration']; tasks = design['main_protocol']['tasks']
    family_map = {f['id']: f for f in grid['families']}
    jobs = []
    for d in design['designs']:
        family = deepcopy(family_map[d['family']]); family['partner_values'] = d['partner_values']
        settings = {**grid, 'seed': design['confirmation_seed'], 'iterations': design['confirmation_iterations']}
        for task in tasks:
            for i, primary in enumerate(family['primary_values']):
                for j, partner in enumerate(family['partner_values']):
                    value = mechanism_input(d['context'], task, family, i, j, settings)
                    jobs.append({'input': value, 'meta': {**d['context'], 'design_id': d['design_id'], 'family': d['family'],
                        'ecology': d['ecology'], 'task': task['id'], 'primary_index': i, 'partner_index': j,
                        'primary_value': primary, 'partner_value': partner,
                        'strategy': presets()[d['context']['class']]['apl']}})
    return jobs


def csv_write(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def analyze(run):
    design = json.loads((run/'inputs'/DESIGN_NAME).read_text())
    results = json.loads((run/'RESULTS.json').read_text())
    if results['errors'] or any(r is None for r in results['rows']):
        raise ValueError('Failed or incomplete confirmation must remain visible')
    cfg = design['main_protocol']; tasks = [t['id'] for t in cfg['tasks']]
    table = {(r['design_id'], r['task'], r['primary_index'], r['partner_index']): r for r in results['rows']}
    unique = {r['cache_key'] for r in results['rows']}
    critical = float(student_t.ppf(1-.05/(2*len(unique)), CONFIRM_N-1))
    summaries = []; detail = []
    for d in design['designs']:
        cube = np.array([[[table[d['design_id'], q, i, j]['dps_mean'] for q in tasks]
                          for j in range(5)] for i in range(6)])
        se = np.array([[[table[d['design_id'], q, i, j]['dps_se'] for q in tasks]
                       for j in range(5)] for i in range(6)])
        scale = np.array(d['scale']); cap = np.array(d['cap']); mask = np.array(d['frozen_admission_mask'])
        reference = d['reference_primary_index']
        actual, inspect = finite_oracle(cube, mask, reference, scale, cfg, True)
        util, _ = finite_oracle(cube, mask, reference, scale, cfg, False)
        selected_rows, prefix, _ = inspect(d['predicted_value_legacy']['path'])
        ucb_power = bool(np.all((cube+critical*se)[mask] <= cap+TOL))
        upper, lower = cube+critical*se, cube-critical*se
        confidence_rows = []; old = [reference]
        for step in selected_rows:
            new = old+[step['primary_index']]
            old_pairs = [(p,j) for p in old for j in range(5) if mask[p,j]]
            new_pairs = [(p,j) for p in new for j in range(5) if mask[p,j]]
            gain_lower = np.maximum(0, (np.max([lower[p,j] for p,j in new_pairs],axis=0)-
                                       np.max([upper[p,j] for p,j in old_pairs],axis=0))/scale)
            gain_upper = (np.max([upper[p,j] for p,j in new_pairs],axis=0)-
                          np.max([lower[p,j] for p,j in old_pairs],axis=0))/scale
            confidence_rows.append({'primary_index': step['primary_index'], 'gain_lower': gain_lower.tolist(),
                'gain_upper': gain_upper.tolist(), 'gain_threshold_lower_pass': bool(np.asarray(cfg['task_weights']) @
                (gain_lower >= cfg['meaningful_gain']) >= cfg['gain_required_mass'])})
            old = new
        frontier = np.max(cube[reference], axis=0)
        row = {'family': d['family'], 'context_id': d['context']['context_id'], 'class': d['context']['class'],
            'faction': d['context']['faction'], 'race': d['context']['race_label'], 'ecology': d['ecology'],
            'predicted_T_utility': d['predicted_utility_only']['capacity'],
            'predicted_T_value_legacy': d['predicted_value_legacy']['capacity'],
            'native_finite_T_utility': util['capacity'], 'native_finite_T_value_legacy': actual['capacity'],
            'prospective_path_successful_prefix': prefix, 'prospective_path_length': len(selected_rows),
            'prospective_path_all_empirical_pass': prefix == len(selected_rows) and all(actual['initial_checks'].values()),
            'baseline_K': actual['initial_K'], 'baseline_legacy_min_mass': min(actual['initial_source_use'].values()),
            'max_taskwise_completion_gap': max(d['normalized_taskwise_max_gap']),
            'min_admitted_native_cap_margin': float(np.min((cap-cube[mask])/scale)),
            'all_admitted_power_approx_simultaneous_ucb_pass': ucb_power,
            'future_crosses_frozen_admitted': int(mask.sum()),
            'confirmed_excluded_but_empirically_safe': int(np.sum((~mask)&np.all(cube<=cap,axis=2))),
            'weaker_direct_escape': 'not_evaluated', 'fixed_budget_escape': 'not_evaluated', 'T_joint_D': 'not_evaluated',
            'status': 'completed_finite_native_confirmation', 'scope': 'Finite five-candidate primary family; native means and frozen masks, not continuous oracle capacity.'}
        summaries.append(row)
        detail.append({'design_id': d['design_id'], 'summary': row, 'confirmed_mean_utility': cube.tolist(),
                       'confirmed_standard_errors': se.tolist(), 'native_finite_oracle': actual,
                       'native_utility_only_oracle': util, 'frozen_path_rows': selected_rows,
                       'frozen_path_gain_intervals': confidence_rows, 'confirmed_initial_frontier': frontier.tolist(),
                       'max_model_mean_error': float(np.max(abs(cube-np.asarray(d['prediction_utility']))))})
    comparisons = []
    for cid in sorted({r['context_id'] for r in summaries}):
        a = next(r for r in summaries if r['context_id']==cid and r['ecology']=='large_gap')
        b = next(r for r in summaries if r['context_id']==cid and r['ecology']=='dense')
        ad = next(r for r in detail if r['design_id']==cid+'__large_gap')
        bd = next(r for r in detail if r['design_id']==cid+'__dense')
        baseline_diff = float(np.max(abs(np.array(ad['confirmed_initial_frontier'])-np.array(bd['confirmed_initial_frontier']))))
        comparisons.append({'family':a['family'],'context_id':cid,'class':a['class'],'faction':a['faction'],
            'predicted_gap_T':a['predicted_T_value_legacy'],'predicted_dense_T':b['predicted_T_value_legacy'],
            'native_gap_T':a['native_finite_T_value_legacy'],'native_dense_T':b['native_finite_T_value_legacy'],
            'gap_prospective_prefix':a['prospective_path_successful_prefix'],'dense_prospective_prefix':b['prospective_path_successful_prefix'],
            'native_capacity_separation':a['native_finite_T_value_legacy']-b['native_finite_T_value_legacy'],
            'baseline_max_absolute_dps_difference':baseline_diff,'same_partner_count':True,
            'baseline_K_gap':a['baseline_K'],'baseline_K_dense':b['baseline_K'],
            'weaker_direct_escape':'not_evaluated','fixed_budget_escape':'not_evaluated',
            'mechanism_scope':'Measured event/resource family; completion response is a task vector, not a globally ordered scalar.'})
    progress = json.loads((run/'PROGRESS.json').read_text())
    artifact = {'schema':1,'run':str(run),'design_sha256':file_hash(run/'inputs'/DESIGN_NAME),
        'protocol_sha256':file_hash(run/'PROTOCOL.json'),'results_sha256':file_hash(run/'RESULTS.json'),
        'logical_cells':len(results['rows']),'retained_physical_receipts':len(unique),
        'physical_battles':len(unique)*CONFIRM_N,'progress':progress,'comparisons':comparisons,'details':detail,
        'student_t_critical':critical,'confidence_scope':'Approximate simultaneous two-sided cell t intervals; max-frontier interval propagation, no population exactness or behavioral-D certificate.',
        'selection_scope':'Frozen path prefix is prospective. Native finite oracle is a complete-table empirical reoptimization, not a preselected path claim.',
        'interventions_scope':'No unvalidated primary interpolation or unrelated signed budget used. Main scalar study owns its two escape tests.'}
    out=setup_paths()/'artifacts'/STAGE
    atomic_json(out/'MECHANISM_CAPACITY_CONFIRMATION.json',artifact)
    atomic_json(run/'MECHANISM_CAPACITY_CONFIRMATION.json',artifact)
    csv_write(out/'MECHANISM_CAPACITY_RESULTS.csv',summaries)
    csv_write(out/'MECHANISM_DIVERSITY.csv',comparisons)
    print(json.dumps({k:v for k,v in artifact.items() if k!='details'},indent=2),flush=True)
    return artifact


def self_test():
    # One task, old1.00; two small updates are possible and all legacy sources
    # stay within5%. This independently fixes the finite oracle's expected path.
    cfg={'task_weights':[1.], 'fixed_headroom':.05,'legacy_epsilon':.05,'legacy_required_mass':.05,
         'portfolio_coverage':.95,'portfolio_K':1,'meaningful_gain':.01,'gain_required_mass':1.}
    u=np.array([[[1.]],[[1.02]],[[1.04]]]);m=np.ones((3,1),bool)
    r,_=finite_oracle(u,m,0,np.array([1.]),cfg)
    assert r['capacity']==2 and r['path']==[1,2]
    cfg2={**cfg,'legacy_epsilon':.015}
    r,_=finite_oracle(u,m,0,np.array([1.]),cfg2)
    ru,_=finite_oracle(u,m,0,np.array([1.]),cfg2,False)
    assert r['capacity']==0 and ru['capacity']==2
    assert minimum_portfolio(np.array([[1.,0.],[0.,1.]]),np.ones(2),np.ones(2),.05,[.5,.5],.95)==2


def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=32)
    p.add_argument('--resume',action='store_true');p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--analyze-only',action='store_true');args=p.parse_args()
    self_test();root=setup_paths();out=root/'artifacts'/STAGE;out.mkdir(parents=True,exist_ok=True)
    run=root/'runs'/STAGE/RUN_ID
    if args.analyze_only: analyze(run);return
    design_path=out/DESIGN_NAME
    if design_path.exists():
        design=json.loads(design_path.read_text())
        if canonical_hash(design)!=canonical_hash(build_design()):
            raise ValueError('Existing frozen mechanism design differs; do not overwrite')
    else:
        design=build_design();atomic_json(design_path,design)
    jobs=jobs_from_design(design)
    print(json.dumps({'logical_cells':len(jobs),'unique_inputs':len({canonical_hash(j['input']) for j in jobs}),
        'predictions':[{k:d[k] for k in ('design_id','partner_width','reference_primary_index')}|{
            'T_utility':d['predicted_utility_only']['capacity'],'T_value_legacy':d['predicted_value_legacy']['capacity'],
            'path':d['predicted_value_legacy']['path']} for d in design['designs']]},indent=2),flush=True)
    if args.prepare_only:return
    selected={d['context']['class'] for d in design['designs']}
    inputs={p[k]:engine_root()/p[k] for cls,p in presets().items() if cls in selected for k in ('gear','apl')}
    inputs[DESIGN_NAME]=design_path;inputs[CAL_NAME]=out/CAL_NAME
    run=run_jobs(jobs,RUN_ID,{'purpose':design['scope'],'prospective_design_sha256':file_hash(design_path),
        'tasks':design['main_protocol']['tasks'],'seed':CONFIRM_SEED,'iterations':CONFIRM_N,
        'full_domain':'All six declared primaries and five old partners, both matched ecologies, six contexts, eight tasks.',
        'no_retuning':'Frozen cap,scale,admission,thresholds,source identities,candidate set and predicted sequence remain fixed.'},
        workers=args.workers,resume=args.resume,source_paths=[Path(__file__),
            SOURCE_ROOT/'src/wowfs/experiments/fc_mechanisms.py',SOURCE_ROOT/'src/wowfs/experiments/fc_calibration.py',
            SOURCE_ROOT/'src/wowfs/experiments/r3_affine.py',SOURCE_ROOT/'configs/fc_mechanisms.json',
            SOURCE_ROOT/'configs/final_completion_capacity.json',SOURCE_ROOT/'configs/fc_presets.json',
            SOURCE_ROOT/'configs/official_contexts.yaml'],input_artifacts=inputs)
    analyze(run)


if __name__=='__main__':main()
