"""Native counterfactual weapon-DPS by speed phase diagram, fixed other effects."""
from copy import deepcopy
import itertools
from wowfs.paths import setup_paths
from wowfs.experiments.r3_native import r2_witness_inputs, run_jobs

DPS=[24,28,32,36,51/1.3,42,46,50,54]
SPEEDS=[1.0,1.3,1.6,1.9,2.2,2.5,2.8]
OFFHANDS=[871,12590,18816,19019]
TRINKETS=list(itertools.product([11815,19951],[13965,20130]))

def main():
    root=setup_paths();inputs=r2_witness_inputs();jobs=[]
    for (gear,race,task,policy),base in inputs.items():
        if gear!='5ae0e1e5d00fbdb1':continue
        for di,si,offhand,trinkets in itertools.product(range(len(DPS)),range(len(SPEEDS)),OFFHANDS,TRINKETS):
            value=deepcopy(base);items=value['request']['raid']['parties'][0]['players'][0]['equipment']['items']
            items[12]={'id':trinkets[0]};items[13]={'id':trinkets[1]};items[14]={'id':12795};items[15]={'id':offhand}
            value['request']['simOptions'].update(iterations=32,randomSeed='309240201',saveAllValues=True,useLabeledRands=True,debugFirstIteration=False)
            value['research_variants']=[{'item_id':12795,'weapon_damage_scale':DPS[di]/(51/1.3),
                                          'weapon_speed_seconds':SPEEDS[si],'speed_mode':'hold_base_dps'}]
            jobs.append({'input':value,'meta':{'point':f'd{di}_s{si}','base_dps':DPS[di],
                'weapon_speed':SPEEDS[si],'race':race,'task':task,'strategy':policy,
                'offhand':offhand,'trinket1':trinkets[0],'trinket2':trinkets[1],
                'research_family':'BloodTalon_native_effect_fixed','stage':'phase_development'}})
    protocol={'purpose':'controlled contiguous complement region, exploratory phase',
        'axes':{'base_weapon_dps':DPS,'weapon_speed_seconds':SPEEDS},
        'speed_intervention':'native weapon speed; scaled min/max preserve specified base DPS independently',
        'kept_fixed':'Blood Talon 1PPM,10damage×10ticks every3s; static armor/body/talents/buffs',
        'same_seed_all_cells':309240201,'iterations':32,
        'counterpart_offhands':OFFHANDS,'trinket_pairs':TRINKETS,
        'before_state':'R2 expanded_interleaved_0 round19, all old finite catalogue configurations/policies',
        'reference':'R2 independently sampled185initial envelopes;0and5% cumulative cap, no reanchoring',
        'power_views':'unfiltered all-counterpart peak AND fixed-cap per-loadout reference filter; never conflate',
        'behavior':'frozen R2 seven physical coordinates; infinity distance0.05; no ID dimension',
        'next_step':'freeze a small set of informative region points for new-seed128 confirmation'}
    run_jobs(jobs,'phase-grid-v1',root/'envs/r3-go/wowfs-native-variants',protocol)

if __name__=='__main__':main()
