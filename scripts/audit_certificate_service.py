#!/usr/bin/env python3
"""Compile all registered menus, then challenge arbitrary-target reuse."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

from wowfs.experiments import co_certificate_service
from wowfs.experiments.co_certificate_service import compile_bundle,query_interface
from wowfs.experiments.co_native_analysis import verify_replay_publication


def independent_full_mask_oracle(certificate):
    """Direct witness definition for every P; no service compilation code."""
    c=certificate['replay_certificate'];names=c['items'];h=c['history_mask'];size=1<<len(names)
    possible={mode:bytearray(size) for mode in ('supported','possible')};valid_counts={}
    for mode,exists in possible.items():
        for p in range(size):
            if p&h!=h:continue
            publication=[name for i,name in enumerate(names) if p>>i&1]
            if verify_replay_publication(certificate,publication,mode)['valid']:exists[p]=1
        valid_counts[mode]=sum(exists)
        # Exact subset closure of every valid publication, independent of the
        # stored maximal antichain. It represents all 2^n target questions.
        for bit in range(len(names)):
            flag=1<<bit
            for mask in range(size):
                if not mask&flag and exists[mask|flag]:exists[mask]=1
    return possible,valid_counts


def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve().is_relative_to(a.bundle.resolve()):raise ValueError('Audit output must be outside immutable bundle')
    a.output.mkdir(parents=True,exist_ok=False)
    rows=[];all_target_checks=[];serialized_bytes=0
    paths=sorted((a.bundle/'data/native').glob('*/**/CONFIDENCE_CERTIFICATES.json'))
    for path in paths:
        c=json.loads(path.read_text());interface=compile_bundle(a.bundle,c['world_id'],c['variant'])
        target=a.output/'interfaces'/c['world_id']/(c['variant']+'.json');target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(interface,indent=2,sort_keys=True)+'\n');serialized_bytes+=target.stat().st_size
        # Reload the actual representation before any query audit.
        interface=json.loads(target.read_text())
        for query in c['queries']:
            result=query_interface(interface,query['required'])
            assert result['status']==query['status'],(c['world_id'],c['variant'],query,result)
            if result['status']=='YES':assert verify_replay_publication(c,result['witness'])['valid']
            rows.append(dict(world_id=c['world_id'],variant=c['variant'],query_id=query['query_id'],status=result['status']))
        if c['world_id'] in ('co_warrior_weapon_skill__validation_01','co_mage_timed_resources__validation_00'):
            oracle,valid_counts=independent_full_mask_oracle(c);names=interface['items'];counts={}
            for mask in range(1<<len(names)):
                target=[name for i,name in enumerate(names) if mask>>i&1]
                expected='YES' if oracle['supported'][mask] else 'NO' if not oracle['possible'][mask] else 'UNKNOWN'
                result=query_interface(interface,target)
                assert result['status']==expected,(c['world_id'],c['variant'],target,expected,result)
                counts[expected]=counts.get(expected,0)+1
            assert all(interface['modes'][m]['valid_publications']==valid_counts[m] for m in oracle)
            all_target_checks.append(dict(world_id=c['world_id'],variant=c['variant'],
                target_masks_checked=1<<len(names),valid_publication_counts=valid_counts,target_status_counts=counts))
        print(json.dumps({'compiled':c['world_id'],'variant':c['variant'],'kernels':{m:len(v['maximal_masks']) for m,v in interface['modes'].items()}}),flush=True)
    assert len(paths)==24 and len(rows)==192 and len(all_target_checks)==4
    receipt=dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),menu_contracts=24,
        registered_answers_replayed=192,all_target_mask_checks=all_target_checks,
        all_target_masks_total=sum(r['target_masks_checked'] for r in all_target_checks),
        interfaces_serialized_bytes=serialized_bytes,new_native_calls=0,additional_alpha=0,
        scope='Review utility and correctness demonstration. Arbitrary symbolic queries reuse the same finite event; no new registered evidence, no seventh performance baseline.',
        source_sha256={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in
            [Path(__file__),Path(co_certificate_service.__file__)]})
    (a.output/'REGISTERED_REPLAY.json').write_text(json.dumps(rows,indent=2)+'\n')
    (a.output/'SERVICE_AUDIT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
