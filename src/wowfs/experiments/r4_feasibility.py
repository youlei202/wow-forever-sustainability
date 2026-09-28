"""Exact finite-table joint admission with protected old choices.

This solves a frozen empirical response table. It does not certify population
means, source-only prediction, or a bounded item-price representation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Iterable
import warnings

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from wowfs.experiments.r2_sequence_analysis import nearest_distances, portfolio_cover


@dataclass
class FiniteProblem:
    values: np.ndarray
    behavior: np.ndarray
    sources: list[Iterable[str | int]]
    protected: Iterable[int] | np.ndarray
    new_sources: Iterable[str | int]
    protected_sources: Iterable[str | int]
    scale: np.ndarray
    cap: np.ndarray
    archive: list[np.ndarray] | None = None
    weights: np.ndarray | None = None
    epsilon: float = .05
    delta: float = .05
    min_mass: float = .05
    k_max: int = 4
    coverage: float = .95
    require_D_each_new: bool = False
    gear_ids: list[str] | None = None
    tolerance: float = 1e-9
    best: np.ndarray = field(init=False, repr=False)
    novel_best: np.ndarray = field(init=False, repr=False)
    distances: np.ndarray = field(init=False, repr=False)
    safe: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        self.values = np.asarray(self.values, float)
        self.behavior = np.asarray(self.behavior, float)
        if self.values.ndim != 3 or self.behavior.shape[:3] != self.values.shape or self.behavior.ndim != 4:
            raise ValueError("Expected G×policy×task values and G×policy×task×feature behavior")
        if not np.isfinite(self.values).all() or not np.isfinite(self.behavior).all():
            raise ValueError("Incomplete/nonfinite response table")
        g, _, tasks = self.values.shape
        self.sources = [frozenset(map(str, ss)) for ss in self.sources]
        if len(self.sources) != g:
            raise ValueError("Source table differs from gear domain")
        self.new_sources = tuple(sorted(set(map(str, self.new_sources))))
        self.protected_sources = tuple(sorted(set(map(str, self.protected_sources))))
        raw_protected = np.asarray(list(self.protected))
        if raw_protected.dtype == bool:
            if raw_protected.shape != (g,):
                raise ValueError("Protected mask shape mismatch")
            self.protected = raw_protected.copy()
        else:
            self.protected = np.zeros(g, bool)
            self.protected[raw_protected.astype(int)] = True
        if not np.any(self.protected):
            raise ValueError("Protected old domain must be nonempty")
        if any(set(self.new_sources) & self.sources[i] for i in np.flatnonzero(self.protected)):
            raise ValueError("A current new source is already in the protected old domain")
        self.scale, self.cap = np.asarray(self.scale, float), np.asarray(self.cap, float)
        if self.scale.shape != (tasks,) or self.cap.shape != (tasks,) or np.any(self.scale <= 0):
            raise ValueError("Invalid fixed scale/cap")
        self.weights = np.full(tasks, 1 / tasks) if self.weights is None else np.asarray(self.weights, float)
        if self.weights.shape != (tasks,) or np.any(self.weights < 0) or not np.isclose(self.weights.sum(), 1):
            raise ValueError("Task weights must be nonnegative and sum to one")
        self.gear_ids = list(map(str, range(g))) if self.gear_ids is None else list(self.gear_ids)
        if len(self.gear_ids) != g:
            raise ValueError("Gear ID table differs from response domain")
        # New-subset admission cannot silently manipulate old-only substitutes.
        optional_old = [i for i in range(g) if not self.protected[i] and not set(self.new_sources) & self.sources[i]]
        if optional_old:
            raise ValueError("Unprotected old-only gear must be excluded from the candidate domain or explicitly protected")
        self.best = self.values.max(axis=1)
        self.safe = np.all(self.best <= self.cap + self.tolerance, axis=1)
        self.distances = np.empty_like(self.values)
        for k in range(tasks):
            reference = self.behavior[self.protected, :, k].reshape(-1, self.behavior.shape[-1])
            if self.archive is not None and len(self.archive[k]):
                reference = np.concatenate([reference, np.asarray(self.archive[k], float)])
            self.distances[:, :, k] = nearest_distances(
                self.behavior[:, :, k].reshape(-1, self.behavior.shape[-1]), reference).reshape(g, -1)
        eligible = self.distances >= self.delta - self.tolerance
        self.novel_best = np.where(eligible, self.values, -np.inf).max(axis=1)

    @property
    def tol_vector(self):
        return self.epsilon * self.scale


def evaluate_admission(problem: FiniteProblem, admitted) -> dict:
    p = problem; admitted = np.asarray(admitted, bool)
    if admitted.shape != p.protected.shape:
        raise ValueError("Admission mask shape mismatch")
    indices = np.flatnonzero(admitted)
    if not len(indices):
        raise ValueError("An admission state cannot be empty")
    optimum = p.best[admitted].max(axis=0)
    close = (p.best >= optimum - p.tol_vector - p.tolerance) & admitted[:, None]
    novel = (p.novel_best >= optimum - p.tol_vector - p.tolerance) & admitted[:, None]
    all_sources = sorted(set.union(set(), *(set(s) for s in p.sources)))
    masses, novel_masses = {}, {}
    for s in all_sources:
        mask = np.array([s in ss for ss in p.sources])
        masses[s] = float(p.weights @ np.any(close[mask], axis=0))
        novel_masses[s] = float(p.weights @ np.any(novel[mask], axis=0))
    new_mask = np.array([bool(set(p.new_sources) & ss) for ss in p.sources])
    novel_mass = float(p.weights @ np.any(novel[new_mask], axis=0))
    cover = portfolio_cover(p.best[admitted], optimum, p.scale, p.epsilon,
                            p.weights, p.coverage)
    portfolio = [int(indices[i]) for i in cover["indices"]]
    checks = {
        "P": bool(np.all(optimum <= p.cap + p.tolerance)),
        "N": bool(p.new_sources) and all(masses.get(s, 0) >= p.min_mass - p.tolerance for s in p.new_sources),
        "D": (all(novel_masses.get(s, 0) >= p.min_mass - p.tolerance for s in p.new_sources)
              if p.require_D_each_new else novel_mass >= p.min_mass - p.tolerance),
        "L": all(masses.get(s, 0) >= p.min_mass - p.tolerance for s in p.protected_sources),
        "H": bool(np.all(admitted[p.protected])),
        "C": cover["K"] is not None and cover["K"] <= p.k_max,
    }
    return {**checks, "joint_pass": all(checks.values()), "failure_reasons": [k for k, v in checks.items() if not v],
            "optimum": optimum.tolist(), "cap_slack": (p.cap - optimum).tolist(),
            "source_masses": masses, "source_novel_masses": novel_masses, "novel_task_mass": novel_mass,
            "worst_protected_source_mass": min((masses.get(s, 0) for s in p.protected_sources), default=None),
            "K": cover["K"], "portfolio_indices": portfolio,
            "portfolio_item_count": len(set.union(set(), *(set(p.sources[g]) for g in portfolio))),
            "portfolio_item_count_scope": "distinct supplied source IDs in the portfolio; add omitted fixed-slot items for a full carried-item count",
            "admitted_indices": indices.tolist(), "admitted_new_gears": int(np.sum(admitted & ~p.protected)),
            "excluded_safe_new_gears": int(np.sum(p.safe & ~p.protected & ~admitted)),
            "mean_inference": "frozen finite empirical table; no population confidence claim"}


class _Rows:
    def __init__(self):
        self.i, self.j, self.data, self.low, self.high = [], [], [], [], []

    def add(self, terms, low=-np.inf, high=np.inf):
        r = len(self.low)
        for j, value in terms:
            self.i.append(r); self.j.append(int(j)); self.data.append(float(value))
        self.low.append(low); self.high.append(high)

    def constraint(self, n):
        a = coo_matrix((self.data, (self.i, self.j)), shape=(len(self.low), n)).tocsc()
        return LinearConstraint(a, self.low, self.high)


def solve_joint_admission(problem: FiniteProblem, objective="max_admitted", time_limit=30.,
                          rule_rows=0, features=None, price_upper=100., rejection_margin=1e-6) -> dict:
    """MILP existential subset reference; a timeout is never an infeasibility claim.

    Frontier variables need only upper-bound the admitted response maxima.
    Competitive witnesses bound them from above. Lowering a feasible frontier
    to its actual admitted maximum preserves every witness and portfolio.
    """
    p = problem; started = monotonic(); g, tasks = p.best.shape
    if np.any(p.protected & ~p.safe):
        return {"status": "infeasible_protected_power", "proved_infeasible": True,
                "feasible": False, "seconds": monotonic() - started}
    if not p.new_sources:
        return {"status": "infeasible_no_new_source", "proved_infeasible": True, "feasible": False}
    variables, lb, ub, integer = 0, [], [], []
    def block(shape, lower=0., upper=1., integral=True):
        nonlocal variables
        n = int(np.prod(shape)); indices = np.arange(variables, variables + n).reshape(shape); variables += n
        lb.extend(np.broadcast_to(lower, shape).flat); ub.extend(np.broadcast_to(upper, shape).flat)
        integer.extend([int(integral)] * n)
        return indices
    z = block((g,), p.protected.astype(float), p.safe.astype(float))
    lower_frontier = p.best[p.protected].max(axis=0)
    frontier = block((tasks,), lower_frontier, p.cap, False)
    competitive = block((g, tasks))
    novel = block((g, tasks), upper=np.isfinite(p.novel_best).astype(float))
    required = tuple(sorted(set(p.protected_sources) | set(p.new_sources)))
    source_task = block((len(required), tasks))
    d_sources = p.new_sources if p.require_D_each_new else (None,)
    d_task = block((len(d_sources), tasks))
    portfolio = block((g,))
    covered_by = block((g, tasks))
    task_covered = block((tasks,))
    # Optional matched generic nonnegative additive budgets, jointly optimized
    # with ecological witnesses. z is the entire induced opening, not a free
    # blacklist layered on top of a price rule.
    price = rejects = None
    feature_labels = None
    if rule_rows:
        if rule_rows < 1 or int(rule_rows) != rule_rows:
            raise ValueError("rule_rows must be a nonnegative integer")
        if features is None:
            feature_labels = sorted(set.union(set(), *(set(ss) for ss in p.sources)))
            features = np.array([[s in ss for s in feature_labels] for ss in p.sources], float)
        else:
            features = np.asarray(features, float)
        if features.ndim != 2 or features.shape[0] != g or not np.isfinite(features).all() or np.any(features < 0):
            raise ValueError("Additive budget features must be a finite nonnegative gear-feature matrix")
        price = block((rule_rows, features.shape[1]), upper=price_upper, integral=False)
        rejects = block((g, rule_rows))
    rows = _Rows()
    for i in range(g):
        rows.add([(portfolio[i], 1), (z[i], -1)], high=0)
        for k in range(tasks):
            big = max(0., p.best[i, k] - lower_frontier[k])
            rows.add([(frontier[k], 1), (z[i], -big)], low=p.best[i, k] - big)
            for witness, value in ((competitive, p.best[i, k]), (novel, p.novel_best[i, k])):
                rows.add([(witness[i, k], 1), (z[i], -1)], high=0)
                if np.isfinite(value):
                    m = max(0., p.cap[k] - value - p.tol_vector[k])
                    rows.add([(frontier[k], 1), (witness[i, k], m)], high=value + p.tol_vector[k] + m)
            rows.add([(covered_by[i, k], 1), (portfolio[i], -1)], high=0)
            rows.add([(covered_by[i, k], 1), (competitive[i, k], -1)], high=0)
    for si, s in enumerate(required):
        gears = [i for i, ss in enumerate(p.sources) if s in ss]
        for k in range(tasks):
            rows.add([(source_task[si, k], 1)] + [(competitive[i, k], -1) for i in gears], high=0)
        rows.add([(source_task[si, k], p.weights[k]) for k in range(tasks)], low=p.min_mass)
    for si, s in enumerate(d_sources):
        gears = [i for i, ss in enumerate(p.sources) if s in ss] if s is not None else [
            i for i, ss in enumerate(p.sources) if set(p.new_sources) & ss]
        for k in range(tasks):
            rows.add([(d_task[si, k], 1)] + [(novel[i, k], -1) for i in gears], high=0)
        rows.add([(d_task[si, k], p.weights[k]) for k in range(tasks)], low=p.min_mass)
    rows.add([(portfolio[i], 1) for i in range(g)], high=p.k_max)
    for k in range(tasks):
        rows.add([(task_covered[k], 1)] + [(covered_by[i, k], -1) for i in range(g)], high=0)
    rows.add([(task_covered[k], p.weights[k]) for k in range(tasks)], low=p.coverage)
    if rule_rows:
        for i in range(g):
            rows.add([(rejects[i, q], 1) for q in range(rule_rows)] + [(z[i], 1)], low=1)
            for q in range(rule_rows):
                terms = [(price[q, f], features[i, f]) for f in range(features.shape[1]) if features[i, f]]
                rows.add([(rejects[i, q], 1), (z[i], 1)], high=1)
                m = max(0., price_upper * features[i].sum() - 1)
                rows.add(terms + [(z[i], m)], high=1 + m)
                rows.add(terms + [(rejects[i, q], -(1 + rejection_margin))], low=0)
    cost = np.zeros(variables)
    if objective == "max_admitted": cost[z] = -1
    elif objective == "min_admitted": cost[z] = 1
    elif objective != "feasible": raise ValueError("Unknown admission objective")
    scheduler_retry = None
    with warnings.catch_warnings():
        # scipy forwards this supported HiGHS option while warning that it is
        # outside scipy's small public option list. Keep each worker single-core.
        warnings.filterwarnings("ignore", message="Unrecognized options detected:.*threads.*", category=RuntimeWarning)
        result = milp(cost, integrality=np.asarray(integer), bounds=Bounds(lb, ub),
                      constraints=rows.constraint(variables), options={"time_limit": float(time_limit), "mip_rel_gap": 0.,
                          "threads": 1, "mip_feasibility_tolerance": 1e-9, "primal_feasibility_tolerance": 1e-9})
        # HiGHS has a process-global scheduler. A previous unrelated linprog
        # may initialize it with another thread count; then threads=1 returns
        # "Not Set" without solving any model. Reset only after that exact
        # failure, retain the first result, and retry the identical MILP once.
        # Older SciPy versions without this native hook retain the error.
        if result.status == 4 and result.x is None and "HiGHS Status 0: Not Set" in result.message:
            try:
                from scipy.optimize._highspy._core import _Highs
            except ImportError:
                pass
            else:
                scheduler_retry = {"initial_status": int(result.status), "initial_message": result.message,
                    "action": "resetGlobalScheduler(wait=True), then retry unchanged model and options once"}
                _Highs.resetGlobalScheduler(True)
                result = milp(cost, integrality=np.asarray(integer), bounds=Bounds(lb, ub),
                              constraints=rows.constraint(variables), options={"time_limit": float(time_limit), "mip_rel_gap": 0.,
                                  "threads": 1, "mip_feasibility_tolerance": 1e-9, "primal_feasibility_tolerance": 1e-9})
    output = {"status": {0: "optimal", 1: "limit", 2: "infeasible", 3: "unbounded", 4: "solver_error"}.get(result.status, str(result.status)),
              "message": result.message, "proved_infeasible": result.status == 2, "feasible": False,
              "objective": objective, "variables": variables, "constraints": len(rows.low),
              "rule_rows": int(rule_rows), "rule_class": "joint_generic_nonnegative_additive_budgets" if rule_rows else "arbitrary_new_subset_reference",
              "rejection_margin": rejection_margin if rule_rows else None,
              "price_upper_bound": price_upper if rule_rows else None,
              "seconds": monotonic() - started,
              "minimization_dual_bound": float(result.mip_dual_bound) if getattr(result, "mip_dual_bound", None) is not None else None,
              "mip_gap": float(result.mip_gap) if getattr(result, "mip_gap", None) is not None else None}
    if scheduler_retry is not None:
        output["runtime_scheduler_retry"] = scheduler_retry
    if result.x is not None:
        admitted = result.x[z] > .5
        metrics = evaluate_admission(p, admitted)
        output.update(feasible=metrics["joint_pass"], metrics=metrics,
                      admitted=admitted.tolist(), frontier=result.x[frontier].tolist(),
                      objective_value=float(result.fun))
        if not metrics["joint_pass"]:
            output["status"] = "invalid_incumbent"
        if rule_rows:
            prices = result.x[price]
            induced = np.all(features @ prices.T <= 1 + 1e-8, axis=1)
            output.update(prices=prices.tolist(), price_feature_labels=feature_labels,
                          induced_opening_matches=bool(np.array_equal(induced, admitted)),
                          rule_scalar_parameters=int(prices.size))
            if not np.array_equal(induced, admitted):
                output.update(feasible=False, status="invalid_rule_incumbent")
    if objective == "max_admitted" and not output["proved_infeasible"]:
        dual = output["minimization_dual_bound"]
        protected_count = int(np.sum(p.protected))
        upper = (min(g, int(np.floor(-dual + 1e-7))) if dual is not None and np.isfinite(dual) else g)
        output["maximum_total_admitted_upper_bound"] = upper
        output["maximum_total_admitted_lower_bound"] = int(np.sum(output["admitted"])) if output["feasible"] else None
        output["minimum_safe_new_exclusions_lower_bound"] = max(0, int(np.sum(p.safe & ~p.protected)) - (upper - protected_count))
        output["minimum_safe_new_exclusions_upper_bound"] = (output["metrics"]["excluded_safe_new_gears"] if output["feasible"] else None)
    return output


def frontier_closure(problem: FiniteProblem, frontier):
    """Full-information response-box admission; not an item-feature rule."""
    return np.all(problem.best <= np.minimum(problem.cap, frontier) + problem.tolerance, axis=1)


def eval_all_safe(problem: FiniteProblem):
    """Diagnostic maximal power-safe opening, never a joint-feasibility oracle."""
    # Preserve H even when the input state itself violates P, and report that.
    return evaluate_admission(problem, problem.safe | problem.protected)


def solve_subset(problem: FiniteProblem, **kwargs):
    """Short public alias used by release and branch replay analyses."""
    return solve_joint_admission(problem, **kwargs)
