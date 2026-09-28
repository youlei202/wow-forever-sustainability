"""Complete native tables, exact mean decisions, and all-width finite certificates.

The confidence procedure is a fixed-N paired-t / Bonferroni approximation. It is
not distribution-free. Its optimistic model contains every population-feasible
publication on the declared joint event, while its pessimistic witnesses imply
all constraints on that event. No sample means are substituted into a population
claim and no candidate/cardinality truncation is used.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
from itertools import combinations
import json
from pathlib import Path
import time

import numpy as np
from scipy.stats import t as student_t

from wowfs.experiments.co_exact import Model, evaluate
from wowfs.paths import atomic_json, canonical_hash


DEFAULT_RULE = {"tolerance":"0.01", "headroom":"0.10", "gain":"0.01",
                "retention_mass":"1/2", "gain_mass":"1/2"}


def _domain(world, variant="expanded"):
    if variant not in ("base","expanded"): raise ValueError("unknown menu variant")
    ai = world["base_candidate_indices"] if variant == "base" else range(len(world["candidates"]))
    xi = world["base_partner_indices"] if variant == "base" else range(len(world["partners"]))
    pairs = [(i,j) for i in ai for j in xi]
    return dict(left=[f"a{i:02}" for i in ai],right=[f"x{j}" for j in xi],
                pairs=pairs,configuration_ids=[f"a{i:02}__x{j}" for i,j in pairs],
                supports=[[f"a{i:02}",f"x{j}"] for i,j in pairs],
                task_ids=[t["task_id"] for t in world["tasks"]])


def moments_from_rows(world, rows):
    """Read merged receipts, reject missing/duplicate/unpaired physical data."""
    domain = _domain(world)
    lookup = {}
    for row in rows:
        if row.get("world_id") != world["world_id"]: continue
        if row.get("world_sha256") != world["world_sha256"]:
            raise ValueError("receipt world definition differs from registered world")
        if row.get("status") not in (None,"completed","complete","success"):
            raise ValueError("failed physical row cannot enter table")
        if row.get("observed_or_reconstructed","observed") != "observed":
            raise ValueError("only physically observed rows are eligible")
        key = (int(row["candidate_index"]),int(row["partner_index"]),int(row["task_index"]),int(row.get("policy_index",0)))
        if row.get("task_id") != world["tasks"][key[2]]["task_id"] or row.get("policy_id") != "native":
            raise ValueError("receipt task or policy differs from registered definition")
        if key in lookup: raise ValueError("duplicate physical logical cell")
        lookup[key] = row
    expected = {(i,j,q,0) for i,j in domain["pairs"] for q in range(len(world["tasks"]))}
    if set(lookup) != expected:
        raise ValueError(f"incomplete table: missing {len(expected-set(lookup))}, extra {len(set(lookup)-expected)}")
    seeds = {r["seed_block_id"] for r in lookup.values()}
    ns = {len(r["dps_samples"]) for r in lookup.values()}
    if len(seeds)!=1 or len(ns)!=1 or next(iter(ns))<2:
        raise ValueError("all configurations/tasks need one complete paired fixed-N seed block")
    n = next(iter(ns))
    if int(next(iter(seeds)).split(":")[1]) != n: raise ValueError("seed block/sample length mismatch")
    if any(int(r["iterations"]) != n for r in lookup.values()): raise ValueError("iterations/sample length mismatch")
    means,covariances = [],[]
    for q in range(len(world["tasks"])):
        sample = np.asarray([lookup[i,j,q,0]["dps_samples"] for i,j in domain["pairs"]],dtype=float)
        if not np.isfinite(sample).all(): raise ValueError("nonfinite native observation")
        means.append(sample.mean(axis=1))
        covariances.append(np.cov(sample,ddof=1))
    receipt = [{k:r.get(k) for k in ("candidate_index","partner_index","task_index","seed_block_id","cache_key",
                 "cache_directory","input_sha256","output_sha256","iterations")} for _,r in sorted(lookup.items())]
    return dict(world_id=world["world_id"],world_sha256=world["world_sha256"],N=n,
                seed_block_id=next(iter(seeds)),domain=domain,means=np.asarray(means),
                covariance=np.asarray(covariances),receipt_index=receipt,
                reference_indices=[domain["pairs"].index((0,0))]*len(world["tasks"]))


def save_moments(moments, output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    archive=output/"MOMENTS.npz"
    if archive.exists(): raise ValueError("refuse to overwrite moments")
    np.savez_compressed(archive,means=moments["means"],covariance=moments["covariance"],N=moments["N"],
                        reference_indices=moments["reference_indices"])
    readable={k:v for k,v in moments.items() if k not in ("means","covariance")}
    readable.update(means=moments["means"].tolist(),covariance=moments["covariance"].tolist(),
                    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    atomic_json(output/"MOMENTS_READABLE.json",readable)
    return readable["archive_sha256"]


def model_from_moments(world,moments,rule,variant="expanded", *, retention=True):
    domain=_domain(world,variant)
    indices=[moments["domain"]["pairs"].index(tuple(p)) for p in domain["pairs"]]
    values=[[Fraction(repr(float(moments["means"][q,i]))) for q in range(len(world["tasks"]))] for i in indices]
    reference=[Fraction(repr(float(moments["means"][q,r]))) for q,r in enumerate(moments["reference_indices"])]
    h,e,g=(Fraction(rule[k]) for k in ("headroom","tolerance","gain"))
    raw=dict(slots={**{i:0 for i in domain["left"]},**{i:1 for i in domain["right"]}},
             configurations=[dict(support=s,values=list(map(str,v))) for s,v in zip(domain["supports"],values)],
             weights=[str(Fraction(str(w))) for w in world["task_weights"]],
             tolerance=[str(e*s) for s in reference],cap=[str((1+h)*s) for s in reference],gain=[str(g*s) for s in reference],
             required_mass=rule["retention_mass"] if retention else "0",gain_mass=rule["gain_mass"],history=world["history"])
    return Model.from_dict(raw)


def exact_queries(world,moments,rule,variant="expanded", *, time_limit=60):
    from wowfs.experiments.co_generic import IncrementalSAT
    model=model_from_moments(world,moments,rule,variant)
    value_model=model_from_moments(world,moments,rule,variant,retention=False)
    main,value=IncrementalSAT(model),IncrementalSAT(value_model)
    result=[]
    try:
        for query in world["queries"]:
            answer=main.query(query["required"],time_limit=time_limit)
            ablation=value.query(query["required"],time_limit=time_limit)
            direct=evaluate(model,model.history|frozenset(query["required"]))
            result.append(dict(query_id=query["query_id"],required=query["required"],mean_answer=answer,
                               value_only_answer=ablation,direct_release=direct,
                               retention_decision_active=answer["status"]=="NO" and ablation["status"]=="YES"))
    finally:
        main.close(); value.close()
    return dict(world_id=world["world_id"],variant=variant,model=model.to_dict(),model_sha256=model.digest,
                evidence_level="NATIVE_MEAN_TABLE",queries=result)


def heuristic_queries(model,queries):
    """Constructive-only comparison: every reported YES has exact verification.

    Greedy scores may use floats because they choose search order only. The same
    complete table, source identities and optional helpers are available to every
    method. A search failure, including the depth-two limit, always is UNKNOWN.
    """
    values=np.asarray([[float(v) for v in c.values] for c in model.configurations])
    supports=[c.support for c in model.configurations]
    weights=np.asarray([float(w) for w in model.weights])
    reference=np.asarray([max(float(c.values[q]) for c in model.configurations if c.support<=model.history)
                          for q in range(model.q)])
    tolerance=np.asarray(list(map(float,model.tolerance)))
    def statistics(p):
        active=[k for k,s in enumerate(supports) if s<=p]
        f=values[active].max(axis=0)
        margins=[]
        for source in sorted(p):
            rows=[k for k in active if source in supports[k]]
            margin=np.max(values[rows],axis=0)-f+tolerance if rows else np.full(model.q,-np.inf)
            mass=float(weights[margin>=0].sum())
            # Worst source first; its best normalized margin breaks zero-mass ties.
            margins.append((mass,float(np.max(margin/np.maximum(reference,1)))))
        return f,min(margins),float(weights@((f-reference)/np.maximum(reference,1)))
    results=[]
    initial_valid=evaluate(model,model.history,require_gain=False)["valid"]
    for query in queries:
        initial=model.history|frozenset(query["required"])
        optional=sorted(model.items-initial)
        for method in ("direct","minimum_increment_greedy","current_gain_greedy","weakest_source_repair","lookahead2"):
            started=time.perf_counter(); checked=0; answer=None; trace=[]
            if not initial_valid:
                results.append(dict(query_id=query["query_id"],required=query["required"],method=method,
                                    status="INVALID_INITIAL",verifier=None,checked_publications=0,
                                    elapsed_seconds=time.perf_counter()-started,greedy_addition_trace=[]))
                continue
            def attempt(p):
                nonlocal checked
                checked+=1
                return evaluate(model,p)
            direct=attempt(initial)
            if direct["valid"]: answer=direct
            elif method=="lookahead2":
                for width in (1,2):
                    for helpers in combinations(optional,width):
                        trial=attempt(initial|frozenset(helpers))
                        if trial["valid"]:
                            answer=trial;break
                    if answer is not None:break
            elif method!="direct":
                p=initial
                for _ in optional:
                    before=statistics(p)
                    ranked=[]
                    for item in sorted(model.items-p):
                        f,weak,gain=statistics(p|{item})
                        increment=float(weights@((f-before[0])/np.maximum(reference,1)))
                        if method=="minimum_increment_greedy": score=(increment<=0,increment if increment>0 else float("inf"),item)
                        elif method=="current_gain_greedy": score=(-gain,item)
                        else:score=(-weak[0],-weak[1],-gain,item)
                        ranked.append((score,item))
                    if not ranked:break
                    _,item=min(ranked)
                    p=p|{item};trace.append(item)
                    trial=attempt(p)
                    if trial["valid"]:
                        answer=trial;break
                    if trial.get("reason")=="cap":break  # activation is monotone
            results.append(dict(query_id=query["query_id"],required=query["required"],method=method,
                                status="YES" if answer else "UNKNOWN",verifier=answer,
                                checked_publications=checked,elapsed_seconds=time.perf_counter()-started,
                                greedy_addition_trace=trace,
                                failure_scope="Constructive heuristic exhaustion is not a nonexistence certificate" if answer is None else None))
    return results


def finite_bounds(moments,rule,alpha):
    """All caps and all ordered gain/retention row-pair contrasts, diagonals included."""
    mean=np.asarray(moments["means"],float); cov=np.asarray(moments["covariance"],float)
    q,m=mean.shape; n=int(moments["N"])
    if cov.shape!=(q,m,m) or n<2 or not 0<alpha<1: raise ValueError("invalid moments/alpha")
    if not np.isfinite(mean).all() or not np.isfinite(cov).all(): raise ValueError("nonfinite moments")
    count=q*(m+2*m*m)
    critical=float(student_t.isf(alpha/(2*count),n-1))
    if not np.isfinite(critical): raise ValueError("nonfinite critical value")
    h,e,g=(float(Fraction(rule[k])) for k in ("headroom","tolerance","gain"))
    result={name:np.empty((q,m) if name.startswith("cap") else (q,m,m))
            for name in ("cap_lower","cap_upper","gain_lower","gain_upper","retention_lower","retention_upper")}
    coefficient_hash=hashlib.sha256()
    for t in range(q):
        ref=moments["reference_indices"][t]
        for family,offset in (("cap",1+h),("gain",-g),("retention",e)):
            # Rows of A are exact declared finite contrast directions before
            # ordinary floating-point paired moment evaluation.
            pairs=[(c,None) for c in range(m)] if family=="cap" else [(c,d) for c in range(m) for d in range(m)]
            a=np.zeros((len(pairs),m))
            for k,(c,d) in enumerate(pairs):
                a[k,ref]+=offset
                a[k,c]+= -1 if family=="cap" else 1
                if d is not None: a[k,d]-=1
            coefficient_hash.update(a.tobytes())
            estimates=a@mean[t]
            variances=np.einsum("ij,jk,ik->i",a,cov[t],a,optimize=True)
            scale=np.maximum(1,np.abs(a)@np.abs(cov[t])@np.abs(a).sum(axis=0))
            if np.any(variances < -1e-9*scale): raise ValueError("material negative contrast variance")
            radii=critical*np.sqrt(np.maximum(variances,0)/n)
            shape=(m,) if family=="cap" else (m,m)
            # Guard ordinary roundoff in comparisons; inference remains the
            # explicitly stated approximate t construction, not exact arithmetic.
            guard=128*np.finfo(float).eps*np.maximum(1,np.abs(estimates)+radii)
            result[family+"_lower"][t]=(estimates-radii-guard).reshape(shape)
            result[family+"_upper"][t]=(estimates+radii+guard).reshape(shape)
    result["manifest"]=dict(alpha=alpha,family_size=count,critical=critical,N=n,df=n-1,
        family="Q*(M+2*M*M): cap (1+h)S-u_c; gain u_c-u_d-gS; retention u_c-u_d+eS, all diagonals",
        coefficient_sha256=coefficient_hash.hexdigest(),rule=dict(rule),reference_indices=moments["reference_indices"],
        population_method="Fixed-N simultaneous paired-t Bonferroni approximation; not distribution-free",
        domain_sha256=canonical_hash(moments["domain"]),
        numerical_guard="128 machine eps times max(1,abs(estimate)+radius)")
    return result


def _bits(indices):
    value=0
    for i in indices: value |= 1<<int(i)
    return value


def certify_queries(world,moments,bounds,rule,variant="expanded", *, retention=True):
    """Exhaust every allowed P. Optimistic exclusion does not fix a frontier.

    A true source witness c must satisfy R(c,d)>=0 for every activated d;
    a true gain witness c must satisfy G(c,d)>=0 for every history d.
    Thus upper bounds are necessary and lower bounds sufficient. Witnesses may
    differ across tasks. Every helper has its own full source obligation.
    """
    start=time.perf_counter()
    domain=_domain(world,variant)
    full_pairs=[tuple(p) for p in moments["domain"]["pairs"]]
    rows=[full_pairs.index(tuple(p)) for p in domain["pairs"]]
    items=domain["left"]+domain["right"]
    item_index={i:k for k,i in enumerate(items)}
    history=_bits(item_index[i] for i in world["history"])
    supports=[_bits(item_index[i] for i in s) for s in domain["supports"]]
    incident=[_bits(c for c,s in enumerate(domain["supports"]) if i in s) for i in items]
    hrows=[c for c,s in enumerate(supports) if s & history == s]
    if not hrows: raise ValueError("empty physical history")
    q=len(world["tasks"])
    weights=[Fraction(str(w)) for w in world["task_weights"]]
    rho=Fraction(rule["retention_mass"]) if retention else Fraction(0)
    gain_mass=Fraction(rule["gain_mass"])
    masks=list(range(1<<q))
    enough_ret={z:sum(weights[t] for t in range(q) if z>>t&1)>=rho for z in masks}
    enough_gain={z:sum(weights[t] for t in range(q) if z>>t&1)>=gain_mass for z in masks}
    compiled={}
    for mode,endpoint in (("supported","lower"),("possible","upper")):
        cap=bounds["cap_"+endpoint][:,rows]
        ret=bounds["retention_"+endpoint][:,rows][:,:,rows]
        gain=bounds["gain_"+endpoint][:,rows][:,:,rows]
        compiled[mode]=dict(capbad=_bits(c for c in range(len(rows)) if np.any(cap[:,c]<0)),
            ret_bad=[[_bits(np.flatnonzero(ret[t,c]<0)) for c in range(len(rows))] for t in range(q)],
            gain_good=[_bits(c for c in range(len(rows)) if np.all(gain[t,c,hrows]>=0)) for t in range(q)])
    def check(publication,active,mode,need_gain=True):
        data=compiled[mode]
        if active & data["capbad"]: return "cap"
        if rho:
            useful_by_task=[]
            for t in range(q):
                useful_by_task.append(_bits(c for c in range(len(rows)) if active>>c&1 and not(active & data["ret_bad"][t][c])))
            for i in range(len(items)):
                if publication>>i&1:
                    useful=_bits(t for t in range(q) if useful_by_task[t]&incident[i])
                    if not enough_ret[useful]: return "retention"
        if need_gain and not enough_gain[_bits(t for t in range(q) if active&data["gain_good"][t])]: return "gain"
        return "valid"
    hactive=_bits(hrows)
    initial={mode:check(history,hactive,mode,False) for mode in compiled}
    optional=[i for i in range(len(items)) if not(history>>i&1)]
    query_masks=[_bits(item_index[i] for i in query["required"]) for query in world["queries"]]
    decisions=[{mode:None for mode in compiled} for _ in query_masks]
    query_counts=[{mode:{r:0 for r in ("cap","retention","gain","valid")} for mode in compiled} for _ in query_masks]
    totals={mode:{r:0 for r in ("cap","retention","gain","valid")} for mode in compiled}
    digests={mode:hashlib.sha256() for mode in compiled}
    examined=1<<len(optional)
    for mask in range(examined):
        p=history|_bits(optional[k] for k in range(len(optional)) if mask>>k&1)
        active=_bits(c for c,s in enumerate(supports) if s&p==s)
        for mode in compiled:
            status=check(p,active,mode)
            totals[mode][status]+=1
            digests[mode].update(f"{p}:{status}\n".encode())
            for j,d in enumerate(query_masks):
                if d&p==d:query_counts[j][mode][status]+=1
            if status=="valid":
                for j,d in enumerate(query_masks):
                    if d&p==d and (decisions[j][mode] is None or p.bit_count()<decisions[j][mode].bit_count()):
                        decisions[j][mode]=p
    out=[]
    for j,(query,decision) in enumerate(zip(world["queries"],decisions)):
        if initial["possible"]!="valid": status="INVALID_INITIAL"
        elif initial["supported"]!="valid": status="UNKNOWN_INITIAL"
        elif decision["supported"] is not None: status="YES"
        elif decision["possible"] is None: status="NO"
        else: status="UNKNOWN"
        witness=decision["supported"]
        out.append(dict(query_id=query["query_id"],required=query["required"],status=status,
                        witness=[i for k,i in enumerate(items) if witness is not None and witness>>k&1] if witness is not None else None,
                        optimistic_completion=[i for k,i in enumerate(items) if decision["possible"] is not None and decision["possible"]>>k&1] if decision["possible"] is not None else None,
                        exhaustive_target_publication_counts=query_counts[j]))
    return dict(world_id=world["world_id"],variant=variant,queries=out,initial=initial,
                retention_enforced=retention,examined_publications=examined,
                rejected_or_accepted_counts=totals,exhaustive_trace_sha256={mode:h.hexdigest() for mode,h in digests.items()},
                bounds_manifest=bounds["manifest"],elapsed_seconds=time.perf_counter()-start,
                replay_certificate={"items":items,"row_indices_in_full_table":rows,"support_masks":supports,
                                    "history_mask":history,"query_masks":query_masks,"compiled_masks":compiled,
                                    "enough_retention_mass_masks":[m for m,ok in enough_ret.items() if ok],
                                    "enough_gain_mass_masks":[m for m,ok in enough_gain.items() if ok]},
                proof="Any true feasible P satisfies every optimistic necessary check; every pessimistic accepted P satisfies all true constraints on the joint event.",
                evidence_level="FRESH_CONFIRMATION")


def verify_replay_publication(certificate,items,mode="supported", *, require_gain=True):
    """Check a concrete frozen witness against the exported finite masks."""
    c=certificate["replay_certificate"]
    if not set(items)<=set(c["items"]):return dict(valid=False,reason="unknown_item")
    p=_bits(c["items"].index(i) for i in items)
    if p&c["history_mask"]!=c["history_mask"]:return dict(valid=False,reason="history")
    active=_bits(k for k,s in enumerate(c["support_masks"]) if s&p==s)
    data=c["compiled_masks"][mode]
    if active&data["capbad"]:return dict(valid=False,reason="cap",active_mask=active)
    q=len(data["gain_good"])
    witnesses={}
    for i in items:
        k=c["items"].index(i)
        by_task=[]
        for t in range(q):
            by_task.append([r for r,s in enumerate(c["support_masks"])
                            if active>>r&1 and s>>k&1 and not(active&data["ret_bad"][t][r])])
        taskmask=_bits(t for t,x in enumerate(by_task) if x)
        if taskmask not in c["enough_retention_mass_masks"]:
            return dict(valid=False,reason="retention",source=i,witnesses_by_task=by_task)
        witnesses[i]=by_task
    gainmask=_bits(t for t in range(q) if active&data["gain_good"][t])
    if require_gain and gainmask not in c["enough_gain_mass_masks"]:return dict(valid=False,reason="gain")
    return dict(valid=True,items=list(items),active_mask=active,source_witnesses=witnesses,gain_task_mask=gainmask,
                bound_endpoint_mode=mode)


def run_analysis(registry,batch,thresholds,output,*,mode,predictions=None,alpha=.0025):
    """Create a new immutable analysis directory; no native execution occurs."""
    from datetime import datetime,timezone
    from wowfs.experiments.co_catalogs import load_registry
    from wowfs.experiments.r2_native import file_hash
    from wowfs.experiments import co_exact,co_generic
    import csv
    registry,batch,thresholds,output=map(Path,(registry,batch,thresholds,output))
    if mode not in ("predict","confirm"):raise ValueError("unknown analysis mode")
    if mode=="confirm" and predictions is None:raise ValueError("confirmation requires immutable predictions")
    if output.exists():raise ValueError("new output directory required; preserve previous analysis")
    worlds=[w for w in load_registry(registry) if w["split"]=="validation"]
    rule=json.loads(thresholds.read_text())["rule"]
    result_path=batch/"RESULTS.json" if batch.is_dir() else batch
    raw=json.loads(result_path.read_text())
    if raw.get("errors") or raw.get("status") not in ("completed","complete"):
        raise ValueError("complete error-free batch required; missing cells cannot be imputed")
    rows=raw["rows"]
    output.mkdir(parents=True)
    manifest=dict(mode=mode,created_utc=datetime.now(timezone.utc).isoformat(),
                  registry_sha256=file_hash(registry),batch_results_sha256=file_hash(result_path),
                  threshold_sha256=file_hash(thresholds),rule=rule,world_ids=[w["world_id"] for w in worlds],
                  source_hashes={str(p):file_hash(p) for p in map(Path,(__file__,co_exact.__file__,co_generic.__file__))},
                  alpha_per_unit=alpha if mode=="confirm" else None,
                  predictions_directory=str(predictions) if predictions else None,
                  evidence_level="FRESH_CONFIRMATION" if mode=="confirm" else "EXPLORATORY_PREDICTION")
    atomic_json(output/"ANALYSIS_MANIFEST.json",manifest)
    decisions=[];expansions=[];completed=[]
    for world in worlds:
        wdir=output/world["world_id"]; wdir.mkdir()
        moments=moments_from_rows(world,rows)
        save_moments(moments,wdir)
        bounds=finite_bounds(moments,rule,alpha) if mode=="confirm" else None
        if bounds is not None:
            atomic_json(wdir/"BOUNDS_MANIFEST.json",bounds["manifest"])
            np.savez_compressed(wdir/"BOUNDS.npz",**{k:v for k,v in bounds.items() if k!="manifest"})
        variants={}
        for variant in world["universe_variants"]:
            vdir=wdir/variant; vdir.mkdir()
            exact=exact_queries(world,moments,rule,variant)
            atomic_json(vdir/"EXACT_QUERIES.json",exact)
            model=Model.from_dict(exact["model"])
            heuristics=heuristic_queries(model,world["queries"])
            atomic_json(vdir/"HEURISTICS.json",heuristics)
            cert=certify_queries(world,moments,bounds,rule,variant) if bounds is not None else None
            value_cert=certify_queries(world,moments,bounds,rule,variant,retention=False) if bounds is not None else None
            if cert is not None:
                for answer in cert["queries"]:
                    if answer["witness"] is not None:
                        answer["witness_check"]=verify_replay_publication(cert,answer["witness"])
                        if not answer["witness_check"]["valid"]:raise AssertionError("certificate witness replay failed")
                atomic_json(vdir/"CONFIDENCE_CERTIFICATES.json",cert)
                atomic_json(vdir/"VALUE_ONLY_CONFIDENCE.json",value_cert)
            predicted=None
            if predictions:
                predicted=json.loads((Path(predictions)/world["world_id"]/variant/"EXACT_QUERIES.json").read_text())
                if predicted["model"]["history"]!=exact["model"]["history"]:raise ValueError("history changed after prediction")
            variant_rows=[]
            for qi,query in enumerate(exact["queries"]):
                pred=predicted["queries"][qi] if predicted else query
                if pred["query_id"]!=query["query_id"] or pred["required"]!=query["required"]:raise ValueError("query changed")
                ca=cert["queries"][qi] if cert else None
                va=value_cert["queries"][qi] if value_cert else None
                pw=pred["mean_answer"].get("items")
                pw_check=verify_replay_publication(cert,pw) if cert and pw else None
                row=dict(world_id=world["world_id"],stratum=world["stratum"],
                         **{"class":world["context"]["class"],"race":world["context"]["race_label"],"faction":world["context"]["faction"]},
                         variant=variant,query_id=query["query_id"],required=query["required"],
                         development_prediction=pred["mean_answer"]["status"],
                         fresh_mean_answer=query["mean_answer"]["status"] if mode=="confirm" else None,
                         confidence_status=ca["status"] if ca else "NOT_RUN",
                         value_only_mean_answer=query["value_only_answer"]["status"],
                         value_only_confidence=va["status"] if va else "NOT_RUN",
                         retention_decision_active_mean=query["retention_decision_active"],
                         retention_decision_active_confidence=(ca["status"]=="NO" and va["status"]=="YES") if ca else None,
                         frozen_prediction_witness=pw,prediction_witness_confidence_check=pw_check,
                         prediction_changed_on_fresh_mean=(pred["mean_answer"]["status"]!=query["mean_answer"]["status"]) if mode=="confirm" else None,
                         native_N=moments["N"],seed_block_id=moments["seed_block_id"],
                         evidence_level="FRESH_CONFIRMATION" if mode=="confirm" else "EXPLORATORY_PREDICTION")
                decisions.append(row);variant_rows.append(row)
            variants[variant]=variant_rows
        if world["candidate_expansion_registered"]:
            for base,extended in zip(variants["base"],variants["expanded"]):
                mean_key="fresh_mean_answer" if mode=="confirm" else "development_prediction"
                before,after=base[mean_key],extended[mean_key]
                if before=="YES" and after=="NO":raise AssertionError("optional candidate monotonicity violation")
                expansions.append(dict(world_id=world["world_id"],query_id=base["query_id"],required=base["required"],
                                       base_mean=before,expanded_mean=after,base_confidence=base["confidence_status"],
                                       expanded_confidence=extended["confidence_status"],
                                       common_physical_rows_and_reference=True,
                                       expansion_removed_mean_obstruction=before=="NO" and after=="YES"))
        completed.append(world["world_id"])
        atomic_json(output/"PROGRESS.json",dict(status="running",completed_worlds=completed,expected_worlds=len(worlds)))
        print(json.dumps({"world_id":world["world_id"],"analysis_mode":mode,"status":"completed"}),flush=True)
    atomic_json(output/"NATIVE_DECISIONS.json",decisions)
    atomic_json(output/"CATALOG_EXPANSION_RESULTS.json",expansions)
    fields=[k for k in decisions[0] if k not in ("prediction_witness_confidence_check",)] if decisions else []
    with (output/"NATIVE_DECISIONS.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in decisions:
            writer.writerow({k:json.dumps(row[k],sort_keys=True) if isinstance(row[k],(list,dict)) else row[k] for k in fields})
    atomic_json(output/"PROGRESS.json",dict(status="complete",completed_worlds=completed,expected_worlds=len(worlds),
                                           logical_query_rows=len(decisions),unique_main_queries=sum(len(w["queries"]) for w in worlds),
                                           expanded_menu_queries=len(expansions)))
    return output


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry",required=True)
    parser.add_argument("--batch",required=True)
    parser.add_argument("--thresholds",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--mode",choices=("predict","confirm"),required=True)
    parser.add_argument("--predictions")
    parser.add_argument("--alpha",type=float,default=.0025)
    args=parser.parse_args()
    run_analysis(args.registry,args.batch,args.thresholds,args.output,mode=args.mode,predictions=args.predictions,alpha=args.alpha)


if __name__=="__main__":main()

