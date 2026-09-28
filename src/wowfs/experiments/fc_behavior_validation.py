"""Independent read-only check of original Warrior behavior interpolation."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import numpy as np

from wowfs.experiments.fc_behavior import profile_from_output, profile_from_outputs
from wowfs.experiments.r3_affine import raw
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_group(args):
    context,task,duration,rows=args
    bypoint={(round(r['primary_coefficient'],14),round(r['partner_coefficient'],14)):r for r in rows}
    lo=raw(bypoint[0.,0.]);hi=raw(bypoint[.148,0.]);unit=rows[0]['stat_unit']
    checked=[]
    for row in rows:
        output=raw(row);total=(row['primary_coefficient']+row['partner_coefficient'])*unit
        predicted=profile_from_outputs(lo,hi,total,.148*unit,duration,'Warrior')
        actual=profile_from_output(output,duration,'Warrior')
        channel=float(np.max(np.abs(np.asarray(actual['raw_channels'])-predicted['raw_channels'])))
        rage=float(np.max(np.abs(np.asarray(actual['warrior_resource_numerators'])-predicted['warrior_resource_numerators'])))
        typed=0.
        for key in actual['typed_resources'].keys()|predicted['typed_resources'].keys():
            fields=actual['typed_resources'].get(key,{})|predicted['typed_resources'].get(key,{})
            for field in fields:
                typed=max(typed,abs(actual['typed_resources'].get(key,{}).get(field,0.)-
                                    predicted['typed_resources'].get(key,{}).get(field,0.)))
        checked.append({'context_id':context,'task':task,'primary_coefficient':row['primary_coefficient'],
            'partner_coefficient':row['partner_coefficient'],'cache_key':row['cache_key'],
            'max_original_damage_channel_residual':channel,'max_rage_numerator_residual':rage,
            'max_typed_resource_rate_residual':typed,'pass':max(channel,rage,typed)<=1e-8})
    return checked


def main():
    root=setup_paths();run=root/'runs/final-completion-capacity/capacity-confirmation-v1'
    results=json.loads((run/'RESULTS.json').read_text());cfg=json.loads((run/'inputs/FROZEN_MAIN_PROTOCOL.json').read_text())
    durations={t['id']:t['duration'] for t in cfg['tasks']};groups={}
    for row in results['rows']:
        if row['class']=='Warrior':groups.setdefault((row['context_id'],row['task']),[]).append(row)
    args=[(cid,task,durations[task],rows) for (cid,task),rows in sorted(groups.items())]
    with ThreadPoolExecutor(max_workers=8) as pool:
        checks=[row for block in pool.map(inspect_group,args) for row in block]
    payload={'schema':1,'analysis_only':True,'new_native_calls':0,'source_results_sha256':digest(run/'RESULTS.json'),
        'source_sha256':digest(__file__),'profile_source_sha256':digest(SOURCE_ROOT/'src/wowfs/experiments/fc_behavior.py'),
        'contexts':len({r['context_id'] for r in checks}),'context_task_groups':len(groups),
        'physical_checkpoints_checked':len(checks),'tolerance':1e-8,'all_pass':all(r['pass'] for r in checks),
        'max_original_damage_channel_residual':max(r['max_original_damage_channel_residual'] for r in checks),
        'max_rage_numerator_residual':max(r['max_rage_numerator_residual'] for r in checks),
        'max_typed_resource_rate_residual':max(r['max_typed_resource_rate_residual'] for r in checks),
        'scope':'Original Warrior7 damage-channel and resource numerators at every executed checkpoint; finite-point interpolation validation, not a population D confidence bound or all-parameter proof.',
        'checks':checks}
    out=root/'artifacts/final-completion-capacity/ORIGINAL_BEHAVIOR_INTERPOLATION_CHECK.json'
    atomic_json(out,payload)
    print(json.dumps({k:v for k,v in payload.items() if k!='checks'},indent=2))


if __name__=='__main__':main()
