#!/usr/bin/env python3
"""Recheck the declared 18-sequence construction using its frozen source snapshot."""
from pathlib import Path
import argparse, json, collections, hashlib, os, sys
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run-dir', type=Path)
args = parser.parse_args()
source = Path(__file__).resolve().parents[1]
work = Path(os.environ.get('WOWFS_WORK_ROOT', source.parent.parent / 'wow-forever-sustainability-work'))
run = (args.run_dir or Path(json.loads((work / 'runs/LATEST.json').read_text())['run_dir'])).resolve()
if run.is_relative_to(source):
    parser.error('Audit output must remain outside the source repository')
sys.path.insert(0, str(run / 'source_snapshot'))
from wowfs.experiments.exact import build_domain, METHODS
data=[json.loads(p.read_text())['result'] for p in sorted((run/'checkpoints').glob('*.json'))]
assert len(data)==18

def prefix(rows):
    s=0
    for row in sorted(rows,key=lambda x:x['round']):
        if row['status']!='pass': break
        s+=1
    return s

summary={'run_id':run.name,'instances':len(data),'independent_pools':9,
         'methods':{},'trade_certificates':{},'order_effects':{},'first_failures':{},'by_variant':{}}
certificate_counts=[]
matched_equal_count=0
first_failures=[]
index={}
for r in data:
    e=r['evidence']; variant=e['variant']; seed=e['seed']
    d=build_domain(seed,variant)
    assert hashlib.sha256(d.response.tobytes()).hexdigest()==e['table_sha256']
    index[(variant,seed)]=r
    for t in range(1,7):
        rule_by_method={x['method']:x for x in r['rules'] if x['round']==t}
        assert rule_by_method['structured_hyperedges']['admitted_ids']==rule_by_method['generic_matched_budget']['admitted_ids']==rule_by_method['safe_set_envelope']['admitted_ids']
        matched_equal_count+=1
    for feasibility in r['feasibility']:
        if feasibility['solver_status']!='infeasible_exact_trade_certificate': continue
        t=feasibility['round']; visible=d.visible_ids(t)
        safe=np.all(d.response[visible]<=d.cap[None,None,:]+1e-12,axis=(1,2))
        new=d.configurations[visible,d.order[t-1]]==2
        cert=feasibility['certificate']
        rule=next(x for x in r['rules'] if x['round']==t and x['method']==feasibility['method'])
        witnesses=cert['witnesses_local_ids']
        assert set(x[0] for x in witnesses)==set(np.flatnonzero(safe&new))
        for p,h,q,z in witnesses:
            assert safe[p] and new[p] and int(visible[h]) in rule['registered_before']
            assert not safe[q] and not safe[z]
            np.testing.assert_array_equal(d.incidence[visible[p]]+d.incidence[visible[h]],d.incidence[visible[q]]+d.incidence[visible[z]])
        certificate_counts.append({'variant':variant,'seed':seed,'round':t,'method':feasibility['method'],'witnesses':len(witnesses)})
    for method in METHODS:
        rows=[x for x in r['rounds'] if x['method']==method]
        s=prefix(rows)
        failure=next((x for x in rows if x['round']==s+1),None)
        if failure:
            first_failures.append({'variant':variant,'seed':seed,'method':method,'S6':s,'round':failure['round'],
                                   'reasons':failure['failure_reasons'],'solver_status':failure['solver_status']})

for method in METHODS:
    prefixes=[prefix([x for x in r['rounds'] if x['method']==method]) for r in data]
    rows=[x for r in data for x in r['rounds'] if x['method']==method]
    fs=[x for x in first_failures if x['method']==method]
    feasible=[x for r in data for x in r['feasibility'] if x['method']==method]
    summary['methods'][method]={
        'mean_S6':float(np.mean(prefixes)),'pass6':sum(s==6 for s in prefixes),'n':18,
        'prefix_distribution':dict(collections.Counter(prefixes)),
        'failed_rounds':sum(x['status']!='pass' for x in rows),
        'first_failure_reasons':dict(collections.Counter(','.join(x['reasons']) for x in fs)),
        'first_failure_solver':dict(collections.Counter(x['solver_status'] for x in fs)),
        'solver_status':dict(collections.Counter(x['solver_status'] for x in feasible)),
        'fallback_rounds':sum(bool(x.get('fallback_used')) for x in feasible),
        'ranges':{key:[min(x[key] for x in rows),max(x[key] for x in rows)] for key in
            ('power_ratio','power_cap_ratio','N','D','legacy_fraction','legacy_worst','H','H_all','K','floor','rule_dimensions')
            if all(x[key] is not None for x in rows)}
    }
    differences=[]
    for variant in ('pair','triple','mixed'):
        for pool in range(3):
            r0=index[(variant,2*pool)]; r1=index[(variant,2*pool+1)]
            assert r0['evidence']['table_sha256']==r1['evidence']['table_sha256']
            s0=prefix([x for x in r0['rounds'] if x['method']==method])
            s1=prefix([x for x in r1['rounds'] if x['method']==method])
            differences.append({'variant':variant,'pool_seed':pool,'even_order_S6':s0,'odd_order_S6':s1,'difference':s1-s0})
    summary['order_effects'][method]={'changed_pools':sum(x['difference']!=0 for x in differences),
                                      'max_abs_difference':max(abs(x['difference']) for x in differences),
                                      'differences':differences}
    summary['first_failures'][method]=fs
    summary['by_variant'][method]={variant:{'mean_S6':float(np.mean([prefix([x for x in r['rounds'] if x['method']==method]) for r in data if r['evidence']['variant']==variant])),
                                           'pass6':sum(prefix([x for x in r['rounds'] if x['method']==method])==6 for r in data if r['evidence']['variant']==variant)}
                                  for variant in ('pair','triple','mixed')}
summary['trade_certificates']={'count':len(certificate_counts),'total_candidate_witnesses':sum(x['witnesses'] for x in certificate_counts),
                               'min_candidates':min(x['witnesses'] for x in certificate_counts),'max_candidates':max(x['witnesses'] for x in certificate_counts),'rows':certificate_counts}
summary['matched_safe_set_equality_rounds']=matched_equal_count
output=run/'INDEPENDENT_ABSTRACT_AUDIT.json'
output.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({"output": str(output), "instances": len(data), "certificate_count": len(certificate_counts), "matched_rounds": matched_equal_count}))
