"""One declared adaptive reallocation: independent native pools, calibrated t0."""
from __future__ import annotations
import argparse,copy,json,shutil
from itertools import combinations
from pathlib import Path
import numpy as np
import yaml
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_native import load_config,prepare,run_jobs
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_feasibility import evaluate_admission

PREDICTIONS=[
 {'id':'UD1','pool':'unseen_resource_cost','race':'RaceOrc','release':['18203','19951'],
  'direction':'Joint pair can pass with one admitted new configuration; neither singleton passes.',
  'mechanism':'Replace Onyxia neck with native Mugamba heroic-strike cost reduction. Joint timing/resource support should persist without Heroism set feedback.'},
 {'id':'UD2','pool':'unseen_skill_trade','race':'RaceOrc','release':['18203','19019'],
  'direction':'Removing Edgemaster sword/axe skill while retaining fist skill reduces the relative weak-MH compensation; pair loses cap margin or joint feasibility.',
  'mechanism':'Native Devilsaur gloves replace Edgemaster. This also changes AP/crit, explicitly measured; not a pure skill-only causal intervention.'},
 {'id':'UF1','pool':'unseen_resource_cost','race':'both','direction':'At least one matched qualified current pair has unequal one-step continuation under the same common future inventory; three/five-step survival is not predicted.',
  'status':'Risky adaptive prediction after first F confirmation failed; current pair selected before future-run outcomes.'}]

def config():
    cfg=copy.deepcopy(load_config());original={p['id']:p for p in cfg['pools']};pools=[]
    for src,name,override,selected in [('timing_extra','unseen_resource_cost',{'neck':19577},None),
                                     ('timing_shared','unseen_skill_trade',{'hands':15063},{'18203','19019'})]:
        p=copy.deepcopy(original[src]);p['id']=name;p['parent_discovery_pool']=src;p.setdefault('fixed',{}).update(override)
        if selected:p['slots']={k:v[:2]+[x for x in v[2:]if str(x)in selected]for k,v in p['slots'].items()}
        pools.append(p)
    cfg['pools']=pools;cfg['candidate_design_families']=[]
    cfg['ecology_scope']='Two genuinely changed fixed-equipment pools; complete finite domains. No claim of independent random ecological sampling.'
    return cfg

def perform(cfg,name,workers,old_only=False):
    root=setup_paths();jobs,eco=prepare(cfg)
    if old_only:
        initial=set(g for p in eco['ecosystems']for g in p['initial_gear_ids']);jobs=[j for j in jobs if j['meta']['gear_id']in initial]
    run=root/'runs/r4-foundational-discovery'/name;run.mkdir(parents=True,exist_ok=True)
    actual=yaml.safe_dump(cfg,sort_keys=False);p=run/'CONFIG.yaml'
    if p.exists()and p.read_text()!=actual:raise ValueError('Frozen actual config changed')
    p.write_text(actual);atomic_json(run/'BASE_ECOSYSTEMS.json',eco)
    (run/'source').mkdir(exist_ok=True);shutil.copy2(Path(__file__),run/'source'/Path(__file__).name)
    science={'config':cfg,'predictions':PREDICTIONS,'old_only':old_only,'source_sha256':file_hash(Path(__file__)),
             'permission':'A native existing items, new fixed ecology from t0; no original cap changes','anchor':'Calibrate old16 at independent512 seeds then freeze numerical caps before candidates'}
    run_jobs(jobs,name,scientific_protocol=science,workers=workers,resume=(run/'PROTOCOL.json').exists());return run,eco

def anchors(run,eco):
    rows=json.loads((run/'RESULTS.json').read_text())['rows'];lookup={(r['gear_id'],r['race'],r['task'],r['strategy']):r['dps_mean']for r in rows};output={}
    for pool in eco['ecosystems']:
        ids=pool['initial_gear_ids'];sources=pool['source_ids_by_gear']
        for race in eco['races']:
            values=np.array([[[lookup[(g,race,t['id'],p['id'])]for t in eco['tasks']]for p in eco['strategies']]for g in ids])
            scale=values.max(axis=(0,1));close=values.max(axis=1)>=.95*scale
            old=pool['old_source_ids'];registry=[str(s)for s in old if np.any(close[np.array([s in sources[g]for g in ids])])]
            output[pool['id']+'__'+race]={'scale':scale.tolist(),'cap':(1.05*scale).tolist(),'protected_sources':registry,'seed':409280001,'iterations':512}
    return output

