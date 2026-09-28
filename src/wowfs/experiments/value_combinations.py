"""Low-cost line B comparison on unchanged, complete R4 native domains."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.value_native import load_decision_ecologies
from wowfs.experiments.value_admission import decision_metrics, solve_gain_subset

PAIRS = {
    'static_skill': [('12590','17068')],
    'timing_extra': [('18203','19951')],
    'timing_shared': [('18203','19019'),('19019','22268')],
    'resource_haste': [('19951','22000')],
}


def compare(ecology, release, seconds=20):
    e=ecology; p,indices=e.problem(release)
    labels=sorted(set.union(set(),*map(set,p.sources)))
    features=np.array([[s in ss for s in labels] for ss in p.sources],float)
    singleton={}; risk=np.zeros(len(labels))
    for source in release:
        single, _=e.problem([source])
        raw=single.best.max(axis=0)
        safe=single.best[single.safe|single.protected].max(axis=0)
        normalized=(raw-e.scale)/e.scale
        risk[labels.index(source)]=max(0.,float(normalized.max()))/.05
        singleton[source]={'unrestricted_gain':normalized.tolist(),
            'all_safe_gain':((safe-e.scale)/e.scale).tolist(),
            'positive_singleton_risk_price':float(risk[labels.index(source)])}
    structured=(features@risk<=1+1e-9)
    masks={'natural_complete':np.ones(len(indices),bool),
           'all_power_safe_reference':p.safe|p.protected,
           'singleton_increment_budget':structured}
    details=[]
    for method,mask in masks.items():
        metrics=decision_metrics(p,mask)
        details.append({'method':method,'metrics':metrics,'admitted':mask.tolist(),
            'rule':({'rows':1,'features':labels,'prices':risk.tolist(),
                'scope':'Development rule from full old plus singleton responses; no claimed safe composition theorem.'}
                if method=='singleton_increment_budget' else None)})
    for method,rows in [('matched_generic_1row',1),('arbitrary_subset',0)]:
        solved=solve_gain_subset(p,time_limit=seconds,per_witness_limit=5.,
                                 rule_rows=rows,features=features)
        details.append({'method':method,'solver':solved,
                        'metrics':solved['result']['metrics'] if solved['feasible'] else None,
                        'admitted':solved['result']['admitted'] if solved['feasible'] else None})
    safe_gain=(p.best[p.safe|p.protected].max(axis=0)-e.scale)/e.scale
    residual=safe_gain-sum(np.maximum(singleton[s]['all_safe_gain'],0) for s in release)
    return {'pool':e.pool['id'],'race':e.race,'release':list(release),
        'task_ids':[t['id'] for t in e.tasks],'policies':e.policies,
        'gear_ids':[e.gear_ids[i] for i in indices],
        'complete_domain_size':len(indices),'old_domain_size':int(p.protected.sum()),
        'legacy_source_registry':list(p.protected_sources),
        'initial_source_ids':sorted(set.union(set(),*[s for s,old in zip(p.sources,p.protected) if old])),
        'singleton':singleton,'safe_batch_minus_sum_safe_single_gain':residual.tolist(),
        'safe_batch_gain':safe_gain.tolist(),'methods':details,
        'scope':'Adaptive development comparison selected from previously observed R4 table,16 seeds/cell; no fresh validation or population certificate.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=20)
    args=parser.parse_args();root=setup_paths();out=root/'artifacts/decisive-value'
    run=root/'runs/decisive-value/combination-screen-v1';run.mkdir(parents=True,exist_ok=True)
    protocol={'created_utc':datetime.now(timezone.utc).isoformat(),
        'analysis_only':True,'native_calls':0,'source_run':str(root/'runs/r4-foundational-discovery/baseline-v1'),
        'selection':'Development-selected pairs from complete16-seed native tables; no prospective confirmation claim.',
        'pairs':PAIRS,'gain_threshold':.01,'gain_mass':.125,'cap_multiplier':1.05,
        'comparison':'Same native table, all16 old gears and3 policies protected; D reported separately from G.',
        'methods':['natural_complete','all_power_safe_reference','singleton_increment_budget','matched_generic_1row','arbitrary_subset']}
    atomic_json(run/'PROTOCOL.json',protocol)
    records=[]
    for e in load_decision_ecologies(PAIRS):
        for pair in PAIRS[e.pool['id']]:
            record=compare(e,pair,args.seconds);records.append(record)
            atomic_json(out/'LINE_B_COMBINATIONS.json',records)
            for d in record['methods']:
                m=d['metrics'];print(json.dumps({'pool':record['pool'],'race':record['race'],
                    'release':pair,'method':d['method'],'status':d.get('solver',{}).get('status','evaluated'),
                    'joint_G':m['all_seven_pass'] if m else None,
                    'gain':max(m['normalized_gain']) if m else None}),flush=True)
    rows=[]
    for r in records:
        for method in r['methods']:
            m=method['metrics'];rows.append({'pool':r['pool'],'race':r['race'],
                'release':'|'.join(r['release']),'method':method['method'],
                'solver_status':method.get('solver',{}).get('status','evaluated'),
                **{k:m[k] if m else None for k in ['P','N','D','L','H','C','G','K','all_seven_pass','gain_mass']},
                'max_gain':max(m['normalized_gain']) if m else None,
                'complete_domain':r['complete_domain_size'],'old_domain':r['old_domain_size'],
                'physical_new_calls':0,'scope':'cached16seed_development'})
    with (out/'LINE_B_COMBINATIONS.csv').open('w') as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    atomic_json(run/'RESULTS.json',{'analysis_only':True,'native_calls':0,'records':records})


if __name__=='__main__':main()
