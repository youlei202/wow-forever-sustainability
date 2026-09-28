"""Load the compact, portable read-only R4 tensor export without native code."""
import json
from pathlib import Path
import numpy as np
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_data import Ecology


def load_export(folder, pool_ids=None, races=None, verify=True):
    """Reconstruct the same Ecology API used by the original cached screens."""
    folder=Path(folder);manifest=json.loads((folder/'MANIFEST.json').read_text())
    selected=set(pool_ids) if pool_ids is not None else None
    race_set=set(races) if races is not None else None
    result=[]
    for record in manifest['contexts']:
        if selected is not None and record['pool'] not in selected:continue
        if race_set is not None and record['race'] not in race_set:continue
        tensor=folder/record['tensor_file'];metadata=folder/record['metadata_file']
        if verify and (file_hash(tensor)!=record['tensor_sha256'] or file_hash(metadata)!=record['metadata_sha256']):
            raise ValueError('Exported native-derived tensor or metadata hash mismatch')
        meta=json.loads(metadata.read_text())
        with np.load(tensor,allow_pickle=False) as values:
            arrays={k:values[k].copy() for k in values.files}
        result.append(Ecology(meta['pool'],meta['race'],meta['tasks'],meta['policies'],
            meta['gear_ids'],meta['gears'],arrays['values'],arrays['behavior'],arrays['samples'],
            [set(s) for s in meta['sources']],arrays['initial'],tuple(meta['new_items']),
            arrays['scale'],arrays['cap'],tuple(meta['protected_sources']),meta['config']))
    return result


def previous_subset_masks(folder, ecology):
    """Return recorded old solver masks needed by value_history.screen."""
    path=Path(folder)/(ecology.pool['id']+'__'+ecology.race+'.cached_subsets.json')
    return json.loads(path.read_text()) if path.exists() else {}
