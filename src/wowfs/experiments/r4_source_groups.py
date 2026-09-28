"""Descriptive source grouping from frozen metadata, never a replacement for item L."""
import json
from collections import defaultdict
import numpy as np
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r2_sequence_analysis import write_csv

def main():
    root=setup_paths();out=root/'artifacts/r4-foundational-discovery';base=json.loads((out/'BASE_ECOSYSTEMS.json').read_text())
    groups=defaultdict(set);unknown=[]
    for key,item in base['item_metadata'].items():
        if not item.get('sources'):unknown.append(key)
        for source in item.get('sources')or[]:
            for typ,record in source.items():
                if typ=='drop':
                    for field in ['zoneId','npcId']:
                        if record.get(field):groups['acquisition:'+field+':'+str(record[field])].add(key)
                elif typ=='quest'and record.get('id'):groups['acquisition:quest:'+str(record['id'])].add(key)
                elif typ=='crafted'and record.get('profession'):groups['acquisition:profession:'+str(record['profession'])].add(key)
                else:groups['acquisition:'+typ+':'+json.dumps(record,sort_keys=True)].add(key)
    for family in base['candidate_design_families']:groups['curriculum:'+family['id']].update(map(str,family['item_ids']))
    rows=[]
    for e in load_ecologies(root/'runs/r4-foundational-discovery/baseline-v1'):
        best=e.values.max(axis=1);safe=np.all(best<=e.cap,axis=1);after=best[safe].max(axis=0)
        for key,items in groups.items():
            owns=np.array([bool(items&set(map(str,g.values())))for g in e.gears]);old=owns&e.initial
            if not np.any(old):continue
            before_mass=float(np.mean(np.any(best[old]>=e.scale-.05*e.scale,axis=0)))
            if before_mass<.05:continue
            new=owns&safe;after_mass=float(np.mean(np.any(best[new]>=after-.05*e.scale,axis=0)))if np.any(new)else 0.
            rows.append({'ecology':e.pool['id'],'race':e.race,'group':key,'member_item_ids':sorted(items),
                'initial_mass':before_mass,'all_safe_terminal_mass':after_mass,'retained':after_mass>=.05,
                'scope':'Secondary descriptive grouping from frozen database/curriculum; fullgear membership; does not replace per-item L or establish actual live drop provenance'})
    atomic_json(out/'SOURCE_GROUP_MAP.json',{'groups':{k:sorted(v)for k,v in groups.items()},'items_without_acquisition_metadata':unknown,
        'timing':'Original acquisition records and curricula frozen before native runs; deterministic grouping calculated afterward, no outcome-based clustering.',
        'unknown_handling':'Unknown provenance omitted from acquisition grouping, not merged into a fake shared source.',
        'warning':'Embedded community-engine metadata, not independently verified current live drops; zone/NPC/quest/profession scopes overlap.'})
    write_csv(out/'SOURCE_GROUP_DIAGNOSTICS.csv',rows)

if __name__=='__main__':main()
