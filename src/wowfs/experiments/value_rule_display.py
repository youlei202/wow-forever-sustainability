"""Integer presentation of already-selected finite admission masks.

This does not search for a better ecological outcome or change an admission.
"""
import json
from math import gcd
from functools import reduce
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from wowfs.paths import setup_paths, atomic_json


def main():
    root=setup_paths();out=root/'artifacts/decisive-value'
    data=json.loads((out/'LINE_B_COMBINATIONS.json').read_text())
    base=json.loads((root/'runs/r4-foundational-discovery/baseline-v1/BASE_ECOSYSTEMS.json').read_text())
    pools={p['id']:p for p in base['ecosystems']};records=[]
    for r in data:
        d=next(x for x in r['methods'] if x['method']=='matched_generic_1row')
        if not d['solver']['feasible']:continue
        labels=next(x for x in r['methods'] if x['method']=='singleton_increment_budget')['rule']['features']
        source=pools[r['pool']]['source_ids_by_gear']
        matrix=np.array([[int(s) in source[g] for s in labels] for g in r['gear_ids']],float)
        admitted=np.asarray(d['admitted'],bool)
        coefficients=np.column_stack((matrix,-np.ones(len(matrix))))
        constraints=LinearConstraint(coefficients,
            np.where(admitted,-np.inf,1.),np.where(admitted,0.,np.inf))
        fit=milp(np.ones(len(labels)+1),integrality=np.ones(len(labels)+1),
            bounds=Bounds(np.zeros(len(labels)+1),np.full(len(labels)+1,100.)),
            constraints=constraints,options={'time_limit':10.,'mip_rel_gap':0.})
        if fit.x is None:
            records.append({'pool':r['pool'],'race':r['race'],'release':r['release'],
                            'status':'unresolved','solver_message':fit.message});continue
        weights=np.rint(fit.x[:-1]).astype(int);budget=int(round(fit.x[-1]))
        matches=np.array_equal(matrix@weights<=budget,admitted)
        if not matches:raise ValueError('Integer presentation changed selected finite admission')
        rule={'item_weights':{s:int(w) for s,w in zip(labels,weights)},'budget':budget,
              'predicate':'sum(weights of equipped variable-slot items) <= budget',
              'domain':'Exactly this frozen release domain; prices for unseen items are undefined.'}
        records.append({'pool':r['pool'],'race':r['race'],'release':r['release'],
            'status':'optimal_integer_presentation' if fit.status==0 else 'feasible_integer_presentation',
            'rule':rule,'same_mask':matches,'admitted_gears':int(admitted.sum()),
            'total_gears':len(admitted),'rule_rows':1,'feature_dimension':len(labels),
            'nonzero_weights':int(np.sum(weights!=0)),
            'serialized_rule_bytes':len(json.dumps(rule,sort_keys=True,separators=(',',':')).encode()),
            'gain_and_ecological_metrics_unchanged':True,
            'minimum_slack_for_rejected':int(np.min((matrix@weights-budget)[~admitted])),
            'extraction_scope':'Posthoc display of selected generic rule; not a predictive source-only rule.'})
    atomic_json(out/'LINE_B_INTEGER_RULES.json',{'native_calls':0,'rules':records})
    for r in records:print(json.dumps(r),flush=True)


if __name__=='__main__':main()
