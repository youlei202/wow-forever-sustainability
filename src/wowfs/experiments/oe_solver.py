"""Finite full-history release planning for the open exploration campaign.

A state is the actual set of published items. Every declared physically legal
configuration is retained, including over-cap configurations: publishing all its
items activates it and can therefore invalidate a release. Configurations may
contain multiple new items and separate policies may be separate configurations.

All thresholds are expressed relative to fixed positive task references. Source
retention is per published item, with fixed task weights; a source's best use may
choose a different active configuration/policy on each task. This is an exact
combinatorial solver of a finite numerical table (with the explicit numerical
comparison epsilon), not statistical certification or a continuous-domain bound.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
import math
import time
from typing import Any, Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class Configuration:
    id: str
    items: frozenset[str]
    utilities: tuple[float, ...]


@dataclass(frozen=True)
class Problem:
    items: tuple[str, ...]
    initial_items: frozenset[str]
    configurations: tuple[Configuration, ...]
    task_weights: tuple[float, ...]
    reference: tuple[float, ...]
    gain: float
    cap: float | tuple[float, ...]
    tolerance: float | tuple[float, ...]
    gain_mass: float
    retention_mass: float
    total_item_budget: int | None = None
    epsilon: float = 1e-10

    def __post_init__(self) -> None:
        q = len(self.reference)
        if len(set(self.items)) != len(self.items) or not self.items:
            raise ValueError('Items must be unique and nonempty.')
        if not self.initial_items <= set(self.items) or not self.initial_items:
            raise ValueError('Need a nonempty initial subset of declared items.')
        if not q or len(self.task_weights) != q:
            raise ValueError('Reference and task weights must have same positive length.')
        if any(not math.isfinite(x) or x <= 0 for x in self.reference):
            raise ValueError('References must be finite positive constants.')
        if any(not math.isfinite(x) or x < 0 for x in self.task_weights):
            raise ValueError('Task weights must be finite nonnegative constants.')
        if not math.isclose(sum(self.task_weights), 1, abs_tol=1e-12):
            raise ValueError('Fixed task weights must sum to one; no automatic renormalization.')
        if not math.isfinite(self.gain) or self.gain <= 0:
            raise ValueError('Gain must be finite and positive.')
        if not 0 < self.gain_mass <= 1 or not 0 < self.retention_mass <= 1:
            raise ValueError('Gain/retention task mass must be in (0,1].')
        if self.epsilon < 0 or not math.isfinite(self.epsilon):
            raise ValueError('Numerical epsilon must be finite and nonnegative.')
        if self.total_item_budget is not None and self.total_item_budget < 0:
            raise ValueError('Total item budget must be nonnegative.')
        for name in ('cap', 'tolerance'):
            vec = _vector(getattr(self, name), q)
            if not np.all(np.isfinite(vec)) or (name == 'tolerance' and np.any(vec < 0)):
                raise ValueError(f'Invalid {name}.')
        if len({c.id for c in self.configurations}) != len(self.configurations):
            raise ValueError('Configuration IDs must be unique.')
        for c in self.configurations:
            if not c.items or not c.items <= set(self.items):
                raise ValueError(f'Undeclared or empty item incidence in {c.id}.')
            if len(c.utilities) != q or not all(math.isfinite(x) for x in c.utilities):
                raise ValueError(f'Every legal configuration needs finite utilities on every task: {c.id}.')


def _vector(value: float | Sequence[float], q: int) -> np.ndarray:
    vec = np.asarray(value, dtype=float)
    if vec.ndim == 0:
        return np.full(q, float(vec))
    if vec.shape != (q,):
        raise ValueError('Task-specific parameter has incorrect length.')
    return vec


@dataclass
class StateMetrics:
    published: tuple[str, ...]
    active_configurations: tuple[str, ...]
    frontier: tuple[float, ...]  # normalized by fixed reference
    source_best: dict[str, tuple[float, ...]]
    source_masses: dict[str, float]
    source_margins: dict[str, float]  # weighted quantile margin at required mass
    power_valid: bool
    retention_valid: bool
    missing_sources: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.power_valid and self.retention_valid and not self.missing_sources


@dataclass
class Solution:
    status: str
    capacity_lower: int | None
    capacity_upper: int | None
    batches: list[tuple[str, ...]] = field(default_factory=list)
    frontiers: list[tuple[float, ...]] = field(default_factory=list)
    source_masses: list[dict[str, float]] = field(default_factory=list)
    source_margins: list[dict[str, float]] = field(default_factory=list)
    states_evaluated: int = 0
    transitions_evaluated: int = 0
    elapsed_seconds: float = 0.0
    batch_limit: int = 1
    total_item_budget: int | None = None
    initial_items: tuple[str, ...] = ()
    retention_enforced: bool = True
    numerical_epsilon: float = 1e-10
    invalid_attempt: tuple[str, ...] | None = None
    invalid_reason: str | None = None

    @property
    def capacity(self) -> int | None:
        """Convenience alias, only exact if lower == upper and status finite_exact."""
        return self.capacity_lower


class _Deadline(Exception):
    pass


class _Evaluator:
    def __init__(self, p: Problem, initial_items: Iterable[str] | None = None):
        self.p = p
        self.initial = frozenset(initial_items) if initial_items is not None else p.initial_items
        if not p.initial_items <= self.initial or not self.initial <= set(p.items):
            raise ValueError('Continuation must preserve every originally published item.')
        self.candidates = tuple(x for x in p.items if x not in self.initial)
        self.index = {x: i for i, x in enumerate(self.candidates)}
        self.previously_added = len(self.initial - p.initial_items)
        self.budget = len(self.candidates) if p.total_item_budget is None else p.total_item_budget - self.previously_added
        self.weights = np.array(p.task_weights)
        self.cap = _vector(p.cap, len(p.reference))
        self.tolerance = _vector(p.tolerance, len(p.reference))
        self.utilities = np.array([c.utilities for c in p.configurations], dtype=float).reshape((-1,len(p.reference))) / np.array(p.reference)
        self.requirements = np.array([sum(1 << self.index[x] for x in c.items if x in self.index)
                                      for c in p.configurations], dtype=np.int64)
        self.incidence = {x: np.array([x in c.items for c in p.configurations]) for x in p.items}
        self.transitions = 0
        self.metrics = lru_cache(maxsize=None)(self._metrics)

    def _metrics(self, mask: int) -> StateMetrics:
        p = self.p
        published = tuple(x for x in p.items if x in self.initial or (x in self.index and mask & (1 << self.index[x])))
        active = (self.requirements & mask) == self.requirements
        values = self.utilities[active]
        if len(values) == 0:
            return StateMetrics(published, (), tuple(-math.inf for _ in p.reference), {}, {}, {}, False, False, published)
        frontier = values.max(axis=0)
        best, masses, margins, missing = {}, {}, {}, []
        for x in published:
            selected = active & self.incidence[x]
            if not np.any(selected):
                missing.append(x)
                best[x] = tuple(-math.inf for _ in p.reference)
                masses[x], margins[x] = 0.0, -math.inf
                continue
            source = self.utilities[selected].max(axis=0)
            slack = source - frontier + self.tolerance
            best[x] = tuple(float(v) for v in source)
            masses[x] = float(self.weights[slack >= -p.epsilon].sum())
            # Largest slack threshold supported on at least retention_mass.
            order = np.argsort(-slack, kind='stable')
            idx = int(np.searchsorted(np.cumsum(self.weights[order]), p.retention_mass - 1e-12))
            margins[x] = float(slack[order[min(idx, len(order)-1)]])
        return StateMetrics(published, tuple(c.id for c,a in zip(p.configurations,active) if a),
                            tuple(float(v) for v in frontier), best, masses, margins,
                            bool(np.all(frontier <= self.cap + p.epsilon)),
                            all(v >= p.retention_mass - 1e-12 for v in masses.values()), tuple(missing))

    def valid(self, mask: int, retention: bool = True) -> bool:
        s = self.metrics(mask)
        return (mask.bit_count() <= self.budget and s.power_valid
                and (not retention or (s.retention_valid and not s.missing_sources)))

    def gain_mass(self, mask: int, nxt: int) -> float:
        diff = np.array(self.metrics(nxt).frontier) - np.array(self.metrics(mask).frontier)
        return float(self.weights[diff >= self.p.gain - self.p.epsilon].sum())

    def successors(self, mask: int, B: int, retention: bool = True):
        rem = [i for i in range(len(self.candidates)) if not mask & (1 << i)]
        for size in range(1, min(B, len(rem), self.budget-mask.bit_count())+1):
            for ids in combinations(rem, size):
                self.transitions += 1
                nxt = mask | sum(1 << i for i in ids)
                if self.valid(nxt, retention) and self.gain_mass(mask,nxt) >= self.p.gain_mass - 1e-12:
                    yield nxt, tuple(self.candidates[i] for i in ids)

    def upper(self, mask: int) -> int:
        # Every release consumes >=1 new item and increases weighted frontier
        # by >= gain*gain_mass (up to declared numerical comparison epsilon).
        items = min(len(self.candidates)-mask.bit_count(), self.budget-mask.bit_count())
        headroom = float(np.dot(self.weights,np.maximum(0,self.cap-np.array(self.metrics(mask).frontier)+self.p.epsilon)))
        per_step = (self.p.gain-self.p.epsilon)*max(0,self.p.gain_mass-1e-12)
        return max(0,min(items,math.floor(headroom/per_step+1e-9))) if per_step > 0 else max(0,items)


def _solution(e: _Evaluator, path: list[tuple[str,...]], status: str, upper: int | None,
              B: int, start: float, retention: bool, invalid_attempt=None, invalid_reason=None) -> Solution:
    mask = 0
    fronts, masses, margins = [], [], []
    for batch in path:
        mask |= sum(1 << e.index[x] for x in batch)
        s = e.metrics(mask)
        fronts.append(s.frontier); masses.append(s.source_masses); margins.append(s.source_margins)
    lower = None if status == 'initially_invalid' else len(path)
    return Solution(status,lower,upper,path,fronts,masses,margins,e.metrics.cache_info().currsize,
                    e.transitions,time.monotonic()-start,B,e.p.total_item_budget,tuple(sorted(e.initial)),
                    retention,e.p.epsilon,invalid_attempt,invalid_reason)


def state_metrics(p: Problem, published_items: Iterable[str] | None = None) -> StateMetrics:
    return _Evaluator(p,published_items).metrics(0)


def validate_history(p: Problem, batches: Sequence[Sequence[str]], batch_limit: int = 1,
                     initial_items: Iterable[str] | None = None, retention: bool = True) -> list[StateMetrics]:
    """Raises on any infeasible prefix, including all newly published sources."""
    e = _Evaluator(p,initial_items)
    if batch_limit < 1 or not e.valid(0,retention):
        raise ValueError('Invalid initial state or release width.')
    mask, states = 0, [e.metrics(0)]
    for batch in batches:
        if not batch or len(batch)>batch_limit or len(set(batch)) != len(batch):
            raise ValueError('Invalid batch width or duplicate item.')
        if any(x not in e.index or mask & (1 << e.index[x]) for x in batch):
            raise ValueError('Batch item already published or not a candidate.')
        nxt = mask | sum(1 << e.index[x] for x in batch)
        if not e.valid(nxt,retention) or e.gain_mass(mask,nxt)<p.gain_mass-1e-12:
            raise ValueError(f'Invalid release {tuple(batch)} from published subset {e.metrics(mask).published}.')
        states.append(e.metrics(nxt));mask=nxt
    return states


def exact_capacity(p: Problem, batch_limit: int = 1, *, initial_items: Iterable[str] | None = None,
                   retention: bool = True, max_candidates: int = 12,
                   timeout_seconds: float | None = None) -> Solution:
    """Exact full-subset DP; bounded time returns a feasible LB and valid coarse UB.

    total_item_budget counts all releases since p.initial_items, including items
    in a supplied continuation state. No existing source is compressed away.
    """
    start=time.monotonic();e=_Evaluator(p,initial_items)
    if batch_limit<1: raise ValueError('Batch limit must be positive.')
    if len(e.candidates)>max_candidates: raise ValueError('Finite oracle candidate limit exceeded; explicitly reduce/expand the declared domain.')
    if not e.valid(0,retention):return _solution(e,[],'initially_invalid',None,batch_limit,start,retention)
    deadline=math.inf if timeout_seconds is None else start+max(0,timeout_seconds)
    best_path: list[tuple[str,...]]=[]
    prefix: list[tuple[str,...]]=[]

    @lru_cache(maxsize=None)
    def solve(mask: int) -> tuple[tuple[str,...],...]:
        nonlocal best_path
        if time.monotonic()>=deadline:raise _Deadline
        best: tuple[tuple[str,...],...]=()
        for nxt,batch in e.successors(mask,batch_limit,retention):
            if time.monotonic()>=deadline:raise _Deadline
            prefix.append(batch)
            if len(prefix)>len(best_path):best_path=list(prefix)
            try: tail=solve(nxt)
            finally: prefix.pop()
            candidate=(batch,)+tail
            if len(candidate)>len(best):best=candidate
        return best
    try:
        path=list(solve(0));status='finite_exact';upper=len(path)
    except _Deadline:
        path=best_path;status='timeout';upper=e.upper(0)
    # Validate independent of the recursion, including timeout incumbent.
    validate_history(p,path,batch_limit,initial_items,retention)
    return _solution(e,path,status,upper,batch_limit,start,retention)


def greedy_capacity(p: Problem, batch_limit: int = 1, *, policy: str = 'max_gain',
                    initial_items: Iterable[str] | None = None, retention: bool = True,
                    max_steps: int | None = None) -> Solution:
    """Same table, candidate set, release width and total item budget baselines.

    max_gain is retention-feasible current-gain greedy; source_aware maximizes
    worst retained-source margin before gain; lookahead2 maximizes feasible
    two-step count, then minimum source margin and current gain. value_only
    intentionally ignores source retention while choosing, then stops and records
    the first unsafe proposal; its output path still contains only valid releases.
    """
    if policy not in {'max_gain','source_aware','lookahead2','value_only'}:
        raise ValueError('Unknown policy.')
    if batch_limit<1:raise ValueError('Batch limit must be positive.')
    start=time.monotonic();e=_Evaluator(p,initial_items)
    if not e.valid(0,retention):return _solution(e,[],'initially_invalid',None,batch_limit,start,retention)
    path=[];mask=0;invalid=None;reason=None
    def score(nxt: int, batch: tuple[str,...], current: int):
        s=e.metrics(nxt)
        gain=float(np.dot(e.weights,np.array(s.frontier)-np.array(e.metrics(current).frontier)))
        margin=min(s.source_margins.values(),default=-math.inf)
        if policy=='source_aware':return (margin,gain,-len(batch))
        if policy=='lookahead2':
            more=any(e.successors(nxt,batch_limit,retention))
            return (int(more),margin,gain,-len(batch))
        return (gain,margin,-len(batch))
    while max_steps is None or len(path)<max_steps:
        options=list(e.successors(mask,batch_limit,retention and policy!='value_only'))
        if not options:break
        nxt,batch=max(options,key=lambda pair:score(*pair,mask))
        if retention and not e.valid(nxt,True):
            invalid=batch;reason='source_retention_failed';break
        path.append(batch);mask=nxt
    validate_history(p,path,batch_limit,initial_items,retention)
    return _solution(e,path,'heuristic',e.upper(0),batch_limit,start,retention,invalid,reason)


def first_step_continuations(p: Problem, batch_limit: int=1, *, retention: bool=True,
                             timeout_seconds: float | None=None) -> list[dict[str,Any]]:
    """Conditional exact remaining capacity of every feasible first release."""
    e=_Evaluator(p)
    if not e.valid(0,retention):return []
    rows=[]
    for nxt,batch in e.successors(0,batch_limit,retention):
        s=e.metrics(nxt)
        sol=exact_capacity(p,batch_limit,initial_items=s.published,retention=retention,timeout_seconds=timeout_seconds)
        rows.append({'batch':batch,'frontier':s.frontier,'source_masses':s.source_masses,
                     'source_margins':s.source_margins,'continuation':sol})
    return rows


def fixed_partner_problem(utilities: Any, *, row_ids: Sequence[str], partner_ids: Sequence[str],
                          initial_rows: Sequence[str], task_weights: Sequence[float], reference: Sequence[float],
                          gain: float, cap: float | tuple[float,...], tolerance: float | tuple[float,...],
                          gain_mass: float, retention_mass: float, legal: Any=None,
                          total_item_budget: int | None=None, epsilon: float=1e-10) -> Problem:
    """Build full incidence from row x partner x task [x policy] responses.

    IDs must be globally unique across the two item types. `legal` is a physical
    row x partner [x policy] mask fixed before utility/cap checks. Missing legal
    measurements fail loudly; never mark an over-cap pair physically illegal.
    Policies are choices within each task, not additional equally weighted tasks.
    """
    a=np.asarray(utilities,dtype=float)
    if a.ndim==3:a=a[:,:,:,None]
    if a.ndim!=4 or a.shape[:3]!=(len(row_ids),len(partner_ids),len(reference)):
        raise ValueError('Expected row x partner x task [x policy] tensor.')
    mask=np.ones((a.shape[0],a.shape[1],a.shape[3]),dtype=bool) if legal is None else np.asarray(legal,dtype=bool)
    if mask.ndim==2:mask=np.repeat(mask[:,:,None],a.shape[3],axis=2)
    if mask.shape!=(a.shape[0],a.shape[1],a.shape[3]):raise ValueError('Incorrect physical legality mask.')
    if not set(initial_rows)<=set(row_ids):raise ValueError('Unknown initial row.')
    configs=tuple(Configuration(f'{r}|{x}|policy{k}',frozenset((r,x)),tuple(a[i,j,:,k]))
                  for i,r in enumerate(row_ids) for j,x in enumerate(partner_ids)
                  for k in range(a.shape[3]) if mask[i,j,k])
    return Problem(tuple(row_ids)+tuple(partner_ids),frozenset(initial_rows)|frozenset(partner_ids),configs,
                   tuple(task_weights),tuple(reference),gain,cap,tolerance,gain_mass,retention_mass,total_item_budget,epsilon)


def task_choice_diagnostics(p: Problem, published_items: Iterable[str] | None=None) -> dict[str,Any]:
    """Descriptive H-branch diagnostics; no claim of behavioral novelty.

    Reports task-optimal configuration IDs and fixed-reference regrets. A new ID
    alone never counts as a useful new behavior or a certified horizontal gain.
    """
    s=state_metrics(p,published_items)
    frontier=np.array(s.frontier)
    active=set(s.active_configurations)
    regrets={c.id:tuple(frontier-np.array(c.utilities)/np.array(p.reference)) for c in p.configurations if c.id in active}
    winners=[tuple(cid for cid,r in regrets.items() if r[q]<=p.epsilon) for q in range(len(p.reference))]
    return {'frontier':s.frontier,'task_winners':winners,'configuration_regrets':regrets,
            'single_configuration_optimal_all_tasks':any(all(v<=p.epsilon for v in r) for r in regrets.values()),
            'source_masses':s.source_masses,'interpretation':'descriptive finite-table task choice; not behavioral novelty'}
