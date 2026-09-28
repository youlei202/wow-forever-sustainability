"""Replay frozen current-wave choices on shared native responses, with no redraws."""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
import yaml
from wowfs.paths import setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r2_sequence_analysis import load_context, behavior_vector, nearest_distances, portfolio_cover, scalar_reprice, write_csv
from wowfs.experiments.r3_phase_analysis import source_state
from wowfs.experiments.r3_sequences import PROFILES, METHODS

def source_mass(means, sources, optimum, scale):
    result={}
    close=np.any(means >= optimum[None,None,:]-.05*scale[None,None,:]-1e-10,axis=1)
    for source in sorted(set(s for row in sources for s in row)):
        mask=np.array([source in row for row in sources])
        result[source]=float(np.mean(np.any(close[mask],axis=0)))
    return result

def new_metrics(old_m,old_b,new_m,new_b,scale,cap,archive):
    if len(new_m)==0:
        return {'P':bool(np.all(old_m.max(axis=(0,1))<=cap+1e-10)), 'N':False,'D':False,
                'new_task_mass':0.,'novel_task_mass':0.,'distance':0.,'novel_profiles':[[] for _ in range(4)]}
    optimum=np.maximum(old_m.max(axis=(0,1)),new_m.max(axis=(0,1)))
    close=new_m>=optimum[None,None,:]-.05*scale[None,None,:]-1e-10
    novel=np.zeros_like(close);distances=[];profiles=[]
    for k in range(4):
        queries=new_b[:,:,k].reshape(-1,7)
        distance=np.minimum(nearest_distances(queries,old_b[:,:,k].reshape(-1,7)),nearest_distances(queries,archive[k]))
        d=distance.reshape(len(new_m),3);novel[:,:,k]=close[:,:,k]&(d>=.05-1e-10)
        distances.extend(d[close[:,:,k]].tolist());profiles.append(new_b[:,:,k][novel[:,:,k]].tolist())
    return {'P':bool(np.all(optimum<=cap+1e-10)),
            'N':bool(np.any(close)),'D':bool(np.any(novel)),
            'new_task_mass':float(np.mean(np.any(close,axis=(0,1)))),
            'novel_task_mass':float(np.mean(np.any(novel,axis=(0,1)))),
            'distance':max(distances,default=0.),'novel_profiles':profiles}

def scalar_mask(old_m,old_s,new_m,new_s,cap,scale):
    all_m=np.concatenate([old_m,new_m]);all_s=old_s+new_s
    items=sorted(set(x for ss in all_s for x in ss))
    incidence=np.array([[ss.count(x) for x in items] for ss in all_s],float)
    unsafe=np.any(all_m>cap[None,None,:]+1e-10,axis=(1,2))
    history=np.arange(len(all_m))<len(old_m)
    safe_opt=all_m[~unsafe].max(axis=(0,1))
    competitive=np.any(all_m.max(axis=1)>=safe_opt-.05*scale,axis=1)
    candidates=np.flatnonzero(~history&~unsafe&competitive).tolist()
    prices,solved=scalar_reprice(incidence,unsafe,history,candidates,np.zeros(len(items)))
    allowed=incidence@prices<=1+1e-8
    feasible=solved['solver_status'].startswith('optimal') and np.all(allowed[history]) and not np.any(unsafe&allowed)
    return allowed[len(old_m):] if feasible else np.zeros(len(new_m),bool),solved,len(items),prices.tolist()

