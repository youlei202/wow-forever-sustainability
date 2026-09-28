"""Observed-table diagnostics for open exploration; no imputed native cells."""
from __future__ import annotations
import argparse
import csv
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
from wowfs.paths import atomic_json, canonical_hash


def write_csv(path, rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        out=csv.DictWriter(f,fieldnames=keys);out.writeheader()
        for row in rows:
            out.writerow({k:json.dumps(v) if isinstance(v,(list,dict,tuple)) else v for k,v in row.items()})


def tensor(rows):
    """Return physically observed response tensor, with NaNs for missing cells."""
    dims=[[str(x) for x in sorted({r[k] for r in rows})] for k in
          ('candidate_id','partner_id','task_id','policy_id')]
    indexes=[{v:i for i,v in enumerate(d)} for d in dims]
    shape=tuple(map(len,dims));mean=np.full(shape,np.nan);se=np.full(shape,np.nan)
    records={}
    for r in rows:
        key=tuple(indexes[i][str(r[k])] for i,k in enumerate(('candidate_id','partner_id','task_id','policy_id')))
        if key in records: raise ValueError('duplicate logical cell: explicitly select one fidelity batch')
        mean[key]=r['dps_mean'];se[key]=r['dps_se'];records[key]=r
    return {'dimensions':dims,'means':mean,'se':se,'records':records,'complete':bool(np.isfinite(mean).all())}


def diagnose(world,rows):
    t=tensor(rows);x=t['means'];dims=t['dimensions'];r0=dims[0].index('a00') if 'a00' in dims[0] else 0
    # Tasks are not collapsed to one scalar. Strategies are kept as alternatives.
    best=np.nanmax(x,axis=3)
    initial_partners=[dims[1].index('x'+str(j)) for j in world.get('initial_partner_ids',range(len(dims[1])))
                      if 'x'+str(j) in dims[1]]
    old=np.nanmax(best[r0,initial_partners],axis=0)
    valid=np.isfinite(x)
    mixed=best-best[:,[0],:]-best[[r0],:,:]+best[r0,0]
    mixed_relative=float(np.nanmax(abs(mixed)/np.maximum(old,1e-12)))
    cross=0;preferred=[]
    for i in range(len(dims[0])):
        if np.isfinite(best[i]).all():
            choice=np.argmax(best[i],axis=0).tolist();preferred.append(choice)
            cross+=len(set(choice))>1
    flattened=(best/np.maximum(old,1e-12)).reshape((-1,len(old)))
    finite=flattened[np.isfinite(flattened).all(axis=1)]
    centered=finite-finite.mean(axis=0)
    singular=np.linalg.svd(centered,compute_uv=False) if len(finite)>1 else np.zeros(len(old))
    sv_ratio=float(singular[1]/singular[0]) if len(singular)>1 and singular[0]>0 else 0.
    control_hashes={canonical_hash({'actions':{k:v['casts'] for k,v in r['actions'].items()},
                                   'resources':r['resources']}) for r in rows}
    thresholds=[]
    for e in [.01,.03,.05]:
        source_mass=np.mean(best[r0,initial_partners]>=old[None,:]-e*old[None,:],axis=1)
        for h in [.03,.05,.10]:
            permanent=np.mean(best[r0,initial_partners]>=old[None,:]*(1+h-e),axis=1)
            thresholds.append({'e':e,'h':h,'initial_valid':bool(np.all(source_mass>=.5)),
                'min_initial_source_mass':float(source_mass.min()),
                'all_old_partners_trivially_safe_through_cap':bool(np.all(permanent>=.5)),
                'old_primary_trivially_safe_through_cap':bool(h<=e)})
    expected=[len(world['candidates']),len(world['partners']),len(world['tasks']),len(world['policies'])]
    full=t['complete'] and list(x.shape)==expected
    return {'world_id':world['world_id'],'mechanism_id':world['mechanism_id'],
        'lineage_id':world.get('lineage_id',world['mechanism_id']),
        'model_scope':world.get('model_scope','fixed partner multi-task'),
        'physical_cells':len(rows),'physical_tensor_shape':list(x.shape),'declared_tensor_shape':expected,
        'full_tensor_observed':full,'missing_tensor_cells':int(np.prod(expected)-valid.sum()),'max_relative_mixed_contrast':mixed_relative,
        'centered_task_singular_ratio_2_over_1':sv_ratio,
        'rows_with_different_best_partner_across_tasks':cross,
        'distinct_observed_control_summaries':len(control_hashes),
        'old_task_frontier':old.tolist(),'threshold_diagnostics':thresholds,
        'status':'exploratory_complete_table' if full else 'exploratory_partial_table',
        'claim_status':'development only; nonlinearity/rank/crossing does not establish a decision effect',
        'tensor_dimensions':dims}


def analyze(batch, registry):
    batch=Path(batch);result=json.loads((batch/'RESULTS.json').read_text())
    groups=defaultdict(list)
    for r in result['rows']:
        if r is not None:groups[r['world_id']].append(r)
    worlds={w['world_id']:w for w in registry}
    atlas=[diagnose(worlds[k],rows) for k,rows in sorted(groups.items())]
    atomic_json(batch/'DIAGNOSTICS.json',atlas)
    write_csv(batch/'MECHANISM_ATLAS.csv',atlas)
    return atlas


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True);args=p.parse_args()
    worlds=[json.loads(line) for line in args.registry.read_text().splitlines() if line.strip()]
    atlas=analyze(args.batch,worlds)
    print(json.dumps({'worlds':len(atlas),'full_tables':sum(x['full_tensor_observed'] for x in atlas),
        'nonzero_mixed':sum(x['max_relative_mixed_contrast']>.005 for x in atlas),
        'task_crossings':sum(x['rows_with_different_best_partner_across_tasks']>0 for x in atlas)}))


if __name__=='__main__':main()