def freeze_current_pairs(run,anchor,full_cfg):
    pairs=[];allnew=sorted({str(i)for p in full_cfg['pools']if p['id']=='unseen_resource_cost'for v in p['slots'].values()for i in v[2:]})
    for e in load_ecologies(run,run/'CONFIG.yaml'):
        a=anchor[e.pool['id']+'__'+e.race];e.scale=np.array(a['scale']);e.cap=np.array(a['cap']);e.protected_sources=tuple(a['protected_sources'])
        actions=[]
        for release in [('19951',),('18203',),('18203','19951')]:
            p,ix=e.problem(release,archive=e.initial_archive())
            for j in np.flatnonzero(p.safe&~p.protected):
                mask=p.protected.copy();mask[j]=True;m=evaluate_admission(p,mask)
                if m['joint_pass']:actions.append({'release':list(release),'gear_id':p.gear_ids[j],'metrics':m})
        candidates=[]
        for x,y in combinations(actions,2):
            if x['release']!=y['release']or x['metrics']['K']!=y['metrics']['K']:continue
            d=float(np.max(np.abs(np.array(x['metrics']['optimum'])-y['metrics']['optimum'])/e.scale))
            mass=max(abs(x['metrics']['novel_task_mass']-y['metrics']['novel_task_mass']),abs(x['metrics']['worst_protected_source_mass']-y['metrics']['worst_protected_source_mass']))
            candidates.append((d,mass,len(x['release']),x['gear_id'],y['gear_id'],x,y))
        result={'pool':e.pool['id'],'race':e.race,'qualified_actions':len(actions),'status':'no_pair','actions':actions}
        if candidates:
            chosen=min(candidates,key=lambda p:p[:5]);d,mass,_,_,_,x,y=chosen
            result.update(status='matched'if d<=.01 and mass<=.125 else 'unmatched_nearest',distance=d,mass_distance=mass,
                          selected=[x,y],future_items=[s for s in allnew if s not in x['release']][:5])
        pairs.append(result)
    return pairs

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['initial_current','future']);parser.add_argument('--workers',type=int,default=16);args=parser.parse_args()
    root=setup_paths();out=root/'artifacts/r4-foundational-discovery';cfg=config()
    protocol={'predictions':PREDICTIONS,'config':cfg,'stages':{'initial':'allold16,512seed409280001','current':'resource pool only with18203/19951,512seed409290001','future':'complete228 configurations across2pools,256seed409300001'},
              'selection':'Same-release same-K one-gear admissions; minimum normalized frontier distance then massdifference then smallerrelease andgearIDs; <=.01frontier and<=.125mass consideredmatched',
              'reuse':'No unseen future means loaded for currentpairselection','superseded_results':'Discovery16 and failed512 confirmations retained; original caps not changed'}
    freeze=out/'UNSEEN_POOL_PREDICTIONS.json'
    if freeze.exists()and json.loads(freeze.read_text())!=protocol:raise ValueError('Unseen protocol changed')
    atomic_json(freeze,protocol)
    if args.stage=='initial_current':
        cfg['sampling'].update(iterations=512,seed_start=409280001);run,eco=perform(cfg,'unseen-initial-v1',args.workers,True)
        anchor=anchors(run,eco);atomic_json(out/'UNSEEN_FROZEN_ANCHORS.json',anchor)
        current=copy.deepcopy(cfg);current['pools']=[copy.deepcopy(cfg['pools'][0])]
        current['pools'][0]['slots']={k:v[:2]+[x for x in v[2:]if str(x)in {'18203','19951'}]for k,v in current['pools'][0]['slots'].items()}
        current['sampling'].update(iterations=512,seed_start=409290001)
        run,_=perform(current,'unseen-current-v1',args.workers)
        atomic_json(out/'UNSEEN_CURRENT_BRANCH_SELECTION.json',freeze_current_pairs(run,anchor,cfg))
    else:
        if not(out/'UNSEEN_CURRENT_BRANCH_SELECTION.json').exists():raise ValueError('Must freeze current pair before future physics')
        cfg['sampling'].update(iterations=256,seed_start=409300001);perform(cfg,'unseen-future-v1',args.workers)

if __name__=='__main__':main()
