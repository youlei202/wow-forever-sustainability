"""Evaluate predeclared new-reward physical-amplitude construction."""
from __future__ import annotations
import json
import numpy as np
from scipy.stats import t as student_t
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_world_analysis import world_ecology
from wowfs.experiments.r4_feasibility import eval_all_safe,evaluate_admission
from wowfs.experiments.r4_batches import solve_problem

def main():
    root=setup_paths();out=root/'artifacts/r4-foundational-discovery';run=root/'runs/r4-foundational-discovery/constructive-reward-v1'
    table=json.loads((run/'RESULTS.json').read_text())['rows'];templates=load_ecologies(run,run/'CONFIG.yaml')
    baseline={(e.pool['id'],e.race):e for e in load_ecologies(root/'runs/r4-foundational-discovery/baseline-v1')}
    rows=[];details=[];certificates=[]
    for scale in [.5,.75,1.,1.25]:
        records=[r for r in table if r['weapon_damage_scale']==scale]
        for template in templates:
            e=world_ecology(template,records);b=baseline[(e.pool['id'],e.race)]
            e.scale=b.scale;e.cap=b.cap;e.protected_sources=b.protected_sources
            for release in [['18203'],['19019'],['18203','19019']]:
                p,ix=e.problem(release,archive=e.initial_archive());full=eval_all_safe(p);rr=solve_problem(p,30)
                rows.append({'ecology':e.pool['id'],'race':e.race,'weapon_damage_scale':scale,'release_items':release,
                    'subset_feasible':rr['feasible'],'status':rr['status'],'all_safe_joint':full['joint_pass'],'all_safe_failures':full['failure_reasons'],
                    'worst_L':full['worst_protected_source_mass'],'K':full['K'],'D_mass':full['novel_task_mass'],
                    'permission':'B synthetic new TF-like physical damage only; original old items untouched'})
                details.append({'race':e.race,'scale':scale,'release':release,'subset':rr,'all_safe':full})
                if len(release)!=2:continue
                q=student_t.ppf(1-.05/(2*len(table)),e.samples.shape[-1]-1)
                for j in np.flatnonzero(p.safe&~p.protected):
                    mask=p.protected.copy();mask[j]=True;m=evaluate_admission(p,mask)
                    if not m['joint_pass']:continue
                    selected=ix[mask];se=e.samples[selected].std(axis=-1,ddof=1)/np.sqrt(e.samples.shape[-1])
                    upper=e.values[selected]+q*se;certificates.append({'race':e.race,'scale':scale,'gear_id':p.gear_ids[j],
                        'metrics':m,'min_cap_slack':float(np.min(p.cap-p.best[mask].max(axis=0))),
                        'simultaneous_DPS_upper_cap_excess':float(np.max(upper-e.cap[None,None,:])),
                        'uncertainty':'Conservative family6912 pointwise Student-t DPS bounds; approximate iid seed inference, no D confidence from aggregate means'})
    write_csv(out/'CONSTRUCTIVE_REWARD_RESULTS.csv',rows);atomic_json(out/'CONSTRUCTIVE_REWARD_DETAILS.json',{'rows':details,'one_gear_certificates':certificates})
    print(json.dumps({'rows':rows,'certificates':[{k:x[k]for k in ['race','scale','gear_id','min_cap_slack','simultaneous_DPS_upper_cap_excess']}for x in certificates]},indent=2))

if __name__=='__main__':main()
