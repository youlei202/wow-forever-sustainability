"""Review-only reuse of a fixed native simultaneous-event certificate.

These interfaces are complete antichains of sufficient and necessary interval
tests, not extra native observations or a seventh timed benchmark method.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from wowfs.paths import canonical_hash

MODES = ('supported', 'possible')


def _items(names, mask):
    return [name for i, name in enumerate(names) if mask >> i & 1]


def complete_publications(certificate):
    """Enumerate once, caching all valid masks before maximality reduction.

    Reduction must consider arbitrary strict supersets: checking only single
    additions misses mutually supporting helpers.
    """
    c = certificate['replay_certificate']; names = c['items']; supports = c['support_masks']
    history = c['history_mask']; n = len(names); m = len(supports)
    if len(set(names)) != n or not n or history < 0 or history >> n:
        raise ValueError('Invalid source identity/history masks')
    if not supports or any(s <= 0 or s >> n for s in supports):
        raise ValueError('Invalid physical support masks')
    q = len(c['compiled_masks']['supported']['gain_good'])
    for mode in MODES:
        data = c['compiled_masks'][mode]
        masks = [data['capbad'], *data['gain_good'], *(z for task in data['ret_bad'] for z in task)]
        if len(data['gain_good']) != q or len(data['ret_bad']) != q or any(len(t) != m for t in data['ret_bad']):
            raise ValueError('Malformed task/row mask dimensions')
        if any(v < 0 or v >> m for v in masks):raise ValueError('Mask extends outside physical rows')
    retention = set(c['enough_retention_mass_masks']); gain = set(c['enough_gain_mass_masks'])
    if any(k < 0 or k >= 1 << q for k in retention | gain):raise ValueError('Invalid task mass mask')
    incident = [[(r, s & ~(1 << i)) for r, s in enumerate(supports) if s >> i & 1] for i in range(n)]
    hactive = sum(1 << r for r, s in enumerate(supports) if s & history == s)
    if not hactive:raise ValueError('History has no physical configuration')

    def assess(p, active, mode, need_gain=True):
        data = c['compiled_masks'][mode]
        if active & data['capbad']:return 'cap'
        source_tasks = [0] * n
        for t, bad in enumerate(data['ret_bad']):
            useful_sources = 0; remaining = active
            while remaining:
                bit = remaining & -remaining; remaining ^= bit; r = bit.bit_length() - 1
                if not active & bad[r]:useful_sources |= supports[r]
            while useful_sources:
                bit = useful_sources & -useful_sources; useful_sources ^= bit
                source_tasks[bit.bit_length() - 1] |= 1 << t
        if any(source_tasks[i] not in retention for i in range(n) if p >> i & 1):return 'retention'
        if need_gain and sum(1 << t for t, good in enumerate(data['gain_good']) if active & good) not in gain:return 'gain'
        return 'valid'

    initial = {mode:assess(history, hactive, mode, False) for mode in MODES}
    if initial != certificate['initial']:raise ValueError('Initial contract differs from source certificate')
    optional = [i for i in range(n) if not history >> i & 1]; size = 1 << len(optional)
    publications = [history] * size; active_rows = [hactive] * size
    valid = {mode:[] for mode in MODES}; totals = {mode:Counter(cap=0, retention=0, gain=0, valid=0) for mode in MODES}
    traces = {mode:hashlib.sha256() for mode in MODES}
    for mask in range(size):
        if mask:
            low = mask & -mask; previous = mask ^ low; i = optional[low.bit_length()-1]
            p = publications[previous] | 1 << i; active = active_rows[previous]
            for r, other in incident[i]:
                if other & p == other:active |= 1 << r
            publications[mask] = p; active_rows[mask] = active
        else:p, active = history, hactive
        for mode in MODES:
            status = assess(p, active, mode); totals[mode][status] += 1
            traces[mode].update(f'{p}:{status}\n'.encode())
            if status == 'valid':valid[mode].append(p)
    if size != certificate['examined_publications']:raise ValueError('Publication domain differs')
    if totals != certificate['rejected_or_accepted_counts']:raise ValueError('Replayed certificate counts differ')
    if {mode:h.hexdigest() for mode,h in traces.items()} != certificate['exhaustive_trace_sha256']:
        raise ValueError('Replayed certificate trace differs')
    if not set(valid['supported']) <= set(valid['possible']):raise ValueError('Sufficient model is not inside necessary model')
    return valid


def maximal_antichain(valid):
    kernels = []
    for p in sorted(set(valid), key=lambda x:(-x.bit_count(), x)):
        if not any(p & k == p for k in kernels):kernels.append(p)
    return kernels


def seal_interface(interface):
    interface.pop('interface_sha256', None)
    interface['interface_sha256'] = canonical_hash(interface)
    return interface


def compile_certificate(certificate, contract=None, source_certificate_sha256=None):
    started = time.perf_counter(); valid = complete_publications(certificate)
    c = certificate['replay_certificate']
    if contract is None:
        contract = dict(world_id=certificate['world_id'],variant=certificate['variant'],
                        items=c['items'],history_mask=c['history_mask'],support_masks=c['support_masks'],
                        bounds_manifest=certificate['bounds_manifest'])
    result = dict(format='wowfs-finite-event-antichains-v1',complete=True,
        world_id=certificate['world_id'],variant=certificate['variant'],items=c['items'],
        history_mask=c['history_mask'],initial=certificate['initial'],contract=contract,
        contract_sha256=canonical_hash(contract),
        source_certificate_sha256=source_certificate_sha256 or canonical_hash(certificate),
        source_hash_kind='file_sha256' if source_certificate_sha256 else 'canonical_certificate_json',
        source_exhaustive_trace_sha256=certificate['exhaustive_trace_sha256'],
        examined_publications=certificate['examined_publications'],
        modes={mode:dict(complete=True,valid_publications=len(valid[mode]),
            maximal_masks=[hex(p) for p in maximal_antichain(valid[mode])]) for mode in MODES},
        additional_alpha=0,new_native_calls=0,evidence_level='REVIEW_UTILITY_ON_EXISTING_EVENT',
        scope='Fixed history, menu, tasks, policy, rules and original simultaneous event. Arbitrary targets inside this menu, including empty target; gain still required. No claim about all release orders.',
        necessary_model_warning='Possible publications satisfy necessary interval tests; they need not be population-feasible.',
        statistical_method=certificate['bounds_manifest'].get('population_method'),
        build_seconds=time.perf_counter()-started)
    return seal_interface(result)


def query_interface(interface, target=(), expected_contract_sha256=None):
    identity = dict(interface); recorded = identity.pop('interface_sha256', None)
    if canonical_hash(identity) != recorded:raise ValueError('Interface content hash mismatch')
    if interface.get('format') != 'wowfs-finite-event-antichains-v1':raise ValueError('Unsupported interface format')
    if canonical_hash(interface['contract']) != interface['contract_sha256']:raise ValueError('Contract hash mismatch')
    if expected_contract_sha256 is not None and expected_contract_sha256 != interface['contract_sha256']:
        raise ValueError('Requested contract differs from compiled interface')
    names = interface['items']; target = frozenset(target)
    if not target <= set(names):raise ValueError('INVALID_QUERY: source outside measured menu: '+repr(sorted(target-set(names))))
    d = sum(1 << names.index(i) for i in target)
    containing = {mode:next((int(k,16) for k in interface['modes'][mode]['maximal_masks'] if int(k,16)&d==d),None) for mode in MODES}
    if interface['initial']['possible'] != 'valid':status='INVALID_INITIAL'
    elif interface['initial']['supported'] != 'valid':status='UNKNOWN_INITIAL'
    elif containing['supported'] is not None:status='YES'
    elif interface.get('complete') and interface['modes']['possible'].get('complete') and containing['possible'] is None:status='NO'
    else:status='UNKNOWN'
    return dict(status=status,target=sorted(target),
        witness=_items(names,containing['supported']) if status=='YES' else None,
        optimistic_completion=_items(names,containing['possible']) if containing['possible'] is not None else None,
        interface_sha256=recorded,contract_sha256=interface['contract_sha256'],
        source_certificate_sha256=interface['source_certificate_sha256'],
        additional_alpha=0,new_native_calls=0,evidence_level='REVIEW_UTILITY_ON_EXISTING_EVENT')


def compile_bundle(bundle, world_id, variant):
    from wowfs.experiments.co_review_check import verify_manifest, inside, read, digest
    bundle = Path(bundle).resolve(); manifest = verify_manifest(bundle)
    native = bundle/'data/native'; analysis = read(native/'ANALYSIS_MANIFEST.json')
    if analysis['mode'] != 'confirm':raise ValueError('Fresh confirmation certificate required')
    registry = native/'CATALOG_REGISTRY.jsonl'
    if digest(registry) != analysis['registry_sha256']:raise ValueError('Registry differs from frozen analysis')
    worlds = {w['world_id']:w for w in map(json.loads,registry.read_text().splitlines()) if w}
    if world_id not in analysis['world_ids'] or world_id not in worlds:raise ValueError('Unknown confirmation world')
    world = worlds[world_id]; definition = dict(world); expected=definition.pop('world_sha256')
    if canonical_hash(definition) != expected:raise ValueError('World contract hash mismatch')
    if variant not in world['universe_variants']:raise ValueError('Menu variant not registered')
    path=inside(bundle,f'data/native/{world_id}/{variant}/CONFIDENCE_CERTIFICATES.json'); certificate=read(path)
    if (certificate['world_id'],certificate['variant']) != (world_id,variant):raise ValueError('Certificate contract differs')
    contract=dict(world=world,variant=variant,rule=analysis['rule'],
        items=certificate['replay_certificate']['items'],history_mask=certificate['replay_certificate']['history_mask'],
        support_masks=certificate['replay_certificate']['support_masks'],bounds_manifest=certificate['bounds_manifest'])
    result=compile_certificate(certificate,contract,digest(path))
    result['provenance']=dict(bundle_root=str(bundle),bundle_manifest_sha256=manifest['manifest_sha256'],
        certificate_relative_path=str(path.relative_to(bundle)),compiled_utc=datetime.now(timezone.utc).isoformat())
    return seal_interface(result)


def _write_new(path, value, forbidden):
    path=Path(path).resolve()
    if any(path==p or path.is_relative_to(p) for p in forbidden):raise ValueError('Output must be outside the immutable bundle/input')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    comp=sub.add_parser('compile');comp.add_argument('--bundle',type=Path,required=True);comp.add_argument('--world',required=True)
    comp.add_argument('--variant',choices=['base','expanded'],required=True);comp.add_argument('--output',type=Path,required=True)
    query=sub.add_parser('query');query.add_argument('--interface',type=Path,required=True);query.add_argument('--target',nargs='*',default=[])
    query.add_argument('--contract-sha256');query.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    if a.command=='compile':
        result=compile_bundle(a.bundle,a.world,a.variant);forbidden=[a.bundle.resolve()]
    else:
        interface=json.loads(a.interface.read_text());result=query_interface(interface,a.target,a.contract_sha256)
        forbidden=[a.interface.resolve()]
        if interface.get('provenance',{}).get('bundle_root'):forbidden.append(Path(interface['provenance']['bundle_root']).resolve())
    _write_new(a.output,result,forbidden)
    print(json.dumps({'output':str(a.output),'status':result.get('status','COMPLETE'),'contract_sha256':result['contract_sha256']}))


if __name__=='__main__':main()
