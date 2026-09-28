"""Permission-C native worlds applied from t=0; separate executable and cache keys."""
from __future__ import annotations
import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json,canonical_hash
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_native import run_jobs,make_input,load_config

INTERVENTIONS=[
 {'id':'A1','pool':'timing_shared','world':'independent_offensive','research_world':{'independent_offensive_cooldowns':True}},
 {'id':'A2','pool':'timing_extra','world':'unified_offensive_60s','research_world':{'all_offensive_shared_seconds':60}},
 {'id':'A3','pool':'timing_periodic','world':'unified_offensive_60s','research_world':{'all_offensive_shared_seconds':60}},
 {'id':'A4','pool':'resource_set_pair','world':'heroism_no_extra','research_world':{'heroism_excludes_extra_attacks':True}},
 {'id':'A5','pool':'resource_cost','world':'heroism_no_extra','research_world':{'heroism_excludes_extra_attacks':True}},
 {'id':'A6','pool':'resource_haste','world':'heroism_no_extra','research_world':{'heroism_excludes_extra_attacks':True}},
 {'id':'A7','pool':'timing_extra','world':'no_extra_reentry','research_world':{'block_extra_attack_reentry':True}},
 {'id':'A8','pool':'resource_haste','world':'no_extra_reentry','research_world':{'block_extra_attack_reentry':True}}]


def frozen_ecology():return json.loads((setup_paths()/'runs/r4-foundational-discovery/baseline-v1/BASE_ECOSYSTEMS.json').read_text())

def binary():return setup_paths()/'envs/r4-go/wowfs-native-worlds'

def raw(row):
 with gzip.open(Path(row['cache_directory'])/'output.json.gz','rt') as f:return json.load(f)

def canonical_result(value):
 if isinstance(value,dict):return {k:canonical_result(v) for k,v in value.items()}
 if isinstance(value,list):
  values=[canonical_result(v) for v in value]
  if values and all(isinstance(v,dict) and 'id' in v for v in values):values.sort(key=lambda v:json.dumps(v['id'],sort_keys=True))
  return values
 return value

def smoke():
 root=setup_paths();eco=frozen_ecology();cfg=load_config();jobs=[]
 incoming=json.loads((root/'runs/r4-foundational-discovery/incoming-smoke-v1/RESULTS.json').read_text())['rows'][0]
 golden=json.loads((Path(incoming['cache_directory'])/'input.json').read_text())
 jobs.append({'input':golden,'meta':{'case':'native_default_golden','reference_cache_directory':incoming['cache_directory']}})
 cases=[('shared',{'main_hand':17112,'off_hand':17705,'trinket1':20130,'trinket2':19289,'legs':14554},{'independent_offensive_cooldowns':True}),
        ('unified',{'main_hand':17112,'off_hand':17705,'trinket1':20130,'trinket2':19951,'legs':22385},{'all_offensive_shared_seconds':60}),
        ('heroism',{'head':21999,'shoulder':22001,'wrist':21996,'chest':21997,'main_hand':11684,'off_hand':871,'trinket1':11815,'trinket2':19289},{'heroism_excludes_extra_attacks':True}),
        ('reentry',{'main_hand':11684,'off_hand':871,'trinket1':11815,'trinket2':19289},{'block_extra_attack_reentry':True})]
 for case,overrides,world in cases:
  gear=dict(cfg['character']['base_equipment']);gear.update(overrides)
  task=cfg['tasks'][1] if case in ('shared','unified') else cfg['tasks'][0]
  value=make_input(gear,task,cfg['strategies'][1],'RaceHuman',409239101,32,cfg,debug=True)
  for state in [False,True]:
   env=deepcopy(value);env['research_world']=world if state else {}
   jobs.append({'input':env,'meta':{'case':case,'intervention':state}})
 run=run_jobs(jobs,'world-smoke-v2',binary(),{'purpose':'Default parity and actual changed-event smoke; shared-resource fixtures use short task to make simultaneous demand explicit, not ecological inference.'},workers=4)
 rows=json.loads((run/'RESULTS.json').read_text())['rows'];actual=raw(rows[0]);actual.pop('wowfsResearchWorld',None)
 reference=raw(incoming);assert canonical_result(actual)==canonical_result(reference),'Default world did not preserve canonical native result'
 assert actual['logs']==reference['logs'],'Default event log changed'
 summary=[]
 for row in rows:
  output=raw(row);summary.append({'case':row['case'],'intervention':row.get('intervention'),
   'dps_mean':row['dps_mean'],'telemetry':output['wowfsResearchWorld'],'cache_key':row['cache_key']})
 result={'default_full_canonical_result_and_log_identical':True,'binary_sha256':file_hash(binary()),
         'canonicalization':'Sort only metric lists of records with id fields; native Go map iteration order is not combat order. Event log and seed-value order unchanged.',
         'calls':len(jobs),'battles':2+8*32,'rows':summary}
 atomic_json(run/'WORLD_SMOKE.json',result);print(json.dumps(result,indent=2));return result