def analyze():
    root=setup_paths();out=root/'artifacts/r3-gold';r2=root/'runs/r2-discovery/unseen-v1'
    run=root/'runs/r3-gold/sequences-v1'
    protocol=json.loads((run/'PROTOCOL.json').read_text())['science']
    results=json.loads((run/'RESULTS.json').read_text())
    if results['errors']:raise ValueError(results['errors'])
    frozen=json.loads((r2/'FROZEN_DESIGN.json').read_text());oldrows=json.loads((r2/'RESULTS.json').read_text())['rows']
    cfg=yaml.safe_load((r2/'source/r2_discovery.yaml').read_text());tasks=cfg['tasks'];policies=[s['id'] for s in cfg['strategies']]
    tids={v['id']:i for i,v in enumerate(tasks)};pids={v:i for i,v in enumerate(policies)}
    profiles={tuple(p):i for i,p in enumerate(PROFILES)};gearids=sorted(frozen['gears'])
    calibration=json.loads((out/'AFFINE_CALIBRATION.json').read_text())
    atomic_json(out/'SEQUENTIAL_ANALYSIS_PROTOCOL.json',{
        'analysis_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'frozen_physics_protocol_sha256':hashlib.sha256((run/'PROTOCOL.json').read_bytes()).hexdigest(),
        'candidate_results_sha256':hashlib.sha256((run/'RESULTS.json').read_bytes()).hexdigest(),
        'rule_calibration_sha256':canonical_hash(calibration),
        'analysis_corrections_before_final_report':['Include blocked legacy sources from before_raw at mass0 in reactivation denominator.',
            'Register every newly competitive legacy source, including reactivated old sources.',
            'Count432coefficients perrace,864bothraces for144/288threecoefficient inequalities.',
            'Immediate/novelty/legacy selection enforce the same observed current P constraint as complement; all receive these current responses. Random remains basic-plausibility only.'],
        'no_physics_changes':True,'cap_scope':'Frozen numeric cap, point estimates; no sequential simultaneous certificate.'})
    models={(r['race'],r['weapon_speed'],r['offhand'],r['trinket1'],r['trinket2'],r['task'],r['strategy']):r for r in calibration['models']}
    groups=defaultdict(list)
    for row in results['rows']:groups[(row['race'],row['variant_id'])].append(row)
    prepared={}
    for item in protocol['pools']:
        for race in protocol['races']:
            m=np.full((4,3,4),np.nan);b=np.full((4,3,4,7),np.nan);prediction=np.full_like(m,np.nan)
            for row in groups[(race,item['variant_id'])]:
                g=profiles[(row['offhand'],row['trinket1'],row['trinket2'])];p=pids[row['strategy']];k=tids[row['task']]
                m[g,p,k]=row['dps_mean'];b[g,p,k]=behavior_vector(row,tasks[k]['duration_seconds'])
                model=models[(race,item['weapon_speed'],row['offhand'],row['trinket1'],row['trinket2'],row['task'],row['strategy'])]
                prediction[g,p,k]=np.dot(model['mean_coefficients'],[1,item['base_dps']-24,item['dot_damage']])
            if not np.isfinite(m).all() or not np.isfinite(b).all():raise ValueError('incomplete native candidate')
            sources=[[item['variant_id'],str(oh),str(t1),str(t2)] for oh,t1,t2 in PROFILES]
            prepared[(race,item['variant_id'])]=(m,b,prediction,sources)
    all_rounds=[];all_sequences=[];decisions=[];reward_rows=[]
    for race in protocol['races']:
        om,ob,ol,ou=load_context(oldrows,gearids,tasks,policies,race,128)
        state=source_state(frozen,gearids,om,ob,.05);before=state['before'];scale=state['scale'];cap=state['cap']
        base_m=om[before];base_b=ob[before]
        base_s=[[str(frozen['gears'][gearids[g]][slot]) for slot in ('main_hand','off_hand','trinket1','trinket2')] for g in before]
        base_keys=[gearids[g] for g in before]
        initial_mass=source_mass(base_m,base_s,state['optimum'],scale)
        # A blocked source has no legal loadout, but remains in the reactivation denominator.
        for g in state['before_raw']:
            for slot in ('main_hand','off_hand','trinket1','trinket2'):
                initial_mass.setdefault(str(frozen['gears'][gearids[g]][slot]),0.)
        for sequence in range(2):
            pool=[i for i in protocol['pools'] if i['sequence']==sequence]
            for method in METHODS:
                current_m=base_m.copy();current_b=base_b.copy();current_s=list(base_s);current_keys=list(base_keys)
                archive=[x.copy() for x in state['archive_profiles']]
                registered={s:0 for s,m in initial_mass.items() if m>=.05};reactivated=set();packing=[[] for _ in tasks]
                prefix=0;open_prefix=True;accepted=0;seqrows=[]
                rng=np.random.default_rng(309245001+sequence)
                for wave in range(1,21):
                    candidates=[i for i in pool if i['wave']==wave];options=[]
                    oldopt=current_m.max(axis=(0,1));before_mass=source_mass(current_m,current_s,oldopt,scale)
                    for item in candidates:
                        m,b,pred,ss=prepared[(race,item['variant_id'])]
                        allowed=np.all(pred<=cap[None,None,:]+1e-10,axis=(1,2));solver={'solver_status':'fixed_affine_envelope'};parameters=432
                        if method=='scalar_reprice':allowed,solver,parameters,prices=scalar_mask(current_m,current_s,m,ss,cap,scale)
                        nm=m[allowed];nb=b[allowed];ns=[s for s,a in zip(ss,allowed) if a]
                        metrics=new_metrics(current_m,current_b,nm,nb,scale,cap,archive)
                        after_m=np.concatenate([current_m,nm]);after_s=current_s+ns;optimum=after_m.max(axis=(0,1))
                        masses=source_mass(after_m,after_s,optimum,scale)
                        metrics['L']=all(masses.get(s,0)>=.05 for s in registered)
                        metrics['H']=True;cover=portfolio_cover(after_m.max(axis=1),optimum,scale)
                        metrics['C']=cover['K'] is not None and cover['K']<=4
                        recovered=[s for s in initial_mass if before_mass.get(s,0)<.05<=masses.get(s,0)]
                        gain=sum(max(0,masses.get(s,0)-before_mass.get(s,0)) for s in initial_mass)
                        metrics.update(reactivated_sources=recovered,legacy_gain=gain,
                            utility=float(np.mean(nm.max(axis=(0,1))/scale)) if len(nm) else -1.,K=cover['K'])
                        passed=all(metrics[c] for c in ('P','N','D','L','H','C'))
                        options.append({'item':item,'allowed':allowed,'metrics':metrics,'solver':solver,'parameters':parameters,
                                        'passed':passed,'masses':masses})
                    def complement_score(o):
                        x=o['metrics'];return (len(x['reactivated_sources']),x['legacy_gain'],x['utility'],-o['item']['candidate'])
                    if method in ('complement_constrained','generic_multiobjective','scalar_reprice'):
                        feasible=[o for o in options if o['passed']];chosen=max(feasible,key=complement_score) if feasible else None
                    elif method=='random_horizontal':chosen=options[int(rng.integers(6))]
                    else:
                        # The brief asks for these baselines under the cap. They
                        # receive the same observed current P information as the
                        # constrained method, not just noisy affine predictions.
                        feasible=[o for o in options if np.any(o['allowed']) and o['metrics']['P']]
                        def score(o):
                            x=o['metrics'];tie=-o['item']['candidate']
                            if method=='immediate_utility':return (x['utility'],tie)
                            if method=='novelty_first':return (x['novel_task_mass'],x['distance'],x['utility'],tie)
                            return (len(x['reactivated_sources']),x['legacy_gain'],x['utility'],tie)
                        chosen=max(feasible,key=score) if feasible else None
                    admitted=chosen is not None and np.any(chosen['allowed'])
                    if admitted:
                        item=chosen['item'];m,b,pred,ss=prepared[(race,item['variant_id'])];mask=chosen['allowed']
                        oldcount=len(current_m);current_m=np.concatenate([current_m,m[mask]]);current_b=np.concatenate([current_b,b[mask]])
                        current_s.extend(s for s,a in zip(ss,mask) if a);current_keys.extend(item['variant_id']+':'+str(g) for g in np.flatnonzero(mask))
                        metrics=chosen['metrics'];accepted+=1
                        for k,profiles_added in enumerate(metrics['novel_profiles']):
                            for profile in profiles_added:
                                if not packing[k] or min(nearest_distances([profile],packing[k]))>=.05-1e-10:packing[k].append(profile)
                        close=current_m[oldcount:]>=current_m.max(axis=(0,1))[None,None,:]-.05*scale[None,None,:]-1e-10
                        for k in range(4):
                            newprofiles=current_b[oldcount:,:,k][close[:,:,k]]
                            if len(newprofiles):archive[k]=np.concatenate([archive[k],newprofiles])
                        reactivated.update(metrics['reactivated_sources'])
                        if metrics['N']:registered[item['variant_id']]=wave
                        for source,mass in chosen['masses'].items():
                            if mass>=.05 and source not in registered:
                                registered[source]=0 if source in initial_mass else wave
                    else:
                        metrics=new_metrics(current_m,current_b,np.empty((0,3,4)),np.empty((0,3,4,7)),scale,cap,archive)
                        masses=source_mass(current_m,current_s,current_m.max(axis=(0,1)),scale)
                        metrics.update(L=all(masses.get(s,0)>=.05 for s in registered),H=True,C=True,reactivated_sources=[],legacy_gain=0.)
                    optimum=current_m.max(axis=(0,1));cover=portfolio_cover(current_m.max(axis=1),optimum,scale)
                    masses=source_mass(current_m,current_s,optimum,scale)
                    checks={c:bool(metrics[c]) for c in ('P','N','D','L','H','C')};passed=all(checks.values())
                    if open_prefix and passed:prefix+=1
                    else:open_prefix=False
                    ages=[wave-age for source,age in registered.items() if masses.get(source,0)>=.05]
                    row={'sequence':sequence,'race':race,'method':method,'wave':wave,'admitted':bool(admitted),
                        'selected_variant':chosen['item']['variant_id'] if chosen else None,**checks,'joint_pass':passed,
                        'failure_reasons':[c for c,v in checks.items() if not v],'new_task_mass':metrics['new_task_mass'],
                        'novel_task_mass':metrics['novel_task_mass'],'maximum_competitive_old_archive_distance':metrics['distance'],
                        'power_growth':float(np.max(optimum/scale-1)),'power_ratio_to_fixed_cap':float(np.max(optimum/cap)),
                        'distinct_new_choices':sum(map(len,packing)),'reactivated_legacy_sources':len(reactivated),
                        'legacy_source_denominator':len(registered),'legacy_retained_fraction':float(np.mean([masses.get(s,0)>=.05 for s in registered])),
                        'competitive_legacy_ages':ages,'mean_competitive_legacy_age':float(np.mean(ages)) if ages else None,
                        'K':cover['K'],'admitted_gears':len(current_m),'accepted_items':accepted,
                        'rule_rows':1 if method=='scalar_reprice' else 144,
                        'all_race_rule_rows':288 if method!='scalar_reprice' else 2,
                        'rule_scalar_parameters':chosen['parameters'] if chosen else (432 if method!='scalar_reprice' else len(set(s for ss in current_s for s in ss))),
                        'item_specific_exceptions':0,'headroom':.05,
                        'power_status':'independent_seed_point_estimate_not_joint_certificate',
                        'behavior_scope':'mean_damage_shares_and_rage; amplitude_only_can_change_shares_without_action_frequency',
                        'source_scope':'before-state variable-slot item sources plus previously useful released research variants'}
                    seqrows.append(row);all_rounds.append(row)
                    decisions.append({'sequence':sequence,'race':race,'method':method,'wave':wave,
                        'selected_variant':row['selected_variant'],'current_candidates':[
                            {'variant_id':o['item']['variant_id'],'allowed_profiles':o['allowed'].tolist(),
                             'joint_pass':o['passed'],'metrics':{k:v for k,v in o['metrics'].items() if k!='novel_profiles'},'solver':o['solver']} for o in options]})
                    for s,age in registered.items():reward_rows.append({'sequence':sequence,'race':race,'method':method,'wave':wave,'source':s,'release_wave':age,'competitive_task_mass':masses.get(s,0)})
                all_sequences.append({'sequence':sequence,'race':race,'method':method,'rounds':20,'S20':prefix,'Pass20':prefix==20,
                    'useful_fraction':float(np.mean([r['N'] for r in seqrows])),'novel_fraction':float(np.mean([r['D'] for r in seqrows])),
                    'joint_passing_waves':sum(r['joint_pass'] for r in seqrows),'rejected_waves':sum(not r['admitted'] for r in seqrows),
                    'max_power_growth':max(r['power_growth'] for r in seqrows),'power_violating_waves':sum(not r['P'] for r in seqrows),
                    'distinct_new_choices':seqrows[-1]['distinct_new_choices'],'reactivated_legacy_sources':len(reactivated),
                    'final_K':seqrows[-1]['K'],'final_legacy_retained_fraction':seqrows[-1]['legacy_retained_fraction'],
                    'rule_rows':seqrows[-1]['rule_rows'],'item_specific_exceptions':0})
                print(race,sequence,method,all_sequences[-1],flush=True)
    write_csv(out/'SEQUENTIAL_EXPANSION_RESULTS.csv',all_sequences)
    write_csv(out/'SEQUENTIAL_WAVE_RESULTS.csv',all_rounds)
    write_csv(out/'SEQUENTIAL_SOURCE_RESULTS.csv',reward_rows)
    atomic_json(out/'SEQUENTIAL_DECISIONS.json',decisions)
    atomic_json(out/'SEQUENTIAL_SUMMARY.json',{'sequences':all_sequences,'native_cells':len(results['rows']),
        'physical_battles':len(results['rows'])*128,'trajectory_rows':len(all_rounds),
        'protocol':protocol,'calibration_sha256':canonical_hash(calibration),
        'generic_complement_match':all(
            [{k:v for k,v in r.items() if k!='method'} for r in all_rounds if r['method']=='complement_constrained' and r['race']==race and r['sequence']==s]==
            [{k:v for k,v in r.items() if k!='method'} for r in all_rounds if r['method']=='generic_multiobjective' and r['race']==race and r['sequence']==s]
            for race in protocol['races'] for s in range(2))})

if __name__=='__main__':analyze()
