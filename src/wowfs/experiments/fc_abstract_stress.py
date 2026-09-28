"""Exact mathematical stress cases; never native outcomes or class coverage."""
import csv
import hashlib
import json
from pathlib import Path

from wowfs.experiments.fc_theory import q, continuous_value_capacity, inspect_sequence
from wowfs.experiments.fc_planner import optimal_value_sequence
from wowfs.paths import setup_paths, atomic_json


def scalar_case(name, dimension, partners, *, headroom='.05', gain='.01',
                minimum_increment='.0502', relevance='.05'):
    xs=list(map(q,partners));a0=1-max(xs);tau=1+q(headroom);g=q(gain);e=q(relevance)
    amin=a0+q(minimum_increment)
    model=continuous_value_capacity(xs,a0,amin,tau,g)
    bands=model['intervals']
    initial_ok=max(xs)-min(xs)<=e
    restricted=[dict(b,upper=min(b['upper'],1+e)) for b in bands]
    # The old primary cannot gain a new partner in this model, so L alone
    # bounds the final frontier by its unchanged best1 plus e.
    restricted=[b for b in restricted if b['upper']>b['lower'] or
                (b['upper']==b['lower'] and b['lower_closed'])]
    values=optimal_value_sequence(restricted,gain=g)
    primaries=[]
    for y in values:
        choices=[b for b in restricted if y<=b['upper'] and
                 (y>b['lower'] or (y==b['lower'] and b['lower_closed']))]
        primaries.append(y-max(b['partner'] for b in choices))
    rows=inspect_sequence(xs,a0,primaries,tau,g,e) if initial_ok else []
    prefix=0
    for row in rows:
        if not row['value_joint']:break
        prefix+=1
    upper=len(values) if initial_ok else None
    certified=initial_ok and prefix==upper
    result={'case':name,'stress_axis':dimension,'scope':'abstract_exact_not_native',
        'native_calls':0,'executed_class_race_contexts':0,'partner_count':len(xs),
        'partner_values':[str(x) for x in xs],'h':str(q(headroom)),'g':str(g),
        'lambda':str(q(minimum_increment)),'e':str(e),'delta':str(model['delta']),
        'raw_gap_formula':model['unqualified_gap_prediction'],
        'continuous_value_capacity':model['value_capacity'],
        'direct_capacity':model['direct_capacity'],'accessible_gap_capacity':model['gap_capacity'],
        'initial_all_sources_relevant':initial_ok,
        'retained_capacity_lower':prefix if initial_ok else None,
        'retained_capacity_upper':upper,
        'retained_capacity_exact':prefix if certified else None,
        'retained_bound_reason':'continuous value bands clipped by unavoidable old-primary L bound; exact only if displayed full-source path attains it',
        'primary_path':[str(x) for x in primaries],
        'frontier_path':[str(r['frontier']) for r in rows],
        'path_failure_checks':[{k:v for k,v in r['checks'].items() if not v} for r in rows],
        'D_status':'not_defined_scalar_model','T_joint':None,
        'status':'exact_value_and_retention' if certified else
                 'invalid_initial_source_obligations' if not initial_ok else 'retention_interval_unresolved'}
    return result


def cases():
    large=['0','.0001','.0002','.0003','.044']
    dense=['0','.011','.022','.033','.044']
    result=[]
    for name,xs in [('large',large),('dense',dense)]:
        for g in ['.005','.01','.015','.02']:
            result.append(scalar_case(f'{name}_g_{g}','gain',xs,gain=g))
        for h in ['.03','.04','.05','.06']:
            result.append(scalar_case(f'{name}_h_{h}','headroom',xs,headroom=h))
        for lam in ['.005','.01','.03','.0502','.07','.10']:
            result.append(scalar_case(f'{name}_lambda_{lam}','incoming_minimum',xs,minimum_increment=lam))
    for n in [2,3,5,9]:
        result.append(scalar_case(f'uniform_count_{n}','partner_count',
                                 [q('.044')*i/(n-1) for i in range(n)]))
    for e in ['.025','.044','.05','.07']:
        result.append(scalar_case(f'legacy_e_{e}','legacy_tolerance',dense,relevance=e))
    for name,xs in [('cluster_low',large),('uniform',dense),
                    ('largest_gap_low',['0','.02','.028','.036','.044']),
                    ('cluster_high',['0','.0437','.0438','.0439','.044'])]:
        result.append(scalar_case('density_'+name,'gap_location_and_density',xs))
    boundary=scalar_case('continuous_four_partner_L_obstruction','legacy_boundary',
                        [0,'.06','.08','.10'],headroom='.10',gain='.02',
                        minimum_increment='.1001',relevance='.10')
    boundary.update(retained_capacity_lower=2,retained_capacity_upper=2,retained_capacity_exact=2,
                    primary_path=['1.06','1.02'],frontier_path=['1.06','1.10'],
                    path_failure_checks=[{},{}],status='continuous_proof_in_THEORY_section4',
                    retained_bound_reason='separate continuous legacy impossibility proof, including nonmonotone releases')
    result.append(boundary)
    behavior=scalar_case('single_physical_channel_D_zero','behavior_boundary',large)
    behavior.update(D_status='one actual damage channel; all normalized profiles identically(1), distance0',
                    T_joint=0,status='exact_behavior_counterexample_not_native')
    result.append(behavior)
    result.append({'case':'heterogeneous_partner_order','stress_axis':'task_heterogeneity_boundary',
                   'scope':'abstract_exact_not_native'})
    return result


def main():
    root=setup_paths();out=root/'artifacts/final-completion-capacity'
    rows=cases()
    # This boundary has no scalar Delta; do not invent a number or interpret a
    # generalized vector statistic as the theorem's exact quantity.
    rows[-1]={'case':'heterogeneous_partner_order','stress_axis':'task_heterogeneity_boundary',
        'scope':'abstract_exact_not_native','native_calls':0,'executed_class_race_contexts':0,
        'status':'scalar_theorem_not_applicable',
        'partner_values':['(0,.044)','(.044,0)'],
        'D_status':'not_assessed','T_joint':None,
        'reason':'Two tasks order the same partners oppositely; no common scalar positive-slope partner spectrum. No capacity value is asserted.'}
    payload={'schema':1,'scope':'abstract exact arithmetic only; zero native calls and class/race coverage',
             'native_calls':0,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'design':'Deterministic mathematical axes specified in source; no future native outcomes read or fitted.',
             'rows':rows}
    atomic_json(out/'ABSTRACT_STRESS.json',payload)
    keys=sorted({key for row in rows for key in row})
    with (out/'ABSTRACT_STRESS.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        writer.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)
    print(json.dumps({'rows':len(rows),'native_calls':0,'file':str(out/'ABSTRACT_STRESS.csv')}))


if __name__=='__main__':main()