def prepare_worlds():
 root=setup_paths();eco=frozen_ecology();cfg=load_config();poolmap={p['id']:p for p in eco['ecosystems']};jobs=[]
 for contrast in INTERVENTIONS:
  pool=poolmap[contrast['pool']]
  for gid in pool['terminal_gear_ids']:
   gear=eco['gears'][gid]['gear']
   for task in cfg['tasks']:
    for strategy in cfg['strategies']:
     for race in cfg['races']:
      env=make_input(gear,task,strategy,race,cfg['sampling']['seed_start'],cfg['sampling']['iterations'],cfg)
      env['research_world']=contrast['research_world']
      jobs.append({'input':env,'meta':{'intervention_id':contrast['id'],'pool':pool['id'],'pools':eco['gears'][gid]['pools'],
       'gear_id':gid,'race':race,'task':task['id'],'strategy':strategy['id'],'world':contrast['world'],'stage':'t0_research_world'}})
 return jobs,eco


def run(workers=64,resume=False):
 root=setup_paths();jobs,eco=prepare_worlds();sources=[SOURCE_ROOT/'src/wowfs/experiments/r4_worlds.py',SOURCE_ROOT/'src/wowfs/simulator/r4_worlds.go',SOURCE_ROOT/'scripts/native_build_r4.sh']
 science={'permission':'C: independent alternate worlds applied before character construction at t=0; not admission-only algorithms.',
  'interventions':INTERVENTIONS,'world_initial_anchors':'Recompute16 initial native means and own1.05 caps in each world; also preserve common native old means and raw performance differences.',
  'marginal_matching':'No strength compensation or claim of perfectly matched single-item marginals. Report standalone and joint shifts explicitly.',
  'semantics':{'independent_offensive':'One timer per GetOffensiveTrinketCD registration, including active legs; independent resources replace native shared timer.',
   'unified_offensive_60s':'Every registered spell with native SpellFlagOffensiveEquipment shares one60s timer perunit. Replaces existing shared timers while retaining each personal cooldown; includes active rage and active stat effects.',
   'heroism_no_extra':'Filter eligible landed melee events tagged OtherActionAttack tag3 before Heroism PPM draw; other ordinary/special triggers remain.',
   'no_extra_reentry':'Suppress entire extra-MH generation request batch only when triggerAction is native extra-auto tag3; stored and immediate requests covered. Already-triggered companion auras remain.'},
  'limitations':'Tagged extra-auto only: a queued special replacing an extra swing has its own action identity and is not claimed to be classified as extra. Request counts differ from realized attack counts.',
  'baseline_ecosystems_sha256':canonical_hash(eco),'source_hashes':{str(p.relative_to(SOURCE_ROOT)):file_hash(p) for p in sources},
  'binary_sha256':file_hash(binary()),'comparison_unit':'Eight pool-intervention pairs, two races; shared equipment and RNG do not imply independent ecological replication.'}
 runpath=root/'runs/r4-foundational-discovery/worlds-v1'
 for p in sources:
  dst=runpath/'source'/p.relative_to(SOURCE_ROOT);dst.parent.mkdir(parents=True,exist_ok=True)
  if dst.exists() and file_hash(dst)!=file_hash(p):raise ValueError('frozen world source changed')
  if not dst.exists():shutil.copy2(p,dst)
 atomic_json(root/'artifacts/r4-foundational-discovery/C_WORLD_INTERVENTIONS.json',science)
 runpath=run_jobs(jobs,'worlds-v1',binary(),science,workers,resume)
 atomic_json(runpath/'BASE_ECOSYSTEMS.json',eco)
 print(runpath,flush=True)


def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['smoke','run']);p.add_argument('--workers',type=int,default=64);p.add_argument('--resume',action='store_true');a=p.parse_args()
 if a.stage=='smoke':smoke()
 else:run(a.workers,a.resume)

if __name__=='__main__':main()
