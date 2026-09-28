"""R6 model audit restricted to the original R3 amplitude rectangle."""
from collections import defaultdict
import json
import numpy as np

from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r6_geometry import affine_fit, damage_channels, line_segment, polygon_vertices, segment_certificate

DURATIONS = {'sustained':180, 'short_burst':30, 'four_target':90, 'high_armor':180}


def analyze():
    root = setup_paths()
    source = root/'runs/r3-gold/affine-calibration-v1/RESULTS.json'
    rows = json.loads(source.read_text())['rows']
    groups = defaultdict(dict)
    for row in rows:
        if row['race']=='RaceHuman' and row['weapon_speed']==1.3:
            groups[(row['offhand'], row['trinket2'], row['strategy'], row['task'])][row['anchor']] = row
    models, old_frontier = {}, defaultdict(float)
    for key, anchors in groups.items():
        points = [[anchors[i]['base_dps'], anchors[i]['dot_damage']] for i in range(3)]
        u = affine_fit(points, [anchors[i]['dps_mean'] for i in range(3)])
        c = affine_fit(points, [damage_channels(anchors[i], DURATIONS[key[-1]]) for i in range(3)])
        old = float(np.array([1.,54.,0.]) @ u)
        old_frontier[key[-1]] = max(old_frontier[key[-1]], old)
        models[key] = (u,c)
    witness = (19019,13965,'native_reck','high_armor')
    u,c = models[witness]
    f0 = old_frontier['high_armor']
    a = [[-1,0],[1,0],[0,-1],[0,1]]
    b = [-24,54,0,30]
    labels = ['DPS>=24','DPS<=54','tick>=0','tick<=30']
    for key,(uu,_) in sorted(models.items()):
        a.append(uu[1:].tolist());b.append(old_frontier[key[-1]]-uu[0]);labels.append(str(key))
    a.append((-u[1:]).tolist());b.append(u[0]-.95*f0);labels.append('designated witness usefulness')
    endpoints = line_segment(a,b,u,.975*f0)
    certificate = segment_certificate(a,b,endpoints,c/f0,.05,12,12)
    vertices = polygon_vertices(a,b)
    # For a fixed comparator, a linear-fractional coordinate with positive
    # denominator attains extrema at vertices. This is an upper diagnostic,
    # not a guarantee of distance from the entire archive.
    same_profile_bounds=[]
    for key,(uu,cc) in sorted(models.items()):
        old_behavior = (np.array([1,54,0]) @ cc)/(np.array([1,54,0]) @ uu)
        fractions = (np.c_[np.ones(len(vertices)), vertices] @ cc)/(np.c_[np.ones(len(vertices)), vertices] @ uu)[:,None]
        same_profile_bounds.append({'context':list(key),'max_vertex_distance_from_same_old_profile':float(np.max(np.abs(fractions-old_behavior)))})
    result={'scope':'Existing R3 native calibration only; no new battles; finite fitted response domain.',
            'source_results':str(source), 'race':'RaceHuman', 'weapon_speed':1.3,
            'old_research_anchor':[54,0], 'domain':{'DPS':[24,54],'tick_damage':[0,30]},
            'partners':{'offhand':[12590,19019],'fixed_trinket':11815,'other_trinket':[13965,20130]},
            'policies':['native_no_reck','native_reck','rage_conserve'],'tasks':list(DURATIONS),
            'full_cross_contexts':len(models), 'initial_frontiers':dict(old_frontier),
            'witness':list(witness),'utility_coefficients':u.tolist(),
            'behavior_definition':'Five native action-channel DPS coordinates divided by fixed old high-armor frontier; R3 normalized-share definition audited separately.',
            'A':a,'b':b,'constraint_labels':labels,'vertices':vertices.tolist(),
            'contained_segment':endpoints.tolist(),'certificate':certificate,
            'same_old_profile_fraction_distance_bounds':same_profile_bounds,
            'conclusion':'This explicit R3-range segment gives a zero capacity certificate; this is not an impossibility theorem for the whole region or game.'}
    dest=root/'artifacts/r6-theory-native/ORIGINAL_R3_DOMAIN_DIAGNOSTIC.json'
    atomic_json(dest,result)
    print(json.dumps({'artifact':str(dest),'certificate':certificate,'vertices':len(vertices)},indent=2))
    return result


if __name__=='__main__':
    analyze()
