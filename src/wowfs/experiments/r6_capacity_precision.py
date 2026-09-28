"""One fixed-size, disjoint-seed precision follow-up without design changes."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from wowfs.paths import setup_paths, atomic_json, SOURCE_ROOT
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r6_native import run_jobs
from wowfs.experiments.r6_neutral import native_job
from wowfs.experiments.r6_neutral_analysis import analyze_rows


def execute(workers=32):
    root=setup_paths();out=root/'artifacts/r6-theory-native'
    bpath=out/'FRONTIER_NEUTRAL_POLYTOPE.json';cpath=out/'FROZEN_CAPACITY_DESIGN.json'
    spec=json.loads(bpath.read_text());original=json.loads(cpath.read_text())
    protocol={'created_utc':datetime.now(timezone.utc).isoformat(),
        'original_capacity_design_sha256':file_hash(cpath),'polytope_sha256':file_hash(bpath),
        'unchanged_parameters_and_order':True,'blocks':32,'iterations_per_block':2048,
        'seed_start':614000001,'seed_stride':10000,'global_alpha':.05,'per_panel_alpha':.0125,
        'reason':'Initial four-threshold panel had all point successes but two novelty interval bounds remained unresolved. Fixed-size follow-up; no design retuning, no pooling, no further optional sample-size checks.',
        'initial_seed_overlap_disclosure':'Initial C seed starts609280001+10000b partially overlapped B609260001+10000b. Its native calls are real, but that panel was not fully independent of B. This final panel is disjoint from every prior R6 seed range.',
        'analysis':'Use only this new dataset for final four-panel simultaneous approximate inference. Preserve initial results separately.'}
    path=out/'FROZEN_CAPACITY_PRECISION.json'
    if path.exists(): raise ValueError('Final precision panel already frozen')
    atomic_json(path,protocol)
    designs=[{'design_id':'old_anchor','theta':spec['old_theta']}]+[d for p in original['panels'] for d in p['designs']]
    jobs=[native_job(d['theta'],d['design_id'],protocol['seed_start']+block*protocol['seed_stride'],protocol['iterations_per_block'],block=block)
          for block in range(protocol['blocks']) for d in designs]
    print(run_jobs(jobs,'capacity-precision-v1',protocol,workers=workers,
          source_paths=[Path(__file__),SOURCE_ROOT/'src/wowfs/experiments/r6_neutral.py',SOURCE_ROOT/'src/wowfs/experiments/r6_neutral_analysis.py'],
          input_artifacts={'frozen_capacity_precision.json':path,'frozen_capacity.json':cpath,'frozen_polytope.json':bpath}))


def analyze():
    root=setup_paths();out=root/'artifacts/r6-theory-native'
    spec=json.loads((out/'FRONTIER_NEUTRAL_POLYTOPE.json').read_text())
    original=json.loads((out/'FROZEN_CAPACITY_DESIGN.json').read_text())
    protocol=json.loads((out/'FROZEN_CAPACITY_PRECISION.json').read_text())
    data=json.loads((root/'runs/r6-theory-native/capacity-precision-v1/RESULTS.json').read_text())
    if data['errors']: raise ValueError('Final precision native errors')
    summaries=[];analyses=[];sequences=[]
    for panel in original['panels']:
        order=['old_anchor']+[d['design_id'] for d in panel['designs']]
        result=analyze_rows([r for r in data['rows'] if r['design_id'] in order],order,
            spec['initial_frontier'],spec['epsilon_raw'],panel['delta'],spec['fixed_cap'],protocol['per_panel_alpha'])
        analyses.append({'delta':panel['delta'],**result})
        sequences.extend({'panel':'capacity_final_precision',**r} for r in result['rows'])
        summaries.append({'delta':panel['delta'],'r':1,'same_frozen_region':True,
            'theorem_guaranteed':panel['theorem_T_guaranteed'],
            'fitted_continuous_maximum':panel['construction']['exact_fitted_continuous_capacity'],
            'native_fresh_candidates':len(panel['designs']),'confirmed_prefix':result['confirmed_updates'],
            'all_joint_supported':result['all_joint_supported'],
            'point_successes':sum(r['joint_point_estimate'] for r in result['rows']),
            'minimum_novelty_lower':min(r['min_full_archive_distance_lower'] for r in result['rows']),
            'maximum_frontier_growth':max(r['point_frontier_growth_vs_fresh_old'] for r in result['rows']),
            'minimum_frontier_slack_lower':min(-r['paired_difference_upper'] for r in result['rows']),
            'K':1,'fixed_rule_rows':6,'samples_per_design':result['samples_per_design'],
            'fresh_seed_blocks':32,'per_panel_alpha':protocol['per_panel_alpha'],
            'inference_dataset':'capacity-precision-v1 only; no pooling with initial panel',
            'scope':'Native lower bound plus fitted-line numeric geometric maximum. Approximate simultaneous inference; no population/whole-game maximum claim.'})
    for name in ['CAPACITY_SCALING.csv','CAPACITY_SEQUENCES.csv']:
        destination=out/name.replace('.csv','_INITIAL.csv')
        if not destination.exists(): shutil.copy2(out/name,destination)
    atomic_json(out/'CAPACITY_PRECISION_CONFIRMATION.json',{'protocol':protocol,'panels':analyses,'summary':summaries})
    write_csv(out/'CAPACITY_SCALING.csv',summaries);write_csv(out/'CAPACITY_SEQUENCES.csv',sequences)
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['execute','analyze']);parser.add_argument('--workers',type=int,default=32)
    args=parser.parse_args()
    execute(args.workers) if args.phase=='execute' else analyze()
