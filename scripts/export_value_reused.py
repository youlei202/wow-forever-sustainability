#!/usr/bin/env python3
"""Export four complete R4 ecologies as small portable native-derived tensors."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import numpy as np
from wowfs.paths import setup_paths,atomic_json,SOURCE_ROOT,canonical_hash
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.value_reused import load_export

POOLS=('static_skill','timing_extra','timing_shared','resource_haste')

README='''# Compact cached native data

This is a read-only-derived export of the existing R4 `baseline-v1` response
table: four complete equipment ecologies, Human/Orc Warrior, eight real combat
tasks, three declared policies, and sixteen native battle samples per cell.
It adds **zero native calls**. Overlapping ecologies are not independent samples.
These are exploratory cached means, not new independent confirmation.

`MANIFEST.json` records the original RESULTS hash and full source PROTOCOL,
configuration/domain hashes, plus each exported tensor/metadata hash. The large
original RESULTS is intentionally omitted. `SOURCE_PROTOCOL.json` and
`SOURCE_CONFIG.yaml` are exact copies; their hashes can be checked locally.
The stored original RESULTS hash is a provenance commitment, not a claim that
the omitted source can be independently inspected from this small export alone.

For each `pool__race`, the NPZ contains `values` [gear,policy,task], `behavior`
[gear,policy,task,7], `samples` [gear,policy,task,16], `initial` [gear], and the
fixed `scale`/`cap` [task]. Metadata provides exact axis order, native item IDs,
complete gear dictionaries, source memberships, registered protected sources,
new items, frozen pool and experiment configuration. No pickle is used.
The seven behavior coordinates retain the original R4 definition: five native
damage shares, rage gain rate divided by20, and rage waste fraction. They are
not substituted for actual combat decision utility.

The small `.cached_subsets.json` files retain only the original solver masks
and their domain indices used by `value_history.screen`. They are solver inputs
to this reanalysis, not new physics. Their full original file hashes are recorded.

## Load and recompute

From the supplied source checkout, source `scripts/env.sh`, then set DATA_DIR
to the absolute path of this exported directory. No native binary, external
item database, original billion-byte RESULTS, or earlier runtime is required
for loading or recalculating decisions from these tensors.

```bash
source scripts/env.sh
export DATA_DIR="$WOWFS_WORK_ROOT/artifacts/decisive-value/reused_r4"
python - <<'PY'
import os
from pathlib import Path
from wowfs.paths import atomic_json
from wowfs.experiments.value_reused import load_export,previous_subset_masks
from wowfs.experiments.value_history import screen
from wowfs.experiments.value_combinations import compare,PAIRS

folder=Path(os.environ['DATA_DIR'])
ecologies=load_export(folder)  # verifies tensor and metadata hashes
# Natural, all-power-safe and recorded subset line C screen, including
# complete old-policy reoptimization, source deletions and gain curves.
history=[screen(e,previous_subset_masks(folder,e)) for e in ecologies]
atomic_json(folder/'RECOMPUTED_LINE_C.json',history)
# Line B with the same source-incidence features and all legacy obligations.
# Generic MILP optima may have tied masks; feasibility/gain is the comparison.
combinations=[compare(e,pair,seconds=15) for e in ecologies
              for pair in PAIRS[e.pool['id']]]
atomic_json(folder/'RECOMPUTED_LINE_B.json',combinations)
print(len(ecologies),'contexts; zero new native calls')
PY
```

`value_demand.decision_metrics` can directly accept each Ecology's tensors and
the masks returned by `e.problem(release)` for the stable-task/precommit demand
contrast. Run outputs above are derived analysis only and never replace the
packaged native observations or the frozen original screen results.
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args()
    root=setup_paths();run=root/'runs/r4-foundational-discovery/baseline-v1'
    out=Path(args.output) if args.output else root/'artifacts/decisive-value/reused_r4'
    if (out/'MANIFEST.json').exists():raise ValueError('Export already frozen; use another output path')
    out.mkdir(parents=True,exist_ok=True)
    paths={'results':run/'RESULTS.json','protocol':run/'PROTOCOL.json',
           'config':run/'source/configs/r4_ecosystems.yaml','domain':run/'BASE_ECOSYSTEMS.json'}
    provenance={k:{'original_path':str(p),'sha256':file_hash(p),'bytes':p.stat().st_size}
                for k,p in paths.items()}
    shutil.copy2(paths['protocol'],out/'SOURCE_PROTOCOL.json')
    shutil.copy2(paths['config'],out/'SOURCE_CONFIG.yaml')
    ecologies=[e for e in load_ecologies(run) if e.pool['id'] in POOLS]
    if len(ecologies)!=8:raise ValueError('Expected four ecologies times two races')
    records=[]
    for e in ecologies:
        if e.samples.shape[-1]!=16 or e.initial.sum()!=16:raise ValueError('Frozen R4 domain/sample count mismatch')
        name=e.pool['id']+'__'+e.race;tensor=out/(name+'.npz');metadata=out/(name+'.json')
        np.savez_compressed(tensor,values=e.values,behavior=e.behavior,samples=e.samples,
                            initial=e.initial,scale=e.scale,cap=e.cap)
        meta={'pool':e.pool,'race':e.race,'tasks':e.tasks,'policies':e.policies,
            'gear_ids':e.gear_ids,'gears':e.gears,'sources':[sorted(s) for s in e.sources],
            'protected_sources':list(e.protected_sources),'new_items':list(e.new_items),
            'config':e.config,'source_results_sha256':provenance['results']['sha256'],
            'source_protocol_sha256':provenance['protocol']['sha256'],
            'scope':'Read-only-derived cached16 native data, zero new executions.',
            'axes':{'values':['gear','policy','task'],'behavior':['gear','policy','task','feature'],
                    'samples':['gear','policy','task','seed_offset']},
            'feature_names':['auto_attack_damage_share','execute_damage_share','whirlwind_cleave_damage_share',
                             'bloodthirst_damage_share','other_damage_share','rage_gain_per_second_over20','rage_waste_fraction']}
        atomic_json(metadata,meta)
        original=root/'runs/r4-foundational-discovery/batch-screen-v1'/(name+'.json')
        cached={}
        if original.exists():
            prior=json.loads(original.read_text());details=[]
            for detail in prior.get('details',[]):
                subset=detail.get('subset',{})
                if subset.get('feasible'):
                    details.append({'release_items':detail['release_items'],'indices':detail['indices'],
                                    'subset':{'feasible':True,'admitted':subset['admitted']}})
            cached={'source_path':str(original),'source_sha256':file_hash(original),'details':details,
                    'scope':'Original cached R4 feasible admission masks only; not new solver claims or native calls.'}
        masks=out/(name+'.cached_subsets.json');atomic_json(masks,cached)
        records.append({'pool':e.pool['id'],'race':e.race,'tensor_file':tensor.name,
            'tensor_sha256':file_hash(tensor),'metadata_file':metadata.name,'metadata_sha256':file_hash(metadata),
            'cached_masks_file':masks.name,'cached_masks_sha256':file_hash(masks),
            'gears':len(e.gear_ids),'initial_gears':int(e.initial.sum()),
            'response_cells':int(e.values.size),'native_samples_per_cell':16,
            'reused_battle_samples':int(e.samples.size)})
    manifest={'schema':1,'created_utc':datetime.now(timezone.utc).isoformat(),
        'native_new_calls':0,'native_new_battles':0,'source_native_run':str(run),
        'scope':'Derived read-only cached16 native tables; reused observations are not additional physical battles.',
        'source_provenance':provenance,'source_protocol':json.loads(paths['protocol'].read_text()),
        'contexts':records,'exporter_sha256':file_hash(Path(__file__)),
        'adapter_sha256':file_hash(SOURCE_ROOT/'src/wowfs/experiments/value_reused.py')}
    atomic_json(out/'MANIFEST.json',manifest)
    loaded=load_export(out)
    for expected,actual in zip(ecologies,loaded):
        for field in ['values','behavior','samples','initial','scale','cap']:
            if not np.array_equal(getattr(expected,field),getattr(actual,field)):raise ValueError('Tensor roundtrip changed '+field)
        for field in ['pool','race','tasks','policies','gear_ids','gears','sources','new_items','protected_sources','config']:
            if getattr(expected,field)!=getattr(actual,field):raise ValueError('Metadata roundtrip changed '+field)
    (out/'README.md').write_text(README)
    audit={'native_new_calls':0,'contexts':len(loaded),'array_and_metadata_roundtrip_exact':True,
        'response_cells':sum(r['response_cells'] for r in records),
        'reused_native_battle_samples':sum(r['reused_battle_samples'] for r in records),
        'export_files_bytes':sum(p.stat().st_size for p in out.iterdir() if p.is_file()),
        'manifest_sha256':file_hash(out/'MANIFEST.json')}
    atomic_json(out/'EXPORT_CHECK.json',audit);print(json.dumps(audit,indent=2),flush=True)


if __name__=='__main__':main()
