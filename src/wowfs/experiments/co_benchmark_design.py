"""Outcome-independent exact benchmark registry for completion interfaces.

These are synthetic finite models, never native equipment/coverage claims.
The matching/source family implements the supplied theorem reduction; all
other families are registered stress/control distributions, not prevalence.
"""
from __future__ import annotations
import argparse
from fractions import Fraction as F
import hashlib
from itertools import combinations, product
import json
from pathlib import Path
import random

FAMILIES=('frontier_grid_control','concentrated_conflicts','matching_sources',
          'alternative_supports','nonseparable_rational','output_heavy')
SIZES=(16,32,64,128,256)


def frac(x):return str(F(x))


def generate(family, nominal_n, q, seed, instance_id):
    rng=random.Random(seed)
    nl=nominal_n//2;nr=nominal_n-nl
    left=[f'l{i:03}' for i in range(nl)];right=[f'r{i:03}' for i in range(nr)]
    history=[left[0],right[0]];target=[left[1]]
    tolerance=['2']*q; cap=['12']*q; gain=['1']*q;rho='1/2';gm='1/'+str(q)
    rows=[]; construction={}
    if family=='matching_sources':
        q=1;vertices=max(3,min(16,(nominal_n-3)//4))
        edge_count=max(1,(nominal_n-3-2*vertices)//2)
        all_edges=list(combinations(range(vertices),3))
        rng.shuffle(all_edges)
        edges=all_edges[:min(edge_count,len(all_edges))]
        # Every third generated seed is a declared Fano obstruction plus noise.
        if vertices>=7 and seed%3==0:
            edges=list(dict.fromkeys([(0,1,2),(0,3,4),(0,5,6),(1,3,5),(1,4,6),(2,3,6),(2,4,5)]+edges))
        left=['l0']+[f'p{j}' for j in range(len(edges))]+[f'f{i}' for i in range(vertices)]+['d']
        right=['r0']+[f'n{j}' for j in range(len(edges))]+[f't{i}' for i in range(vertices)]
        history=['l0','r0']+[f'p{j}' for j in range(len(edges))]+[f'n{j}' for j in range(len(edges))]
        target=['d']; tolerance=['5'];cap=['25'];gain=['3'];rho=gm='1'
        for l,r in product(left,right):
            v=16
            if (l,r)==('l0','r0'):v=20
            if (l,r)==('d','r0'):v=24
            if l=='l0' and r.startswith('t'):v=22
            if l.startswith('f') and r=='r0':v=22
            if l.startswith('p') and r.startswith('t') and int(r[1:]) in edges[int(l[1:])]:v=22
            if l.startswith('f') and r.startswith('n') and int(l[1:]) in edges[int(r[1:])]:v=22
            if l.startswith('f') and r.startswith('t') and l[1:]==r[1:]:v=30
            rows.append({'id':l+'__'+r,'support':[l,r],'values':[str(v)]})
        fixed_y=['24'];construction={'vertices':vertices,'hyperedges':edges,'theorem_generated':True}
    else:
        # Large sparse tables still give every identity physical incidences.
        # The missing configurations are declared physical exclusions, never a
        # reduction applied to an already frozen complete table.
        pairs={(i,0) for i in range(nl)}|{(0,j) for j in range(nr)}
        if nominal_n<=64:pairs.update(product(range(nl),range(nr)))
        else:
            for i in range(1,nl):
                pairs.add((i,i%nr))
                pairs.update((i,j) for j in rng.sample(range(1,nr),min(10,nr-1)))
        if family=='frontier_grid_control':
            pairs={(i,0) for i in range(nl)}|{(0,j) for j in range(nr)}
            construction['physical_domain']='Declared star: at most one optional identity per configuration; residual conflict cover is zero at every frontier.'
        for i,j in sorted(pairs):
            if family=='frontier_grid_control':
                # Half are deliberately infeasible despite no above-cap edge:
                # legacy l0 can never match gain on every task (rho=1).
                hard=seed%2==0;rho='1' if hard else '1/2'
                tolerance=['1/8' if hard else '4']*q
                vals=[F(10) if (i,j)==(0,0) else
                      (F(10)-F((j+t)%7,20) if i==0 else F(10)+F(1+(i*17+j*13+t*7)%37,20)) for t in range(q)]
                cap=['12']*q;gain=['1/2']*q
            elif family=='concentrated_conflicts':
                k=(0,1,2,4,8,12,16)[seed%7];construction['designated_conflict_left_count']=min(k,nl-1)
                vals=[F(10) if (i,j)==(0,0) else F(14) if 1<=i<=k and j>0 and (i+j+t)%3==0 else F(rng.choice([9,10,11,12])) for t in range(q)]
                tolerance=['2']*q
            elif family=='alternative_supports':
                vals=[F(10) if (i,j)==(0,0) else F(12) if ((i+j+t)%4 in (0,1)) else F(8) for t in range(q)]
                tolerance=['1']*q;rho='1';construction['cycle_support_pattern']='alternating task witnesses plus independently declared physical sparsity'
            elif family=='nonseparable_rational':
                vals=[F(10) if (i,j)==(0,0) else F(rng.randrange(24,43),3) for t in range(q)]
                tolerance=[str(F(3+(seed+t)%5,3)) for t in range(q)]
                rho=str(F(1+(seed%q),q))
            elif family=='output_heavy':
                vals=[F(10) if (i,j)==(0,0) else F(14) if i==j and i>0 else F(11) for _ in range(q)]
                tolerance=['2']*q;cap=['12']*q;rho='1';gm='1'
                construction['matching_conflicts']=min(nl,nr)-1
            else:raise ValueError(family)
            rows.append({'id':left[i]+'__'+right[j],'support':[left[i],right[j]],'values':list(map(frac,vals))})
        fixed_y=[str(max(F(row['values'][t]) for row in rows if F(row['values'][t])<=F(cap[t]))) for t in range(q)]
    obj={'instance_id':instance_id,'data_kind':'SYNTHETIC_EXACT','family':family,'generation_seed':seed,
         'nominal_N_axis':nominal_n,'actual_N':len(left)+len(right),'actual_M':len(rows),'Q':q,
         'slots':{i:0 for i in left}|{i:1 for i in right},'configurations':rows,'history':history,
         'weights':[str(F(1,q))]*q,'tolerance':tolerance,'cap':cap,'gain':gain,
         'required_mass':rho,'gain_mass':gm,'target':target,'fixed_y':fixed_y,'construction':construction}
    obj['unique_response_levels']=[len({r['values'][t] for r in rows}) for t in range(q)]
    count=1
    for t in range(q):count*=len({r['values'][t] for r in rows if F(10)<=F(r['values'][t])<=F(cap[t])})
    obj['frontier_cartesian_upper_using_initial_10']=count if family!='matching_sources' else None
    return obj


def query_stream(obj, seed, limit=10000):
    rng=random.Random(seed);e=sorted(set(obj['slots'])-set(obj['history']))
    streams=[];seen=set()
    def add(d,kind):
        d=tuple(sorted(d))
        if d and d not in seen:seen.add(d);streams.append({'target':list(d),'query_kind':kind})
    for i in e:add([i],'singleton')
    pairs=list(combinations(e,2));rng.shuffle(pairs)
    for p in pairs[:min(len(pairs),4000)]:add(p,'pair')
    # Fair interleaving prevents a free prefix consisting exclusively of
    # direct singleton decisions. All targets generated before labels exist.
    for _ in range(limit*3):
        k=rng.choice([2,3,3,4]) if len(e)>=4 else rng.randrange(1,len(e)+1)
        add(rng.sample(e,k),'small_joint')
        if len(streams)>=limit:break
    rng.shuffle(streams)
    return {'instance_id':obj['instance_id'],'seed':seed,'unique':True,'count':len(streams),
            'future_universe':e,'prefixes':[x for x in (1,10,100,1000,10000) if x<=len(streams)]+([len(streams)] if len(streams) not in (1,10,100,1000,10000) else []),
            'queries':[{'query_index':j+1,**r} for j,r in enumerate(streams)]}


def registry(split):
    n=10 if split=='develop' else 20
    seed_base=270926000 if split=='develop' else 280927000
    rows=[]
    for fi,family in enumerate(FAMILIES):
        for rep in range(n):
            size=SIZES[rep%5];q=(1,2,4,8)[rep//5] if split!='develop' else (1,2)[rep//5]
            identity=f'{split}_{fi:02}_{rep:02}'
            row=generate(family,size,q,seed_base+fi*100+rep,identity)
            if split=='develop':row['workflow']='fixed_y' if rep%2==0 else 'unknown_y';rows.append(row)
            else:
                for mode in ('fixed_y','unknown_y'):
                    rows.append({**row,'instance_id':identity+'_'+mode,'workflow':mode})
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['develop','test'],required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows=registry(a.split)
    f=a.output/'BENCHMARK_INSTANCES.jsonl';f.write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in rows))
    query_rows=[query_stream(x,390000+j) for j,x in enumerate(rows) if x['workflow']=='unknown_y' and x['nominal_N_axis'] in (16,64) and (x['Q']==1 or (x['family']=='matching_sources' and x['instance_id'].split('_')[2] in ('00','02')))]
    # One compact and one medium history per structural family, fixed solely
    # by registry position; no interface/result-based selection.
    chosen=[]
    for family in FAMILIES:
        for nominal in (16,64):
            eligible=[s for s in query_rows if next(x for x in rows if x['instance_id']==s['instance_id'])['family']==family and next(x for x in rows if x['instance_id']==s['instance_id'])['nominal_N_axis']==nominal]
            if eligible:chosen.append(eligible[0])
    (a.output/'QUERY_STREAMS.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in chosen))
    (a.output/'REGISTRY_HASHES.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.output.glob('*.jsonl')},indent=2)+'\n')
    print(json.dumps({'split':a.split,'instances':len(rows),'query_histories':len(chosen),'directory':str(a.output)}))

if __name__=='__main__':main()
