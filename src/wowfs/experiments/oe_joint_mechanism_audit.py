"""Read-only development audit of two selected native interaction mechanisms.

All estimates and threshold suggestions use DEVELOPMENT data. Prospective sample
size calculations hold pilot means/variances fixed and are not promises of power.
No native observations are reconstructed, simulated, or overwritten here.
"""
import argparse
from functools import lru_cache
import gzip
import hashlib
from itertools import product
import json
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from scipy.stats import t
from wowfs.paths import atomic_json,canonical_hash
from wowfs.experiments.oe_analysis import write_csv

CASES=[{'world_id':'resistance_penetration__Alliance_Gnome_Mage__s0','a':'a10','x':'x3','old_x':'x1','proposed_h':.043},
       {'world_id':'mana_regen__Alliance_NightElf_Druid__s0','a':'a16','x':'x0','old_x':'x1','proposed_h':.055}]
NEGATIVE_CONTROLS=[
    {'world_id':CASES[0]['world_id'],'a':'a04','x':'x3','old_x':'x1','proposed_h':.043,
     'role':'Signed reverse: overlapping penetration crosses the same resistance cap twice.'},
    {'world_id':CASES[0]['world_id'],'a':'a10','x':'x0','old_x':'x1','proposed_h':.043,
     'role':'Same-primary near-zero development contrast; absence requires an equivalence test.'},
    {'world_id':CASES[1]['world_id'],'a':'a16','x':'x3','old_x':'x1','proposed_h':.055,
     'role':'Signed reverse: both replacements trade spell power for mana regeneration.'}]


def lookup(rows,world,policy='native'):
    chosen=[r for r in rows if r and r['world_id']==world and r['policy_id']==policy]
    out={}
    for r in chosen:
        key=(r['candidate_id'],r['partner_id'],r['task_id'])
        if key in out:raise ValueError('duplicate physical cell')
        if r['observed_or_reconstructed']!='observed':raise ValueError('observed cells only')
        out[key]=r
    return out


def quartet(data,a,x,oldx):
    tasks=sorted({q for _,_,q in data})
    out=[]
    for q in tasks:
        keys=[('a00',oldx,q),(a,oldx,q),('a00',x,q),(a,x,q)]
        if not all(key in data for key in keys):raise ValueError('Missing quartet')
        rows=[data[key] for key in keys]
        if len({r['seed_block_id'] for r in rows})!=1:raise ValueError('unpaired quartet')
        s,u,v,w=[np.array(r['dps_samples'],float) for r in rows]
        out.append({'task_id':q,'rows':rows,'reference':s,'one_a':u,'one_x':v,'joint':w,
                    'forecast':u+v-s,'mixed':w-u-v+s})
    return out


def means(qs):
    details=[]
    for z in qs:
        ref=z['reference'].mean()
        details.append({'task_id':z['task_id'],'baseline_mean':ref,
            **{key:float(z[key].mean()/ref-1) for key in ('one_a','one_x','forecast','joint')},
            'mixed_relative_mean':float(z['mixed'].mean()/ref),
            'mixed_relative_seed_sd':float(z['mixed'].std(ddof=1)/ref),
            'mixed_max_abs_per_seed':float(np.max(np.abs(z['mixed']))),
            'iterations':len(z['reference'])})
    low=max(0,max(d[k] for d in details for k in ('one_a','one_x','forecast')))
    high=max(d['joint'] for d in details)
    return {'tasks':details,'mean_admissible_h_lower':low,'mean_admissible_h_upper':high,
            'mean_h_window_width':high-low,'has_mean_window':high>low}


