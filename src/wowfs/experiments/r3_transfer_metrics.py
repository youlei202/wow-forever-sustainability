"""Shared finite-pool utility, novelty and legacy outcomes for transfer rules."""
from collections import defaultdict
import csv
import json
import numpy as np
import yaml
from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r2_sequence_analysis import load_context,behavior_vector,nearest_distances,portfolio_cover,write_csv
from wowfs.experiments.r3_phase_analysis import source_state
from wowfs.experiments.r3_sequence_analysis import source_mass

def main():
    root=setup_paths();out=root/'artifacts/r3-gold';r2=root/'runs/r2-discovery/unseen-v1'
    frozen=json.loads((r2/'FROZEN_DESIGN.json').read_text());oldrows=json.loads((r2/'RESULTS.json').read_text())['rows']
    cfg=yaml.safe_load((r2/'source/r2_discovery.yaml').read_text());tasks=cfg['tasks'];policies=[p['id'] for p in cfg['strategies']]
    tids={t['id']:i for i,t in enumerate(tasks)};pids={p:i for i,p in enumerate(policies)};ids=sorted(frozen['gears'])
    native=json.loads((root/'runs/r3-gold/affine-transfer-v1/RESULTS.json').read_text())['rows']
    decisions=list(csv.DictReader((out/'AFFINE_TRANSFER_DECISIONS.csv').open()))
    methods=list(csv.DictReader((out/'AFFINE_METHOD_COMPARISON.csv').open()))
    output=[]
    for race in ('RaceHuman','RaceOrc'):
        means,behavior,lower,upper=load_context(oldrows,ids,tasks,policies,race,128)
        state=source_state(frozen,ids,means,behavior,.05);before=state['before'];scale=state['scale'];cap=state['cap']
        oldm=means[before];oldb=behavior[before]
        oldsources=[[str(frozen['gears'][ids[g]][slot]) for slot in ('main_hand','off_hand','trinket1','trinket2')] for g in before]
        masses_before=source_mass(oldm,oldsources,state['optimum'],scale)
        for g in state['before_raw']:
            for slot in ('main_hand','off_hand','trinket1','trinket2'):masses_before.setdefault(str(frozen['gears'][ids[g]][slot]),0.)
        selected=[d for d in decisions if d['race']==race]
        key=lambda r:(int(r['variant_index']),int(r['offhand']),int(r['trinket1']),int(r['trinket2']))
        index={key(r):i for i,r in enumerate(selected)};n=len(selected)
        m=np.full((n,3,4),np.nan);b=np.full((n,3,4,7),np.nan)
        for row in native:
            if row['panel']!='same_control' or row['race']!=race:continue
            g=index[key(row)];p=pids[row['strategy']];k=tids[row['task']]
            m[g,p,k]=row['dps_mean'];b[g,p,k]=behavior_vector(row,tasks[k]['duration_seconds'])
        if not np.isfinite(m).all():raise ValueError('Incomplete transfer physical table')
        sources=[['variant_'+str(d['variant_index']),str(d['offhand']),str(d['trinket1']),str(d['trinket2'])] for d in selected]
        for meta in methods:
            method=meta['method'];allow=np.array([r[method]=='True' for r in selected])
            nm=m[allow];nb=b[allow];ns=[s for s,a in zip(sources,allow) if a]
            allm=np.concatenate([oldm,nm]);alls=oldsources+ns;optimum=allm.max(axis=(0,1))
            close=nm>=optimum[None,None,:]-.05*scale[None,None,:]-1e-10
            novel=np.zeros_like(close)
            for k in range(4):
                if not len(nm):continue
                queries=nb[:,:,k].reshape(-1,7)
                distance=np.minimum(nearest_distances(queries,oldb[:,:,k].reshape(-1,7)),nearest_distances(queries,state['archive_profiles'][k]))
                novel[:,:,k]=close[:,:,k]&(distance.reshape(len(nm),3)>=.05-1e-10)
            useful={s[0] for s,c in zip(ns,close) if np.any(c)};distinct={s[0] for s,c in zip(ns,novel) if np.any(c)}
            masses=source_mass(allm,alls,optimum,scale);legacy=[s for s,v in masses_before.items() if v>=.05]
            reactivated=[s for s,v in masses_before.items() if v<.05<=masses.get(s,0)]
            cover=portfolio_cover(allm.max(axis=1),optimum,scale)
            row={'panel':'same_control_paired_seed_structural_transfer','race':race,'method':method,
                'attempted_items':32,'tested_loadouts':n,'admitted_loadouts':int(allow.sum()),
                'unsafe_admitted_loadouts':int(np.sum(allow&np.any(m>cap[None,None,:]+1e-10,axis=(1,2)))),
                'safe_rejected_loadouts':int(np.sum(~allow&np.all(m<=cap[None,None,:]+1e-10,axis=(1,2)))),
                'useful_new_items':len(useful),'useful_new_rate':len(useful)/32,
                'behaviorally_novel_items_vs_old':len(distinct),'behaviorally_novel_rate_vs_old':len(distinct)/32,
                'novelty_note':'Each item vs old-only+old archive, not mutually distinct across all held-out items.',
                'legacy_denominator':len(legacy),'legacy_retained':sum(masses.get(s,0)>=.05 for s in legacy),
                'reactivated_legacy_sources':reactivated,'legacy_reactivation_count':len(reactivated),
                'P':bool(np.all(optimum<=cap+1e-10)),'L':all(masses.get(s,0)>=.05 for s in legacy),'H':True,
                'K':cover['K'],'C':cover['K']<=4,'power_growth':float(np.max(optimum/scale-1)),
                'native_test_cells_for_rule':int(meta['heldout_response_cells_used_for_decision']),
                'admission_vs_reference_disagreements':int(np.sum(allow!=np.array([r['finite_safe_reference']=='True' for r in selected]))),
                'inference':'Paired calibration/test seeds identify structure; not independent expected-mean safety certificate.',
                'family_scope':'Previously unseen research amplitudes in3calibrated speed kernels; official item IDs unchanged.'}
            output.append(row)
    write_csv(out/'TYPE_TRANSFER_RESULTS.csv',output)
    atomic_json(out/'TYPE_TRANSFER_METRICS.json',{'rows':output,'shifted_panels':'AFFINE_TRANSFER.json reports unsupported speed/PPM/resource shifts. Frozen typed/generic domain rejects unknown kernels; forced extrapolation is a diagnostic, not authorized admission.',
        'complexity':'RULE_COMPLEXITY_SCALING.csv includes dense constraints, numerical facet pruning, selectors, coefficients and serialized rule bytes.'})

if __name__=='__main__':main()
