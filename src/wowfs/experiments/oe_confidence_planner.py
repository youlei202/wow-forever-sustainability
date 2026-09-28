"""Full-history release graphs from one frozen finite simultaneous contrast family.

The lower graph contains interval-supported states/edges. Its paths construct
conditional statistical capacity lower bounds. The upper graph contains every
state/edge not excluded by the intervals. Only its COMPLETED maximum path search
bounds true finite capacity from above. An optimistic incumbent is not a feasible
witness and never becomes a true-capacity lower bound.

This module reads Problem incidence, thresholds and budgets, never its point
utilities or numerical-reference headroom. Inference remains approximate paired
t, with the assumptions and alpha allocation of the supplied FiniteBounds.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from itertools import combinations
import math
import time
from typing import Iterable
import numpy as np
from wowfs.experiments.oe_solver import Problem
from wowfs.experiments.oe_inference import FiniteBounds


@dataclass
class ConfidenceSolution:
    status: str
    mode: str
    capacity_lower: int | None
    capacity_upper: int | None
    graph_capacity_lower: int | None
    graph_capacity_upper: int | None
    batches: list[tuple[str,...]] = field(default_factory=list)
    path_kind: str = ''
    path_checks: list[dict] = field(default_factory=list)
    initial_status: str = ''
    initial_checks: dict = field(default_factory=dict)
    initial_items: tuple[str,...] = ()
    remaining_candidates: tuple[str,...] = ()
    configuration_order: tuple[str,...] = ()
    states_evaluated: int = 0
    transitions_evaluated: int = 0
    memoized_states: int = 0
    elapsed_seconds: float = 0.
    batch_limit: int = 1
    remaining_item_budget: int = 0
    total_item_budget: int | None = None
    retention_enforced: bool = True
    graph_search_complete: bool = False
    bounds_manifest: dict = field(default_factory=dict)
    scope: str = ('Conditional approximate simultaneous-t bounds on the complete '
                  'declared finite physical domain; no continuous-domain claim.')
    interpretation: str = ''


class _Deadline(Exception):
    pass


@dataclass(frozen=True)
class _Node:
    active: tuple[int,...]
    lower: bool
    upper: bool


def apply_retention_requirement(result:dict,retention:bool)->dict:
    """Keep every source diagnostic but optionally omit retention as a constraint.

    Reuses the same frozen power/gain intervals. No relaxed tolerance, numeric
    point check, or additional error budget is introduced. No-active-config
    states remain invalid even for the value-only objective.
    """
    if not isinstance(retention,bool):raise ValueError('retention must be a boolean')
    result=dict(result);checks=dict(result.get('checks',{}))
    if 'retention' in checks:
        checks['retention']={**checks['retention'],'enforced':retention}
    result['checks']=checks;result['retention_enforced']=retention
    if 'power' in checks:
        for key in ('mean','lower','upper'):
            result[key]=all(check[key] for name,check in checks.items() if name!='retention' or retention)
        result['statistical_status']=('interval_supported' if result['lower'] else
            ('unresolved' if result['upper'] else 'interval_excluded'))
    return result


class _ConfidenceGraph:
    def __init__(self,p:Problem,bounds:FiniteBounds,initial_items:Iterable[str]|None,retention:bool):
        self.p=p;self.bounds=bounds;self.retention=retention
        self.initial=frozenset(initial_items) if initial_items is not None else p.initial_items
        if not p.initial_items<=self.initial or not self.initial<=set(p.items):
            raise ValueError('Continuation must preserve all originally published items.')
        if bounds.count!=len(p.configurations) or bounds.tasks!=len(p.task_weights):
            raise ValueError('Problem configuration order and task count must match the bounds tensor.')
        if float(p.gain)!=bounds.gain:
            raise ValueError('Problem gain differs from the frozen contrast family.')
        for name in ('cap','tolerance'):
            vec=np.asarray(getattr(p,name),dtype=float)
            if vec.ndim==0:vec=np.repeat(vec,bounds.tasks)
            if vec.shape!=(bounds.tasks,) or not np.all(vec==getattr(bounds,name)):
                raise ValueError('Problem '+name+' differs from the frozen scalar contrast family.')
        self.candidates=tuple(x for x in p.items if x not in self.initial)
        self.index={x:i for i,x in enumerate(self.candidates)}
        spent=len(self.initial-p.initial_items)
        self.budget=len(self.candidates) if p.total_item_budget is None else p.total_item_budget-spent
        self.limit=max(0,min(len(self.candidates),self.budget))
        self.requirements=tuple(sum(1<<self.index[x] for x in c.items if x in self.index)
                                for c in p.configurations)
        self.incidence={x:tuple(i for i,c in enumerate(p.configurations) if x in c.items) for x in p.items}
        self.weights=np.asarray(p.task_weights,dtype=float)
        self.nodes:dict[int,_Node]={};self.states=0;self.transitions=0

    def published(self,mask):
        return tuple(x for x in self.p.items if x in self.initial or
                     (x in self.index and mask&(1<<self.index[x])))

    def sources(self,mask):
        return {x:self.incidence[x] for x in self.published(mask)}

    def active(self,mask):
        return tuple(i for i,required in enumerate(self.requirements) if required&mask==required)

    def evaluate(self,mask,*,details=False):
        if mask in self.nodes and not details:return self.nodes[mask]
        active=self.active(mask)
        if not active:
            result={'mean':False,'lower':False,'upper':False,
                    'statistical_status':'interval_excluded',
                    'reason':'no_active_physical_configuration',
                    'stateconfig_indices':[],'sources':{},'checks':{}}
        elif not self.retention and not details:
            # Internal value-only nodes need only the universal cap constraint.
            # Initial/final path records still compute and preserve every source
            # diagnostic. Skipping unused retention arithmetic here materially
            # reduces full-domain search cost without changing its state graph.
            indices=list(active)
            power={'mean':bool(np.all(self.bounds.cap_mean[indices]>=0.)),
                   'lower':bool(np.all(self.bounds.cap_lower[indices]>=0.)),
                   'upper':bool(np.all(self.bounds.cap_upper[indices]>=0.))}
            result={**power,'checks':{'power':power}}
        else:
            result=self.bounds.evaluate(active,self.sources(mask),self.weights,self.p.retention_mass)
        result=apply_retention_requirement(result,self.retention)
        if self.budget<0 or mask.bit_count()>self.budget:
            result={**result,'mean':False,'lower':False,'upper':False,
                    'reason':'total_item_budget_exceeded','statistical_status':'interval_excluded'}
        if mask not in self.nodes:
            self.nodes[mask]=_Node(active,bool(result['lower']),bool(result['upper']))
            self.states+=1
        return result if details else self.nodes[mask]

    def edge(self,mask,nxt,mode):
        self.transitions+=1
        before=self.evaluate(mask);after=self.evaluate(nxt)
        if not getattr(after,mode):return False
        lo,hi=self.bounds.frontier_contrast(after.active,before.active,self.bounds.gain)
        values=lo if mode=='lower' else hi
        mass=float(self.weights[values>=0.].sum())
        return mass>=self.p.gain_mass-1e-12

    def remaining(self,mask):
        return max(0,min(len(self.candidates)-mask.bit_count(),self.budget-mask.bit_count()))


def confidence_capacity(problem:Problem,bounds:FiniteBounds,mode='lower',batch_limit=1,
                        *,initial_items=None,timeout_seconds=None,max_candidates=19,
                        retention=True)->ConfidenceSolution:
    """Solve a supported or possible full-subset DAG under a hard candidate limit.

    Configurations are in EXACTLY Problem.configurations order on bounds' C axis.
    Separate policies are separate physical configurations, not extra tasks.
    Every released old/new source and every activated legal configuration is
    recorded. retention=False disables only the source-usefulness constraint;
    its diagnostics and every physical configuration remain present. No mean-table
    rejection or point-estimate headroom pruning is used.

    Timeout is checked between bounded state/edge operations; initial assessment
    and final incumbent verification are always completed. At timeout, the true
    capacity upper bound is only min(remaining candidates, remaining item budget).
    A complete lower graph still supplies no sharper true-capacity upper bound.
    """
    started=time.monotonic()
    if mode not in ('lower','upper'):raise ValueError('mode must be lower or upper')
    if not isinstance(retention,bool):raise ValueError('retention must be a boolean')
    if isinstance(batch_limit,bool) or not isinstance(batch_limit,int) or batch_limit<1:
        raise ValueError('batch_limit must be a positive integer')
    if isinstance(max_candidates,bool) or not isinstance(max_candidates,int) or not 0<=max_candidates<=19:
        raise ValueError('max_candidates must be an explicit integer in [0,19]')
    if timeout_seconds is not None and (not math.isfinite(timeout_seconds) or timeout_seconds<0):
        raise ValueError('timeout_seconds must be finite and nonnegative')
    e=_ConfidenceGraph(problem,bounds,initial_items,retention)
    if len(e.candidates)>max_candidates:
        raise ValueError('Declared candidate count exceeds explicit limit; do not silently delete candidates.')
    initial=e.evaluate(0,details=True)
    initial_status=('supported' if initial['lower'] else ('unresolved' if initial['upper'] else 'excluded'))
    deadline=math.inf if timeout_seconds is None else started+timeout_seconds
    memo={};best_path:list[int]=[];prefix:list[int]=[]

    def check_deadline():
        if time.monotonic()>=deadline:raise _Deadline

    def remember(path):
        nonlocal best_path
        if len(path)>len(best_path):best_path=list(path)

    def solve(mask):
        check_deadline()
        if mask in memo:
            remember(prefix+list(memo[mask]))
            return memo[mask]
        best=()
        remain=[i for i in range(len(e.candidates)) if not mask&(1<<i)]
        maximum=e.remaining(mask)
        # Every release consumes at least one previously unpublished item. This
        # bound needs no population-performance estimate or lower-bound table.
        for width in range(1,min(batch_limit,maximum)+1):
            for indices in combinations(remain,width):
                check_deadline()
                batchmask=sum(1<<i for i in indices);nxt=mask|batchmask
                if not e.edge(mask,nxt,mode):continue
                prefix.append(batchmask);remember(prefix)
                try:tail=solve(nxt)
                finally:prefix.pop()
                candidate=(batchmask,)+tail
                remember(prefix+list(candidate))
                if len(candidate)>len(best):best=candidate
                if len(best)==maximum:
                    memo[mask]=best
                    return best
        memo[mask]=best
        return best

    if not initial['upper']:
        status='initial_excluded';path=[];complete=False
        real_low=real_high=graph_low=graph_high=None
    elif mode=='lower' and not initial['lower']:
        status='initial_unresolved';path=[];complete=False
        real_low=None;real_high=e.limit;graph_low=graph_high=None
    else:
        try:
            path=list(solve(0));complete=True;status=mode+'_graph_complete'
        except _Deadline:
            path=best_path;complete=False;status='timeout'
        graph_low=len(path);graph_high=len(path) if complete else e.limit
        if mode=='lower':
            real_low=len(path);real_high=e.limit
        else:
            # An upper-graph path is NOT a supported path. The only guaranteed
            # lower bound here is zero when the initial state itself is supported.
            real_low=0 if initial['lower'] else None
            real_high=len(path) if complete else e.limit
    batches=[tuple(e.candidates[i] for i in range(len(e.candidates)) if mask&(1<<i)) for mask in path]
    checks=[];mask=0
    for batchmask in path:
        nxt=mask|batchmask
        edge=bounds.transition(e.active(mask),e.active(nxt),e.sources(nxt),problem.gain_mass,
                               weights=problem.task_weights,retention_mass=problem.retention_mass)
        edge=apply_retention_requirement(edge,retention)
        if not edge[mode]:raise AssertionError('Returned graph path failed independent transition validation')
        edge['published_items']=list(e.published(nxt))
        edge['released_items']=[e.candidates[i] for i in range(len(e.candidates)) if batchmask&(1<<i)]
        checks.append(edge);mask=nxt
    return ConfidenceSolution(status=status,mode=mode,capacity_lower=real_low,capacity_upper=real_high,
        graph_capacity_lower=graph_low,graph_capacity_upper=graph_high,batches=batches,
        path_kind='interval_supported_witness' if mode=='lower' else 'optimistic_not_a_feasible_witness',
        path_checks=checks,initial_status=initial_status,initial_checks=initial,
        initial_items=tuple(x for x in problem.items if x in e.initial),remaining_candidates=e.candidates,
        configuration_order=tuple(c.id for c in problem.configurations),states_evaluated=e.states,
        transitions_evaluated=e.transitions,memoized_states=len(memo),elapsed_seconds=time.monotonic()-started,
        batch_limit=batch_limit,remaining_item_budget=e.limit,total_item_budget=problem.total_item_budget,
        retention_enforced=retention,
        graph_search_complete=complete,bounds_manifest=bounds.manifest(),
        interpretation=('capacity_lower is a supported-path lower bound; capacity_upper uses only item count. '
                        'An exhausted lower graph is not a true-capacity optimum.' if mode=='lower' else
                        'capacity_upper is the possible-graph optimum only after graph_search_complete; '
                        'otherwise it is the coarse remaining-item bound. Optimistic paths prove no positive lower bound.'))
