"""Native tests of reward-amplitude affine families at fixed control settings."""
from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
import re

import numpy as np

from wowfs.paths import atomic_json, canonical_hash, setup_paths
from wowfs.experiments.r3_native import r2_witness_inputs, run_jobs

ANCHORS = [(24.,0.),(54.,0.),(24.,30.),(54.,30.)]
INTERIORS = [(30.,11.),(44.,23.)]


def make_amplitude_input(base,dps,dot,speed=1.3,offhand=19019,trinkets=(11815,13965),seed=309241001,iterations=128,debug=False):
    value=deepcopy(base)
    items=value['request']['raid']['parties'][0]['players'][0]['equipment']['items']
    items[12]={'id':trinkets[0]};items[13]={'id':trinkets[1]};items[14]={'id':12795};items[15]={'id':offhand}
    value['request']['simOptions'].update(iterations=iterations,randomSeed=str(seed),saveAllValues=True,useLabeledRands=True,debugFirstIteration=debug)
    value['research_variants']=[{'item_id':12795,'weapon_damage_scale':dps/(51/1.3),
        'weapon_speed_seconds':speed,'speed_mode':'hold_base_dps','periodic_damage_per_tick':dot}]
    return value


def raw(row):
    with gzip.open(row['cache_directory']+'/output.json.gz','rt') as f:return json.load(f)


def controls(output):
    player=output['raidMetrics']['parties'][0]['players'][0]
    actions=[]
    for action in player['actions']:
        targets=[{k:v for k,v in t.items() if not any(term in k.lower() for term in ('damage','threat','healing','shielding'))} for t in action['targets']]
        actions.append({**{k:v for k,v in action.items() if k!='targets'},'targets':targets})
    return {'actions':sorted(actions,key=lambda a:json.dumps(a['id'],sort_keys=True)),
            'resources':sorted(player['resources'],key=lambda a:json.dumps(a,sort_keys=True)),
            'auras':sorted(player['auras'],key=lambda a:json.dumps(a['id'],sort_keys=True))}


def trace_events(log):
    events=[]
    for line in log.splitlines():
        if any(token in line for token in ('Casting ','Completed cast ','Aura gained:','Aura faded:','Aura refreshed:','stacks:','Gained ','Spent ','gained ','stored ')):
            events.append(line)
        elif ' damage' in line and ('Hit for ' in line or 'Crit for ' in line or 'Glance for ' in line or 'Block for ' in line):
            line=re.sub(r'[-+\d.eE]+(?= damage)','<reward>',line)
            line=re.sub(r'(?<=Threat: )[-+\d.eE]+','<reward>',line)
            events.append(line)
    return events


def probe(workers=64,resume=False):
    root=setup_paths();inputs=r2_witness_inputs();jobs=[]
    for (gear,race,task,policy),base in inputs.items():
        if gear!='5ae0e1e5d00fbdb1' or policy!='native_reck':continue
        for index,(dps,dot) in enumerate(ANCHORS+INTERIORS):
            jobs.append({'input':make_amplitude_input(base,dps,dot,debug=True),
                         'meta':{'point':index,'base_dps':dps,'dot_damage':dot,'race':race,'task':task,'strategy':policy}})
    protocol={'hypothesis':'At fixed event/control settings, per-seed combat reward is affine in weapon base DPS and Blood Talon tick amplitude.',
        'anchors':ANCHORS,'interior_validation':INTERIORS,'fit':'Three anchors; fourth corner and interiors are predictions, not fitted.',
        'seed_start':309241001,'iterations':128,'contexts':'Human/Orc matched canonical Human gear, 4 tasks, native_reck',
        'control_fixed':{'speed':1.3,'ppm':1,'tick_interval':3,'ticks':10,'offhand':19019,'trinkets':[11815,13965]},
        'test_tolerance_dps':1e-8,'event_checks':'Aggregated cast/hit/crit/tick/resource/aura metrics over 128 battles; normalized event schedule of first logged seed. Do not infer per-seed event timings from aggregate counters.',
        'no_new_type_claim':'These are research amplitude variants retaining the original native effect grammar.'}
    run=run_jobs(jobs,'affine-probe-v1',root/'envs/r3-go/wowfs-native-variants',protocol,workers,resume)
    rows=json.loads((run/'RESULTS.json').read_text())['rows'];groups={}
    for row in rows:groups.setdefault((row['race'],row['task']),{})[row['point']]=row
    contrasts=[];max_residual=0.;all_controls=True;all_traces=True
    for (race,task),cells in sorted(groups.items()):
        values={i:np.asarray(r['dps_samples']) for i,r in cells.items()}
        base_raw=raw(cells[0]);control0=controls(base_raw);trace0=trace_events(base_raw['logs'])
        for i,(dps,dot) in enumerate(ANCHORS+INTERIORS):
            prediction=values[0]+(dps-24)/30*(values[1]-values[0])+dot/30*(values[2]-values[0])
            residual=values[i]-prediction;maximum=float(np.max(np.abs(residual)))
            output=raw(cells[i]);same_control=controls(output)==control0;same_trace=trace_events(output['logs'])==trace0
            contrasts.append({'race':race,'task':task,'point':i,'base_dps':dps,'dot_damage':dot,
                'is_held_out_prediction':i>=3,'mean_dps':float(values[i].mean()),'max_absolute_per_seed_residual':maximum,
                'mean_residual':float(residual.mean()),'aggregate_control_metrics_identical':same_control,
                'first_seed_event_schedule_identical':same_trace,'cache_key':cells[i]['cache_key']})
            max_residual=max(max_residual,maximum);all_controls&=same_control;all_traces&=same_trace
    result={'protocol':protocol,'max_absolute_per_seed_residual':max_residual,
            'affine_predictions_pass_1e_8':max_residual<=1e-8,
            'all_aggregate_control_metrics_identical':all_controls,
            'all_first_seed_event_schedules_identical':all_traces,'rows':contrasts,
            'native_cells':len(jobs),'physical_battles':len(jobs)*128,
            'inference_scope':'Paired-seed structural validation in this finite tested domain, not a theorem about every engine state.'}
    atomic_json(run/'AFFINE_PROBE.json',result);atomic_json(root/'artifacts/r3-gold/AFFINE_PROBE.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','protocol')},indent=2))
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=64);parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();probe(args.workers,args.resume)


if __name__=='__main__':main()
