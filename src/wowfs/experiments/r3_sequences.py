"""Prospective 20-wave controlled-family pilot; every candidate is native simulated."""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
import numpy as np
from wowfs.paths import setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r3_native import r2_witness_inputs, run_jobs
from wowfs.experiments.r3_affine import make_amplitude_input

PROFILES=[(12590,11815,13965),(12590,11815,20130),(19019,11815,13965),(19019,11815,20130)]
SPEEDS=[1.0,1.3,1.9]
METHODS=['random_horizontal','immediate_utility','novelty_first','legacy_first',
         'complement_constrained','generic_multiobjective','scalar_reprice']

def design():
    pools=[]
    for sequence,seed in enumerate([309243101,309243102]):
        rng=np.random.default_rng(seed)
        for wave in range(1,21):
            for candidate in range(6):
                # Two proposals per speed, including substantial vertical pressure.
                speed=SPEEDS[candidate//2]
                dps=float(rng.uniform(26,52));dot=float(rng.uniform(0,30))
                item={'sequence':sequence,'wave':wave,'candidate':candidate,
                      'base_dps':dps,'dot_damage':dot,'weapon_speed':speed}
                item['variant_id']=canonical_hash(item)[:16];pools.append(item)
    return {'schema':1,'status':'prospective_frozen_before_candidate_combats',
        'pool_seeds':[309243101,309243102],'pools':pools,'profiles':PROFILES,
        'native_seed_start':309244001,'iterations':128,'headroom':.05,
        'tasks':['sustained','short_burst','four_target','high_armor'],
        'policies':['native_no_reck','native_reck','rage_conserve'],
        'races':['RaceHuman','RaceOrc'],'methods':METHODS,
        'baseline':'R2 expanded_interleaved_0 round19 finite safe catalogue, independently frozen initial185 cap anchors',
        'admission':'Fixed affine mean envelope for the 3 source-defined control kernels and 4 profiles; previous legal choices immutable. Unknown kernels reject. No fresh per-item cap fit.',
        'selection_information':'All methods see the same current six native response tables, affine predictions, old catalogue and history. No later-wave response is accessed for selection.',
        'selection':'Random chooses uniform source-seeded candidate; immediate maximizes mean normalized new utility; novelty maximizes competitive novelty task mass then distance; legacy maximizes number of newly reactivated old sources then gain. Complement requires P,N,D,L,H,C then maximizes legacy reactivation, new utility and stable candidate ID. Generic contains identical feasible rule and objective, thus ties by construction.',
        'scalar':'Current-only compatible scalar LP may reprice observed item columns, protects all previous legal choices; same constrained selection objective, solver failures are rejections.',
        'P':'All admitted native mean task/policy values <= fixed numeric 1.05 initial task optimum. Independent seeds make calibration misclassification visible.',
        'N':'New item competitive on >=0.05 task mass, tolerance0.05 initial scale, taskweights0.25.',
        'D':'New competitive profile distance>=0.05 L-infinity from ALL legal old-only policies and historical competitive profiles in frozen7dimensional behavior.',
        'L':'Every previously competitive released reward plus initially competitive before-state source remains competitive on >=0.05 task mass.',
        'H':'All previously legal loadouts preserved. No deletion or redraw after failed selection.',
        'C':'Exact equipment portfolio K<=4 covers>=0.95 task mass; finite fixed envelope rule budget.',
        'archive':'Register all competitive profiles on admission, even if not behaviorally novel; cumulative distinct choices are task-conditioned greedy packing lower bounds.',
        'failure':'No feasible candidate => explicit rejected wave, N=D=false, prefix ends. Raw selection failures remain in later state if admitted. Never draw replacements.',
        'scope':'Controlled reward-amplitude/speed family pilot, not a broad resource/caster transfer or an independent official-item discovery. Two pools × two races are4 contexts, not4 independent mechanic families.'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=64)
    parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    root=setup_paths();frozen=design();inputs=r2_witness_inputs();jobs=[]
    for (gear,race,task,policy),base in inputs.items():
        if gear!='5ae0e1e5d00fbdb1':continue
        for item in frozen['pools']:
            for oh,t1,t2 in PROFILES:
                value=make_amplitude_input(base,item['base_dps'],item['dot_damage'],item['weapon_speed'],
                    oh,(t1,t2),frozen['native_seed_start'],frozen['iterations'])
                jobs.append({'input':value,'meta':{**item,'race':race,'task':task,'strategy':policy,
                             'offhand':oh,'trinket1':t1,'trinket2':t2,'stage':'prospective_sequential_pilot'}})
    run=run_jobs(jobs,'sequences-v1',root/'envs/r3-go/wowfs-native-variants',frozen,args.workers,args.resume)
    atomic_json(root/'artifacts/r3-gold/SEQUENTIAL_FROZEN_DESIGN.json',frozen)
    print(run)

if __name__=='__main__':main()
