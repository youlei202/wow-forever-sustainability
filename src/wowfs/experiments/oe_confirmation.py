"""Frozen native confirmation assembly: complete physical cells, fixed references.

CLI: --batch BATCH_DIR --manifest MANIFEST.json --output NEW_DIRECTORY.
The output is a collection of checks and conditional finite bounds, not an
automatic declaration that a research claim has been confirmed.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
from itertools import product
import json
from pathlib import Path
import shutil
import numpy as np
from scipy.stats import t as student_t

from wowfs.paths import SOURCE_ROOT,atomic_json,canonical_hash
from wowfs.experiments.oe_solver import Problem,Configuration
from wowfs.experiments.oe_inference import FiniteBounds
from wowfs.experiments.oe_confidence_planner import confidence_capacity,apply_retention_requirement

IDENTITY=('candidate_id','partner_id','task_id','policy_id')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _domain_ids(world):
    """Accept explicit ID domains or a full, frozen oe_worlds registry object."""
    if all(k in world for k in ('candidate_ids','partner_ids','task_ids','policy_ids')):
        result={k:sorted(str(x) for x in world[k]) for k in ('candidate_ids','partner_ids','task_ids','policy_ids')}
    else:
        result={'candidate_ids':[f'a{i:02}' for i in range(len(world['candidates']))],
                'partner_ids':[f'x{i}' for i in range(len(world['partners']))],
                'task_ids':sorted(str(t['task_id']) for t in world['tasks']),
                'policy_ids':sorted(str(p) for p in world['policies'])}
    if any(not v or len(set(v))!=len(v) for v in result.values()):
        raise ValueError('Frozen world domains must be nonempty and have unique IDs')
    if set(result['candidate_ids'])&set(result['partner_ids']):
        raise ValueError('Candidate and partner source IDs must be disjoint')
    return result


def _world_scope(manifest,world_id,jobs):
    worlds=manifest.get('worlds',{})
    if isinstance(worlds,list):worlds={w['world_id']:w for w in worlds}
    if world_id in worlds:
        return _domain_ids(worlds[world_id]),'manifest_world_domain'
    chosen=[j['meta'] for j in jobs if j.get('meta',{}).get('world_id')==world_id]
    if not chosen:raise ValueError('No manifest world domain or declared batch jobs for '+world_id)
    return {out:sorted({str(r[key]) for r in chosen}) for out,key in
            zip(('candidate_ids','partner_ids','task_ids','policy_ids'),IDENTITY)},'declared_batch_job_domain'


def _validate_claim_scope(manifest,claim,domain):
    """Make initial-history and task-weight changes explicit, never accidental."""
    tasks=domain['task_ids']
    if 'task_ids' in claim and claim['task_ids']!=tasks:
        raise ValueError('claim task_ids must equal sorted physical task order')
    if 'task_weight_mapping' in claim:
        mapping=claim['task_weight_mapping']
        if set(mapping)!=set(tasks) or [mapping[q] for q in tasks]!=claim['task_weights']:
            raise ValueError('task_weight_mapping and sorted task_weights disagree')
    worlds=manifest.get('worlds',{})
    if isinstance(worlds,list):worlds={w['world_id']:w for w in worlds}
    world=worlds.get(claim['world_id'],{})
    if 'initial_candidate_ids' in world and 'initial_partner_ids' in world:
        expected={f'a{i:02}' for i in world['initial_candidate_ids']}|{f'x{i}' for i in world['initial_partner_ids']}
        if expected!=set(claim['initial_items']) and not claim.get('initial_override_reason'):
            raise ValueError('Claim changes registry initial history without an explicit initial_override_reason')
    if 'task_weights' in world:
        order=world.get('task_ids') or [t['task_id'] for t in world['tasks']]
        declared=dict(zip(order,world['task_weights']))
        if [declared[q] for q in tasks]!=claim['task_weights'] and not claim.get('task_weight_override_reason'):
            raise ValueError('Claim changes registry task weights without an explicit task_weight_override_reason')


def _expected_seed_block(manifest,claim):
    value=claim.get('seed_block_id',manifest.get('seed_block_id'))
    if value is None:
        seed=claim.get('seed',manifest.get('seed'))
        n=claim.get('iterations',manifest.get('iterations'))
        if seed is not None and n is not None:value=f'{seed}:{n}'
    if value is None:
        raise ValueError('Confirmation manifest must freeze seed_block_id or seed plus iterations')
    parts=str(value).split(':')
    if len(parts)!=2 or any(not x.isdigit() for x in parts) or int(parts[0])<=0 or int(parts[1])<2:
        raise ValueError('Invalid frozen seed block: expected positive start:N with N>=2; native seed zero uses clock time')
    n=claim.get('iterations',manifest.get('iterations'))
    if n is not None and int(n)!=int(parts[1]):raise ValueError('Frozen seed block and iterations disagree')
    return f'{int(parts[0])}:{int(parts[1])}'


def assemble(rows,claim,domain):
    """Map complete observed cells into C x Q x N, preserving paired seed order."""
    domain=_domain_ids(domain)
    a,x,q,k=(domain[name] for name in ('candidate_ids','partner_ids','task_ids','policy_ids'))
    lookup={}
    for row in rows:
        if row.get('world_id')!=claim['world_id']:continue
        if row.get('observed_or_reconstructed')!='observed':
            raise ValueError('Confirmation accepts actual observed cells only')
        key=tuple(str(row[name]) for name in IDENTITY)
        if key in lookup:raise ValueError('Duplicate logical physical cell '+str(key))
        lookup[key]=row
    expected=set(product(a,x,q,k))
    missing=expected-set(lookup);extra=set(lookup)-expected
    if missing or extra:
        raise ValueError(f'Incomplete or changed physical domain: missing={len(missing)}, extra={len(extra)}')
    seeds={row['seed_block_id'] for row in lookup.values()}
    counts={len(row['dps_samples']) for row in lookup.values()}
    if len(seeds)!=1 or len(counts)!=1 or next(iter(counts))<2:
        raise ValueError('Every cell must use the same complete paired seed block')
    n=next(iter(counts))
    for row in lookup.values():
        if int(row['iterations'])!=n:raise ValueError('Native iterations and sample vector length differ')
        if not np.isfinite(np.asarray(row['dps_samples'],dtype=float)).all():
            raise ValueError('Missing or nonfinite samples cannot be imputed')
    configuration_order=list(product(a,x,k))
    samples=np.array([[lookup[ai,xi,qi,ki]['dps_samples'] for qi in q] for ai,xi,ki in configuration_order],dtype=float)
    reference_map={str(r['task_id']):r for r in claim['reference_mapping']}
    if len(reference_map)!=len(claim['reference_mapping']) or set(reference_map)!=set(q):
        raise ValueError('Reference mapping must explicitly identify exactly one physical configuration per task')
    refs=[];reference_identity=[]
    initial=set(claim['initial_items'])
    for task in q:
        r=reference_map[task]
        key=(str(r['candidate_id']),str(r['partner_id']),task,str(r['policy_id']))
        if key not in lookup:raise ValueError('Frozen physical reference cell was not measured')
        if not {key[0],key[1]}<=initial:raise ValueError('Reference must be an originally available old configuration')
        if 'input_sha256' in r and r['input_sha256']!=lookup[key].get('input_sha256'):
            raise ValueError('Frozen reference physical input hash differs')
        refs.append(lookup[key]['dps_samples'])
        reference_identity.append({**{name:key[i] for i,name in enumerate(IDENTITY)},
                                   'input_sha256':lookup[key].get('input_sha256'),
                                   'cache_key':lookup[key].get('cache_key')})
    references=np.array(refs,dtype=float)
    configurations=tuple(Configuration('|'.join(config),frozenset(config[:2]),tuple(samples[i].mean(axis=1)))
                         for i,config in enumerate(configuration_order))
    p=Problem(tuple(a+x),frozenset(initial),configurations,tuple(claim['task_weights']),
              tuple(references.mean(axis=1)),float(claim['gain']),1+float(claim['headroom']),
              float(claim['tolerance']),float(claim['gain_mass']),float(claim['retention_mass']),
              claim.get('total_item_budget'),epsilon=0.)
    return {'problem':p,'samples':samples,'reference':references,'domain':domain,'lookup':lookup,
            'configuration_order':configuration_order,'task_order':q,'reference_identity':reference_identity,
            'seed_block_id':next(iter(seeds)),'physical_cells':len(lookup)}


def _active(problem,published):
    return [i for i,c in enumerate(problem.configurations) if c.items<=set(published)]


def _incidence(problem,published):
    return {x:[i for i,c in enumerate(problem.configurations) if x in c.items] for x in problem.items if x in published}


def frozen_path_checks(problem,bounds,batches,batch_limit,*,initial_items=None,retention=True):
    """Evaluate every frozen prefix; preserve the first and subsequent failures."""
    present=set(problem.initial_items if initial_items is None else initial_items)
    if not problem.initial_items<=present or not present<=set(problem.items):
        raise ValueError('Frozen path initial history must preserve all original sources')
    active=_active(problem,present)
    if not active:raise ValueError('Frozen path initial history has no active physical configuration')
    initial=bounds.evaluate(active,_incidence(problem,present),problem.task_weights,problem.retention_mass)
    initial=apply_retention_requirement(initial,retention)
    result=[];prefix={key:0 for key in ('mean','lower','upper')};alive={key:initial[key] for key in prefix}
    for number,batch in enumerate(batches,1):
        if isinstance(batch,str):batch=[batch]
        batch=list(batch)
        if not batch or len(batch)>batch_limit or len(set(batch))!=len(batch):
            raise ValueError('Frozen path violates declared release width or contains duplicates')
        if any(x not in problem.items or x in present for x in batch):
            raise ValueError('Frozen path item unknown or previously published')
        previous=active;present|=set(batch);active=_active(problem,present)
        if not active:raise ValueError('Frozen path has no complete physical configuration')
        row=bounds.transition(previous,active,_incidence(problem,present),problem.gain_mass,
                              weights=problem.task_weights,retention_mass=problem.retention_mass)
        row=apply_retention_requirement(row,retention)
        budget=(problem.total_item_budget is None or len(present-problem.initial_items)<=problem.total_item_budget)
        row['checks']['item_budget']={key:budget for key in ('mean','lower','upper')}
        for key in prefix:
            row[key]=bool(row[key] and budget);alive[key]=bool(alive[key] and row[key])
            if alive[key]:prefix[key]=number
        row['statistical_status']=('interval_supported' if row['lower'] else
            ('unresolved' if row['upper'] else 'interval_excluded'))
        row.update(round=number,batch=batch,published_items=[x for x in problem.items if x in present])
        result.append(row)
    return {'initial':initial,'batch_limit':batch_limit,'retention_enforced':retention,
            'batches':[list(b) if not isinstance(b,str) else [b] for b in batches],
            'prefix_lengths':prefix,'steps':result,
            'scope':'Frozen path checks only; a failed supported prefix is not a capacity upper bound.'}


def _graph_pair(problem,bounds,claim,*,initial_items=None,retention=True):
    output={}
    for batch_limit in claim.get('batch_limits',[1,2]):
        if batch_limit in output:raise ValueError('Duplicate release width')
        output[batch_limit]={mode:asdict(confidence_capacity(problem,bounds,mode,batch_limit,
            initial_items=initial_items,max_candidates=claim.get('max_candidates',19),
            timeout_seconds=claim.get('timeout_seconds',60.),retention=retention)) for mode in ('lower','upper')}
    return output


def _matched_first(problem,bounds,claim,table,alpha):
    pair=list(claim['first_pair'])
    if len(pair)!=2 or pair[0]==pair[1] or any(x not in problem.items or x in problem.initial_items for x in pair):
        raise ValueError('first_pair must specify two distinct unpublished components')
    threshold=float(claim.get('match_tolerance',.0025))
    if not 0<threshold:raise ValueError('match_tolerance must be positive')
    auxiliary=FiniteBounds(table['samples'],table['reference'],threshold,problem.tolerance,problem.cap,alpha)
    firstsets=[set(problem.initial_items)|{item} for item in pair]
    states=[_active(problem,present) for present in firstsets]
    directional=[]
    for i,j in ((0,1),(1,0)):
        low,high=auxiliary.frontier_contrast(states[i],states[j],threshold)
        mean=auxiliary.means[states[i]].max(axis=0)-auxiliary.means[states[j]].max(axis=0)-threshold*auxiliary.ref
        directional.append({'left_first':pair[i],'right_first':pair[j],
                            'mean':mean.tolist(),'lower':low.tolist(),'upper':high.tolist(),
                            'mean_within_margin':bool(np.all(mean<=0.)),
                            'within_margin_supported':bool(np.all(high<=0.)),
                            'within_margin_possible':bool(np.all(low<=0.))})
    prefixes={item:frozen_path_checks(problem,bounds,[[item]],1) for item in pair}
    continuations={item:_graph_pair(problem,bounds,claim,initial_items=firstsets[i]) for i,item in enumerate(pair)}
    value_prefixes={item:frozen_path_checks(problem,bounds,[[item]],1,retention=False) for item in pair}
    value_continuations={item:_graph_pair(problem,bounds,claim,initial_items=firstsets[i],retention=False)
                         for i,item in enumerate(pair)}
    separation={}
    for B in claim.get('batch_limits',[1,2]):
        directional_separation=[]
        for better,worse in ((pair[0],pair[1]),(pair[1],pair[0])):
            lower=continuations[better][B]['lower']['capacity_lower']
            upper=continuations[worse][B]['upper']['capacity_upper']
            directional_separation.append({'better':better,'worse':worse,'better_capacity_lower':lower,
                'worse_capacity_upper':upper,'strict_capacity_separation':lower is not None and upper is not None and lower>upper})
        separation[B]=directional_separation
    return {'alpha':alpha,'match_tolerance':threshold,'bounds_manifest':auxiliary.manifest(),
            'directions':directional,'equivalence_mean':all(d['mean_within_margin'] for d in directional),
            'equivalence_supported':all(d['within_margin_supported'] for d in directional),
            'equivalence_possible':all(d['within_margin_possible'] for d in directional),
            'first_prefixes':prefixes,'continuations':continuations,'capacity_separation_checks':separation,
            'value_only_first_prefixes':value_prefixes,'value_only_continuations':value_continuations,
            'value_only_alpha_additional':0.,
            'unselected_first_alternative_retained':True,
            'scope':'Matching requires simultaneous two-direction equivalence on EVERY task, not a nonsignificant difference. '
                    'A continuation bound does not establish the first update was feasible; inspect both frozen first-prefix checks. '
                    'Value-only repeats the identical physical domain, cap, gain and item budget while disabling only source retention; '
                    'it uses the already simultaneous core power/gain contrasts without additional alpha.'}


def _linear_summary(values,critical):
    n=values.shape[-1];mean=values.mean(axis=-1);se=values.std(axis=-1,ddof=1)/np.sqrt(n)
    return {'mean':mean.tolist(),'lower':(mean-critical*se).tolist(),'upper':(mean+critical*se).tolist()}


def _joint_single(problem,claim,table,alpha,*,family_multiplier=1):
    pair=list(claim['joint_pair']);d=table['domain']
    if len(pair)!=2 or pair[0] not in d['candidate_ids'] or pair[1] not in d['partner_ids']:
        raise ValueError('joint_pair must be [candidate_id,partner_id]')
    if any(x in problem.initial_items for x in pair):
        raise ValueError('Both joint_pair components must be unpublished at the original initial state')
    olda=[x for x in d['candidate_ids'] if x in problem.initial_items]
    oldx=[x for x in d['partner_ids'] if x in problem.initial_items]
    policy=claim.get('aux_policy_id')
    if policy is None and len(d['policy_ids'])==1:policy=d['policy_ids'][0]
    reasons=[]
    if len(olda)!=1 or len(oldx)!=1:reasons.append('four-cell diagnosis requires one declared original item in each slot')
    if policy is None or policy not in d['policy_ids']:reasons.append('multiple policies require an explicitly frozen aux_policy_id')
    if reasons:
        return {'status':'not_evaluated_scope_limitation','alpha_reserved':alpha,'reasons':reasons}
    for r in table['reference_identity']:
        if (r['candidate_id'],r['partner_id'],r['policy_id'])!=(olda[0],oldx[0],policy):
            reasons.append('reference identity differs from the four-cell baseline in task '+r['task_id'])
    if reasons:return {'status':'not_evaluated_scope_limitation','alpha_reserved':alpha,'reasons':reasons}
    lookup=table['lookup'];q=table['task_order'];ai,xi=pair
    one_a=np.array([lookup[ai,oldx[0],task,policy]['dps_samples'] for task in q])
    one_x=np.array([lookup[olda[0],xi,task,policy]['dps_samples'] for task in q])
    joint=np.array([lookup[ai,xi,task,policy]['dps_samples'] for task in q])
    reference=table['reference'];cap=problem.cap
    contrasts={'candidate_alone_cap_margin':cap*reference-one_a,
               'partner_alone_cap_margin':cap*reference-one_x,
               'joint_cap_margin':cap*reference-joint,
               'separable_predicted_cap_margin':(cap+1)*reference-one_a-one_x,
               'mixed_interaction':joint-one_a-one_x+reference}
    family_size=5*len(q)*family_multiplier
    critical=float(student_t.isf(alpha/(2*family_size),reference.shape[-1]-1))
    summaries={name:_linear_summary(v,critical) for name,v in contrasts.items()}
    safe=lambda key:bool(np.all(np.array(summaries[key]['lower'])>=0.))
    violated=lambda key:bool(np.any(np.array(summaries[key]['upper'])<0.))
    return {'status':'evaluated_fixed_policy','alpha':alpha,'family_size':family_size,'critical_value':critical,
            'policy_id':policy,'task_order':q,'contrasts':summaries,
            'both_single_component_pairs_cap_supported':safe('candidate_alone_cap_margin') and safe('partner_alone_cap_margin'),
            'joint_pair_cap_excluded':violated('joint_cap_margin'),
            'separable_prediction_cap_supported':safe('separable_predicted_cap_margin'),
            'positive_mixed_interaction_supported_any_task':bool(np.any(np.array(summaries['mixed_interaction']['lower'])>0.)),
            'scope':'Five predeclared paired linear contrasts per task and specified main/control pair, approximate simultaneous t. '
                    'Fixed-policy pair diagnostics alone do not certify every other legal configuration, source retention, or a release path.'}


def _joint_diagnostics(problem,claim,table,alpha):
    """Optional predeclared control pairs share, rather than renew, joint alpha."""
    controls=claim.get('joint_negative_controls',[])
    ids=[control['control_id'] for control in controls]
    if len(set(ids))!=len(ids):raise ValueError('Joint control IDs must be unique')
    result=_joint_single(problem,claim,table,alpha,family_multiplier=1+len(controls))
    result['negative_controls']=[]
    for control in controls:
        selected={**claim,'joint_pair':control['joint_pair']}
        if 'aux_policy_id' in control:selected['aux_policy_id']=control['aux_policy_id']
        measured=_joint_single(problem,selected,table,alpha,family_multiplier=1+len(controls))
        result['negative_controls'].append({'control_id':control['control_id'],
            'prespecified_role':control.get('role','negative control'),**measured})
    result['negative_control_status']='evaluated_prespecified_pairs' if controls else 'not_specified'
    result['negative_control_scope']=('A nonsignificant mixed contrast is not evidence of equivalence or absence. '
        'All declared main/control contrasts share one joint-family alpha allocation; no additional alpha is spent.')
    return result


def analyze_claim(rows,claim,domain):
    table=assemble(rows,claim,domain);p=table['problem'];alpha=float(claim['alpha'])
    if not 0<alpha<=.05:raise ValueError('claim alpha must be positive and no greater than campaign default .05')
    core_alpha=alpha/2
    core=FiniteBounds(table['samples'],table['reference'],p.gain,p.tolerance,p.cap,core_alpha)
    aux_count=sum(key in claim for key in ('first_pair','joint_pair'))
    aux_alpha=alpha/(2*aux_count) if aux_count else alpha/2
    paths={}
    for name,path in claim.get('frozen_paths',{}).items():
        if isinstance(path,dict):batches=path['batches'];width=path.get('batch_limit',claim.get('path_batch_limit',1))
        else:batches=path;width=claim.get('path_batch_limit',1)
        paths[name]=frozen_path_checks(p,core,batches,width)
    result={'claim_id':claim['claim_id'],'kind':claim.get('kind','unspecified'),'world_id':claim['world_id'],
            'model_scope':claim['model_scope'],'status':'analysis_completed','claim_supported':None,
            'claim_status':'Inspect all prespecified conditions; no automatic research-claim declaration.',
            'alpha_allocation':{'claim_total':alpha,'core_family':core_alpha,
                'matched_first_family':aux_alpha if 'first_pair' in claim else 0.,
                'joint_linear_family':aux_alpha if 'joint_pair' in claim else 0.,
                'reserved_unused_auxiliary':alpha/2 if not aux_count else 0.},
            'physical_cells':table['physical_cells'],'configuration_order':['|'.join(x) for x in table['configuration_order']],
            'task_order':table['task_order'],'seed_block_id':table['seed_block_id'],
            'reference_identity':table['reference_identity'],'domain':table['domain'],
            'initial_items':list(claim['initial_items']), 'core_bounds_manifest':core.manifest(),
            'capacity':_graph_pair(p,core,claim),'frozen_paths':paths,
            'scope':'Complete measured physical finite domain; approximate simultaneous t, not distribution-free. '
                    'Raw reference uncertainty remains in every contrast; no response interpolation or reference reselection.'}
    if 'first_pair' in claim:result['matched_first']=_matched_first(p,core,claim,table,aux_alpha)
    if 'joint_pair' in claim:result['joint']=_joint_diagnostics(p,claim,table,aux_alpha)
    return result


def _freeze_audit(batch,manifest,manifest_path):
    protocol=json.loads((batch/'PROTOCOL.json').read_text())
    if protocol.get('phase')!='confirm':raise ValueError('Native batch phase is not confirm')
    science=protocol.get('science',{});known=(file_hash(manifest_path),canonical_hash(manifest))
    links=[science[key] for key in ('confirmation_manifest_sha256','manifest_sha256','confirmation_manifest_hash') if key in science]
    if any(link not in known for link in links):raise ValueError('Frozen batch manifest hash does not match analysis manifest')
    embedded=science.get('confirmation_manifest')
    if embedded is not None and embedded!=manifest:raise ValueError('Frozen batch embedded manifest differs')
    verified=bool(links) or embedded==manifest
    source_checks={}
    for name,expected in manifest.get('analysis_hashes',{}).items():
        path=Path(name) if Path(name).is_absolute() else SOURCE_ROOT/name
        actual=file_hash(path)
        if actual!=expected:raise ValueError('Frozen analysis source changed: '+name)
        source_checks[name]=actual
    for filename in ('oe_confirmation.py','oe_inference.py','oe_confidence_planner.py','oe_solver.py'):
        rel='src/wowfs/experiments/'+filename
        frozen=protocol.get('source_hashes',{}).get(rel)
        if frozen is not None and file_hash(SOURCE_ROOT/rel)!=frozen:
            raise ValueError('Analysis source differs from batch-frozen code: '+rel)
    return {'manifest_link_verified':verified,'manifest_file_sha256':known[0],
            'manifest_canonical_sha256':known[1],'protocol_sha256':file_hash(batch/'PROTOCOL.json'),
            'analysis_source_hashes_verified':source_checks,
            'status':'verified' if verified else 'pre_outcome_manifest_freeze_not_verified',
            'limitation':None if verified else 'Statistics are diagnostics until the pre-outcome design freeze is independently established.'}


def analyze(batch,manifest_path,output):
    batch=Path(batch);batch=batch.parent if batch.is_file() else batch
    manifest_path=Path(manifest_path);output=Path(output)
    if output.exists():raise ValueError('Output must be a NEW directory; prior confirmation analyses are immutable')
    manifest=json.loads(manifest_path.read_text());data=json.loads((batch/'RESULTS.json').read_text())
    if data.get('status')!='completed' or data.get('errors') or any(row is None for row in data['rows']):
        raise ValueError('Confirmation assembly requires a completed native batch with no missing/error rows')
    claims=manifest['claims']
    if not claims:raise ValueError('Manifest has no claims')
    keys=[(c['claim_id'],c['world_id']) for c in claims]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate claim/world allocation')
    budget=float(manifest.get('campaign_alpha_budget',.05));previous=float(manifest.get('previous_alpha_spent',0.))
    allocations=[float(c['alpha']) for c in claims];total=sum(allocations)
    if (not np.isfinite([budget,previous,total,*allocations]).all() or
        any(not 0<a<=.05 for a in allocations) or
        not 0<budget<=.05 or previous<0 or previous+total>budget+1e-12):
        raise ValueError('Confirmation allocations exceed the nonrenewable campaign alpha budget')
    audit=_freeze_audit(batch,manifest,manifest_path)
    jobs=json.loads((batch/'JOBS.json').read_text())
    protocol=json.loads((batch/'PROTOCOL.json').read_text())
    if protocol.get('jobs_sha256')!=canonical_hash(jobs):
        raise ValueError('Physical jobs differ from the batch-frozen job hash')
    if len(jobs)!=len(data['rows']):raise ValueError('Job and observed-row counts differ')
    # JOBS order is the native runner contract, including reused physical inputs.
    for job,row in zip(jobs,data['rows']):
        for key in ('world_id',*IDENTITY):
            if str(row[key])!=str(job['meta'][key]):raise ValueError('Observed identity differs from its frozen physical job')
        if row.get('input_sha256')!=canonical_hash(job['input']):raise ValueError('Physical input identity hash mismatch')
        if row.get('binary_sha256')!=protocol.get('binary_sha256'):
            raise ValueError('Observed native binary differs from the frozen batch executable')
        options=job['input']['request']['simOptions']
        if len(row['dps_samples'])!=int(options['iterations']):raise ValueError('Frozen job and native sample length differ')
        expected_block=f'{options["randomSeed"]}:{options["iterations"]}'
        if row['seed_block_id']!=expected_block:raise ValueError('Claimed paired seed block differs from physical input')
    scopes={c['world_id']:_world_scope(manifest,c['world_id'],jobs) for c in claims}
    seed_allocations={}
    for c in claims:
        _validate_claim_scope(manifest,c,scopes[c['world_id']][0])
        assembled=assemble(data['rows'],c,scopes[c['world_id']][0])
        expected=_expected_seed_block(manifest,c)
        if assembled['seed_block_id']!=expected:
            raise ValueError('Observed paired seed block differs from the confirmation manifest allocation')
        seed_allocations[c['world_id']]=expected
    output.mkdir(parents=True)
    shutil.copy2(manifest_path,output/'FROZEN_MANIFEST.json')
    atomic_json(output/'INPUT_AUDIT.json',{**audit,'batch':str(batch.resolve()),
        'results_sha256':file_hash(batch/'RESULTS.json'),'jobs_sha256':file_hash(batch/'JOBS.json'),
        'alpha':{'campaign_budget':budget,'previous_spent':previous,'this_manifest':total},
        'frozen_seed_allocations_verified':seed_allocations,
        'world_domain_sources':{world:value[1] for world,value in scopes.items()}})
    results=[]
    try:
        for i,claim in enumerate(claims):
            result=analyze_claim(data['rows'],claim,scopes[claim['world_id']][0])
            result['pre_outcome_freeze_verified']=audit['manifest_link_verified']
            result['domain_source']=scopes[claim['world_id']][1]
            result['analysis_input_sha256']=canonical_hash(claim)
            filename=f'CLAIM_{i+1:02}.json';atomic_json(output/filename,result)
            results.append({'claim_id':claim['claim_id'],'world_id':claim['world_id'],'file':filename,
                            'status':result['status'],'claim_supported':None})
            print(json.dumps(results[-1]),flush=True)
    except Exception as exc:
        atomic_json(output/'FAILED.json',{'status':'partial','error':repr(exc),'completed_claims':results})
        raise
    summary={'status':'completed','utc':datetime.now(timezone.utc).isoformat(),'claims':results,
             'pre_outcome_freeze_verified':audit['manifest_link_verified'],
             'alpha_allocation_total':total,'previous_alpha_spent':previous,'campaign_alpha_budget':budget,
             'interpretation':'All designated analyses completed; this status does not mean their scientific claims were supported.'}
    atomic_json(output/'SUMMARY.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(analyze(args.batch,args.manifest,args.output)),flush=True)


if __name__=='__main__':main()
