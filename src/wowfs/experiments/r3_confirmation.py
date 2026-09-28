"""Fresh seed confirmation of a once-selected phase subset, frozen before execution."""
from itertools import product
from wowfs.paths import setup_paths
from wowfs.experiments.r3_native import r2_witness_inputs, run_jobs
from wowfs.experiments.r3_affine import make_amplitude_input
from wowfs.experiments.r3_phase_grid import OFFHANDS, TRINKETS

POINTS=[(28,1.0),(28,1.3),(32,1.0),(32,1.3),(24,1.0),(28,1.9),
        (51/1.3,1.3),(46,1.3),(54,1.0),(54,2.8)]

def main():
    root=setup_paths();inputs=r2_witness_inputs();jobs=[]
    for (gear,race,task,policy),base in inputs.items():
        if gear!='5ae0e1e5d00fbdb1':continue
        for index,(dps,speed) in enumerate(POINTS):
            for oh,trinkets in product(OFFHANDS,TRINKETS):
                value=make_amplitude_input(base,dps,10,speed,oh,trinkets,309246001,1024)
                jobs.append({'input':value,'meta':{'point':f'confirm_{index}','base_dps':dps,
                    'weapon_speed':speed,'race':race,'task':task,'strategy':policy,'offhand':oh,
                    'trinket1':trinkets[0],'trinket2':trinkets[1], 'stage':'fresh_phase_confirmation'}})
    protocol={'selection':'10 points chosen once from32-seed development before this fresh seed block.',
        'points':POINTS,'seed_start':309246001,'iterations':1024,'counterpart_offhands':OFFHANDS,
        'trinket_pairs':TRINKETS,'primary_family':'four interior2x2points ×2races at5%cap, all4tasks3policies16gears',
        'other_points':'low-power control, slower-region, nativeboundary, nearupperboundary, race-dependentboundary, outside highpower control',
        'power_inference':'Simultaneous Student-t means across all confirmation cells vs frozennumericR2cap; underlying populationinitialanchor uncertainty separate sensitivity.',
        'utility_and_behavior':'Report frozen nearoptimality and0.05meanbehavior; do not treat aggregatebehavior as confidence bound.',
        'raw_and_filtered':'Keep full newgear raw peak and cap-filtered finite reference separate.',
        'scope':'Controlled nativevariant parameter family, not new official IDs or positiveprocsynergy.'}
    run_jobs(jobs,'phase-confirmation-v1',root/'envs/r3-go/wowfs-native-variants',protocol,workers=24)

if __name__=='__main__':main()
