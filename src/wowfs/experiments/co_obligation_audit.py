"""Secondary source-obligation ablations on an already simultaneous event.

This diagnostic was planned after prediction tables, before confirmation. It
does not alter the primary completion contract and spends no additional alpha:
each obligation is composed entirely from the original finite contrast masks.
"""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time

from wowfs.paths import atomic_json
from wowfs.experiments.r2_native import file_hash


SCOPES=("all","only_history","only_targets","only_helpers",
        "drop_history","drop_targets","drop_helpers","none")


def obligations(scope,p,history,targets):
    helpers=p & ~(history|targets)
    return {"all":p,"only_history":p&history,"only_targets":p&targets,"only_helpers":helpers,
            "drop_history":p&~history,"drop_targets":p&~targets,"drop_helpers":p&~helpers,"none":0}[scope]


def _bits(values):
    answer=0
    for k in values:answer |= 1<<k
    return answer


def audit(certificate):
    """Enumerate all publications for every scope using unchanged exported masks."""
    started=time.perf_counter()
    c=certificate["replay_certificate"]
    items=c["items"]; h=c["history_mask"]; supports=c["support_masks"]
    queries=certificate["queries"]; targets=c["query_masks"]
    optional=[k for k in range(len(items)) if not(h>>k&1)]
    ret_allowed=set(c["enough_retention_mass_masks"]);gain_allowed=set(c["enough_gain_mass_masks"])
    q=len(c["compiled_masks"]["possible"]["gain_good"])
    witnesses=[{scope:{mode:None for mode in ("supported","possible")} for scope in SCOPES} for _ in queries]
    counts=[{scope:{mode:{r:0 for r in ("cap","gain","retention","valid")} for mode in ("supported","possible")}
             for scope in SCOPES} for _ in queries]
    traces=[{scope:{mode:hashlib.sha256() for mode in ("supported","possible")} for scope in SCOPES} for _ in queries]
    for mask in range(1<<len(optional)):
        p=h|_bits(optional[k] for k in range(len(optional)) if mask>>k&1)
        active=_bits(r for r,s in enumerate(supports) if s&p==s)
        relevant=[qi for qi,d in enumerate(targets) if d&p==d]
        if not relevant:continue
        for mode,data in c["compiled_masks"].items():
            if active&data["capbad"]:common="cap"
            elif _bits(t for t in range(q) if active&data["gain_good"][t]) not in gain_allowed:common="gain"
            else:common=None
            failed=0
            if common is None:
                useful=[_bits(r for r in range(len(supports)) if active>>r&1 and not(active&data["ret_bad"][t][r])) for t in range(q)]
                for k in range(len(items)):
                    if not(p>>k&1):continue
                    incident=_bits(r for r,s in enumerate(supports) if s>>k&1)
                    if _bits(t for t in range(q) if useful[t]&incident) not in ret_allowed:failed |= 1<<k
            for qi in relevant:
                for scope in SCOPES:
                    status=common or ("retention" if failed&obligations(scope,p,h,targets[qi]) else "valid")
                    counts[qi][scope][mode][status]+=1
                    traces[qi][scope][mode].update(f"{p}:{status}\n".encode())
                    old=witnesses[qi][scope][mode]
                    if status=="valid" and (old is None or p.bit_count()<old.bit_count()):witnesses[qi][scope][mode]=p
    out=[]
    for qi,query in enumerate(queries):
        scopes={}
        for scope in SCOPES:
            w=witnesses[qi][scope]
            if certificate["initial"]["possible"]!="valid":status="INVALID_INITIAL"
            elif certificate["initial"]["supported"]!="valid":status="UNKNOWN_INITIAL"
            elif w["supported"] is not None:status="YES"
            elif w["possible"] is None:status="NO"
            else:status="UNKNOWN"
            scopes[scope]=dict(status=status,
                supported_witness=[i for k,i in enumerate(items) if w["supported"] is not None and w["supported"]>>k&1] if w["supported"] is not None else None,
                possible_witness=[i for k,i in enumerate(items) if w["possible"] is not None and w["possible"]>>k&1] if w["possible"] is not None else None,
                exhaustive_counts=counts[qi][scope],trace_sha256={mode:v.hexdigest() for mode,v in traces[qi][scope].items()})
        if scopes["all"]["status"]!=query["status"]:raise AssertionError("primary certificate disagreement")
        plain={scope:value["status"] for scope,value in scopes.items()}
        isno=plain["all"]=="NO";valueyes=plain["none"]=="YES"
        labels=dict(retention_essential=isno and valueyes,
                    legacy_necessary_for_obstruction=isno and plain["drop_history"]=="YES",
                    targets_necessary_for_obstruction=isno and plain["drop_targets"]=="YES",
                    helpers_necessary_for_obstruction=isno and plain["drop_helpers"]=="YES",
                    legacy_alone_sufficient=valueyes and plain["only_history"]=="NO",
                    targets_alone_sufficient=valueyes and plain["only_targets"]=="NO",
                    helpers_alone_sufficient=valueyes and plain["only_helpers"]=="NO")
        out.append(dict(query_id=query["query_id"],required=query["required"],scopes=scopes,diagnostic_labels=labels))
    return dict(world_id=certificate["world_id"],variant=certificate["variant"],queries=out,
                original_bounds_manifest=certificate["bounds_manifest"],elapsed_seconds=time.perf_counter()-started,
                additional_alpha=0,evidence_level="SECONDARY_FRESH_EVENT_CONSEQUENCE",
                interpretation="Relaxed source-obligation contracts; labels can overlap. Main completion still requires every published source.")


