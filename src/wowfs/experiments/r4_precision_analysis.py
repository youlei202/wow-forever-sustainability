"""Selected certificates with pooled native blocks and simultaneous uncertainty."""
from __future__ import annotations
import copy,json
from pathlib import Path
import numpy as np
from scipy.stats import t as student_t
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_sequence_analysis import behavior_vector,portfolio_cover,write_csv
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_feasibility import evaluate_admission

def pool_rows(rows):
    if not rows or len({r['iterations']for r in rows})!=1:
        raise ValueError('Pooling requires nonempty equal-size native blocks')
    if any(len(r['dps_samples'])!=r['iterations']for r in rows):
        raise ValueError('Native block sample count mismatch')
    out=copy.deepcopy(rows[0]);out['iterations']=sum(r['iterations']for r in rows)
    out['dps_samples']=sum([r['dps_samples']for r in rows],[]);out['dps_mean']=float(np.mean(out['dps_samples']))
    actions={}
    for row in rows:
        for key,a in row['actions'].items():
            target=actions.setdefault(key,{'damage':0.,'casts':0.});target['damage']+=a['damage']/len(rows);target['casts']+=a['casts']/len(rows)
    total=sum(a['damage']for a in actions.values())
    for a in actions.values():a['fraction']=a['damage']/total if total else 0
    resources={}
    for row in rows:
        for res in row['resources']:
            key=json.dumps([res['type'],res['id']],sort_keys=True);target=resources.setdefault(key,{'type':res['type'],'id':res['id'],'gain':0.,'actualGain':0.,'events':0.})
            for field in ['gain','actualGain','events']:target[field]+=res[field]/len(rows)
    out['actions']=actions;out['resources']=list(resources.values());return out

def paired_behavior_lower_bounds(blocks,pooled,old_mask,candidate,quantile):
    """Block-paired coordinate rectangles, then min-reference max-coordinate.

    A block is the leading axis. ``take`` makes reference selection explicit
    so separated scalar/Boolean advanced indices cannot move that axis.
    Pooled ratio centers plus block-ratio standard errors are approximate.
    """
    blocks=np.asarray(blocks,float);pooled=np.asarray(pooled,float);old_mask=np.asarray(old_mask,bool)
    if blocks.ndim!=5 or pooled.shape!=blocks.shape[1:] or old_mask.shape!=(blocks.shape[1],):
        raise ValueError('Expected block×gear×policy×task×coordinate and matching pooled array')
    if blocks.shape[0]<2 or not np.any(old_mask) or old_mask[candidate] or quantile<0:
        raise ValueError('Need multiple paired blocks, old references and a distinct new candidate')
    reference_blocks=np.take(blocks,np.flatnonzero(old_mask),axis=1)
    reference_centers=np.take(pooled,np.flatnonzero(old_mask),axis=0)
    count,_,policies,tasks,coords=blocks.shape
    lower=np.empty((policies,tasks))
    for policy in range(policies):
        for task in range(tasks):
            center=pooled[candidate,policy,task]-reference_centers[:,:,task,:].reshape(-1,coords)
            old_blocks=reference_blocks[:,:,:,task,:].reshape(count,-1,coords)
            difference=blocks[:,candidate,policy,task][:,None,:]-old_blocks
            radius=quantile*difference.std(axis=0,ddof=1)/np.sqrt(count)
            lower[policy,task]=float(np.maximum(np.abs(center)-radius,0).max(axis=1).min())
    return lower

