"""Assemble exact native/abstract witness records without adding physics."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import shutil

from wowfs.paths import setup_paths, SOURCE_ROOT, atomic_json
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_feasibility import eval_all_safe
from wowfs.experiments.r4_support import minimum_support_bound, old_retention_box, sparsify_feasible_release


def main():
    root=setup_paths(); out=root/'artifacts/r4-foundational-discovery'
    causal=json.loads((out/'CAUSAL_PAIR_DETAILS.json').read_text())
    factors=list(csv.DictReader((out/'CAUSAL_PAIR_FACTORIALS.csv').open()))
    behavior=list(csv.DictReader((out/'CAUSAL_PAIR_WITNESSES.csv').open()))
    records=[]
    selected={('resource_haste','RaceHuman'):'331790c18dd3a920',
              ('timing_shared','RaceOrc'):'26007bac9b64ca50',
              ('timing_extra','RaceOrc'):'48d1cb0f8a17565d'}
    for certificate in causal['one_gear_certificates']:
        key=(certificate['pool'],certificate['race'])
        if selected.get(key)!=certificate['gear_id']:
            continue
        matches=lambda row: (row['pool'],row['race'],row['gear_id'])==(*key,certificate['gear_id'])
        records.append({'kind':'native_callback_world_certificate','native':True,
            'scope':'Empirical complete36-gear selected domain; H contains all16 old gears; no population behavior certificate.',
            'selection':'Original two named discovery gears; timing_extra gear selected from this ablation panel.',
            'run':'causal-pairs-v1','seed_start':409260001,'iterations':256,
            **certificate,
            'behavior_witness_rows':[row for row in behavior if matches(row) and int(row['mask'])==certificate['mask']],
            'paired_factorial_rows':[row for row in factors if matches(row)]})
    for name in ['E_MINIMAL_NATIVE_WITNESS.json','SELECTED_PAIR_CONSTRUCTIVE_CERTIFICATES.json']:
        path=out/name
        if path.exists():
            records.append({'kind':'prior_native_discovery_witness','native':True,'artifact':name,
                'scope':'16-seed discovery only; subsequent fresh failures are not overwritten. E repairs N, not L; generic controls match.',
                'data':json.loads(path.read_text())})
    if (out/'UNSEEN_E_COMPARISON.json').exists():
        records.append({'kind':'native_unseen_exploratory_subset_repair','native':True,
            'scope':'Detected after a previously predicted new-pool D study. Not a preregistered E prediction. Same current information and permissions for all rule classes.',
            'data':json.loads((out/'UNSEEN_E_COMPARISON.json').read_text())})
    if (out/'HIGH_PRECISION_CERTIFICATE_RESULTS.json').exists():
        precision=json.loads((out/'HIGH_PRECISION_CERTIFICATE_RESULTS.json').read_text())
        for certificate in precision['certificates']:
            records.append({'kind':'selected_native_research_variant_precision','native':True,
                'permission':'B: change item19019 physical weapon damage only in the new gear; retain old16 native physics.',
                'scope':'Approximate simultaneous finite-support certificate; original numerical anchors, selected then independently confirmed. Not population singleton impossibility.',
                'run':precision['run'],'certificate':certificate})
    records.append({'kind':'abstract_complete_coequipment_lower_bound','native':False,
        'parameter':'m protected source commitments','task_count':1,'behavior_dimension':1,
        'maximum_new_items_per_gear':1,'K':1,'epsilon':.05,'cap':1.05,
        'old_rewards':{'anchor':1,'source_i':.96},'candidate_rewards':{'diagonal_i_i':1.04,'all_off_diagonal_i_j':.96},
        'candidate_domain':'Every old-source/new-item combination is available; no omitted coequipment edge.',
        'behavior':'Diagonal1 novel; all other profiles may be zero. Test uses all diagonals novel, same proof.',
        'minimum_release_size':'m','proof':'D forces frontier1.04, threshold.99, so each old source needs its own diagonal new item.',
        'independent_check':'tests/test_r4_support.py enumerates all512 candidate admission masks for m3.'})
    bounds=[]
    for e in load_ecologies(root/'runs/r4-foundational-discovery/baseline-v1'):
        p,indices=e.problem(e.new_items,archive=e.initial_archive())
        bound=minimum_support_bound(p);box=old_retention_box(p);full=eval_all_safe(p)
        row={'pool':e.pool['id'],'race':e.race,'new_source_count':len(e.new_items),
             'protected_source_count':len(p.protected_sources),'D_support_bound':bound,
             'old_only_retention_box':box,'all_safe_joint':full['joint_pass']}
        if full['joint_pass']:
            row['sparsified']=sparsify_feasible_release(p,p.safe|p.protected)
        bounds.append(row)
    atomic_json(out/'QUALIFYING_SUPPORT_BOUNDS.json',{'contexts':bounds,
        'scope':'Finite16-seed baseline response table; D support lower bound is necessary only; old-only boxes are sufficient constructions, not oracle optima.'})
    (out/'STRUCTURAL_WITNESSES.jsonl').write_text(''.join(json.dumps(record,sort_keys=True)+'\n' for record in records))
    for name in ['THEORY.md','CLAIM_PRIOR_WORK_MAP.md','CAUSAL_FINDINGS.md','PRECISION_REVIEW.md']:
        shutil.copy2(SOURCE_ROOT/'docs/r4'/name,out/name)
    atomic_json(out/'STRUCTURAL_WITNESS_AUDIT.json',{'source_sha256':file_hash(Path(__file__)),
        'native_calls':0,'records':len(records),'baseline_contexts':len(bounds),
        'native_record_count':sum(record['native'] for record in records),
        'abstract_record_count':sum(not record['native'] for record in records)})
    print(json.dumps({'records':len(records),'support_bounds':[(r['pool'],r['race'],r['D_support_bound']['minimum_release_size_lower_bound']) for r in bounds]},indent=2))


if __name__=='__main__':main()
