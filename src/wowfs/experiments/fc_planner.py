"""Prospective completion sequences from old native data only; no native calls.

Exact rational interval optimization concerns the fitted scalar model. Native
confirmation and original D are separate. All masks and amplitudes are frozen
before future response outcomes are read.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from wowfs.experiments.fc_theory import q, ceil_q
from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json

STAGE = 'final-completion-capacity'
G, CAP, EPS = q('.01'), q('1.05'), .05
STRONG_MIN, MAX_PRIMARY = q('.0502'), q('.104')
CORRECTED_BUDGET_INTERIOR = ['.05218', '.05165', '.05120']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scalar_bands(partners, ratio, minimum, maximum=MAX_PRIMARY, rule='power_only'):
    """All optimized-value branches under bounded amplitude and fixed rules.

    Partner and primary coefficients are in physical units U. Equalities admit
    the next stronger partner, hence branch lower endpoints are often open.
    """
    xs = list(map(q, partners)); r = q(ratio)
    if r <= 0:
        raise ValueError('A positive native slope ratio is required')
    a0 = 1-q('.044')*r
    total_cap = q('.044')+q('.05')/r
    bands = []
    for i,x in enumerate(xs):
        upper = min(q(maximum), total_cap-x)
        if rule == 'budget12':
            upper = min(upper, (q('.648')-x)/12)
        if i+1 < len(xs):
            boundary = total_cap-xs[i+1]
            if rule == 'budget12':
                boundary = min(boundary, (q('.648')-xs[i+1])/12)
            lower = max(q(minimum), boundary)
            closed = q(minimum) > boundary
        else:
            lower, closed = q(minimum), True
        if lower < upper or (lower == upper and closed):
            bands.append({'partner_index':i, 'partner':x,
                          'primary_lower':lower, 'primary_upper':upper,
                          'lower':a0+r*(lower+x), 'upper':a0+r*(upper+x),
                          'lower_closed':closed})
    return bands


def optimal_value_sequence(bands, gain=G, initial=q(1)):
    """Exact continuous maximum cardinality by greedy selection from the end.

    Every band has a closed upper endpoint. Replacing a sequence's last value
    by the largest attainable one cannot hurt any preceding gain. Repeating
    the exchange argument proves the upper bound and gives a realizing path.
    """
    ceiling = max((b['upper'] for b in bands), default=initial)
    reverse = []
    while True:
        options = []
        for b in bands:
            value = min(b['upper'], ceiling)
            if value > b['lower'] or (value == b['lower'] and b['lower_closed']):
                if value >= initial+gain:
                    options.append(value)
        if not options:
            return list(reversed(reverse))
        value = max(options); reverse.append(value); ceiling = value-gain


def realize_values(values, bands, ratio):
    r=q(ratio);a0=1-q('.044')*r; primaries=[]
    for value in values:
        choices=[b for b in bands if value <= b['upper'] and
                 (value > b['lower'] or (value == b['lower'] and b['lower_closed']))]
        if not choices:
            return None
        # The least amplitude among equal-value realizations maximizes access
        # to higher partner sources. Source usefulness is still checked below.
        b=max(choices,key=lambda b:b['partner'])
        primaries.append((value-a0)/r-b['partner'])
    return primaries


def portfolio(utilities, optimum, scales, weights):
    """Exact finite task-cover size (8 tasks), with declared 95% mass target."""
    masks=[]
    for row in utilities:
        mask=sum(1<<i for i,v in enumerate(row) if v >= optimum[i]-.05*scales[i]-1e-9)
        masks.append(mask)
    solutions={0:()}
    for idx,mask in enumerate(masks):
        for covered,path in list(solutions.items()):
            combined=covered|mask;candidate=path+(idx,)
            if combined not in solutions or len(candidate)<len(solutions[combined]):
                solutions[combined]=candidate
    choices=[v for mask,v in solutions.items()
             if sum(w for i,w in enumerate(weights) if mask&(1<<i))>=.95-1e-12]
    return min(choices,key=len) if choices else None


def inspect_plan(context, ecology, primary_coefficients, rule, weights):
    """Taskwise predictions plus all old/new scalar source obligations."""
    old=context['regimes'][ecology]
    xs=np.asarray(old['partner_coefficients'],dtype=float)
    U=context['U'];B=np.asarray(context['B']);c=np.asarray(context['c'])
    s=np.asarray(context['s_q']);caps=np.asarray(context['caps'])
    old_values=np.asarray(old['values'],dtype=float)
    before=old_values.max(axis=0);history=np.ones((1,len(xs)),dtype=bool)
    primaries=[0.];rows=[];prefix=0;failed=False
    for step,p in enumerate(primary_coefficients,1):
        primaries.append(float(p))
        predicted=B+c*(U*(np.asarray(primaries)[:,None]+xs[None,:]))[:,:,None]
        predicted[0]=old_values  # complete observed old library, never a selected witness
        mask=np.all(predicted<=caps+1e-9,axis=2)
        if rule=='budget12':mask &= 12*np.asarray(primaries)[:,None]+xs[None,:]<=.648+1e-12
        admitted=predicted[mask]
        optimum=admitted.max(axis=0)
        source_best={}
        for i in range(len(primaries)):
            source_best['old_primary' if i==0 else f'primary_{i}']=(predicted[i][mask[i]].max(axis=0)
                if mask[i].any() else np.full(len(s),-np.inf))
        for j in range(len(xs)):
            source_best[f'partner_{j}']=(predicted[:,j][mask[:,j]].max(axis=0)
                if mask[:,j].any() else np.full(len(s),-np.inf))
        masses={name:float(np.sum(np.asarray(weights)*(values>=optimum-.05*s-1e-9)))
                for name,values in source_best.items()}
        gain=(optimum-before)/s
        cover=portfolio(admitted,optimum,s,weights)
        checks={'P':bool(np.all(optimum<=caps+1e-9)),
                'N':masses[f'primary_{step}']>=.05-1e-12,
                'L':all(m>=.05-1e-12 for name,m in masses.items() if name!=f'primary_{step}'),
                'H':bool(np.all(mask[:-1][history])),
                'C':cover is not None and len(cover)<=4,
                'G':float(np.sum(np.asarray(weights)*(gain>=.01-1e-10)))>=.125-1e-12}
        passed=all(checks.values());failed|=not passed
        if not failed:prefix+=1
        binding=context['tasks'].index(context['binding_effective_task'])
        flat=np.where(mask.ravel(),predicted[:,:,binding].ravel(),-np.inf)
        pi,xi=np.unravel_index(int(np.argmax(flat)),mask.shape)
        scalar=1+(float(np.asarray(primaries)[pi]+xs[xi])-.044)*U/context['U_eff']
        rows.append({'round':step,'primary_coefficient':float(p),'primary_stat':float(p)*U,
                     'admission_mask':mask.tolist(),'admitted_configurations':int(mask.sum()),
                     'complete_configurations':int(mask.size),
                     'predicted_frontier_primary_index':int(pi),'predicted_frontier_partner_index':int(xi),
                     'predicted_frontier_primary_coefficient':primaries[pi],
                     'predicted_frontier_partner_coefficient':float(xs[xi]),
                     'predicted_optimum':optimum.tolist(),'before_optimum':before.tolist(),
                     'scalar_frontier':scalar,'normalized_gain':gain.tolist(),
                     'gain_mass':float(np.sum(np.asarray(weights)*(gain>=.01-1e-10))),
                     'minimum_normalized_cap_margin':float(np.min((caps-optimum)/s)),
                     'source_masses':masses,'checks':checks,'value_legacy_pass':passed,
                     'K':len(cover) if cover is not None else None,
                     'D':'not_established_by_scalar_planner'})
        before=optimum;history=mask
    return rows,prefix


def plan_context(context,weights):
    r=q(context['U'])/q(context['U_eff']);a0=1-q('.044')*r
    sequences=[]
    for name,ecology,rule in [('large_gap','large_gap','power_only'),('dense','dense','power_only'),
                              ('weaker_direct','dense','power_only'),('fixed_budget','dense','budget12')]:
        xs=context['regimes'][ecology]['partner_coefficients']
        minimum=G/r if name=='weaker_direct' else STRONG_MIN
        bands=scalar_bands(xs,r,minimum,rule=rule)
        exact_values=optimal_value_sequence(bands)
        exact=realize_values(exact_values,bands,r)
        if exact is None:raise AssertionError('The exact interval path was not realizable')
        if name in ('large_gap','weaker_direct'):
            targets=[q(1)+q('.011')*i for i in range(1,5)]
            guarded=realize_values(targets,bands,r)
        elif name=='dense':
            guarded=realize_values([q('1.041')],bands,r)
        else:
            guarded=list(map(q,CORRECTED_BUDGET_INTERIOR))
        if guarded is None:
            # Preserve a declared finite control when requested robust targets
            # are unavailable; it is not silently replaced using future data.
            guarded=[]
        gap=max((q(b)-q(a) for a,b in zip(xs,xs[1:])),default=q(0))*r
        for variant,primaries in [('exact',exact),('interior',guarded)]:
            rows,prefix=inspect_plan(context,ecology,primaries,rule,weights)
            affine=bool(context['affinity_validated'])
            sequences.append({'name':name if variant=='exact' else name+'_interior',
                'regime':name,'variant':variant,'ecology':ecology,'rule':rule,
                'primary_coefficients':list(map(float,primaries)),
                'primary_stats':[float(p)*context['U'] for p in primaries],
                'partner_coefficients':xs,'partner_stats':[x*context['U'] for x in xs],
                'minimum_primary_coefficient':float(minimum),'maximum_primary_coefficient':float(MAX_PRIMARY),
                'minimum_primary_increment_U_eff':float(minimum*r),
                'nominal_minimum_primary_coefficient':.01 if name=='weaker_direct' else .0502,
                'continuous_utility_upper':len(exact_values) if affine else None,
                'fitted_scalar_continuous_capacity':len(exact_values),
                'continuous_bound_scope':'Exact for frozen fitted scalar response and bounded family; native validity conditional on response reduction.' if affine else 'not_established: scalar affinity failed',
                'unqualified_gap_formula':min(5,ceil_q(gap/G)) if name in ('large_gap','dense') else None,
                'completion_gap_U_eff':float(gap),
                'accessible_bands':[{k:float(v) if k not in ('partner_index','lower_closed') else v for k,v in b.items()} for b in bands],
                'fitted_value_legacy_successful_prefix':prefix,
                'achieved_value_legacy_lower':prefix if affine else None,
                'value_legacy_capacity_exactly_matched':bool(affine and prefix==len(exact_values) and variant=='exact'),
                'prediction_status':'conditional_affine_prediction' if affine else 'nonaffine_diagnostic_no_theory_prediction',
                'execution_plan':'exact_not_run_nonaffine' if not affine and variant=='exact' else
                    'full_grid_native_nonaffine' if not affine else 'native_anchor_and_checkpoint_validated_interpolation',
                'rows':rows})
    return {k:context[k] for k in ('context_id','class','faction','race','race_label','physical_stat','native_racial_incomplete',
                                  'U','U_eff','s_q','caps','B','c','binding_effective_task','affinity_validated','tasks')} | {
        'ratio_U_over_U_eff':float(r),'scalar_old_primary':float(a0),
        'scalar_cap':1.05,'scalar_gain':.01,'legacy_epsilon':.05,
        'sequences':sequences}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--old-analysis',type=Path)
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    root=setup_paths();out=root/'artifacts'/STAGE
    oldpath=args.old_analysis or out/'OLD_ECOLOGY_ANALYSIS.json'
    destination=args.output or out/'FUTURE_SEQUENCE_DESIGN.json'
    old=json.loads(oldpath.read_text())
    result={'schema':1,'stage':STAGE,'analysis_only':True,'native_calls':0,
        'source_sha256':sha(__file__),'theory_helper_sha256':sha(SOURCE_ROOT/'src/wowfs/experiments/fc_theory.py'),
        'old_analysis_sha256':sha(oldpath),'old_analysis_path':str(oldpath),
        'tasks':old['tasks'],'task_definitions':old['task_definitions'],'task_weights':old['task_weights'],
        'gain_threshold':.01,'gain_required_mass':.125,'legacy_epsilon':.05,'legacy_required_mass':.05,
        'scalar_interval_arithmetic':'Exact rational arithmetic on frozen decimal old-data estimates; numerical mask tolerance1e-9 DPS and1e-12 budget only.',
        'cap_estimand':'1.05 times the fixed initial strongest-configuration expected task utility; unknown population reference is measured independently at confirmation. Calibration numeric cap sensitivity reported separately.',
        'weaker_direct_minimum':'p_min=.01/(U/U_eff), chosen from old data so the normalized minimum direct increment equals g; nominal physical .01 may shift.',
        'prototype_erratum':{'source':'fc_capacity.py GUARDED_PATHS fixed_budget_interior',
            'unexecuted_primary_coefficients':[.0545,.0545-.011/12,.0545-.022/12],
            'reason':'The first prototype has12p>.648 even with partner0 and is inadmissible. It was never executed as a future sequence.',
            'prospective_replacement':list(map(float,CORRECTED_BUDGET_INTERIOR)),
            'frozen_original_modified':False},
        'coverage_scope':'51 validated affine contexts receive conditional continuous predictions; five nonaffine Warlock contexts have finite diagnostic attempts and no theorem bound. Exact paths for nonaffine contexts are not_run, not zero.',
        'physical_confirmation_scope':'Affine full-grid responses may be derived from independent per-seed anchors only after checks against directly executed checkpoints. Derived cells are labeled interpolated, never native-call counts.',
        'contexts':[plan_context(c,old['task_weights']) for c in old['contexts']]}
    if destination.exists():
        if json.loads(destination.read_text())!=result:raise ValueError('Frozen future plan differs; use a new output/run version')
    else:atomic_json(destination,result)
    csvpath=destination.with_name('THEORY_PREDICTIONS.csv')
    columns=['context_id','class','faction','race','affinity_validated','name','variant','ecology','rule',
             'completion_gap_U_eff','unqualified_gap_formula','continuous_utility_upper',
             'fitted_scalar_continuous_capacity','fitted_value_legacy_successful_prefix',
             'value_legacy_capacity_exactly_matched','prediction_status','execution_plan']
    with csvpath.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for c in result['contexts']:
            for s in c['sequences']:writer.writerow({k:(c[k] if k in c else s.get(k)) for k in columns})
    print(json.dumps({'path':str(destination),'contexts':len(result['contexts']),
                      'sequences':sum(len(c['sequences']) for c in result['contexts']),
                      'native_calls':0},indent=2))


if __name__=='__main__':main()