def main():
    root=setup_paths();out=root/'artifacts/r4-foundational-discovery'
    candidates=list((root/'runs/r4-foundational-discovery').glob('*precision*/RESULTS.json'))
    if len(candidates)!=1:raise ValueError('Expected one final precision run; found '+str(candidates))
    run=candidates[0].parent;rows=json.loads(candidates[0].read_text())['rows']
    baseline={e.race:e for e in load_ecologies(root/'runs/r4-foundational-discovery/baseline-v1')if e.pool['id']=='timing_shared'}
    results=[];sens=[]
    for race,scale in [('RaceHuman',.5),('RaceOrc',.75)]:
        b=baseline[race];gid='d9ddad879238ea73';selected=set(np.array(b.gear_ids)[b.initial])|{gid};indices=[i for i,g in enumerate(b.gear_ids)if g in selected]
        e=copy.deepcopy(b);e.gear_ids=[b.gear_ids[i]for i in indices];e.gears=[b.gears[i]for i in indices];e.sources=[b.sources[i]for i in indices];e.initial=b.initial[indices]
        e.values=np.empty((17,3,8));e.behavior=np.empty((17,3,8,7));e.samples=np.empty((17,3,8,4096));blocks=np.empty((8,17,3,8,7))
        lookup={}
        for r in rows:
            if r['race']==race:lookup.setdefault((r['gear_id'],r['strategy'],r['task']),[]).append(r)
        for g,key in enumerate(e.gear_ids):
            for p,policy in enumerate(e.policies):
                for t,task in enumerate(e.tasks):
                    cells=sorted(lookup[(key,policy,task['id'])],key=lambda r:r['block'])
                    if [r['block']for r in cells]!=list(range(8)):raise ValueError('Incomplete independent blocks')
                    pooled=pool_rows(cells);e.values[g,p,t]=pooled['dps_mean'];e.samples[g,p,t]=pooled['dps_samples'];e.behavior[g,p,t]=behavior_vector(pooled,task['duration_seconds'])
                    for i,cell in enumerate(cells):blocks[i,g,p,t]=behavior_vector(cell,task['duration_seconds'])
        p,ix=e.problem(['18203','19019'],archive=e.initial_archive());mask=np.ones(17,bool);point=evaluate_admission(p,mask)
        # Divide a familywise 5% error budget between performance and behavior.
        alpha_perf=.025;perf_family=17*3*8*2;q=student_t.ppf(1-alpha_perf/(2*perf_family),4095)
        se=e.samples.std(axis=-1,ddof=1)/np.sqrt(4096);lower=e.values-q*se;upper=e.values+q*se;top=upper.max(axis=(0,1));lowbest=lower.max(axis=1)
        close=lowbest>=top-.05*e.scale;mass={s:float(np.mean(np.any(close[np.array([s in ss for ss in e.sources])],axis=0)))for s in set.union(set(),*e.sources)}
        j=e.gear_ids.index(gid);d_family=48*3*8*7*2;qd=student_t.ppf(1-.025/(2*d_family),7)
        d_lower=paired_behavior_lower_bounds(blocks,e.behavior,e.initial,j,qd)
        novel=(d_lower>=.05)&(lower[j]>=top-.05*e.scale)
        cover=portfolio_cover(lowbest,top,e.scale,epsilon=.05,weights=np.ones(8)/8,coverage=.95)
        checks={'P':bool(np.all(top<=e.cap)),'N':all(mass[s]>=.05 for s in ['18203','19019']),
                'D':bool(np.mean(np.any(novel,axis=0))>=.05),'L':all(mass[s]>=.05 for s in e.protected_sources),
                'H':True,'C':cover['K']is not None and cover['K']<=4}
        witnesses=[]
        for policy in range(3):
            for t,task in enumerate(e.tasks):
                if e.values[j,policy,t]>=e.values.max(axis=(0,1))[t]-.05*e.scale[t]:
                    witnesses.append({'task':task['id'],'policy':e.policies[policy],'D_point':p.distances[j,policy,t],
                        'D_lower':d_lower[policy,t],'competitive_lower_margin':lower[j,policy,t]-top[t]+.05*e.scale[t]})
        result={'race':race,'TF_weapon_damage_scale':scale,'new_gear_id':gid,'iterations_per_cell':4096,'blocks':8,'point_metrics':point,
            'simultaneous_approximate_checks':checks,'simultaneous_approximate_joint':all(checks.values()),'robust_K':cover['K'],
            'point_min_cap_slack_DPS':float(np.min(e.cap-e.values.max(axis=(0,1)))),
            'lower_confidence_cap_slack_DPS':float(np.min(e.cap-top)),'robust_source_masses':mass,'witnesses':witnesses,
            'method':{'performance':'Two-sided Student-t mean hyperrectangle, family816, alpha.025, df4095; paired label dependence does not invalidate Bonferroni union, iid seed/normal approximation assumed.',
                'behavior':'Paired eight-block coordinate differences against every old policy profile, family16128, alpha.025, df7. Ratio-of-means behavior centers and block SE; approximate, not exact finite-sample coverage.',
                'D_definition':'Original seven coordinates and delta.05; all H-old policy profiles retained. Behavior CI is conservative across every potential new policy/task witness.',
                'scope':'Selected joint-admission certificate only. Earlier complete-domain singleton failure is a separate empirical claim; this17-gear run cannot prove population singleton impossibility.'}}
        results.append(result)
        for param,values in [('epsilon',[.025,.05,.1]),('delta',[.025,.05,.075]),('headroom',[0,.05]),('k_max',[1,2,4])]:
            for value in values:
                pp,_=e.problem(['18203','19019'],archive=e.initial_archive(),**{param:value});m=evaluate_admission(pp,np.ones(17,bool))
                sens.append({'race':race,'scale':scale,'changed_parameter':param,'value':value,'joint':m['joint_pass'],'failures':m['failure_reasons'],'K':m['K'],'diagnostic_not_main_success':param!='headroom'or value!=.05})
    atomic_json(out/'HIGH_PRECISION_CERTIFICATE_RESULTS.json',{'certificates':results,'run':str(run),'native_calls':len(rows),'native_battles':sum(r['iterations']for r in rows)})
    write_csv(out/'THRESHOLD_SENSITIVITY.csv',sens)
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
