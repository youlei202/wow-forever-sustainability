"""Predeclared Q=4 to Q=2 task-contract challenge, retaining the original event.

Keep registered task indices [0,3], use weights [1/2,1/2], and preserve H, D,
rows and absolute per-task thresholds. This is not optional-item monotonicity.
Confirmation slices the original Q=4 bounds without recomputing a critical
value or reducing its family size.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path

import numpy as np

from wowfs.experiments.co_catalogs import load_registry
from wowfs.experiments.co_native_analysis import exact_queries,certify_queries,verify_replay_publication
from wowfs.experiments.r2_native import file_hash
from wowfs.paths import atomic_json,canonical_hash

TASK_INDICES=(0,3)


def project(world,moments,bounds=None):
    if len(world["tasks"])!=4:raise ValueError("projection requires registered Q=4 world")
    projected=deepcopy(world)
    projected["tasks"]=[deepcopy(world["tasks"][i]) for i in TASK_INDICES]
    projected["task_weights"]=[.5,.5]
    projected["parent_world_sha256"]=world["world_sha256"]
    projected["task_projection"]={"indices":list(TASK_INDICES),"weights":["1/2","1/2"],
                                  "contract":"different allowed task distribution; no monotonicity assertion"}
    projected.pop("world_sha256")
    projected["world_sha256"]=canonical_hash(projected)
    reduced=deepcopy(moments)
    reduced["world_sha256"]=projected["world_sha256"]
    reduced["means"]=np.asarray(moments["means"])[list(TASK_INDICES)]
    reduced["covariance"]=np.asarray(moments["covariance"])[list(TASK_INDICES)]
    reduced["reference_indices"]=[moments["reference_indices"][i] for i in TASK_INDICES]
    reduced["domain"]["task_ids"]=[moments["domain"]["task_ids"][i] for i in TASK_INDICES]
    sliced=None
    if bounds is not None:
        sliced={k:np.asarray(v)[list(TASK_INDICES)] for k,v in bounds.items() if k!="manifest"}
        sliced["manifest"]=deepcopy(bounds["manifest"])
        sliced["manifest"]["projection_derivation"]={"original_task_indices":list(TASK_INDICES),
                 "new_weights":["1/2","1/2"],"original_family_size_and_critical_retained":True,
                 "additional_alpha":0,"reason":"No new random coefficient vector; deterministic reuse of a subset of the original simultaneous event"}
    return projected,reduced,sliced


def run(registry,analysis,thresholds,output,*,mode,predictions=None):
    import csv
    registry,analysis,thresholds,output=map(Path,(registry,analysis,thresholds,output))
    if output.exists():raise ValueError("new output directory required")
    if mode not in ("predict","confirm"):raise ValueError("unknown mode")
    if mode=="confirm" and predictions is None:raise ValueError("frozen projection predictions required")
    rule=json.loads(thresholds.read_text())["rule"]
    worlds=[w for w in load_registry(registry) if w["split"]=="validation" and len(w["tasks"])==4]
    output.mkdir(parents=True)
    atomic_json(output/"PROJECTION_MANIFEST.json",dict(mode=mode,created_utc=datetime.now(timezone.utc).isoformat(),
                source_sha256=file_hash(Path(__file__)),registry_sha256=file_hash(registry),thresholds_sha256=file_hash(thresholds),
                original_analysis_manifest_sha256=file_hash(analysis/"ANALYSIS_MANIFEST.json"),
                source_task_indices=list(TASK_INDICES),projected_weights=["1/2","1/2"],
                world_ids=[w["world_id"] for w in worlds],contract="Different task distribution; not candidate expansion",
                family_coverage="Original Q=4 finite event retained unchanged; no additional alpha" if mode=="confirm" else "Prediction only"))
    rows=[]
    for world in worlds:
        original=analysis/world["world_id"]
        moments=json.loads((original/"MOMENTS_READABLE.json").read_text())
        moments["domain"]["pairs"]=[tuple(p) for p in moments["domain"]["pairs"]]
        bounds=None
        if mode=="confirm":
            with np.load(original/"BOUNDS.npz") as archive:bounds={k:archive[k] for k in archive.files}
            bounds["manifest"]=json.loads((original/"BOUNDS_MANIFEST.json").read_text())
        w,m,b=project(world,moments,bounds)
        for variant in world["universe_variants"]:
            path=output/world["world_id"]/variant;path.mkdir(parents=True)
            answer=exact_queries(w,m,rule,variant)
            atomic_json(path/"EXACT_QUERIES.json",answer)
            full=json.loads((original/variant/"EXACT_QUERIES.json").read_text())
            cert=certify_queries(w,m,b,rule,variant) if b is not None else None
            if cert is not None:
                atomic_json(path/"CONFIDENCE_CERTIFICATES.json",cert)
                full_cert=json.loads((original/variant/"CONFIDENCE_CERTIFICATES.json").read_text())
                predicted=json.loads((Path(predictions)/world["world_id"]/variant/"EXACT_QUERIES.json").read_text())
            for qi,(small,large) in enumerate(zip(answer["queries"],full["queries"])):
                pred=predicted["queries"][qi] if cert else small
                pw=pred["mean_answer"].get("items")
                rows.append(dict(world_id=world["world_id"],stratum=world["stratum"],variant=variant,
                    query_id=small["query_id"],required=small["required"],
                    full_Q4_mean=large["mean_answer"]["status"],projected_Q2_mean=small["mean_answer"]["status"],
                    full_Q4_confidence=full_cert["queries"][qi]["status"] if cert else "NOT_RUN",
                    projected_Q2_confidence=cert["queries"][qi]["status"] if cert else "NOT_RUN",
                    projected_prediction=pred["mean_answer"]["status"],
                    projected_prediction_witness_check=verify_replay_publication(cert,pw) if cert and pw else None,
                    mean_decision_changed=large["mean_answer"]["status"]!=small["mean_answer"]["status"],
                    evidence_level="FRESH_CONFIRMATION_CONSEQUENCE" if cert else "EXPLORATORY_PREDICTION"))
    atomic_json(output/"NATIVE_TASK_PROJECTION.json",rows)
    fields=[k for k in rows[0] if k!="projected_prediction_witness_check"] if rows else []
    with (output/"NATIVE_TASK_PROJECTION.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(row[k]) if isinstance(row[k],list) else row[k] for k in fields})
    return rows


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("registry","analysis","thresholds","output"):p.add_argument("--"+key,required=True)
    p.add_argument("--mode",choices=("predict","confirm"),required=True)
    p.add_argument("--predictions")
    a=p.parse_args();run(a.registry,a.analysis,a.thresholds,a.output,mode=a.mode,predictions=a.predictions)


if __name__=="__main__":main()
