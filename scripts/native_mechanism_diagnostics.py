#!/usr/bin/env python3
"""Descriptive actual-action/resource/aura audit; never infer casts from an APL."""
from collections import defaultdict,Counter
import argparse
import csv
import hashlib
import json
from pathlib import Path


PROBES=[
 ("warrior_weapon_skill","Whirlwind executed","action","spellId",1680,"casts",None),
 ("warrior_weapon_skill","Bloodthirst executed","action","spellId",23894,"casts",None),
 ("warrior_weapon_skill","Native attack actions","action","otherId","OtherActionAttack","casts",None),
 ("paladin_seal_twisting","Seal of Command cast","action","spellId",20920,"casts",None),
 ("paladin_seal_twisting","Seal of Righteousness cast","action","spellId",20293,"casts",None),
 ("paladin_seal_twisting","Command proc damage","action","spellId",20424,"damage",None),
 ("paladin_seal_twisting","Righteousness proc damage","action","spellId",25713,"damage",None),
 ("mage_timed_resources","Second Wind activation","action","spellId",15604,"casts",11819),
 ("mage_timed_resources","Second Wind actual mana gain","resource","spellId",15604,"actualGain",11819),
 ("mage_timed_resources","Draconic Infused Emblem activation","action","itemId",22268,"casts",22268),
 ("mage_timed_resources","Talisman of Ephemeral Power activation","action","itemId",18820,"casts",18820),
 ("mage_timed_resources","Burst of Knowledge activation","action","itemId",11832,"casts",11832),
 ("mage_timed_resources","Blue Dragon aura uptime","aura","spellId",23688,"uptimeSecondsAvg",19288),
 ("mage_timed_resources","Fire Ruby activation","action","itemId",20036,"casts",20036),
 ("mage_timed_resources","Fire Ruby actual mana gain","resource","itemId",20036,"actualGain",20036),
 ("mage_timed_resources","Hazzarah charm activation","action","itemId",19959,"casts",19959),
 ("druid_passive_resources","Wrath executed","action","spellId",9912,"casts",None),
 ("druid_passive_resources","Guarded Starfire executed","action","spellId",25298,"casts",None),
 ("druid_passive_resources","Moonfire executed","action","spellId",9835,"casts",None),
 ("druid_passive_resources","Insect Swarm executed","action","spellId",24977,"casts",None),
 ("druid_passive_resources","Mana regeneration actual gain","resource","otherId","OtherActionManaRegen","actualGain",None),
]


def observed(row,kind,field,value,metric):
    if kind=="action":
        prefix=f"{field}:{value}"
        return sum(v.get(metric,0) for k,v in row["actions"].items() if k==prefix or k.startswith(prefix+"/"))
    values=row["resources"] if kind=="resource" else row["auras"]
    return sum(v.get(metric,0) for v in values if v["id"].get(field)==value)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--batch",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();batch=Path(a.batch);output=Path(a.output)
    if output.exists():raise ValueError("new output directory required")
    raw=json.loads(batch.read_text())
    if raw["errors"] or raw["status"]!="completed":raise ValueError("complete batch required")
    rows=raw["rows"];worlds=defaultdict(list)
    for row in rows:worlds[row["world_id"]].append(row)
    assert len(worlds)==16 and len(rows)==1712 and {r["iterations"] for r in rows}=={16384}
    probes=[];events=[]
    for wid,unit in sorted(worlds.items()):
        first=unit[0]
        for stratum,label,kind,field,value,metric,item in PROBES:
            if first["mechanism_id"]!=stratum:continue
            eligible=[r for r in unit if item is None or item in r["native_source_item_ids"]]
            values=[observed(r,kind,field,value,metric) for r in eligible]
            probes.append(dict(world_id=wid,stratum=stratum,**{k:first[k] for k in ("class","race","faction","context_id")},
                 indicator=label,event_kind=kind,event_id=f"{field}:{value}",native_metric=metric,
                 total_measured_cells=len(unit),eligible_equipped_cells=len(eligible),
                 positive_cells=sum(x>0 for x in values),nonzero_cells=sum(x!=0 for x in values),
                 min_native_average=min(values) if values else None,max_native_average=max(values) if values else None,
                 evidence="actual native output summary" if eligible else "item absent from this registered menu",
                 causal_interpretation="execution diagnostic, not an isolated intervention or mechanism effect estimate"))
        observed_events=defaultdict(list)
        for ci,row in enumerate(unit):
            for event,v in row["actions"].items():
                for metric in ("casts","damage"):observed_events["action",event,metric].append((ci,v[metric]))
            for kind,key,metrics in (("resource","resources",("events","gain","actualGain")),("aura","auras",("procsAvg","uptimeSecondsAvg"))):
                for event in row[key]:
                    identity=json.dumps(event["id"],sort_keys=True,separators=(",",":"))+":"+event.get("type","")
                    for metric in metrics:
                        if metric in event:observed_events[kind,identity,metric].append((ci,event[metric]))
        for (kind,event,metric),values in sorted(observed_events.items()):
            percell=defaultdict(float)
            for ci,value in values:percell[ci]+=value
            events.append(dict(world_id=wid,stratum=first["mechanism_id"],kind=kind,event=event,metric=metric,
                               total_measured_cells=len(unit),reported_cells=len(percell),
                               positive_cells=sum(v>0 for v in percell.values()),negative_cells=sum(v<0 for v in percell.values()),
                               min_reported_average=min(percell.values()),max_reported_average=max(percell.values())))
    output.mkdir(parents=True)
    for name,values in (("NativeMechanismDiagnostics",probes),("AllNativeEventDiagnostics",events)):
        (output/(name+".json")).write_text(json.dumps(values,indent=2,sort_keys=True)+"\n")
        with (output/(name+".csv")).open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
    summary=dict(native_result_sha256=hashlib.sha256(batch.read_bytes()).hexdigest(),physical_cells=len(rows),
                 battles=sum(r["iterations"] for r in rows),classes=sorted({r["class"] for r in rows}),
                 actual_contexts=sorted({r["context_id"] for r in rows}),
                 cells_per_stratum=dict(Counter(r["mechanism_id"] for r in rows)),
                 warning="Source/APL presence never counts as execution; positive cast/damage/resource/aura records establish execution only. No causal mechanism effect, optimal policy, live acquisition completeness, or racial-mechanism independence is inferred.")
    (output/"SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
