"""Cached native demand screen: behavioral distance is not decision gain."""
from itertools import combinations
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import numpy as np
import yaml
from wowfs.paths import setup_paths,atomic_json,SOURCE_ROOT
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_feasibility import evaluate_admission
from wowfs.experiments.value_native import load_decision_ecologies


def decision_metrics(values, old, allowed, scale, weights, epsilon=.01):
    values=np.asarray(values);old=np.asarray(old,bool);allowed=np.asarray(allowed,bool)
    if not np.all(allowed[old]):raise ValueError('Cannot manufacture value by deleting old alternatives')
    best=values.max(axis=1)
    old_opt=best[old].max(axis=0);new_opt=best[allowed].max(axis=0)
    gain=(new_opt-old_opt)/scale
    # Gear is chosen before a real task draw, policy after task revelation.
    old_precommit=float(np.max((best[old]/scale)@weights))
    new_precommit=float(np.max((best[allowed]/scale)@weights))
    return {'old_reoptimized':old_opt.tolist(),'new_reoptimized':new_opt.tolist(),
        'normalized_gain':gain.tolist(),'gain_mass':float(weights@(gain>=epsilon-1e-10)),
        'weighted_gain':float(weights@gain),'stable_sustained_gain':float(gain[0]),
        'precommit_old':old_precommit,'precommit_new':new_precommit,
        'precommit_gain':new_precommit-old_precommit,
        'complete_old_policy_reoptimization':True}


def main():
    root=setup_paths();out=root/'artifacts/decisive-value';run=root/'runs/decisive-value/demand-screen-v1'
    cfgpath=SOURCE_ROOT/'configs/decisive_value.yaml';cfg=yaml.safe_load(cfgpath.read_text())
    protocol={'created_utc':datetime.now(timezone.utc).isoformat(),'configuration_sha256':file_hash(cfgpath),
        'source_sha256':file_hash(Path(__file__)),'native_source':'R4 baseline-v1 read only',
        'release_sizes':[1,2,'all'],'new_native_calls':0,'stage':'development on existing16-seed observations',
        'D_and_G':'Preserve R4 metrics, add full-old-library decision gain independently.'}
    if (run/'PROTOCOL.json').exists():raise ValueError('Use a new analysis version rather than overwrite a frozen screen')
    run.mkdir(parents=True);atomic_json(run/'PROTOCOL.json',protocol);shutil.copy2(cfgpath,run/'CONFIG.yaml')
    ecologies=load_decision_ecologies(cfg['ecologies'],cfg['races']);records=[];taskrows=[];details=[]
    for e in ecologies:
        releases=[release for size in [1,2] for release in combinations(e.new_items,size)]+[e.new_items]
        for release in releases:
            p,indices=e.problem(release,archive=e.initial_archive())
            for method,mask in [('natural_all_combinations',np.ones(len(indices),bool)),('all_cap_safe_combinations',p.safe|p.protected)]:
                metrics=evaluate_admission(p,mask)
                gain=decision_metrics(p.values,p.protected,mask,p.scale,p.weights)
                reduced=[]
                for item in release:
                    without=mask&np.array([str(item) not in ss for ss in p.sources])
                    if np.all(without[p.protected]):
                        opt=p.best[without].max(axis=0)
                        reduced.append({'source':str(item),'delete_source_optimum':opt.tolist(),
                                        'marginal_normalized_gain':((np.asarray(gain['new_reoptimized'])-opt)/p.scale).tolist()})
                row={'ecology':e.pool['id'],'race':e.race,'release':list(release),'release_size':len(release),
                     'method':method,'all_domain_configurations':len(indices),'admitted_configurations':int(mask.sum()),
                     **{k:metrics[k] for k in ['P','N','D','L','H','C','K','joint_pass']},
                     'G':gain['gain_mass']>=.125-1e-10,'joint_with_G':metrics['joint_pass'] and gain['gain_mass']>=.125-1e-10,
                     'G_stable':gain['stable_sustained_gain']>=.01,'G_precommit':gain['precommit_gain']>=.01,
                     **gain,'source_deletions':reduced,'inference':'exploratory cached16-seed finite means'}
                records.append(row)
                for k,task in enumerate(e.tasks):
                    taskrows.append({'ecology':e.pool['id'],'race':e.race,'release':list(release),'method':method,
                        'task':task['id'],'old_library_utility':gain['old_reoptimized'][k],
                        'new_library_utility':gain['new_reoptimized'][k],
                        'delete_whole_release_utility':gain['old_reoptimized'][k],
                        'normalized_gain':gain['normalized_gain'][k],'fixed_cap':float(p.cap[k]),
                        'scale':float(p.scale[k]),'old_gear_count':int(p.protected.sum()),
                        'policies_optimized':len(e.policies),'P':metrics['P'],'old_source_L':metrics['L']})
                if row['joint_with_G']:
                    details.append({'ecology':e.pool['id'],'race':e.race,'release':list(release),'method':method,
                        'indices':indices.tolist(),'admitted':mask.tolist(),'metrics':metrics,'gain':gain})
        print(json.dumps({'ecology':e.pool['id'],'race':e.race,'rows':len(records),
                          'joint_with_G':sum(r['joint_with_G'] for r in records)}),flush=True)
    write_csv(out/'LINE_A_DEMAND_SCREEN.csv',records);write_csv(out/'DECISION_VALUE_RESULTS.csv',taskrows)
    atomic_json(out/'LINE_A_POSITIVE_WITNESSES.json',details)
    summary={'native_calls':0,'ecological_contexts':len(ecologies),'release_method_rows':len(records),
        'D_true_G_false':sum(r['D'] and not r['G'] for r in records),
        'G_true_D_false':sum(r['G'] and not r['D'] for r in records),
        'joint_with_G':sum(r['joint_with_G'] for r in records),
        'positive_contexts':sorted(set((r['ecology'],r['race']) for r in records if r['joint_with_G'])),
        'best_rows':sorted([r for r in records if r['joint_with_G']],key=lambda r:(r['release_size'],-r['gain_mass'],-r['weighted_gain']))[:20]}
    atomic_json(out/'LINE_A_SUMMARY.json',summary);atomic_json(run/'RESULTS.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='best_rows'},indent=2))


if __name__=='__main__':main()
