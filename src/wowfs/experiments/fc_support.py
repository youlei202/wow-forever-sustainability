"""Frozen all-official-context native execution support check, not capacity."""
import argparse
import gzip
import json
from pathlib import Path
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json,canonical_hash
from wowfs.experiments.fc_native import contexts,presets,engine_root,normalize_gear,make_input,run_jobs,STAGE
from wowfs.experiments.r2_native import file_hash


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    contexts_all=contexts(); task={'id':'sustained','duration':180,'targets':1,'armor':3731,'execute':.2}
    inputs={}; provenance={}
    for cls,p in presets().items():
        for key in ('gear','apl'):
            inputs[p[key]]=engine_root()/p[key]
        items,moves=normalize_gear(json.loads(inputs[p['gear']].read_text())['items'])
        provenance[cls]={**p,'normalized_equipment':items,'preset_slot_moves':moves,
            'gear_source_sha256':file_hash(inputs[p['gear']]),'apl_source_sha256':file_hash(inputs[p['apl']])}
    inputs['native-register_all.go']=engine_root()/'sim/register_all.go'
    inputs['native-racials.go']=engine_root()/'sim/core/racials.go'
    jobs=[{'input':make_input(c,task,seed=810000001,iterations=16,debug=True),
           'meta':{**c,'task':task['id'],'strategy':presets()[c['class']]['apl'],'scope':'execution_support'}} for c in contexts_all]
    science={'purpose':'All56 official class/race native execution support. Not capacity, release-validity, balance or live fidelity coverage.',
        'engine_commit':'17d75ccc8c67d027ae0088243ea3ee806d406847',
        'engine_repository':'https://github.com/sage3648/mythicsim-forever-engine',
        'task':task,'iterations':16,'seed':810000001,'contexts':contexts_all,'presets':provenance,
        'policy_scope':'One native source-defined DPS specialization/APL per class; identical across same-class races.',
        'known_racial_omissions':'HighOrder health/mana regen; Gnome energy/rage pool enlargement. Remaining cases not claimed live validated.'}
    run=run_jobs(jobs,'support-smoke-v1',science,workers=16,resume=args.resume,
        source_paths=[SOURCE_ROOT/'src/wowfs/experiments/fc_support.py',SOURCE_ROOT/'configs/fc_presets.json',SOURCE_ROOT/'configs/official_contexts.yaml'],input_artifacts=inputs)
    rows=json.loads((run/'RESULTS.json').read_text())['rows']; checks=[]
    for row in rows:
        with gzip.open(Path(row['cache_directory'])/'output.json.gz','rt') as f:raw=json.load(f)
        p=raw['raidMetrics']['parties'][0]['players'][0]
        checks.append({k:row[k] for k in ('context_id','class','race','faction','native_racial_incomplete','dps_mean','iterations','cache_directory')} | {
            'native_player_name':p.get('name'),'player_action_count':len(p.get('actions',[])),
            'resources':row['resources'],'pet_metrics':[{'name':x.get('name'),'dps':x.get('dps',{}).get('avg'),
                'action_count':len(x.get('actions',[]))} for x in p.get('pets',[])],
            'positive_finite_damage':row['dps_mean']>0,
            'rotation_warnings':raw.get('raidStats',{}),'output_sha256':row['output_sha256']})
    artifact={'schema':1,'scope':'Executed native support only, not capacity coverage.',
        'run':str(run),'protocol_sha256':file_hash(run/'PROTOCOL.json'),
        'contexts_requested':56,'contexts_completed':len(checks),'classes_completed':len({x['class'] for x in checks}),
        'battles':sum(x['iterations'] for x in checks),'positive_damage_contexts':sum(x['positive_finite_damage'] for x in checks),
        'known_racial_incomplete_contexts':sum(x['native_racial_incomplete'] for x in checks),'checks':checks}
    atomic_json(setup_paths()/'artifacts'/STAGE/'NATIVE_SUPPORT_RECEIPT.json',artifact)
    print(json.dumps({k:v for k,v in artifact.items() if k!='checks'},indent=2))


if __name__=='__main__':main()
