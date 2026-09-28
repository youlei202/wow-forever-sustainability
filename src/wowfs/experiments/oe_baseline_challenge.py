"""Challenge capacity gains with a simple minimum-qualifying-increment baseline.

Same response information, sources, complete physical domain and release width.
No claim of a new algorithm: this tests the gain-rationing explanation.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
from wowfs.paths import atomic_json
from wowfs.experiments.oe_analysis import write_csv
from wowfs.experiments.oe_solver import Problem,Configuration,_Evaluator,validate_history


def problem_from_dict(d):
    return Problem(items=tuple(d['items']),initial_items=frozenset(d['initial_items']),
        configurations=tuple(Configuration(c['id'],frozenset(c['items']),tuple(c['utilities'])) for c in d['configurations']),
        task_weights=tuple(d['task_weights']),reference=tuple(d['reference']),gain=d['gain'],cap=d['cap'],
        tolerance=d['tolerance'],gain_mass=d['gain_mass'],retention_mass=d['retention_mass'],
        total_item_budget=d.get('total_item_budget'),epsilon=d.get('epsilon',1e-10))


def minimum_increment(p,score_weights,preference='weighted'):
    ev=_Evaluator(p);mask=0;path=[]
    if not ev.valid(0):return {'status':'initially_invalid','capacity':None,'path':[]}
    while True:
        options=list(ev.successors(mask,1))
        if not options:break
        before=np.array(ev.metrics(mask).frontier)
        def score(pair):
            nxt,batch=pair;s=ev.metrics(nxt);gain=np.array(s.frontier)-before
            weight=float(np.dot(score_weights,gain))
            if preference=='max_task':weight=float(max(gain))
            return (weight,-min(s.source_margins.values()),tuple(batch))
        mask,batch=min(options,key=score);path.append(batch)
    states=validate_history(p,path,1)
    return {'status':'heuristic','capacity':len(path),'path':path,
        'terminal_frontier':states[-1].frontier,'released_items':len(path),
        'score_weights':score_weights,'score_preference':preference,
        'source_margins':states[-1].source_margins}


def analyze(directory,output):
    directory=Path(directory);output=Path(output)
    rows=json.loads((directory/'PLANNING_RESULTS.json').read_text())
    domains={d['world_id']:d for d in json.loads((directory/'WORLD_DOMAINS.json').read_text())}
    results=[]
    for row in rows:
        if not row['planning_advantage_over_best_greedy_resolved']:continue
        p=replace(problem_from_dict(domains[row['world_id']]['problem_template']),gain=row['g'],cap=1+row['h'],tolerance=row['e'])
        q=len(p.reference)
        weights=[(w,1-w) for w in (0,.25,.5,.75,1)] if q==2 else [p.task_weights]
        choices=[minimum_increment(p,w) for w in weights]+[minimum_increment(p,p.task_weights,'max_task')]
        best=max(choices,key=lambda r:r['capacity'])
        exact=row['methods']['exact_B1_retaining']
        terminal=exact['frontiers'][-1] if exact['frontiers'] else _Evaluator(p).metrics(0).frontier
        results.append({'world_id':row['world_id'],'mechanism_id':row['mechanism_id'],'g':row['g'],'h':row['h'],'e':row['e'],
            'finite_exact_lower':exact['capacity_lower'],'finite_exact_upper':exact['capacity_upper'],
            'previous_best_greedy':row['best_greedy_capacity'],'minimum_increment_best':best['capacity'],
            'planning_gap_survives_challenge':exact['capacity_lower']>best['capacity'],
            'same_terminal_frontier':bool(np.allclose(terminal,best['terminal_frontier'],rtol=0,atol=1e-10)),
            'full_candidate_domain':domains[row['world_id']]['retained_row_ids'],
            'baselines':choices,'mean_only':True,'interpretation':'Search heuristic comparison, not extra content value or algorithmic novelty.'})
    output.mkdir(parents=True,exist_ok=True)
    atomic_json(output/'MIN_INCREMENT_CHALLENGE.json',results)
    write_csv(output/'MIN_INCREMENT_CHALLENGE.csv',[{k:v for k,v in r.items() if k!='baselines'} for r in results])
    summary={'challenged_rows':len(results),'gap_removed':sum(not r['planning_gap_survives_challenge'] for r in results),
             'gap_remains':sum(r['planning_gap_survives_challenge'] for r in results),'scope':'Development mean subdomains only; no new native observations.'}
    atomic_json(output/'SUMMARY.json',summary);return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();print(json.dumps(analyze(args.analysis,args.output)))


if __name__=='__main__':main()