def register(output,predictions,projection_predictions=None):
    output=Path(output)
    if output.exists():raise ValueError("protocol already frozen")
    value=dict(created_utc=datetime.now(timezone.utc).isoformat(),
               source_sha256=file_hash(Path(__file__)),scopes=list(SCOPES),
               stage="Planned after examining prediction tables and before independent confirmation",
               primary_prediction_manifest_sha256=file_hash(Path(predictions)/"ANALYSIS_MANIFEST.json"),
               projection_prediction_manifest_sha256=file_hash(Path(projection_predictions)/"PROJECTION_MANIFEST.json") if projection_predictions else None,
               purpose="Separate threatened legacy obligations, required-target self-retention, and helper self-retention; avoid labelling every retention-active NO as legacy obstruction",
               design="All registered main base/expanded queries, no outcome-selected omission; same H/D, cap, gain, physical domain and finite event",
               labels="Necessity: primary NO + deleting this obligation group gives supported YES. Sufficiency: value-only YES + this obligation group alone gives supported NO. Mixed and overlapping causes retained.",
               alpha_additional=0,alpha_reason="Only deterministic conjunction/disjunction of already simultaneous cap/gain/retention contrasts",
               no_population_prevalence_claim=True)
    atomic_json(output,value)
    return value


def run(analysis,protocol,output):
    import csv
    from collections import Counter
    analysis,protocol,output=map(Path,(analysis,protocol,output))
    spec=json.loads(protocol.read_text())
    if spec["source_sha256"]!=file_hash(Path(__file__)):raise ValueError("diagnostic source differs from frozen protocol")
    if output.exists():raise ValueError("new output directory required")
    output.mkdir(parents=True)
    atomic_json(output/"MANIFEST.json",dict(protocol_sha256=file_hash(protocol),
                confirmation_manifest_sha256=file_hash(analysis/"ANALYSIS_MANIFEST.json"),created_utc=datetime.now(timezone.utc).isoformat()))
    flat=[]
    for path in sorted(analysis.glob("*/**/CONFIDENCE_CERTIFICATES.json")):
        certificate=json.loads(path.read_text())
        result=audit(certificate)
        result["original_certificate_sha256"]=file_hash(path)
        dest=output/result["world_id"]/result["variant"];dest.mkdir(parents=True)
        atomic_json(dest/"OBLIGATION_AUDIT.json",result)
        for query in result["queries"]:
            flat.append(dict(world_id=result["world_id"],variant=result["variant"],query_id=query["query_id"],
                 required=query["required"],**{s:v["status"] for s,v in query["scopes"].items()},**query["diagnostic_labels"]))
    atomic_json(output/"OBLIGATION_DECISIONS.json",flat)
    base=[r for r in flat if r["variant"]=="base"]
    labels=[k for k in base[0] if k.endswith("obstruction") or k.endswith("sufficient") or k=="retention_essential"] if base else []
    atomic_json(output/"SUMMARY.json",dict(base_queries=len(base),all_nested_query_rows=len(flat),
                 base_primary_statuses=dict(Counter(r["all"] for r in base)),
                 base_label_counts={k:sum(r[k] for r in base) for k in labels},
                 affected_base_catalog_counts={k:len({r["world_id"] for r in base if r[k]}) for k in labels},
                 warning="Labels overlap; targets, menus and strata are not a probability sample of all content"))
    if flat:
        with (output/"OBLIGATION_DECISIONS.csv").open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(flat[0]));writer.writeheader()
            for row in flat:writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
    return flat


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    freeze=sub.add_parser("register");freeze.add_argument("--output",required=True);freeze.add_argument("--predictions",required=True);freeze.add_argument("--projection-predictions")
    execute=sub.add_parser("run");execute.add_argument("--analysis",required=True);execute.add_argument("--protocol",required=True);execute.add_argument("--output",required=True)
    a=p.parse_args()
    if a.command=="register":register(a.output,a.predictions,a.projection_predictions)
    else:run(a.analysis,a.protocol,a.output)


if __name__=="__main__":main()
