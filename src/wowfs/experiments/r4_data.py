"""Shared R4 finite physics tables and immutable ecological state construction."""
from __future__ import annotations
from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import numpy as np
import yaml
from wowfs.paths import setup_paths,canonical_hash
from wowfs.experiments.r2_native import legal
from wowfs.experiments.r2_sequence_analysis import behavior_vector
from wowfs.experiments.r4_feasibility import FiniteProblem,evaluate_admission

@dataclass
class Ecology:
    pool:dict
    race:str
    tasks:list
    policies:list
    gear_ids:list
    gears:list
    values:np.ndarray
    behavior:np.ndarray
    samples:np.ndarray
    sources:list
    initial:np.ndarray
    new_items:tuple
    scale:np.ndarray
    cap:np.ndarray
    protected_sources:tuple
    config:dict

    def problem(self, released, *, protected=None, old_released=(), archive=None, protected_sources=None,
                headroom=None, epsilon=.05,delta=.05,weights=None,k_max=4, candidate_filter=None):
        new=set(map(str,released));old_new=set(map(str,old_released));present=new|old_new
        old=self.initial.copy() if protected is None else np.asarray(protected,bool)
        selectable=np.array([bool(new&ss) and not (ss&set(self.new_items))-present for ss in self.sources])
        if candidate_filter is not None:selectable&=np.asarray(candidate_filter,bool)
        domain=old|selectable;indices=np.flatnonzero(domain)
        pp=FiniteProblem(values=self.values[domain],behavior=self.behavior[domain],sources=[self.sources[i] for i in indices],
            protected=old[domain],new_sources=new,protected_sources=self.protected_sources if protected_sources is None else protected_sources,
            scale=self.scale,cap=self.cap if headroom is None else (1+headroom)*self.scale,
            archive=archive,weights=weights,epsilon=epsilon,delta=delta,k_max=k_max,gear_ids=[self.gear_ids[i] for i in indices])
        return pp,indices

    def initial_archive(self):
        return [self.behavior[self.initial,:,k].reshape(-1,self.behavior.shape[-1]).copy() for k in range(len(self.tasks))]


def enumerate_pools(cfg,database):
    output={}
    for pool in cfg['pools']:
        keys=list(pool['slots']);old_count=pool.get('old_choices_per_slot',2);items=pool['slots']
        old_items={int(i) for values in items.values() for i in values[:old_count]}
        new_items={int(i) for values in items.values() for i in values[old_count:]}-old_items
        records=[]
        for combination in itertools.product(*items.values()):
            gear={**cfg['character']['base_equipment'],**pool.get('fixed',{}),**dict(zip(keys,combination))}
            if not legal(gear,database):continue
            initial=all(value in items[key][:old_count] for key,value in zip(keys,combination))
            records.append({'gear_id':canonical_hash(gear)[:16],'gear':gear,'initial':initial,
                            'sources':set(str(gear[key]) for key in keys)})
        records.sort(key=lambda r:r['gear_id'])
        output[pool['id']]={'pool':pool,'records':records,'new_items':tuple(sorted(map(str,new_items)))}
    return output

def load_ecologies(run,config_path=None):
    root=setup_paths();run=Path(run)
    candidates=[run/'source/configs/r4_ecosystems.yaml',run/'source/r4_ecosystems.yaml',run/'CONFIG.yaml']
    if config_path is None:config_path=next((p for p in candidates if p.exists()),None)
    if config_path is None:raise FileNotFoundError('Frozen ecological config not found')
    cfg=yaml.safe_load(Path(config_path).read_text());data=json.loads((run/'RESULTS.json').read_text())
    if data['errors']:raise ValueError('Native physical errors preserved; incomplete ecology cannot be filled with zeros')
    frozen_path=run/'BASE_ECOSYSTEMS.json'
    if not frozen_path.exists():raise FileNotFoundError('Run must archive its exact BASE_ECOSYSTEMS.json domain')
    frozen=json.loads(frozen_path.read_text());specs={}
    for pool in frozen['ecosystems']:
        initial_ids=set(pool['initial_gear_ids'])
        records=[{'gear_id':key,'gear':frozen['gears'][key]['gear'],'initial':key in initial_ids,
                  'sources':set(map(str,pool['source_ids_by_gear'][key]))} for key in sorted(pool['terminal_gear_ids'])]
        specs[pool['id']]={'pool':pool,'records':records,'new_items':tuple(sorted(map(str,pool['new_source_ids'])))}
    tasks=frozen['tasks'];policies=[p['id'] for p in frozen['strategies']]
    lookup={(r['race'],r['gear_id'],r['task'],r['strategy']):r for r in data['rows']}
    output=[]
    for race in cfg['races']:
        for pid,spec in specs.items():
            records=spec['records'];g=len(records);shape=(g,len(policies),len(tasks))
            values=np.empty(shape);behavior=np.empty((*shape,7));samples=None
            for gi,record in enumerate(records):
                for pi,policy in enumerate(policies):
                    for ti,task in enumerate(tasks):
                        row=lookup[(race,record['gear_id'],task['id'],policy)]
                        x=np.asarray(row['dps_samples']);values[gi,pi,ti]=x.mean()
                        behavior[gi,pi,ti]=behavior_vector(row,task['duration_seconds'])
                        if samples is None:samples=np.empty((*shape,len(x)))
                        if len(x)!=samples.shape[-1]:raise ValueError('Unequal seed count')
                        samples[gi,pi,ti]=x
            initial=np.array([r['initial'] for r in records]);sources=[r['sources'] for r in records]
            scale=values[initial].max(axis=(0,1));cap=(1+cfg['metrics']['headroom'])*scale
            old_items=set.union(set(),*[ss for ss,old in zip(sources,initial) if old])
            close=values.max(axis=1)>=scale-.05*scale
            weights=np.asarray(cfg['metrics']['task_weights'])
            protected=tuple(sorted(s for s in old_items if weights@np.any(close[np.array([s in ss for ss in sources])&initial],axis=0)>=.05))
            output.append(Ecology(spec['pool'],race,tasks,policies,[r['gear_id'] for r in records],[r['gear'] for r in records],
                values,behavior,samples,sources,initial,spec['new_items'],scale,cap,protected,cfg))
    return output


def advance_state(ecology,indices,mask,old_mask,archive,registered):
    admitted=np.asarray(old_mask,bool).copy();admitted[indices]=np.asarray(mask,bool)
    newly=admitted&~old_mask;optimum=ecology.values[admitted].max(axis=(0,1))
    close=ecology.values[newly]>=optimum[None,None,:]-.05*ecology.scale[None,None,:]-1e-9
    updated=[np.asarray(a).copy() for a in archive]
    for k in range(len(ecology.tasks)):
        values=ecology.behavior[newly,:,k][close[:,:,k]]
        if len(values):updated[k]=np.concatenate([updated[k],values])
    allclose=ecology.values.max(axis=1)>=optimum-.05*ecology.scale
    registry=set(registered);weights=np.ones(len(ecology.tasks))/len(ecology.tasks)
    for source in set.union(set(),*[ss for ss,a in zip(ecology.sources,admitted) if a]):
        mask=np.array([source in ss for ss in ecology.sources])&admitted
        if weights@np.any(allclose[mask],axis=0)>=.05:registry.add(source)
    return admitted,updated,tuple(sorted(registry))
