"""Post-freeze descriptive comparisons and numeric facet audit; no new physics."""
from collections import defaultdict
import json
import numpy as np
from scipy.optimize import linprog
from wowfs.paths import setup_paths,atomic_json,canonical_hash
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r3_affine_transfer import load_models,model_key,SPEEDS


def caps():
    root=setup_paths();run=root/'runs/r2-discovery/unseen-v1'
    frozen=json.loads((run/'FROZEN_DESIGN.json').read_text());initial=set(frozen['initial_gear_ids'])
    result={}
    for row in json.loads((run/'RESULTS.json').read_text())['rows']:
        if row['gear_id'] in initial:
            key=(row['race'],row['task']);result[key]=max(result.get(key,0.),row['dps_mean']*1.05)
    return result


def prune(rows,cap):
    # A bounded rectangle makes the numeric LP implication problem explicit.
    coeff=np.array([r['mean_coefficients'] for r in rows]);A=coeff[:,1:];b=np.array([cap[(r['race'],r['task'])] for r in rows])-coeff[:,0]
    active=list(range(len(rows)));removed=[];unresolved=[]
    for i in list(active):
        other=[j for j in active if j!=i]
        sol=linprog(-A[i],A_ub=A[other] if other else None,b_ub=b[other] if other else None,
                    bounds=[(0,30),(0,30)],method='highs')
        if sol.status==0:
            violation=float(-sol.fun-b[i])
            if violation<=1e-7:active.remove(i);removed.append(i)
        elif sol.status==2:
            # Other constraints already infeasible; removing this row preserves empty domain.
            active.remove(i);removed.append(i)
        else:unresolved.append({'index':i,'status':sol.status,'message':sol.message})
    return {'input_rows':len(rows),'retained_rows':len(active),'retained_contexts':[
        {k:rows[i][k] for k in ('race','weapon_speed','offhand','trinket1','trinket2','task','strategy')} for i in active],
        'removed_rows':len(removed),'unresolved':unresolved,'numeric_tolerance_dps':1e-7}


