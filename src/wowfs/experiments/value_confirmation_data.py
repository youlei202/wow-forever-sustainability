"""Read-only array API for the frozen decisive-value native confirmation."""
from dataclasses import dataclass
import json
import numpy as np
from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_sequence_analysis import behavior_vector


@dataclass
class ConfirmationTable:
    design:dict
    gear_ids:list
    sources:list
    task_ids:list
    policies:list
    samples:np.ndarray
    values:np.ndarray
    behavior:np.ndarray
    initial:np.ndarray


def load_confirmation(run_id='native-confirmation-v1'):
    run=setup_paths()/'runs/decisive-value'/run_id
    design=json.loads((run/'inputs/frozen_catalog.json').read_text())
    calibration=json.loads((run/'inputs/four_axis_calibration.json').read_text())
    result=json.loads((run/'RESULTS.json').read_text())
    if result['errors'] or any(r is None for r in result['rows']):raise ValueError('Incomplete native confirmation')
    tasks=calibration['protocol']['tasks'];policies=[p['id'] for p in calibration['protocol']['strategies']]
    gear_ids=[g['gear_id'] for g in design['full_cross']]
    sources=[{g['mh_source_id'],g['oh_source_id']} for g in design['full_cross']]
    lookup={(r['gear_id'],r['strategy'],r['task']):r for r in result['rows']}
    samples=np.empty((len(gear_ids),len(policies),len(tasks),1024));behavior=np.empty((*samples.shape[:3],7))
    for gi,gid in enumerate(gear_ids):
        for pi,policy in enumerate(policies):
            for qi,task in enumerate(tasks):
                row=lookup[gid,policy,task['id']]
                samples[gi,pi,qi]=row['dps_samples'];behavior[gi,pi,qi]=behavior_vector(row,task['duration_seconds'])
    initial=np.array([s<=set(design['initial_source_ids']) for s in sources])
    return ConfirmationTable(design,gear_ids,sources,[t['id'] for t in tasks],policies,
                             samples,samples.mean(axis=-1),behavior,initial)


def export():
    root=setup_paths();table=load_confirmation();out=root/'artifacts/decisive-value'
    np.savez_compressed(out/'CONFIRMATION_TABLE.npz',samples=table.samples,values=table.values,
                        behavior=table.behavior,initial=table.initial)
    atomic_json(out/'CONFIRMATION_TABLE_META.json',{'gear_ids':table.gear_ids,
        'sources':[sorted(s) for s in table.sources],'tasks':table.task_ids,'policies':table.policies,
        'axes':'gear, policy, task, sample (or behavior feature)',
        'npz_sha256':file_hash(out/'CONFIRMATION_TABLE.npz'),
        'native_new_calls':0,'origin':'Frozen native-confirmation-v1 RESULTS, no fitted or synthetic observations.'})


if __name__=='__main__':export()
