"""Paired fresh verification of frozen native sequences; no parameter retuning."""
from __future__ import annotations
import argparse
import json
import numpy as np
from scipy.stats import t
from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r6_geometry import damage_channels
from wowfs.experiments.r2_sequence_analysis import write_csv


def analyze_rows(rows, order, f0, epsilon, delta, cap, alpha=.05):
    lookup={(r['design_id'],r.get('block',0)):r for r in rows}
    blocks=sorted({r.get('block',0) for r in rows})
    if len(blocks)<2: raise ValueError('Independent block replication required for behavior intervals')
    samples=np.array([[lookup[(d,b)]['dps_samples'] for b in blocks] for d in order])
    physical=np.array([[damage_channels(lookup[(d,b)],180)/f0 for b in blocks] for d in order])
    n=len(order); total=samples.shape[1]*samples.shape[2]
    # Allocate half the error budget to utility and half to action behavior.
    utility_family=2*n-1
    behavior_family=5*n*(n-1)//2
    uq=float(t.ppf(1-alpha/(4*utility_family),total-1))
    bq=float(t.ppf(1-alpha/(4*max(1,behavior_family)),len(blocks)-1))
    flat=samples.reshape(n,-1)
    mean=flat.mean(axis=1); err=flat.std(axis=1,ddof=1)/np.sqrt(total)
    ulo,uhi=mean-uq*err,mean+uq*err
    diff=flat-flat[0]
    dm=diff.mean(axis=1); de=diff.std(axis=1,ddof=1)/np.sqrt(total)
    dlo,dhi=dm-uq*de,dm+uq*de
    behavior_mean=physical.mean(axis=1)
    records=[]; distances=[]; prefix=True
    for i,d in enumerate(order):
        if i==0: continue
        lows=[]; point_distances=[]
        for j in range(i):
            block_delta=physical[i]-physical[j]
            centered=block_delta.mean(axis=0)
            error=block_delta.std(axis=0,ddof=1)/np.sqrt(len(blocks))
            lower=np.maximum(0.,np.abs(centered)-bq*error)
            point=float(np.max(np.abs(centered))); bound=float(np.max(lower))
            lows.append(bound);point_distances.append(point)
            distances.append({'candidate':d,'comparator':order[j],'point_linf':point,
                              'simultaneous_linf_lower':bound,'coordinate_differences':centered.tolist(),
                              'coordinate_standard_errors':error.tolist(),'all_old_history_profiles_included':True})
        point_frontier=float(max(mean[:i+1]))
        P=bool(max(uhi[:i+1])<=cap)
        neutral=bool(max(dhi[1:i+1])<=0 and max(uhi[1:i+1])<=f0)
        N=bool(dlo[i]>=-epsilon)
        D=bool(min(lows)>=delta)
        L=bool(min(dlo[1:i+1])>=-epsilon)
        point_joint=bool(max(mean[:i+1])<=cap and max(dm[1:i+1])<=0 and max(mean[1:i+1])<=f0
                         and min(dm[1:i+1])>=-epsilon and min(point_distances)>=delta)
        joint=bool(P and neutral and N and D and L)
        prefix=prefix and joint
        records.append({'round':i,'design_id':d,'samples_per_design':total,'delta':delta,
            'mean_DPS':float(mean[i]),'old_mean_DPS':float(mean[0]),'frozen_frontier':f0,
            'point_current_frontier':point_frontier,'point_frontier_growth_vs_fresh_old':point_frontier-float(mean[0]),
            'paired_DPS_difference':float(dm[i]),'paired_difference_lower':float(dlo[i]),'paired_difference_upper':float(dhi[i]),
            'absolute_DPS_upper':float(uhi[i]),'min_full_archive_distance':min(point_distances),
            'min_full_archive_distance_lower':min(lows),'P_supported':P,'frontier_neutral_supported':neutral,
            'N_supported':N,'D_supported':D,'L_supported':L,'H_structural':True,'C_supported':neutral,'K':1,
            'joint_point_estimate':point_joint,'joint_approximate_simultaneous_support':joint,'confirmed_prefix':prefix,
            'useful_new_sources':i,'total_useful_design_choices':i+1,'fixed_primitive_rule_rows':6,
            'scope':'Declared one-task one-policy one-partner native research domain; approximate simultaneous inference.'})
    return {'rows':records,'behavior_comparisons':distances,'confirmed_updates':sum(r['confirmed_prefix'] for r in records),
            'utility_family':utility_family,'behavior_family':behavior_family,'utility_quantile':uq,'behavior_quantile':bq,
            'utility_df':total-1,'behavior_df':len(blocks)-1,'alpha':alpha,'samples_per_design':total,
            'old_mean_DPS':float(mean[0]),'old_absolute_DPS_interval':[float(ulo[0]),float(uhi[0])],
            'all_joint_supported':all(r['joint_approximate_simultaneous_support'] for r in records),
            'inference_limit':'Paired native pseudorandom seed observations; Student t approximations, including block behavior means. Neither exact population certificates nor distribution-free coverage.',
            'behavior_mean_by_design':dict(zip(order,behavior_mean.tolist()))}


def main():
    root=setup_paths();out=root/'artifacts/r6-theory-native'
    spec=json.loads((out/'FRONTIER_NEUTRAL_POLYTOPE.json').read_text())
    result=json.loads((root/'runs/r6-theory-native/neutral-confirmation-v1/RESULTS.json').read_text())
    if result['errors']: raise ValueError('Native confirmation failed')
    order=['old_anchor']+[r['design_id'] for r in spec['frozen_sequence']]
    analysis=analyze_rows(result['rows'],order,spec['initial_frontier'],spec['epsilon_raw'],spec['delta'],spec['fixed_cap'])
    analysis['theorem_guaranteed_updates']=spec['geometry']['T_guaranteed']
    analysis['theorem_lower_bound_met']=analysis['confirmed_updates']>=analysis['theorem_guaranteed_updates']
    atomic_json(out/'FRONTIER_NEUTRAL_CONFIRMATION.json',analysis)
    write_csv(out/'FRONTIER_NEUTRAL_SEQUENCE.csv',analysis['rows'])
    write_csv(out/'FRONTIER_NEUTRAL_ARCHIVE_COMPARISONS.csv',analysis['behavior_comparisons'])
    print(json.dumps({k:v for k,v in analysis.items() if k not in ('behavior_comparisons','behavior_mean_by_design')},indent=2))


if __name__=='__main__': main()
