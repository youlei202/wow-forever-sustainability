"""Item-independent deterministic new demands; explicitly separate task-growth track."""
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import json
import shutil
import yaml
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json,canonical_hash
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_native import make_input,run_jobs

POOLS=['static_skill','static_accuracy','timing_extra','timing_shared','resource_set_pair','resource_cost','target_damage','target_armor']
TASK_PARAMETERS=[(45,1,5000),(120,3,5000),(45,3,7500),(120,1,7500)]


def prepare():
 root=setup_paths();base=root/'runs/r4-foundational-discovery/baseline-v1'
 cfg=yaml.safe_load((base/'source/configs/r4_ecosystems.yaml').read_text())
 original=json.loads((base/'BASE_ECOSYSTEMS.json').read_text());eco=deepcopy(original);tasks=[]
 for duration,targets,armor in TASK_PARAMETERS:
  tasks.append({'id':f'growth_{duration}s_{targets}t_{armor}','duration_seconds':duration,'targets':targets,
                'target_level':63,'target_armor':armor,'execute_proportion_20':.2})
 eco['tasks']=tasks;eco['ecosystems']=[p for p in eco['ecosystems'] if p['id'] in POOLS]
 needed={g for p in eco['ecosystems'] for g in p['terminal_gear_ids']}
 eco['gears']={k:g for k,g in eco['gears'].items() if k in needed};eco['metrics']['task_weights']=[.25]*4
 eco['scope']='Only four additional measured tasks in eight frozen equipment pools. For12-task growth diagnostic, preserve all original8 caps and old source registry separately.'
 cfg['tasks']=tasks;cfg['pools']=[p for p in cfg['pools'] if p['id'] in POOLS];cfg['metrics']['task_weights']=[.25]*4
 cfg['sampling'].update(iterations=16,seed_start=409270001,workers=16)
 science={'permission':'Declared task-growth diagnostic; not a success claim for original fixed8-task problem.',
  'task_generator':'Deterministic2 durations×2 target counts with balanced armor5000/7500; source-defined, item-independent, not a random population.',
  'task_parameters':TASK_PARAMETERS,'tasks':tasks,'pools':POOLS,'seed_start':409270001,'iterations':16,
  'old_constraints':'Retain every original8-task numeric cap and its protected source registry. Do not dilute worst old-task growth by adding task weights.',
  'new_caps':'Each new task uses1.05 times maximum over the same16 initial old configurations and3 policies, separately by pool/race.',
  'weights':'New-only physical metadata has1/4 weights for loader completeness; merged12-task analysis must explicitly declare its weights and preservation obligations.',
  'baseline_ecosystems_sha256':canonical_hash(original),'measured_ecosystems_sha256':canonical_hash(eco),
  'source_sha256':file_hash(SOURCE_ROOT/'src/wowfs/experiments/r4_task_growth.py')}
 freeze=root/'artifacts/r4-foundational-discovery/FROZEN_TASK_GROWTH_DESIGN.json'
 if freeze.exists():
  prior=json.loads(freeze.read_text());assert prior['science']==json.loads(json.dumps(science)),'frozen task design differs'
 else:atomic_json(freeze,{'utc':datetime.now(timezone.utc).isoformat(),'science':science,'status':'frozen_before_new_demand_native_outcomes'})
 jobs=[]
 for gid,record in eco['gears'].items():
  for task in tasks:
   for strategy in cfg['strategies']:
    for race in cfg['races']:
     value=make_input(record['gear'],task,strategy,race,409270001,16,cfg)
     jobs.append({'input':value,'meta':{'gear_id':gid,'pools':[p for p in record['pools'] if p in POOLS],
       'task':task['id'],'race':race,'strategy':strategy['id'],'world':'native','stage':'independent_task_growth'}})
 return jobs,eco,cfg,science


def main():
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=16);p.add_argument('--resume',action='store_true');a=p.parse_args()
 root=setup_paths();jobs,eco,cfg,science=prepare();run=root/'runs/r4-foundational-discovery/task-growth-v1'
 run.mkdir(parents=True,exist_ok=True)
 atomic_json(run/'BASE_ECOSYSTEMS.json',eco)
 frozen_config=run/'CONFIG.yaml';text=yaml.safe_dump(cfg,sort_keys=False)
 if frozen_config.exists():assert frozen_config.read_text()==text
 else:frozen_config.write_text(text)
 source=SOURCE_ROOT/'src/wowfs/experiments/r4_task_growth.py';dest=run/'source/src/wowfs/experiments/r4_task_growth.py';dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(source,dest)
 print(json.dumps({'jobs':len(jobs),'battles':len(jobs)*16,'unique_gears':len(eco['gears'])}),flush=True)
 run_jobs(jobs,'task-growth-v1',scientific_protocol=science,workers=a.workers,resume=a.resume)
 print(run,flush=True)

if __name__=='__main__':main()
