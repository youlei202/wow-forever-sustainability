"""Exact completion for two growing slots with immutable measured responses.

All outputs concern the supplied finite response table.  No interpolation,
statistical inference, or removal of physically available configurations occurs.
The main algorithm decides existence without an item/publication-size budget.
Use Fraction/integer entries for exact arithmetic.  Floats compare the input table
as represented and are suitable only for separately labelled numerical analysis.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from itertools import product
from typing import Sequence, Iterable

@dataclass(frozen=True)
class Configuration:
    support: frozenset[str]
    values: tuple

@dataclass
class Model:
    slots: dict[str, int]
    configurations: tuple[Configuration, ...]
    weights: tuple
    tolerance: tuple
    required_mass: object

    def __post_init__(self):
        self.items = frozenset(self.slots)
        self.q = len(self.weights)
        if self.q < 1 or len(self.tolerance) != self.q:
            raise ValueError('Nonempty task vectors of equal lengths required')
        if any(w < 0 for w in self.weights) or sum(self.weights) != 1:
            raise ValueError('Nonnegative task weights must sum exactly to 1')
        if not 0 <= self.required_mass <= 1 or any(e < 0 for e in self.tolerance):
            raise ValueError('Invalid retention parameters')
        for c in self.configurations:
            if len(c.support) != 2 or not c.support <= self.items:
                raise ValueError('Each configuration contains two known items')
            if {self.slots[i] for i in c.support} != {0, 1}:
                raise ValueError('One item from each of the two slots is required')
            if len(c.values) != self.q:
                raise ValueError('Wrong response dimension')

    def active(self, items):
        items = frozenset(items)
        return [c for c in self.configurations if c.support <= items]

    def frontier(self, items):
        active = self.active(items)
        return tuple(max(c.values[q] for c in active) for q in range(self.q)) if active else None

    def retention(self, items, level):
        """Check every selected source against a fixed comparison vector."""
        items = frozenset(items)
        active = self.active(items)
        for i in items:
            mass = sum(self.weights[q] for q in range(self.q)
                       if any(i in c.support and c.values[q] >= level[q]-self.tolerance[q]
                              for c in active))
            if mass < self.required_mass:
                return False
        return True

    def valid(self, items, cap, level=None):
        f = self.frontier(items)
        return (f is not None and all(f[q] <= cap[q] for q in range(self.q))
                and (level is None or f == tuple(level)) and self.retention(items, f))


def core_slow(model: Model, ambient, level):
    """Independent synchronous deletion implementation."""
    pool = frozenset(ambient)
    trace = []
    while True:
        active = model.active(pool)
        remove = []
        for item in sorted(pool):
            mass = sum(model.weights[q] for q in range(model.q)
                       if any(item in c.support and c.values[q] >= level[q]-model.tolerance[q]
                              for c in active))
            if mass < model.required_mass:
                remove.append(item)
        if not remove:
            return pool, trace
        trace.append(remove)
        pool -= frozenset(remove)


def support_core(model: Model, ambient, level):
    """Greatest source-supporting subset, using a linear incidence queue.

    Source tests compare to fixed `level`; safety is checked by the caller.
    Each configuration is deactivated at most once. O((C+N)*Q) operations.
    """
    pool = set(ambient)
    if not pool <= model.items:
        raise ValueError('Unknown item in ambient set')
    configs = [c for c in model.configurations if c.support <= pool]
    good = [tuple(c.values[q] >= level[q]-model.tolerance[q] for q in range(model.q))
            for c in configs]
    incidence = {i: [] for i in pool}
    counts = {i: [0]*model.q for i in pool}
    for j, c in enumerate(configs):
        for i in c.support:
            incidence[i].append(j)
            for q in range(model.q):
                counts[i][q] += int(good[j][q])
    def mass(i):
        return sum(model.weights[q] for q in range(model.q) if counts[i][q] > 0)
    queue = deque(sorted(i for i in pool if mass(i) < model.required_mass))
    active = [True]*len(configs)
    trace = []
    while queue:
        i = queue.popleft()
        if i not in pool:
            continue
        if mass(i) >= model.required_mass:
            raise AssertionError('Deletion test lost monotonicity')
        trace.append({'item': i, 'available_task_mass': mass(i)})
        pool.remove(i)
        for j in incidence[i]:
            if not active[j]:
                continue
            active[j] = False
            for other in configs[j].support:
                if other not in pool:
                    continue
                for q in range(model.q):
                    counts[other][q] -= int(good[j][q])
                if mass(other) < model.required_mass:
                    queue.append(other)
    return frozenset(pool), trace


def bipartite_cover(edges, slots):
    """Minimum vertex cover via augmenting paths and Konig's construction.

    Ordinary matching is an established subroutine, not a novel algorithm.
    """
    edges = {frozenset(e) for e in edges}
    adj = {}
    for e in edges:
        if len(e) != 2:
            raise ValueError('Expected graph edges')
        left = next(i for i in e if slots[i] == 0)
        right = next(i for i in e if slots[i] == 1)
        adj.setdefault(left, set()).add(right)
    mate_r = {}
    def augment(left, seen):
        for right in sorted(adj.get(left, ())):
            if right in seen:
                continue
            seen.add(right)
            if right not in mate_r or augment(mate_r[right], seen):
                mate_r[right] = left
                return True
        return False
    for left in sorted(adj):
        augment(left, set())
    mate_l = {left:right for right,left in mate_r.items()}
    reach_l = set(adj)-set(mate_l)
    reach_r = set()
    queue = deque(sorted(reach_l))
    while queue:
        left = queue.popleft()
        for right in adj[left]:
            if mate_l.get(left) == right:
                continue
            if right in reach_r:
                continue
            reach_r.add(right)
            if right in mate_r and mate_r[right] not in reach_l:
                reach_l.add(mate_r[right]); queue.append(mate_r[right])
    cover = (set(adj)-reach_l)|reach_r
    assert len(cover) == len(mate_r)
    assert all(e & cover for e in edges)
    return frozenset(cover)


def fixed_frontier(model: Model, mandatory, level, *, all_branches=False,
                   on_kernel=None, progress=None):
    """Exact existence/constructive solution for frontier == level.

    At most 2**k safe ambient sets are tested, k = size of a minimum
    vertex cover of unresolved above-level future-pair conflicts.
    Counts every selected helper as a retention obligation.
    """
    mandatory = frozenset(mandatory); level = tuple(level)
    if progress is not None:
        progress['fixed_frontiers_started'] = progress.get('fixed_frontiers_started', 0)+1
    if not mandatory <= model.items:
        raise ValueError('Unknown mandatory item')
    unsafe = [c.support for c in model.configurations
              if any(c.values[q] > level[q] for q in range(model.q))]
    if any(e <= mandatory for e in unsafe):
        return {'feasible':False, 'reason':'mandatory_above_frontier', 'cover_size':0,
                'branches':0, 'kernels':[]}
    forbidden = set()
    for e in unsafe:
        residual = e-mandatory
        if len(residual) == 1:
            forbidden.update(residual)
    candidates = model.items-mandatory-forbidden
    edges = {e for e in unsafe if e <= candidates}
    cover = bipartite_cover(edges, model.slots)
    if progress is not None:
        progress['max_cover_encountered'] = max(progress.get('max_cover_encountered', 0), len(cover))
    free = candidates-cover
    cs = sorted(cover)
    kernels = []
    branch_count = 0
    for bits in range(1 << len(cs)):
        selected = frozenset(cs[j] for j in range(len(cs)) if bits >> j & 1)
        if any(e <= selected for e in edges):
            continue
        forbidden_free = set()
        for e in edges:
            if e & selected:
                forbidden_free.update(e-selected)
        ambient = mandatory | selected | (free-forbidden_free)
        assert all(not e <= ambient for e in unsafe)
        kernel, trace = support_core(model, ambient, level)
        branch_count += 1
        if progress is not None:
            progress['branches_completed'] = progress.get('branches_completed', 0)+1
            progress['support_deletions'] = progress.get('support_deletions', 0)+len(trace)
        if mandatory | selected <= kernel and model.frontier(kernel) == level:
            assert model.valid(kernel, level, level)
            kernels.append(kernel)
            if on_kernel is not None:
                on_kernel(kernel)
            if not all_branches:
                break
    return {'feasible': bool(kernels), 'cover_size':len(cover),'cover':cover,
            'branches':branch_count,'kernels':kernels,'unary_forbidden':frozenset(forbidden),
            'conflicts':edges}


def gaining_completion(model: Model, history, cap, gain, gain_mass, *, required=(),
                       progress=None):
    """Find any retention-preserving positive-gain completion, unlimited batch.

    This tests completion, not the number of separate publication dates.
    A returned batch may exceed a user's publication/item budget; report its size.
    """
    history = frozenset(history); mandatory = history | frozenset(required)
    f0 = model.frontier(history)
    if f0 is None or not model.valid(history, cap):
        raise ValueError('Initial history must already be power-safe and retaining')
    if len(gain) != model.q or any(g <= 0 for g in gain):
        raise ValueError('Positive task gains required')
    grid = [sorted({c.values[q] for c in model.configurations
                    if f0[q] <= c.values[q] <= cap[q]}) for q in range(model.q)]
    targets = branches = max_cover = 0
    for level in product(*grid):
        if sum(model.weights[q] for q in range(model.q)
               if level[q]-f0[q] >= gain[q]) < gain_mass:
            continue
        targets += 1
        ans = fixed_frontier(model, mandatory, level, progress=progress)
        branches += ans['branches'];max_cover=max(max_cover,ans['cover_size'])
        if ans['feasible']:
            return {'feasible':True,'items':ans['kernels'][0],
                    'release':ans['kernels'][0]-history,'frontier':level,
                    'targets_tested':targets,'branches_tested':branches,'max_cover':max_cover}
    return {'feasible':False,'targets_tested':targets,'branches_tested':branches,'max_cover':max_cover}


def exhaustive_fixed(model, mandatory, level):
    """Independent complete-subset oracle for small exact tests."""
    mandatory = frozenset(mandatory)
    choices = sorted(model.items-mandatory)
    answers=[]
    for bits in range(1 << len(choices)):
        s=mandatory|frozenset(choices[j] for j in range(len(choices)) if bits>>j&1)
        if model.valid(s, level, tuple(level)):
            answers.append(s)
    return answers


def nae_instance(vertices: int, hyperedges: Iterable[Iterable[int]]):
    """Two-slot realization of hypergraph two-colourability.

    Integer scale of the proof: initial optimum 20, target 24, tolerance 5,
    gain 3, cap 25; all values in {16,20,22,24,30}.  Only (f_i,t_i) are unsafe.
    """
    edges=[frozenset(e) for e in hyperedges]
    if any(not e or not e <= set(range(vertices)) for e in edges):
        raise ValueError('Invalid hyperedge')
    left=['l0']+[f'p{j}' for j in range(len(edges))]+[f'f{i}' for i in range(vertices)]+['d']
    right=['r0']+[f'n{j}' for j in range(len(edges))]+[f't{i}' for i in range(vertices)]
    slots={i:0 for i in left}|{i:1 for i in right}
    configs=[]
    for l in left:
        for r in right:
            v=16
            if (l,r)==('l0','r0'):v=20
            if (l,r)==('d','r0'):v=24
            if l=='l0' and r.startswith('t'):v=22
            if l.startswith('f') and r=='r0':v=22
            if l.startswith('p') and r.startswith('t') and int(r[1:]) in edges[int(l[1:])]:v=22
            if l.startswith('f') and r.startswith('n') and int(l[1:]) in edges[int(r[1:])]:v=22
            if l.startswith('f') and r.startswith('t') and l[1:]==r[1:]:v=30
            configs.append(Configuration(frozenset((l,r)), (v,)))
    model=Model(slots,tuple(configs),(1,),(5,),1)
    history=frozenset(['l0','r0']+[f'p{j}' for j in range(len(edges))]+[f'n{j}' for j in range(len(edges))])
    return model,history


def latent_repair_instance(m: int):
    """Two first updates have identical full current source responses.

    One leaves m distinct Pareto-efficient target rewards completable with one
    helper; the other admits no positive-gain extension at any release width.
    There is exactly one unsafe pair, involving the bad first item and the helper.
    """
    from fractions import Fraction as F
    if m < 1:
        raise ValueError('At least one target reward is required')
    left=['old','bad','good']+[f'c{i}' for i in range(m)]
    slots={i:0 for i in left}|{'base':1,'repair':1}
    configs=[]; parameters={}
    for l in left:
        for r in ('base','repair'):
            if l=='old':values=(F(1),F(1)) if r=='base' else (F(51,50),F(1))
            elif l in ('bad','good'):
                values=(F(21,20),F(21,20)) if (l,r)==('bad','repair') else (F(51,50),F(1))
            else:
                i=int(l[1:]);t=F(1,1000)+F(4,1000)*F(i+1,m+1)
                values=(F(51,50)+t,F(257,250)-t-t*t)
                parameters[l]=t
            configs.append(Configuration(frozenset((l,r)),values))
    model=Model(slots,tuple(configs),(F(1,2),F(1,2)),(F(1,100),F(1,100)),F(1,2))
    return model,frozenset(('old','base')),parameters


def completion_interface(model: Model, history, cap, gain, gain_mass):
    """All inclusion-maximal gaining completions of a fixed valid history.

    This is an exact interface for queries 'can required items D be added in
    some jointly published gaining completion?'. It does not preserve bounded
    batch size, minimum publication cost, or every intermediate release history.
    Explicit representation can have exponentially many maximal completions.
    """
    history = frozenset(history)
    f0 = model.frontier(history)
    if f0 is None or not model.valid(history, cap):
        raise ValueError('Valid starting history required')
    if len(gain) != model.q or any(g <= 0 for g in gain) or not 0 < gain_mass <= 1:
        raise ValueError('Positive gains and valid gain mass required')
    grid = [sorted({c.values[q] for c in model.configurations
                    if f0[q] <= c.values[q] <= cap[q]}) for q in range(model.q)]
    kernels = set();targets = branches = max_cover = 0
    for level in product(*grid):
        if sum(model.weights[q] for q in range(model.q)
               if level[q]-f0[q] >= gain[q]) < gain_mass:
            continue
        targets += 1
        ans = fixed_frontier(model, history, level, all_branches=True)
        branches += ans['branches']; max_cover = max(max_cover, ans['cover_size'])
        kernels.update(ans['kernels'])
    # Descending cardinality makes this a complete inclusion antichain.
    maximal = []
    for k in sorted(kernels, key=lambda s: (-len(s), tuple(sorted(s)))):
        if not any(k <= larger for larger in maximal):
            maximal.append(k)
    return {'kernels':maximal, 'targets_tested':targets, 'branches_tested':branches,
            'max_cover':max_cover, 'raw_kernel_count':len(kernels)}


def interface_included(kernels_a, kernels_b, target_items):
    """Whether every completable target set in A is also completable in B.

    The comparison is over a common target-item universe. Kernel lists must
    represent the exact unbudgeted completion languages under their specified
    contracts. A returned negative witness is a target set, not a full update.
    """
    target_items=frozenset(target_items)
    ka=[frozenset(k)&target_items for k in kernels_a]
    kb=[frozenset(k)&target_items for k in kernels_b]
    for a in ka:
        if not any(a<=b for b in kb):
            return {'included':False,'distinguishing_target':a}
    return {'included':True}


# Campaign adapter. Above is the supplied readable Python reference, with only
# rho=0 enabled for the explicitly labelled disabled-retention control.
import signal
import time
from contextlib import contextmanager
from . import co_exact


class DeadlineExceeded(Exception):
    pass


@contextmanager
def _deadline(seconds):
    if seconds <= 0:
        raise DeadlineExceeded()
    def handler(signum, frame):
        raise DeadlineExceeded()
    old_handler = signal.signal(signal.SIGALRM, handler)
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    seconds = min(seconds, old_timer[0]) if old_timer[0] > 0 else seconds
    started = time.perf_counter()
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.signal(signal.SIGALRM, old_handler)
        remaining = max(1e-6, old_timer[0]-(time.perf_counter()-started)) if old_timer[0] > 0 else 0
        signal.setitimer(signal.ITIMER_REAL, remaining, old_timer[1])


class ReferenceSolver:
    """Readable reference Python, timeout-safe and exactly verified on return."""
    def __init__(self, model, fixed_y=None, seed=0):
        start = time.perf_counter()
        self.data, self.fixed_y = model, fixed_y
        self.model = Model(model.slots, tuple(Configuration(c.support,c.values) for c in model.configurations),
                           model.weights,model.tolerance,model.required_mass)
        self.invalid = not co_exact.initial_valid(model)
        self.build_seconds = time.perf_counter()-start
        self.contract_hash = model.digest

    def query(self,D=(),time_limit=60):
        start = time.perf_counter();D=frozenset(D)
        progress={}
        if not D <= self.data.items:
            raise ValueError('Unknown target item')
        if self.invalid:
            return {'status':'INVALID_INITIAL','elapsed_seconds':time.perf_counter()-start}
        try:
            with _deadline(time_limit):
                if self.fixed_y is None:
                    ans = gaining_completion(self.model,self.data.history,self.data.cap,self.data.gain,self.data.gain_mass,required=D,progress=progress)
                    items = ans.get('items')
                else:
                    y=tuple(map(co_exact.rational,self.fixed_y));f0=self.model.frontier(self.data.history)
                    qualifying = (all(y[q]<=self.data.cap[q] for q in range(self.data.q)) and
                                  sum(self.data.weights[q] for q in range(self.data.q) if y[q]-f0[q]>=self.data.gain[q])>=self.data.gain_mass)
                    ans=fixed_frontier(self.model,self.data.history|D,y,progress=progress) if qualifying else {'feasible':False,'branches':0,'cover_size':0}
                    items=ans.get('kernels',[None])[0] if ans['feasible'] else None
                result={'status':'YES' if ans['feasible'] else 'NO','counters':{k:v for k,v in ans.items() if k in ('targets_tested','branches_tested','max_cover','branches','cover_size')}}
                if items is not None:
                    verifier=co_exact.evaluate(self.data,items,fixed_y=self.fixed_y)
                    assert verifier['valid'],verifier
                    result.update(items=sorted(items),verifier=verifier)
        except DeadlineExceeded:
            result={'status':'UNKNOWN_TIMEOUT'}
        result.setdefault('counters',{}).update(progress)
        result['elapsed_seconds']=time.perf_counter()-start
        return result

    def close(self):
        pass


def solve(model,D=(),fixed_y=None,time_limit=60):
    start=time.perf_counter();solver=ReferenceSolver(model,fixed_y=fixed_y)
    result=solver.query(D,time_limit=time_limit-(time.perf_counter()-start))
    result['build_seconds']=solver.build_seconds
    result['elapsed_seconds']=time.perf_counter()-start
    return result


def compile_interface(model,time_limit=900,fixed_y=None,seed=0):
    start=time.perf_counter();solver=ReferenceSolver(model,fixed_y=fixed_y)
    if solver.invalid:return {'status':'INVALID_INITIAL','complete':False,'kernels':[],'elapsed_seconds':time.perf_counter()-start}
    ref=solver.model;f0=ref.frontier(model.history)
    grid=[sorted({c.values[q] for c in ref.configurations if f0[q]<=c.values[q]<=model.cap[q]}) for q in range(model.q)]
    levels=product(*grid) if fixed_y is None else [tuple(map(co_exact.rational,fixed_y))]
    kernels=set();targets=branches=max_cover=raw=0;complete=False;progress={}
    def save_kernel(k):
        assert co_exact.evaluate(model,k,fixed_y=fixed_y)['valid']
        kernels.add(k)
    try:
        with _deadline(time_limit-(time.perf_counter()-start)):
            for y in levels:
                if any(y[q]>model.cap[q] for q in range(model.q)) or sum(model.weights[q] for q in range(model.q) if y[q]-f0[q]>=model.gain[q])<model.gain_mass:
                    continue
                targets+=1
                ans=fixed_frontier(ref,model.history,y,all_branches=True,on_kernel=save_kernel,progress=progress)
                branches+=ans['branches'];max_cover=max(max_cover,ans['cover_size'])
            complete=True
    except DeadlineExceeded:
        pass
    # Processing and verification charged in elapsed time. Partial valid sets
    # support positive queries; never infer NO from an incomplete enumeration.
    maximal=[]
    for k in sorted(kernels,key=lambda s:(-len(s),tuple(sorted(s)))):
        if not any(k<=larger for larger in maximal):maximal.append(k)
    return {'status':'COMPLETE' if complete else 'UNKNOWN_TIMEOUT','complete':complete,
            'kernels':[sorted(k) for k in maximal],'elapsed_seconds':time.perf_counter()-start,
            'build_seconds':solver.build_seconds,'targets_tested':targets,'branches_tested':branches,
            'max_cover_encountered':max(max_cover,progress.get('max_cover_encountered',0)),
            'raw_kernel_count':len(kernels),'live_counters':progress}
