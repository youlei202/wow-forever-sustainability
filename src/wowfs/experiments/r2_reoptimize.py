"""Select on development seeds, confirm winners under global effect ablations."""
from copy import deepcopy
import json
from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r2_native import load_config, run_jobs
from wowfs.experiments.r2_analysis import factorial

def main():
    root=setup_paths();base=root/'runs/r2-discovery';cfg=load_config()
    matrix=json.loads((base/'discovery-v1/JOBS.json').read_text())
    names={'haste_extra':'frequency_haste','extra_resource':'resource_heroism','shared_active':'burst_shared'}
    jobs=[]
    for case in cfg['causal_cases']:
        effects=[case['effect_a'],case['effect_b']]
        for row in matrix:
            if names[case['id']] not in row['meta'].get('pools',[]):continue
            for mask in range(4):
                inp=deepcopy(row['input'])
                disabled=[e for i,e in enumerate(effects) if not mask&(1<<i)]
                if 'optional_effect_c' in case:disabled.append(case['optional_effect_c'])
                inp['disable_item_effects']=[e['item_id'] for e in disabled if 'item_id' in e]
                inp['disable_set_bonuses']=[{'name':e['set_name'],'pieces':e['pieces']} for e in disabled if 'set_name' in e]
                meta={**row['meta'],'case':case['id'],'mask':mask,'n_effects':2,'stage':'reoptimization_development'}
                jobs.append({'input':inp,'meta':meta})
    dev=base/'reoptimization-development-v1'
    run_jobs(jobs,dev,root/'envs/r2-go/wowfs-native',64,resume=dev.joinpath('PROTOCOL.json').exists())
    results=json.loads((dev/'RESULTS.json').read_text())['rows']
    winners={}
    for i,row in enumerate(results):
        key=(row['case'],row['task'],row['mask'])
        if key not in winners or row['dps_mean']>results[winners[key]]['dps_mean']:winners[key]=i
    confirm=[]
    for key,i in sorted(winners.items()):
        job=deepcopy(jobs[i]);opts=job['input']['request']['simOptions']
        opts['randomSeed']='92428001';opts['iterations']=128
        job['meta']['stage']='reoptimization_confirmation';confirm.append(job)
    con=base/'reoptimization-confirmation-v1'
    atomic_json(con/'SELECTION.json',{'scope':'16 native loadouts and 3 policies per case, four switch cells; same budget per cell',
                'development_seed_interval':[24092401,24092432],'confirmation_seed_interval':[92428001,92428128],
                'primary_family':12,'winners':[{k:v for k,v in j['meta'].items()} for j in confirm]})
    run_jobs(confirm,con,root/'envs/r2-go/wowfs-native',64,resume=con.joinpath('PROTOCOL.json').exists())
    groups={}
    for row in json.loads((con/'RESULTS.json').read_text())['rows']:
        groups.setdefault((row['case'],row['task']),{})[row['mask']]=row['dps_samples']
    atomic_json(con/'CONTRASTS.json',[{'case':k[0],'task':k[1],**factorial(v,2,12)} for k,v in groups.items()])

if __name__=='__main__':main()
