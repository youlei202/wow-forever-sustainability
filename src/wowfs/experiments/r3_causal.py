"""Fresh paired effect-switch decomposition of re-entry witnesses/comparators."""
from copy import deepcopy
import csv
import json
from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r3_native import run_jobs, r2_witness_inputs, replace_item
from wowfs.experiments.r2_analysis import factorial

def main():
    root=setup_paths();inputs=r2_witness_inputs();jobs=[]
    for (gear,race,task,policy),base in inputs.items():
        # Both racial contexts receive the identical canonical Human gear;
        # the Orc-selected trinket alternative is a separate descriptive stratum.
        for weapon,name in [(12795,'blood_talon'),(17068,'deathbringer'),(17705,'thrash_blade')]:
            for mask in range(4):
                value=replace_item(base,14,weapon)
                value['request']['simOptions'].update(iterations=128,randomSeed='309240001',saveAllValues=True,useLabeledRands=True,debugFirstIteration=False)
                value['disable_item_effects']=[item for i,item in enumerate([weapon,19019]) if not mask&(1<<i)]
                value['disable_set_bonuses']=[]
                jobs.append({'input':value,'meta':{'case':name,'gear_stratum':gear,'race':race,
                    'task':task,'strategy':policy,'mask':mask,'n_effects':2}})
    protocol={'purpose':'selected native reactivation witness effect factorial; damage/stat fields unchanged',
        'discovery_source':'R2 selected witness; new seed block is independent',
        'seed_start':309240001,'iterations':128,
        'primary_family':8,'primary_case':'blood_talon','primary_gear':'5ae0e1e5d00fbdb1',
        'primary_policy':'native_reck','primary_contexts':['RaceHuman','RaceOrc'],
        'primary_tasks':['sustained','short_burst','four_target','high_armor'],
        'interaction_smallness_threshold':'1% of the independently sampled R2 initial task optimum; adjusted CI must lie inside both margins',
        'other_contrasts':'descriptive comparator/policy/alternate-trinket panels',
        'no_assumed_synergy':'safe-set re-entry does not imply positive effect interaction'}
    run=run_jobs(jobs,'causal-factorials-v1',root/'envs/r2-go/wowfs-native',protocol)
    rows=json.loads((run/'RESULTS.json').read_text())['rows'];groups={}
    for row in rows:
        key=tuple(row[x] for x in ['case','gear_stratum','race','task','strategy'])
        groups.setdefault(key,{})[row['mask']]=row
    signatures=[]
    for key,cells in sorted(groups.items()):
        record=dict(zip(['case','gear_stratum','race','task','strategy'],key))
        primary=key[0]=='blood_talon' and key[1]=='5ae0e1e5d00fbdb1' and key[4]=='native_reck'
        record.update(factorial({m:r['dps_samples'] for m,r in cells.items()},2,8 if primary else 1))
        record['primary']=primary
        record.update({f'mean_{m}':r['dps_mean'] for m,r in cells.items()})
        record['cache_directories']=[r['cache_directory'] for r in cells.values()]
        signatures.append(record)
    atomic_json(root/'artifacts/r3-gold/CAUSAL_FACTORIALS.json',{'protocol':protocol,'signatures':signatures})
    with (root/'artifacts/r3-gold/INTERACTION_SIGNATURES.csv').open('w',newline='') as f:
        fields=list(signatures[0]);writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in signatures:writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
    print(json.dumps([x for x in signatures if x['primary']],indent=2))

if __name__=='__main__':main()