def main():
    root=setup_paths();out=root/'artifacts/r3-gold';transfer=json.loads((out/'AFFINE_TRANSFER.json').read_text())
    models=load_models();cap=caps();races=sorted({k[0] for k in models});groups=defaultdict(list)
    for r in transfer['rows']:
        if r['panel']=='same_control':groups[(r['race'],r['variant_index'],r['offhand'],r['trinket1'],r['trinket2'])].append(r)
    scalar={race:np.max([np.array(m['mean_coefficients'])/cap[(race,m['task'])] for k,m in models.items() if k[0]==race],axis=0) for race in races}
    decisions=[]
    for key,rows in sorted(groups.items()):
        assert len(rows)==12
        r=rows[0];truth=all(x['observed_mean']<=cap[(x['race'],x['task'])]+1e-10 for x in rows)
        typed=all(x['predicted_mean']<=cap[(x['race'],x['task'])]+1e-10 for x in rows)
        scalar_accept=float(scalar[r['race']] @ [1,r['base_dps']-24,r['dot_damage']])<=1+1e-10
        decisions.append({'race':key[0],'variant_index':key[1],'offhand':key[2],'trinket1':key[3],'trinket2':key[4],
            'weapon_speed':r['weapon_speed'],'finite_native_safe':truth,'typed_affine':typed,'same_feature_generic':typed,
            'common_scalar_majorant':scalar_accept,'frozen_item_whitelist':False,'frozen_item_blacklist':True,
            'refitted_item_exception_table':truth,'finite_safe_reference':truth})
    comparisons=[]
    for method in ['common_scalar_majorant','frozen_item_whitelist','frozen_item_blacklist','refitted_item_exception_table','typed_affine','same_feature_generic','finite_safe_reference']:
        selected=[r for r in decisions if r[method]]
        comparisons.append({'method':method,'tested_loadouts':len(decisions),'native_safe_loadouts':sum(r['finite_native_safe'] for r in decisions),
            'admitted_loadouts':len(selected),'unsafe_admitted':sum(not r['finite_native_safe'] for r in selected),
            'safe_rejected':sum(r['finite_native_safe'] and not r[method] for r in decisions),
            'heldout_response_cells_used_for_decision':3072 if method in ('refitted_item_exception_table','finite_safe_reference') else 0,
            'scope':'Paired-seed finite point-estimate comparison, not independent mean safety.'})
    kernels=defaultdict(list)
    for key,m in models.items():kernels[key[:5]].append(m)
    facet_rows=[]
    for key,rows in sorted(kernels.items()):
        facet_rows.append({'race':key[0],'weapon_speed':key[1],'offhand':key[2],'trinket1':key[3],'trinket2':key[4],**prune(rows,cap)})
    def compressed_rule(speeds):
        branches=[]
        for facet in facet_rows:
            if facet['weapon_speed'] not in speeds:continue
            constraints=[]
            for context in facet['retained_contexts']:
                m=models[model_key(*(context[k] for k in ['race','weapon_speed','offhand','trinket1','trinket2','task','strategy']))]
                constraints.append({'task':m['task'],'strategy':m['strategy'],'coefficients':m['mean_coefficients']})
            branches.append({'context':[facet[k] for k in ['race','weapon_speed','offhand','trinket1','trinket2']],
                             'constraints':constraints})
        return {'schema':1,'features':['1','base_dps-24','dot_damage'],
            'domain':{'base_dps':[24,54],'dot_damage':[0,30]},'outside_support':'reject',
            'caps':{race:{task:value for (rr,task),value in cap.items() if rr==race} for race in races},
            'branches':branches}
    def encoded_size(value):return len(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    rule=compressed_rule(SPEEDS)
    atomic_json(out/'AFFINE_ADMISSION_RULE_NUMERIC_PRUNING.json',rule)
    branch_lookup={tuple(b['context']):b for b in rule['branches']}
    compressed_agreement=True
    for row in decisions:
        example=groups[(row['race'],row['variant_index'],row['offhand'],row['trinket1'],row['trinket2'])][0]
        b=branch_lookup[(row['race'],row['weapon_speed'],row['offhand'],row['trinket1'],row['trinket2'])]
        accepted=all(np.dot(c['coefficients'],[1,example['base_dps']-24,example['dot_damage']])<=cap[(row['race'],c['task'])]+1e-10 for c in b['constraints'])
        compressed_agreement &= accepted==row['typed_affine']
    complexity=[]
    for n in [4,8,16,32]:
        current=[r for r in decisions if r['variant_index']<n]
        complexity.append({'panel':'growing_item_count_fixed_palette','parameter_items':n,'speed_kernels':3,
            'tested_loadouts':len(current),'typed_inequality_rows':288,'typed_numeric_coefficients':864,
            'same_feature_generic_rows':288,'fitted_scalar_rows':2,'fitted_scalar_coefficients':6,
            'per_item_response_table_rows':len(current),'per_item_response_table_numeric_values':len(current)*12,
            'per_item_identity_predicates':n,'kernel_predicates':24,
            'native_safe_loadouts':sum(r['finite_native_safe'] for r in current),
            'typed_admitted_loadouts':sum(r['typed_affine'] for r in current)})
    for h in [1,2,3]:
        available=sorted({r['variant_index'] for r in decisions if r['weapon_speed'] in SPEEDS[:h]})[:8]
        current=[r for r in decisions if r['variant_index'] in available]
        complexity.append({'panel':'matched_n_eight_control_kernel_count','parameter_items':8,'speed_kernels':h,
            'tested_loadouts':len(current),'typed_inequality_rows':96*h,'typed_numeric_coefficients':288*h,
            'same_feature_generic_rows':96*h,'fitted_scalar_rows':2,'fitted_scalar_coefficients':6,
            'per_item_response_table_rows':len(current),'per_item_response_table_numeric_values':len(current)*12,
            'per_item_identity_predicates':8,'kernel_predicates':8*h,
            'native_safe_loadouts':sum(r['finite_native_safe'] for r in current),
            'typed_admitted_loadouts':sum(r['typed_affine'] for r in current)})
    for row in complexity:
        speeds=SPEEDS[:row['speed_kernels']];subset=compressed_rule(speeds)
        available=sorted({r['variant_index'] for r in decisions if r['weapon_speed'] in speeds})[:row['parameter_items']]
        current=[r for r in decisions if r['variant_index'] in available]
        lookup={'outside_support':'reject','point_estimate_only':True,'entries':[
            {k:r[k] for k in ['race','variant_index','weapon_speed','offhand','trinket1','trinket2','finite_native_safe']} for r in current]}
        row.update(typed_irredundant_numeric_facets=sum(len(b['constraints']) for b in subset['branches']),
            typed_branch_selectors=len(subset['branches']),shared_rectangle_inequalities=4,
            typed_complete_serialized_rule_bytes=encoded_size(subset),same_feature_generic_serialized_rule_bytes=encoded_size(subset),
            refitted_lookup_serialized_bytes=encoded_size(lookup),
            bytes_scope='Exact compact sorted JSON of deployable mean rule, including bounds/caps/selectors; excludes interpreter and scientific training provenance.')
    result={'methods':comparisons,'scalar_definition':'A deliberately conservative single nonnegative amplitude score per race: take separate maxima of cap-normalized affine intercept and both slopes over the entire calibrated palette. Same anchors; not an optimal scalar LP and not an impossibility result.',
        'exceptions_definition':'Frozen unknown-item whitelist rejects all; frozen empty blacklist admits all; refitted lookup observes all test responses and stores exact finite decisions. This latter method has strictly more outcome information.',
        'generic_definition':'Identical features, data and coefficients, hence no typed-over-generic separation.',
        'numeric_description_accounting':'Each full affine row stores 3 float64 coefficients plus task/policy/kernel predicates;864 coefficients=6912 raw bytes across both races, excluding identifiers, runtime, uncertainty estimates and provenance. Scientific artifact also stores seed coefficients; do not count it as a minimal rule.',
        'facets':facet_rows,'total_original_facets':sum(x['input_rows'] for x in facet_rows),
        'total_retained_numeric_facets':sum(x['retained_rows'] for x in facet_rows),
        'compressed_rule_matches_all_256_full_rule_decisions':bool(compressed_agreement),
        'compressed_rule_compact_json_bytes':encoded_size(rule),'compressed_rule_sha256':canonical_hash(rule),
        'compression_scope':'Numeric LP uses frozen calibration coefficients and cap only; produced after transfer and is not a preregistered deployment. All24 branch selectors and4 shared domain constraints remain in the serialized rule.',
        'facet_domain':'For each fixed race/speed/loadout, all12 task/policy inequalities on DPS[24,54] and DOT[0,30]. Numeric sequential LP redundancy removal; no exact arithmetic/minimum-bit-description claim.',
        'complexity':complexity,'caps':[{'race':race,'task':task,'numeric_cap':value} for (race,task),value in sorted(cap.items())],
        'new_type_claim':False,'context_scope':'Warrior Human/Orc only. Speed is a control-kernel parameter inside the same broad effect vocabulary. New timing or resource contexts are outside the frozen rule support.'}
    atomic_json(out/'AFFINE_COMPARISONS.json',result);write_csv(out/'AFFINE_METHOD_COMPARISON.csv',comparisons)
    write_csv(out/'AFFINE_RULE_COMPLEXITY.csv',complexity);write_csv(out/'AFFINE_TRANSFER_DECISIONS.csv',decisions)
    write_csv(out/'RULE_COMPLEXITY_SCALING.csv',complexity)
    print(json.dumps({k:v for k,v in result.items() if k not in ('facets','complexity','caps')},indent=2))

if __name__=='__main__':main()
