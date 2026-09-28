"""Bounded native set-gate feasibility, with every glove/leg cross-pair retained."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path

from wowfs.paths import setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r6_native import r3_base, run_jobs, native_database, validate_equipment, SLOTS, R5_SHA256

GLOVES=[14551,21998,21278,19143]
LEGS=[22385,22000,15057]
FIXED={'head':21999,'wrist':21996,'chest':15056,'shoulder':15058}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true')
    parser.add_argument('--workers',type=int,default=14);args=parser.parse_args()
    root=setup_paths();base,base_path=r3_base();base.pop('research_variants',None)
    base['disable_item_effects']=[];base['disable_set_bonuses']=[]
    base['request']['simOptions'].update(randomSeed='609270001',iterations=2048,debugFirstIteration=True)
    items=base['request']['raid']['parties'][0]['players'][0]['equipment']['items']
    for slot,item in FIXED.items():items[SLOTS.index(slot)]={'id':item}
    database=native_database();jobs=[]
    for gloves,legs in itertools.product(GLOVES,LEGS):
        value=deepcopy(base);equipment=value['request']['raid']['parties'][0]['players'][0]['equipment']['items']
        equipment[SLOTS.index('hands')]={'id':gloves};equipment[SLOTS.index('legs')]={'id':legs}
        validate_equipment(value)
        counts=Counter(database[i['id']].get('setName') for i in equipment if database[i['id']].get('setName'))
        assert counts['Battlegear of Heroism']==2+int(gloves==21998)+int(legs==22000)
        assert counts['Stormshroud Armor']==2+int(gloves==21278)+int(legs==15057)
        meta={'glove_id':gloves,'leg_id':legs,'condition':'native','race':'RaceHuman',
            'task':'high_armor','strategy':'native_reck','world':'native','stage':'bounded_set_gate_probe',
            'gear_id':canonical_hash(equipment)[:16],'set_piece_counts':dict(counts),
            'glove_role':{14551:'old_anchor',21998:'protected_candidate_heroism',
                          21278:'protected_candidate_stormshroud',19143:'new_core'}[gloves],
            'leg_role':{22385:'old_neutral',22000:'heroism_repair',15057:'stormshroud_repair'}[legs]}
        jobs.append({'input':value,'meta':meta})
    for gloves,legs,set_name,label in [(21998,22000,'Battlegear of Heroism','heroism4_off'),
                                      (21278,15057,'Stormshroud Armor','stormshroud4_off')]:
        original=next(j for j in jobs if j['meta']['glove_id']==gloves and j['meta']['leg_id']==legs)
        control=deepcopy(original)
        control['input']['disable_set_bonuses']=[{'name':set_name,'pieces':4}]
        control['meta'].update(condition=label,world='matching_set4_ablation')
        jobs.append(control)
    science={'formal_r5_sha256':R5_SHA256,
        'purpose':'Bounded native source-gate feasibility; neither a matched cascade nor unique repair is assumed.',
        'context':{'race':'RaceHuman','task':'high_armor','policy':'native_reck','duration_seconds':180,'armor':10000},
        'glove_ids':GLOVES,'leg_ids':LEGS,'fixed_equipment_overrides':FIXED,
        'old_domain':{'gloves':[14551,21998,21278],'legs':[22385]},
        'protected_source_candidates':[21998,21278],'designated_old_anchor':14551,'new_core':19143,
        'repair_mapping':{'21998':22000,'21278':15057},
        'full_legal_domain':'All4gloves×3legs including oldanchor/core×repairs. No offdiagonal combinations hidden.',
        'control_cells':['MatchingHeroism4 disabled with identicalequippedgear','MatchingStormshroud4 disabled with identicalequippedgear'],
        'theory_parameters':{'relevance_epsilon':'.05*f0','fixed_cap':'1.05*f0',
            'f0':'Maximum over all3 oldgloves witholdneutrallegs in this one-task/policy table'},
        'source_hypotheses':['Heroism4 gives actualrage feedback','Stormshroud4 gives14AP',
            'Nativegates alone mayfail unique-repair/stablewitness assumptions because legaloffdiagonals changeutility'],
        'stop_conditions':'If initialsource protection, coreband, uniqueness or stablewitness premises fail, reportpremise failure; no outcome-drivenstat tuning. m4/m8 not_run; statistical locality not_run unlessA premises hold.',
        'amplitudes':'No research_variants. NativeTalon baseweapon/effect restored fromR3template, all ordinary item stats unchanged.',
        'seed_start':609270001,'iterations':2048,'logical_cells':14,'physical_battles':28672,
        'source_input_note':'Imported base_input is exactR3calibrationtemplate; specified substitutions and removalofTalonscale reproduce everyfrozenjob.'}
    freeze=root/'artifacts/r6-theory-native/FROZEN_GATE_PROBE.json'
    if freeze.exists():assert json.loads(freeze.read_text())['science']==science
    else:atomic_json(freeze,{'utc':datetime.now(timezone.utc).isoformat(),'science':science,'status':'frozen_before_A_native_calls'})
    run=run_jobs(jobs,'native-gate-probe-v1',science,workers=args.workers,resume=args.resume,
                 source_paths=[Path(__file__)],input_artifacts={'base_input.json':base_path})
    results=json.loads((run/'RESULTS.json').read_text())
    print(json.dumps({'run':str(run),'errors':results['errors'],'rows':[
        {k:row[k] for k in ['glove_id','leg_id','condition','dps_mean','cache_key']} for row in results['rows']]},indent=2))


if __name__=='__main__':main()
