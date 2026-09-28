"""Posthoc fixed-control diagnostic; never updates frozen admission models."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path

import numpy as np

from wowfs.paths import setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r2_native import file_hash, summarize
from wowfs.experiments.r3_affine import controls
from wowfs.experiments.r6_geometry import damage_channels


def raw_features(pair):
    key,row=pair
    directory=Path(row['cache_directory'])
    with gzip.open(directory/'output.json.gz','rt') as stream:output=json.load(stream)
    request=json.loads((directory/'input.json').read_text())
    regenerated=summarize(output,request)
    assert regenerated['dps_samples']==row['dps_samples']
    assert regenerated['actions']==row['actions']
    duration=request['request']['encounter']['duration']
    return key,{'controls_sha256':canonical_hash(controls(output)),
        'channels':damage_channels(regenerated,duration),
        'action_dps':{k:a['damage']/duration for k,a in regenerated['actions'].items()},
        'iterations':output['iterationsDone'],'seed_start':int(request['request']['simOptions']['randomSeed'])}


def main():
    root=setup_paths();run=root/'runs/r6-theory-native/capacity-precision-v1'
    artifact=root/'artifacts/r6-theory-native'
    archive=run/'RESULTS.json';data=json.loads(archive.read_text())
    assert not data['errors'] and all(data['rows'])
    rows=data['rows'];unique={r['cache_key']:r for r in rows}
    assert len(unique)==736 and len(rows)==832
    frozen_path=run/'inputs/frozen_capacity.json'
    frozen=json.loads(frozen_path.read_text())
    panel=next(p for p in frozen['panels'] if p['delta']==.025)
    anchors=['old_anchor',panel['designs'][0]['design_id'],panel['designs'][-1]['design_id']]
    aliases={(r['block'],r['design_id']):r for r in rows}
    blocks=defaultdict(dict)
    for key,row in unique.items():blocks[row['block']][key]=row
    assert len(blocks)==32 and all(len(b)==23 for b in blocks.values())
    raw={}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for key,features in pool.map(raw_features,unique.items()):raw[key]=features
    records=[];block_records=[]
    for block,cells in sorted(blocks.items()):
        anchor_rows=[aliases[(block,name)] for name in anchors]
        anchor_keys={r['cache_key'] for r in anchor_rows}
        points=np.array([r['theta'] for r in anchor_rows],float)
        matrix=np.c_[np.ones(3),points]
        assert np.linalg.matrix_rank(matrix)==3
        seed_fit=np.linalg.solve(matrix,np.array([r['dps_samples'] for r in anchor_rows]))
        channel_fit=np.linalg.solve(matrix,np.array([raw[r['cache_key']]['channels'] for r in anchor_rows]))
        action_keys=sorted(set().union(*(raw[k]['action_dps'] for k in cells)))
        action_fit=np.linalg.solve(matrix,np.array([[raw[r['cache_key']]['action_dps'].get(k,0)
            for k in action_keys] for r in anchor_rows]))
        reference=raw[anchor_rows[0]['cache_key']]['controls_sha256']
        cell_rows=[]
        for key,row in sorted(cells.items()):
            feature=np.r_[1.,row['theta']];native=raw[key]
            dps_error=np.asarray(row['dps_samples'])-feature@seed_fit
            channel_error=native['channels']-feature@channel_fit
            action_error=np.array([native['action_dps'].get(k,0) for k in action_keys])-feature@action_fit
            record={'block':block,'cache_key':key,'representative_design_id':row['design_id'],
                'theta':row['theta'],'is_posthoc_fit_anchor':key in anchor_keys,
                'iterations':native['iterations'],'seed_start':native['seed_start'],
                'full_controls_sha256':native['controls_sha256'],
                'controls_equal_within_block':native['controls_sha256']==reference,
                'max_absolute_per_seed_dps_residual':float(np.max(abs(dps_error))),
                'max_absolute_action_channel_mean_dps_residual':float(np.max(abs(channel_error))),
                'max_absolute_individual_action_mean_dps_residual':float(np.max(abs(action_error)))}
            cell_rows.append(record);records.append(record)
        block_records.append({'block':block,'unique_native_cells':len(cells),
            'anchor_design_ids':anchors,'anchor_theta':points.tolist(),
            'anchor_matrix_determinant':float(np.linalg.det(matrix)),
            'anchor_matrix_condition_number':float(np.linalg.cond(matrix)),
            'distinct_full_control_hashes':len({raw[k]['controls_sha256'] for k in cells}),
            'heldout_cells':sum(not r['is_posthoc_fit_anchor'] for r in cell_rows),
            'max_heldout_per_seed_dps_residual':max(r['max_absolute_per_seed_dps_residual'] for r in cell_rows if not r['is_posthoc_fit_anchor'])})
    heldout=[r for r in records if not r['is_posthoc_fit_anchor']]
    maximum=max(r['max_absolute_per_seed_dps_residual'] for r in heldout)
    channel_max=max(r['max_absolute_action_channel_mean_dps_residual'] for r in heldout)
    action_max=max(r['max_absolute_individual_action_mean_dps_residual'] for r in heldout)
    result={'schema':1,'created_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Posthoc structural diagnostic on the final frozen precision panel only; these fitted coefficients never update admission, sequence selection, polytope, geometry or inference.',
        'additional_native_calls':0,'additional_physical_battles':0,
        'logical_rows':len(rows),'unique_native_cells':len(unique),'independent_blocks':32,
        'unique_native_designs_per_block':23,'iterations_per_cell':2048,
        'physical_battles_already_executed_and_checked':sum(r['iterations'] for r in records),
        'posthoc_fit_anchor_cells':len(records)-len(heldout),'heldout_native_cells':len(heldout),
        'heldout_per_seed_dps_comparisons':sum(r['iterations'] for r in heldout),
        'fit_anchor_rule':'For every block independently: old_anchor plus first and last designs in the frozen delta0.025 sequence. The old point is off the new-design line; all remaining unique designs are predictions.',
        'fit_anchor_ids':anchors,'tolerance_dps':1e-8,
        'all_full_controls_identical_within_each_block':all(r['controls_equal_within_block'] for r in records),
        'all_heldout_per_seed_dps_residuals_pass':maximum<=1e-8,
        'all_heldout_action_channel_mean_dps_residuals_pass':channel_max<=1e-8,
        'all_heldout_individual_action_mean_dps_residuals_pass':action_max<=1e-8,
        'max_heldout_absolute_per_seed_dps_residual':maximum,
        'max_heldout_absolute_action_channel_mean_dps_residual':channel_max,
        'max_heldout_absolute_individual_action_mean_dps_residual':action_max,
        'action_channels':['auto_attacks','execute','whirlwind_or_cleave','bloodthirst','other_native_actions'],
        'control_definition':'Full r3_affine.controls(raw_output): action/target metrics excluding reward fields, resources and aura summaries; equality is within each common-seed block. No per-seed event trace claim for this unlogged panel.',
        'results_sha256':file_hash(archive),'frozen_capacity_sha256':file_hash(frozen_path),
        'driver_sha256':file_hash(Path(__file__)),'blocks':block_records,'cells':records}
    atomic_json(artifact/'FINAL_FIXED_CONTROL_AUDIT.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('blocks','cells')},indent=2))


if __name__=='__main__':main()