def precision(qs,h,n,alpha=.005,family_multiplier=1):
    """Bonferroni 5Q planning margins and implicit ratio threshold roots."""
    M=5*len(qs)*family_multiplier;critical=float(t.isf(alpha/(2*M),n-1));records=[]
    lows=[];highs=[]
    for z in qs:
        s=z['reference'];ref=s.mean();q=z['task_id'];row={'task_id':q}
        for key in ('one_a','one_x','forecast','joint'):
            val=z[key]
            def bound(headroom,direction):
                delta=(1+headroom)*s-val
                return float(delta.mean()+direction*critical*delta.std(ddof=1)/np.sqrt(n))
            lo=bound(h,-1)/ref;hi=bound(h,1)/ref
            row[key]={'margin_relative_mean':float(((1+h)*s-val).mean()/ref),
                      'margin_relative_lower':lo,'margin_relative_upper':hi,
                      'pilot_relative_sd':float(((1+h)*s-val).std(ddof=1)/ref)}
            safe_threshold=brentq(lambda hh:bound(hh,-1),-.9,5.)
            violation_threshold=brentq(lambda hh:bound(hh,1),-.9,5.)
            row[key].update(h_supports_safety_above=safe_threshold,h_supports_violation_below=violation_threshold)
            if key in ('one_a','one_x','forecast'):lows.append(safe_threshold)
            else:highs.append(violation_threshold)
        mixed=z['mixed'];radius=critical*mixed.std(ddof=1)/np.sqrt(n)/ref
        row['mixed']={'relative_mean':float(mixed.mean()/ref),'relative_halfwidth':float(radius),
                      'relative_lower':float(mixed.mean()/ref-radius),'relative_upper':float(mixed.mean()/ref+radius)}
        records.append(row)
    lower=max(0,max(lows));upper=max(highs)
    return {'sample_size':n,'alpha_hypothetical':alpha,'family_size':M,'critical':critical,'headroom':h,
            'pilot_based_h_interval':[lower,upper],'nonempty_pilot_interval':upper>lower,'tasks':records,
            'scope':'Development-selected pair and pilot variance projection; NOT an independent confirmation or a guaranteed sample-size calculation.'}


@lru_cache(None)
def physical_metrics(folder,expected_hash):
    folder=Path(folder)
    with gzip.open(folder/'output.json.gz','rb') as f:raw=f.read()
    if hashlib.sha256(raw).hexdigest()!=expected_hash:raise ValueError('raw output hash mismatch')
    data=json.loads(raw);u=data['raidMetrics']['parties'][0]['players'][0];n=data['iterationsDone']
    actions={}
    for action in u.get('actions',[]):
        aid=action['id'];key='|'.join(str(aid.get(k,'')) for k in ('spellId','itemId','otherId','tag','rank'))
        fields=('casts','hits','crits','misses','resistedHits','resistedCrits','ticks','critTicks','resistedTicks','damage','resistedDamage','castTimeMs')
        actions[key]={field:float(sum(target.get(field,0) for target in action['targets'])/n) for field in fields}
    resources={}
    for r in u.get('resources',[]):
        key=json.dumps({'id':r['id'],'type':r['type']},sort_keys=True)
        resources[key]={field:float(r.get(field,0)/n) for field in ('events','gain','actualGain')}
    input_data=json.loads((folder/'input.json').read_text())
    return {'actions':actions,'resources':resources,'seconds_oom':u.get('secondsOomAvg'),
            'active_auras':[{'id':a['id'],'procs':a['procsAvg'],'uptime':a['uptimeSecondsAvg']}
                            for a in u.get('auras',[]) if a['procsAvg'] or a['uptimeSecondsAvg']],
            'native_variant_overrides':input_data['research_variants'],
            'apl':input_data['request']['raid']['parties'][0]['players'][0]['rotation'],
            'duration':input_data['request']['encounter']['duration'],
            'cache_directory':str(folder),'output_sha256':expected_hash}


def mechanism_records(qs):
    records=[]
    for q in qs:
        cases={label:physical_metrics(row['cache_directory'],row['output_sha256'])
               for label,row in zip(('S','A','X','AX'),q['rows'])}
        residual={}
        for section in ('actions','resources'):
            keys=set().union(*(d[section] for d in cases.values()))
            for key in keys:
                fields=set().union(*(d[section].get(key,{}) for d in cases.values()))
                for field in fields:
                    residual[section+'::'+key+'::'+field]=sum(sign*cases[label][section].get(key,{}).get(field,0.)
                        for sign,label in [(1,'AX'),(-1,'A'),(-1,'X'),(1,'S')])
        records.append({'task_id':q['task_id'],'corners':cases,'action_resource_mixed_residuals':residual,
            'scope':'Native per-battle averages; action/resource contrasts lack per-seed confidence intervals in the stored aggregate fields.'})
    return records


