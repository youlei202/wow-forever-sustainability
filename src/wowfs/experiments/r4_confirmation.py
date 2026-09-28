"""Frozen fresh-seed confirmation of selected complete release subdomains."""
from __future__ import annotations
import argparse,copy,json,shutil
from pathlib import Path
from wowfs.paths import setup_paths,SOURCE_ROOT,atomic_json,canonical_hash
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_native import load_config,prepare,run_jobs

SELECTIONS={'resource_haste':['18203','19951'],'timing_shared':['18203','19019'],
            'timing_extra':['19951','18203','22321']}
PREDICTIONS=[
 {'id':'D1','ecology':'resource_haste','race':'RaceHuman','release':['18203','19951'],
  'prediction':'Pair retains joint feasibility; both singletons lack competitive D; paired novelty witnesses require both new items.',
  'basis':'Largest discovery D margin .0818 beyond threshold; native rage active plus haste weapon. No assumption of positive damage superadditivity.'},
 {'id':'D2','ecology':'timing_shared','race':'RaceOrc','release':['18203','19019'],
  'prediction':'Pair retains joint feasibility; singleton releases fail; dual-item witness survives in high-armor task.',
  'basis':'D margin .0439 and all-safe cap slack4.53DPS; weapon compensation competes with haste-resource hypothesis.'},
 {'id':'F1','ecology':'timing_extra','race':'RaceHuman','first_item':'19951',
  'branch_gears':['426712995313d7dc','b2a3b09c5d796149'],'future_items':['18203','22321'],
  'prediction':'Both first actions remain jointly qualified and equal current frontiers;18203 admits under Blackhands branch but not HoJ branch;22321 admits under both.',
  'basis':'Discovery current full metrics and archive count identical; later difference exclusively D. This could disappear with independent sampling.'}]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=64);parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    root=setup_paths();cfg=load_config();cfg=copy.deepcopy(cfg)
    pools=[]
    for pool in cfg['pools']:
        if pool['id'] not in SELECTIONS:continue
        selected=set(SELECTIONS[pool['id']]);pool=copy.deepcopy(pool)
        pool['slots']={slot:values[:2]+[v for v in values[2:]if str(v)in selected]for slot,values in pool['slots'].items()}
        pools.append(pool)
    cfg['pools']=pools;cfg['sampling'].update(iterations=512,seed_start=409250001)
    # This is a selected confirmation domain, not the broad mechanism curriculum.
    cfg['candidate_design_families']=[]
    cfg['ecology_scope']='Complete domains induced by the selected new IDs and all original old choices; three discovery-selected pools.'
    protocol={'stage':'independent seeds on discovery-selected complete domains; not unseen ecology',
        'selections':SELECTIONS,'predictions':PREDICTIONS,'config':cfg,
        'comparison':'Same fixed discovery initial cap/scale/registry for primary confirmation; fresh reestimated anchor diagnostic separately.',
        'uncertainty':'Native DPS seed samples and paired means retained; behavior mean summaries do not provide per-seed D confidence bounds.',
        'source_hash':file_hash(Path(__file__))}
    out=root/'artifacts/r4-foundational-discovery';freeze=out/'FRESH_CONFIRMATION_PREDICTIONS.json'
    if freeze.exists()and json.loads(freeze.read_text())!=protocol:raise ValueError('Frozen confirmation changed')
    atomic_json(freeze,protocol)
    jobs,eco=prepare(cfg);runpath=root/'runs/r4-foundational-discovery/confirmation-v1'
    (runpath/'source').mkdir(parents=True,exist_ok=True);shutil.copy2(Path(__file__),runpath/'source'/Path(__file__).name)
    atomic_json(runpath/'BASE_ECOSYSTEMS.json',eco)
    run=run_jobs(jobs,'confirmation-v1',scientific_protocol=protocol,workers=args.workers,resume=args.resume)
    atomic_json(run/'BASE_ECOSYSTEMS.json',eco);print(run,flush=True)

if __name__=='__main__':main()
