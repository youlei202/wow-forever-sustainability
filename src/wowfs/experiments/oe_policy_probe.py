"""Development challenge: keep physics fixed and vary native mana-policy guards."""
from copy import deepcopy
from pathlib import Path
import json
from wowfs.paths import atomic_json,canonical_hash
from wowfs.experiments.oe_worlds import worlds,jobs_for_world


def change_constant(node,old,new):
    count=0
    if isinstance(node,dict):
        if node.get('const',{}).get('val')==old:
            node['const']['val']=new;count+=1
        else:
            for value in node.values():count+=change_constant(value,old,new)
    elif isinstance(node,list):
        for value in node:count+=change_constant(value,old,new)
    return count


def prepare(run):
    run=Path(run);wm={w['world_id']:w for w in worlds()};out=[];registry=[]
    cases=[('resistance_penetration__Alliance_Gnome_Mage__s0',10,'20%',['10%','35%']),
           ('mana_regen__Alliance_NightElf_Druid__s0',16,'35',['20','50'])]
    for wi,(name,candidate,old,alternatives) in enumerate(cases):
        base=wm[name];world=deepcopy(base)
        world['world_id']=name+'__policy_challenge'
        world['initial_partner_ids']=[1];world['model_scope']='joint_two_update_slots'
        world['policies']=['native']+['mana_guard_'+v for v in alternatives]
        world['policy_intervention']={'original_constant':old,'alternatives':alternatives,
            'scope':'Only existing native APL guard changed. Native spells, effects, gear, talents and task definitions unchanged.'}
        world['world_sha256']=canonical_hash(world);registry.append(world)
        original=jobs_for_world(base,'challenge',1048100001+wi*100000,512,
            {'candidate_indices':[0,candidate],'partner_indices':[0,1,2,3]},debug=True)
        for job in original:
            for qi,policy in enumerate(world['policies']):
                j=deepcopy(job);player=j['input']['request']['raid']['parties'][0]['players'][0]
                if qi:
                    count=change_constant(player['rotation'],old,alternatives[qi-1])
                    if count!=1:raise ValueError(f'Expected exactly one native guard; got {count}')
                j['meta'].update(world_id=world['world_id'],world_sha256=world['world_sha256'],
                    policy_id=policy,policy_index=qi,model_scope=world['model_scope'])
                out.append(j)
    dest=run/'requests';dest.mkdir(parents=True,exist_ok=True)
    atomic_json(dest/'policy-challenge-jobs.json',out)
    atomic_json(dest/'policy-challenge.json',{'batch_id':'policy-challenge-v1','jobs_file':str(dest/'policy-challenge-jobs.json'),
        'science':{'purpose':'Challenge selected two-slot synergy with plausible native policy guards; development data only',
            'worlds':registry,'iterations':512,'seed_base':1048100001,'original_mechanisms_unchanged':True,
            'complete_selected_crosses':True,'scope':'Two selected primary candidates crossed with all four original partners, both tasks and three declared policies; not a full 17-primary capacity domain.'}})
    (run/'POLICY_CHALLENGE_REGISTRY.jsonl').write_text(''.join(json.dumps(w,sort_keys=True)+'\n' for w in registry))
    return {'logical_cells':len(out),'requested_battles':len(out)*512}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run-root',required=True)
    print(json.dumps(prepare(p.parse_args().run_root)))