def audit(run,output):
    run=Path(run);output=Path(output)
    if output.exists():raise ValueError('Use a new analysis output directory')
    bybatch={}
    for batch in ('refine-v1','policy-challenge-v1','deep-challenge-v1'):
        p=run/'batches'/batch/'RESULTS.json'
        data=json.loads(p.read_text())
        if data['status']!='completed' or data['errors']:raise ValueError('Development batch not complete')
        bybatch[batch]=data['rows']
    selected=[];histories=[];all_pairs=[]
    for case in CASES:
        data=lookup(bybatch['deep-challenge-v1'],case['world_id'])
        qs=quartet(data,case['a'],case['x'],case['old_x'])
        item={**case,**means(qs),'precision':[precision(qs,case['proposed_h'],n) for n in (4096,32768)],
              'old_h_005_precision':[precision(qs,.05,n) for n in (4096,32768)],
              'mechanism':mechanism_records(qs)}
        selected.append(item)
        for a,x in product(sorted({a for a,_,_ in data if a!='a00'}),sorted({x for _,x,_ in data if x!=case['old_x']})):
            mm=means(quartet(data,a,x,case['old_x']))
            for h in (.03,.05,.1,case['proposed_h']):
                bothsafe=all(max(t['one_a'],t['one_x'])<=h for t in mm['tasks'])
                forecasts=all(t['forecast']<=h for t in mm['tasks'])
                jointsafe=all(t['joint']<=h for t in mm['tasks'])
                all_pairs.append({'world_id':case['world_id'],'a':a,'x':x,'headroom':h,
                    'both_single_safe':bothsafe,'forecast_safe':forecasts,'joint_safe':jointsafe,
                    'individual_only_miss':bothsafe and not jointsafe,
                    'additive_miss':bothsafe and forecasts and not jointsafe,**mm})
        for batch,rows in bybatch.items():
            world=case['world_id']+('__policy_challenge' if batch=='policy-challenge-v1' else '')
            policies=sorted({r['policy_id'] for r in rows if r and r['world_id']==world})
            for policy in policies:
                d=lookup(rows,world,policy);mm=means(quartet(d,case['a'],case['x'],case['old_x']))
                histories.append({'batch':batch,'world_id':world,'policy':policy,**mm,
                    'at_h005':{'both_single_safe':all(max(t['one_a'],t['one_x'])<=.05 for t in mm['tasks']),
                               'forecast_safe':all(t['forecast']<=.05 for t in mm['tasks']),
                               'joint_safe':all(t['joint']<=.05 for t in mm['tasks'])}})
    controls=[]
    for case in NEGATIVE_CONTROLS:
        qs=quartet(lookup(bybatch['deep-challenge-v1'],case['world_id']),case['a'],case['x'],case['old_x'])
        controls.append({**case,**means(qs),'precision':precision(qs,case['proposed_h'],32768),
                         'mechanism':mechanism_records(qs)})
    output.mkdir(parents=True)
    atomic_json(output/'SELECTED_MECHANISMS.json',selected)
    atomic_json(output/'FULL_PAIR_CHALLENGES.json',all_pairs);write_csv(output/'FULL_PAIR_CHALLENGES.csv',all_pairs)
    atomic_json(output/'256_512_4096_HISTORY.json',histories);write_csv(output/'256_512_4096_HISTORY.csv',histories)
    atomic_json(output/'NEGATIVE_CONTROL_MECHANISMS.json',controls)
    summary={'status':'completed_development_analysis','selected_worlds':2,'full_pairs_per_headroom':96,
             'no_native_executions':True,'all_confirmation_claims':'not_run',
             'selected':[{'world_id':x['world_id'],'mean_h_window':[x['mean_admissible_h_lower'],x['mean_admissible_h_upper']],
                          'projected_h_intervals':[{k:p[k] for k in ('sample_size','pilot_based_h_interval')} for p in x['precision']]} for x in selected],
             'threshold_counts':[{'world_id':case['world_id'],'headroom':h,
                 'individual_only_misses':sum(r['individual_only_miss'] for r in all_pairs if r['world_id']==case['world_id'] and r['headroom']==h),
                 'additive_misses':sum(r['additive_miss'] for r in all_pairs if r['world_id']==case['world_id'] and r['headroom']==h)}
                 for case in CASES for h in (.03,.05,.1,case['proposed_h'])]}
    atomic_json(output/'SUMMARY.json',summary)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-root',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();print(json.dumps(audit(args.run_root,args.output),indent=2))
