#!/usr/bin/env python3
"""Materialize a pre-outcome finite-domain confirmation and unseen settings.

The input design is selected using development data only. This command never
reads confirmation outcomes and refuses to replace a prior manifest or jobs.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random

from wowfs.experiments.oe_catalog_worlds import jobs_for_world as catalog_jobs
from wowfs.experiments.oe_worlds import jobs_for_world as variant_jobs, _alias
from wowfs.paths import SOURCE_ROOT, atomic_json, canonical_hash


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def held_out(original, generator_seed):
    """Independent setting, selected before observing any native responses.

    Catalog: independent 0.9--1.1 duration multipliers for the fixed tasks.
    Research variants: one independent 0.9--1.1 multiplier per overridden
    coordinate, shared across the candidate and partner library in that world.
    Sharing preserves the declared tradeoff family; it does not reuse outcomes.
    """
    world=deepcopy(original)
    world['world_id']=original['world_id']+'__heldout_v1'
    rng=random.Random(str(generator_seed)+':'+original['world_id'])
    transformations=[]
    if world['stratum']=='catalog':
        for task in world['tasks']:
            old=task['duration'];factor=rng.uniform(.9,1.1)
            task['duration']=old*factor
            transformations.append({'task_id':task['task_id'],'coordinate':'duration',
                'old':old,'factor':factor,'new':task['duration']})
        method='independent_duration_multiplier_per_task'
    else:
        coordinates=sorted({(outer,inner) for alias in world['candidates']+world['partners']
            for outer,value in alias['parameter_overrides'].items()
            for inner in (value if isinstance(value,dict) else [None])})
        factors={key:rng.uniform(.9,1.1) for key in coordinates}
        for collection in ('candidates','partners'):
            for i,alias in enumerate(world[collection]):
                params=deepcopy(alias['parameter_overrides'])
                for outer,value in params.items():
                    if isinstance(value,dict):
                        for inner in value:value[inner]*=factors[outer,inner]
                    else:params[outer]*=factors[outer,None]
                label=world['world_id']+(':'+'a'+f'{i:02}' if collection=='candidates' else ':x'+str(i))
                world[collection][i]=_alias(label,alias['native_base_item_id'],alias['equipment_slot'],**params)
        transformations=[{'coordinate':[outer,inner],'factor':factor}
                         for (outer,inner),factor in factors.items()]
        method='shared_coordinate_multipliers_across_research_library'
    world['holdout']={'parent_world_id':original['world_id'],'generator_seed':generator_seed,
        'method':method,'transformations':transformations,
        'interpretation':'One predeclared unseen physical setting, not an independent mechanism or population-wide validation.'}
    world.pop('world_sha256',None);world['world_sha256']=canonical_hash(world)
    return world


def prepare(run, design_path):
    design=json.loads(design_path.read_text())
    registry_path=run/'DEEP_CHALLENGE_REGISTRY.jsonl'
    registry={w['world_id']:w for w in map(json.loads,registry_path.read_text().splitlines())}
    output=run/design.get('manifest_filename','CONFIRMATION_MANIFEST.json')
    jobs_path=run/'requests'/f"{design['batch_id']}-jobs.json"
    config_path=run/'requests'/f"{design['batch_id']}.json"
    if any(p.exists() for p in (output,jobs_path,config_path)):
        raise ValueError('Confirmation inputs already exist; no overwrite allowed')
    worlds=[];jobs=[];claims=[]
    for index,setting in enumerate(design['settings']):
        world=deepcopy(registry[setting['parent_world_id']])
        if setting['role']=='heldout':world=held_out(world,design['holdout_generator_seed'])
        seed=design['seed_base']+index*design['seed_stride'];n=setting['iterations']
        factory=catalog_jobs if world['stratum']=='catalog' else variant_jobs
        world_jobs=factory(world,'confirm',seed,n,selection='full')
        claim={k:deepcopy(v) for k,v in setting.items() if k not in ('parent_world_id','iterations')}
        claim.update(world_id=world['world_id'],model_scope=world['model_scope'],
            initial_items=[f'a{i:02}' for i in world['initial_candidate_ids']]+[f'x{i}' for i in world['initial_partner_ids']],
            seed_block_id=f'{seed}:{n}',iterations=n,
            task_weights=[.5,.5],task_weight_mapping={t['task_id']:.5 for t in world['tasks']},
            gain_mass=.5,retention_mass=.5,max_candidates=19,
            total_item_budget=12)
        references=[]
        for task in sorted(t['task_id'] for t in world['tasks']):
            matches=[j for j in world_jobs if j['meta']['candidate_index']==world['initial_candidate_ids'][0]
                and j['meta']['partner_index']==world['initial_partner_ids'][0]
                and j['meta']['task_id']==task and j['meta']['policy_id']=='native']
            if len(matches)!=1:raise ValueError('Unique original reference required')
            j=matches[0]
            references.append({key:j['meta'][key] for key in ('task_id','candidate_id','partner_id','policy_id')}
                |{'input_sha256':canonical_hash(j['input'])})
        claim['reference_mapping']=references
        worlds.append(world);jobs.extend(world_jobs);claims.append(claim)
    allocations=sum(c['alpha'] for c in claims)
    if allocations>design['campaign_alpha_budget']:raise ValueError('Alpha budget exceeded')
    source_names=['src/wowfs/experiments/'+name for name in
        ('oe_confirmation.py','oe_inference.py','oe_confidence_planner.py','oe_solver.py',
         'oe_worlds.py','oe_catalog_worlds.py','oe_runner.py','oe_claim_decisions.py')]
    source_names+=['scripts/prepare_oe_confirmation.py',str(design_path.relative_to(SOURCE_ROOT))]
    manifest={**{k:v for k,v in design.items() if k!='settings'},
        'utc_frozen_before_native_generation':datetime.now(timezone.utc).isoformat(),
        'previous_alpha_spent':0.,'this_manifest_alpha':allocations,
        'unused_alpha':design['campaign_alpha_budget']-allocations,
        'unused_alpha_policy':'Not recycled in this campaign; no result-dependent reruns or sample extensions.',
        'worlds':worlds,'claims':claims,
        'jobs_file':str(jobs_path),'jobs_canonical_sha256':canonical_hash(jobs),
        'design_sha256':sha(design_path),'development_registry_sha256':sha(registry_path),
        'analysis_hashes':{name:sha(SOURCE_ROOT/name) for name in source_names},
        'native_binary_sha256':'59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe',
        'inference':'Fixed N, approximate simultaneous paired Student-t; no distribution-free claim. The population is this executable simulator under the frozen seed-generating setup.',
        'source_unit':'Every published candidate or partner component, including newly published components.',
        'physical_domain':'All candidate x partner x task x native-policy cells; no blacklists or response interpolation.',
        'reference_policy':'The original a00 and original x reference by identity in each task, remeasured with confirmation seeds.',
        'holdout_scope':'Local seed replication and unseen physical settings reported separately; held-out means not used to retune any parameter.'}
    atomic_json(jobs_path,jobs);atomic_json(output,manifest)
    atomic_json(config_path,{'batch_id':design['batch_id'],'jobs_file':str(jobs_path),
        'science':{'confirmation_manifest_sha256':sha(output),'status':'frozen_before_sampling',
            'campaign_alpha':design['campaign_alpha_budget'],'alpha_this_batch':allocations}})
    return {'manifest':str(output),'sha256':sha(output),'jobs':len(jobs),
        'battles':sum(j['input']['request']['simOptions']['iterations'] for j in jobs),
        'config':str(config_path)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-root',required=True,type=Path)
    p.add_argument('--design',required=True,type=Path);args=p.parse_args()
    print(json.dumps(prepare(args.run_root,args.design)))
