"""Prospective native checkpoints and full finite non-affine confirmation.

Unexecuted affine crosses remain explicitly interpolated, never counted as
native calls. Interpolation is conditional on independent per-seed validation.
"""
import argparse
import json
from pathlib import Path

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json
from wowfs.experiments.fc_native import STAGE, run_jobs
from wowfs.experiments.fc_calibration import stat_input
from wowfs.experiments.r2_native import file_hash


def prepare():
    root = setup_paths(); out = root/'artifacts'/STAGE
    plan = json.loads((out/'FUTURE_SEQUENCE_DESIGN.json').read_text())
    old = json.loads((out/'OLD_ECOLOGY_ANALYSIS.json').read_text())
    cfg = json.loads((out/'FROZEN_MAIN_PROTOCOL.json').read_text())
    # The maintained task definitions are imported separately and their hash
    # is frozen by run_jobs. The reference is the fixed strongest old gear.
    tasks = cfg['tasks']
    if [t['id'] for t in tasks] != old['tasks']:
        raise ValueError('Frozen task order differs from old analysis')
    baselines = {c['context_id']: c for c in old['contexts']}
    jobs = []; selected = []
    for ctx in plan['contexts']:
        base = baselines[ctx['context_id']]
        native = {**base, **ctx}; unit = base['U']
        affine = bool(base['affinity_validated'])
        points = {}
        def add(p, x, role):
            key = (round(float(p), 14), round(float(x), 14))
            points.setdefault(key, []).append(role)
        add(0, 0, 'fit_zero')
        add(.148, 0, 'fit_high')
        add(0, .044, 'fixed_old_reference')
        add(.104, 0, 'blocked_probe_not_exhaustive_proof')
        for seq in ctx['sequences']:
            guarded = 'interior' in seq['name'] or 'robust' in seq['name']
            xs = seq['partner_coefficients']
            if not affine and not guarded:
                selected.append({'context_id':ctx['context_id'], 'sequence':seq['name'],
                                 'status':'not_run_nonaffine_exact_path', 'rounds':[]})
                continue
            indices = list(range(len(seq['primary_coefficients']))) if guarded or not affine else sorted(set([0, len(seq['primary_coefficients'])-1]))
            for index in indices:
                p = seq['primary_coefficients'][index]
                if not affine:
                    for x in xs: add(p, x, seq['name']+':round'+str(index+1)+':full_cross')
                else:
                    row = seq['rows'][index]
                    x = xs[row['predicted_frontier_partner_index']]
                    # Even if the candidate fails a prediction check, record it
                    # as a tested candidate, not an admitted successful update.
                    add(p, x, seq['name']+':round'+str(index+1)+':frontier_checkpoint')
            if not affine:
                for x in xs: add(0, x, seq['name']+':old_complete_library')
            selected.append({'context_id':ctx['context_id'], 'sequence':seq['name'],
                             'status':'affine_checkpoints' if affine else 'full_crosses',
                             'rounds':[i+1 for i in indices]})
        for task in tasks:
            for (p,x), roles in sorted(points.items()):
                jobs.append({'input':stat_input(native, task, p*unit, x*unit,
                    seed=820000001, iterations=512, debug=True),
                    'meta':{k:native[k] for k in ('context_id','class','faction','race','native_racial_incomplete')} |
                    {'task':task['id'],'primary_coefficient':p,'partner_coefficient':x,
                     'stat_unit':unit,'roles':roles,'affine_development':affine}})
    science = {
        'phase':'Independent frozen completion-capacity confirmation',
        'seed':820000001,'iterations':512,'tasks':tasks,'selected':selected,
        'fixed_reference':'The same old primary and strongest old partner define population task scales s_q. Cap is 1.05*s_q and meaningful gain is .01*s_q. Independent paired reference observations estimate this fixed comparator; it is never replaced by a future optimum.',
        'calibration_numeric_cap_sensitivity':'Also report safety against the absolute numeric cap estimated from128 development battles, separately from the paired population-reference estimand.',
        'admission':'All masks frozen from old-development response before confirmation; confirmation never readmits unsafe or excluded pairs.',
        'affine_scope':'Fit independent zero/high per-seed responses; check all independently executed allocation/frontier checkpoints and recursive controls. Reoptimize all old/new crosses using interpolation only if validation passes at1e-8. Every interpolated cross is labeled, not counted as executed.',
        'nonaffine_scope':'All guarded-path old/new crosses executed; exact endpoint paths are not_run. No continuous capacity upper bound from failed scalar fits.',
        'statistical_plan':{'alpha':.05,'method':'Paired Student-t contrasts with Bonferroni over all finite cross-task pairs and cap/source contrasts within context and all sequence variants. Approximate Monte Carlo intervals, not distribution-free certificates.',
                            'unit':'Matched ecology/family is scientific unit; combat seeds estimate simulation noise only.',
                            'behavior':'Original Warrior seven-coordinate D at delta .05 as a mean diagnostic. Other classes: distinct five physical damage-share diagnostic; original D not applicable, joint capacity unassessed.'},
        'outcome_handling':'Unresolved thresholds and failed prefixes retained. A failed tested path is not a proof of zero optimal capacity. Continuous scalar upper bounds conditional on mapping are separate from achieved finite paths.',
    }
    return jobs, science


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--workers',type=int,default=32)
    parser.add_argument('--resume',action='store_true'); parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args(); root=setup_paths(); out=root/'artifacts'/STAGE
    jobs,science=prepare()
    if args.prepare_only:
        print(json.dumps({'logical_cells':len(jobs),'requested_battles':sum(j['input']['request']['simOptions']['iterations'] for j in jobs),
                          'selected_sequences':len(science['selected'])},indent=2)); return
    artifacts={p:out/p for p in ('FUTURE_SEQUENCE_DESIGN.json','OLD_ECOLOGY_ANALYSIS.json','FROZEN_MAIN_PROTOCOL.json','THEORY_PREDICTIONS.csv')}
    run=run_jobs(jobs,'capacity-confirmation-v1',science,workers=args.workers,resume=args.resume,
        source_paths=[Path(__file__),SOURCE_ROOT/'src/wowfs/experiments/fc_calibration.py',
                      SOURCE_ROOT/'src/wowfs/experiments/fc_planner.py',SOURCE_ROOT/'configs/fc_presets.json',
                      SOURCE_ROOT/'configs/final_completion_capacity.json'],input_artifacts=artifacts)
    print(run)


if __name__=='__main__': main()
