"""Prespecified all-conditions adjudication of the first confirmation wave.

This module does not relax a failed comparison, reselect a path, or spend alpha.
It reads the already simultaneous finite contrast analysis. The manifest fixes
which alternative should win and which release widths must support the claim.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from wowfs.paths import atomic_json, canonical_hash


def decide(claim, result):
    if sum(key in claim for key in ('first_pair','joint_pair'))!=1:
        raise ValueError('Exactly one prespecified claim type is required')
    for key in ('claim_id','world_id'):
        if claim[key]!=result[key]:raise ValueError('Claim identity differs from analysis: '+key)
    if result['analysis_input_sha256']!=canonical_hash(claim):
        raise ValueError('Analysis claim hash differs from the frozen decision claim')
    checks={'pre_outcome_freeze':result['pre_outcome_freeze_verified']}
    if 'first_pair' in claim:
        m=result['matched_first'];good=claim['expected_better_first']
        bad=next(x for x in claim['first_pair'] if x!=good)
        checks['both_first_releases_supported']=all(
            m['first_prefixes'][x]['prefix_lengths']['lower']==1 for x in claim['first_pair'])
        checks['frontier_equivalence_supported']=m['equivalence_supported']
        capacities={}
        for b in claim['batch_limits']:
            key=str(b)
            get=lambda node: node.get(key,node.get(b))
            rg,rb=get(m['continuations'][good]),get(m['continuations'][bad])
            vg,vb=get(m['value_only_continuations'][good]),get(m['value_only_continuations'][bad])
            gl,bu=rg['lower']['capacity_lower'],rb['upper']['capacity_upper']
            equal_values=[v['lower']['capacity_lower'] is not None and
                          v['lower']['capacity_lower']==v['upper']['capacity_upper']
                          for v in (vg,vb)]
            checks[f'B{b}_strict_retaining_separation']=(gl is not None and bu is not None and gl>bu)
            checks[f'B{b}_equal_value_only_capacity']=(all(equal_values) and
                vg['lower']['capacity_lower']==vb['lower']['capacity_lower'])
            capacities[key]={name:[v['lower']['capacity_lower'],v['upper']['capacity_upper']]
                for name,v in [('better_retaining',rg),('worse_retaining',rb),
                               ('better_value',vg),('worse_value',vb)]}
        detail={'better_first':good,'worse_first':bad,'capacity_bounds':capacities,
            'comparison':'Same complete candidate library, information, cap, gain, budget and release width; only the forced first update differs.'}
    elif 'joint_pair' in claim:
        j=result['joint']
        for name in ('both_single_component_pairs_cap_supported','joint_pair_cap_excluded',
                     'separable_prediction_cap_supported','positive_mixed_interaction_supported_any_task'):
            checks[name]=j.get(name,False)
        detail={'joint_pair':claim['joint_pair'],'task_order':result['task_order'],
            'comparison':'Individual component and additive forecasts versus the observed legal joint configuration, under the same fixed native policy.',
            'scope_limit':'Does not by itself certify source retention, a positive-gain publication path, or optimality over all possible combat policies.'}
    else:
        raise ValueError('No prespecified claim type')
    supported=all(checks.values())
    return {'claim_id':claim['claim_id'],'world_id':claim['world_id'],
        'role':claim['role'],'finding_id':claim['finding_id'],
        'status':('confirmed_local' if claim['role']=='local' else 'confirmed_heldout_setting')
            if supported else 'not_confirmed',
        'all_prespecified_conditions_supported':supported,'conditions':checks,
        'failed_or_unresolved_conditions':[name for name,value in checks.items() if not value],
        'interpretation':'Not confirmed can mean excluded or unresolved. Preserve component intervals; do not infer an absence from a failed support test.',
        'alpha':claim['alpha'],'iterations':claim['iterations'],**detail}


def analyze(manifest_path, analysis, output):
    if output.exists():raise ValueError('Decision output already exists; immutable')
    manifest=json.loads(manifest_path.read_text())
    frozen=json.loads((analysis/'FROZEN_MANIFEST.json').read_text())
    if manifest!=frozen:raise ValueError('Decision manifest differs from the analysis-frozen manifest')
    result=[decide(claim,json.loads((analysis/f'CLAIM_{i+1:02}.json').read_text()))
            for i,claim in enumerate(manifest['claims'])]
    atomic_json(output,{'status':'completed','alpha_total':sum(c['alpha'] for c in manifest['claims']),
        'claims':result,'rule':'Every prespecified condition must pass; no fallback parameters, extra seeds or selection of only successful settings.'})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('manifest','analysis','output'):p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();print(json.dumps(analyze(a.manifest,a.analysis,a.output)))
