#!/usr/bin/env python3
"""Materialize descriptive native counts without changing frozen decisions."""
from collections import Counter
import argparse,csv,json
from pathlib import Path


def load(path):return json.loads(Path(path).read_text())


def write_csv(path,rows):
    if not rows:return
    with Path(path).open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in row.items()})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--native-root",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();root=Path(a.native_root);output=Path(a.output)
    if output.exists():raise ValueError("new summary output directory required")
    confirmation=root/"confirmation-v1";decisions=load(confirmation/"NATIVE_DECISIONS.json")
    expansions=load(confirmation/"CATALOG_EXPANSION_RESULTS.json")
    projections=load(root/"projection-confirmation-v1/NATIVE_TASK_PROJECTION.json")
    obligations=load(root/"obligation-audit-v1/SUMMARY.json")
    witnesses=load(root/"FROZEN_WITNESS_RECHECK.json")
    mechanism=load(root/"mechanism-diagnostics-v1/SUMMARY.json")
    negative=[];summary={};catalogs=[]
    for variant in ("base","expanded"):
        rows=[r for r in decisions if r["variant"]==variant]
        witness_rows=[r for r in witnesses if r["variant"]==variant]
        methods=Counter();needs_helpers=0
        for world in sorted({r["world_id"] for r in rows}):
            exact=load(confirmation/world/variant/"EXACT_QUERIES.json")
            heuristics=load(confirmation/world/variant/"HEURISTICS.json")
            methods.update({method:sum(h["method"]==method and h["status"]=="YES" for h in heuristics)
                            for method in sorted({h["method"] for h in heuristics})})
            helpers=sum(q["mean_answer"]["status"]=="YES" and not q["direct_release"]["valid"] for q in exact["queries"])
            needs_helpers+=helpers
            if variant=="base":
                unit=[r for r in rows if r["world_id"]==world]
                first=unit[0]
                catalogs.append(dict(world_id=world,stratum=first["stratum"],**{k:first[k] for k in ("class","race","faction")},
                    queries=len(unit),prediction_yes=sum(r["development_prediction"]=="YES" for r in unit),
                    mean_yes=sum(r["fresh_mean_answer"]=="YES" for r in unit),
                    confirmed_yes=sum(r["confidence_status"]=="YES" for r in unit),
                    confirmed_no=sum(r["confidence_status"]=="NO" for r in unit),
                    unresolved=sum(r["confidence_status"].startswith("UNKNOWN") for r in unit),
                    invalid_initial=sum(r["confidence_status"]=="INVALID_INITIAL" for r in unit),
                    predicted_mean_answer_changes=sum(r["prediction_changed_on_fresh_mean"] for r in unit),
                    retention_essential_confirmed=sum(r["retention_decision_active_confidence"] for r in unit),
                    mean_yes_requiring_helpers=helpers))
        summary[variant]=dict(query_rows=len(rows),independent_catalogues=len({r["world_id"] for r in rows}),
            mean_answers=dict(Counter(r["fresh_mean_answer"] for r in rows)),
            confidence_answers=dict(Counter(r["confidence_status"] for r in rows)),
            answer_prediction_changes=sum(r["prediction_changed_on_fresh_mean"] for r in rows),
            predicted_yes_witnesses=len(witness_rows),
            frozen_witnesses_fresh_mean_invalid=sum(not r["fresh_mean_check"]["valid"] for r in witness_rows),
            frozen_witnesses_confidence_supported=sum(r["confidence_check"]["valid"] for r in witness_rows),
            frozen_witnesses_statistically_unresolved=sum(not r["confidence_check"]["valid"] for r in witness_rows),
            retention_essential_certified=sum(r["retention_decision_active_confidence"] for r in rows),
            mean_yes_requiring_helpers=needs_helpers,heuristic_supported_mean_yes=dict(methods),
            inference_warning="Query counts are descriptive correlated targets, not independent binomial trials or an estimate of content-wide prevalence")
    for row in decisions:
        common={k:row[k] for k in ("world_id","variant","query_id")}
        if row["fresh_mean_answer"]=="NO":negative.append(dict(kind="EXACT_MEAN_TABLE_NEGATIVE",**common,status="NO",detail="Complete same-menu exact mean-table decision; population status is "+row["confidence_status"]))
        if row["confidence_status"].startswith("UNKNOWN"):
            negative.append(dict(kind="POPULATION_UNRESOLVED",**common,status=row["confidence_status"],detail="Fixed N retained; no sample extension or conversion to NO"))
        if row["prediction_witness_confidence_check"] and not row["prediction_witness_confidence_check"]["valid"]:
            negative.append(dict(kind="FROZEN_POSITIVE_WITNESS_UNRESOLVED",**common,status="UNKNOWN",detail=row["prediction_witness_confidence_check"]))
    for row in projections:
        if row["mean_decision_changed"]:
            negative.append(dict(kind="TASK_PROJECTION_MEAN_FLIP_NOT_JOINTLY_CERTIFIED",**{k:row[k] for k in ("world_id","variant","query_id")},status="UNKNOWN",
                                 detail={k:row[k] for k in ("full_Q4_mean","projected_Q2_mean","full_Q4_confidence","projected_Q2_confidence")}))
    for row in witnesses:
        if not row["fresh_mean_check"]["valid"]:
            negative.append(dict(kind="FROZEN_POSITIVE_WITNESS_FRESH_MEAN_FAILURE",
                                 **{k:row[k] for k in ("world_id","variant","query_id")},status="INVALID_WITNESS",
                                 detail={"frozen_items":row["frozen_witness"],"fresh_mean_check":row["fresh_mean_check"],
                                         "query_confidence_status":row["query_confidence_status"]}))
    base_projection=[r for r in projections if r["variant"]=="base"]
    summary.update(alpha=dict(main=.04,per_catalog=.0025,units=16,reserved_secondary_unspent=.01,
                     old_campaign_alpha=.05,old_and_new_main_union_bound=.09,
                     warning="Paired-t finite-family approximation, not distribution-free; old plus new is not a renewed global .05 guarantee"),
                   sampling=mechanism,obligation_diagnostics=obligations,
                   candidate_expansion=dict(registered_nested_menus=8,paired_queries=len(expansions),
                     mean_transitions={f"{a}->{b}":n for (a,b),n in Counter((r["base_mean"],r["expanded_mean"]) for r in expansions).items()},
                     confidence_transitions={f"{a}->{b}":n for (a,b),n in Counter((r["base_confidence"],r["expanded_confidence"]) for r in expansions).items()},
                     interpretation="Optional candidates; common old rows, reference, rules and seeds. These 64 pairs are not additional independent menus."),
                   task_projection=dict(registered_catalogs=4,base_queries=len(base_projection),
                     fresh_mean_flips=sum(r["mean_decision_changed"] for r in base_projection),
                     projected_answer_prediction_changes=sum(r["projected_prediction"]!=r["projected_Q2_mean"] for r in base_projection),
                     jointly_confirmed_opposite_answers=sum({r["full_Q4_confidence"],r["projected_Q2_confidence"]}=={"YES","NO"} for r in base_projection),
                     confidence_transitions={f"{a}->{b}":n for (a,b),n in Counter((r["full_Q4_confidence"],r["projected_Q2_confidence"]) for r in base_projection).items()}))
    output.mkdir(parents=True)
    tolerance=root/"secondary-tolerance-v1/SUMMARY.json"
    if tolerance.exists():summary["secondary_tolerance"]=load(tolerance)
    (output/"NATIVE_EVIDENCE_SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    write_csv(output/"BASE_CATALOG_SUMMARY.csv",catalogs)
    write_csv(output/"NEGATIVE_AND_UNRESOLVED.csv",negative)
    write_csv(output/"CANDIDATE_EXPANSION_COMPARISONS.csv",expansions)
    write_csv(output/"FROZEN_WITNESS_COMPARISONS.csv",witnesses)


if __name__=="__main__":main()
