"""Exact direct rank CP-SAT and persistent assumptions SAT/PB baselines.

The SAT model uses threshold OR chains and PB constraints; it does not enumerate
Cartesian frontiers. Glucose's persistent object preserves learned state across
calls. CP-SAT model reuse is deliberately not called learned-clause reuse.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from math import lcm
from threading import Timer
import time

from .co_exact import evaluate, frontier, initial_valid, rational


def integer_weights(model):
    values = model.weights + (model.required_mass, model.gain_mass)
    denominator = lcm(*(x.denominator for x in values))
    integers = tuple(int(x*denominator) for x in values)
    if sum(abs(x) for x in integers) >= 2**60:
        raise OverflowError('Exact task-mass integer coefficients exceed conservative int64 guard')
    return integers[:-2], integers[-2], integers[-1]


def _result(model, items, D, fixed_y):
    if not frozenset(D) <= items:
        raise AssertionError('Solver omitted required target')
    verifier = evaluate(model, items, fixed_y=fixed_y)
    if not verifier['valid']:
        raise AssertionError(('Invalid solver witness', verifier))
    return {'status': 'YES', 'items': sorted(items), 'verifier': verifier}


class CPSatSolver:
    """Single-thread exact max-rank encoding; assumptions reset each query."""
    def __init__(self, model, fixed_y=None, seed=0):
        from ortools.sat.python import cp_model
        start = time.perf_counter()
        self.data, self.fixed_y, self.seed = model, fixed_y, seed
        self.cp = cp_model
        self.invalid = not initial_valid(model)
        self.model = m = cp_model.CpModel()
        self.p = {i: m.new_bool_var('p_'+i) for i in sorted(model.items)}
        self.z = [m.new_bool_var('z_'+str(j)) for j in range(len(model.configurations))]
        for i in model.history:
            m.add(self.p[i] == 1)
        for c, z in zip(model.configurations, self.z):
            for i in c.support:
                m.add_implication(z, self.p[i])
            m.add_bool_or([z] + [self.p[i].Not() for i in c.support])
        weights, rho, gain_mass = integer_weights(model)
        f0 = frontier(model, model.history)
        hs = {i: [] for i in model.items}
        gains = []
        for q in range(model.q):
            values = sorted({c.values[q] for c in model.configurations})
            f = m.new_int_var(-1, max(-1, len(values)-1), 'f_'+str(q))
            if self.z:
                ranks = {x:j for j, x in enumerate(values)}
                m.add_max_equality(f, [(ranks[c.values[q]]+1)*z-1 for c,z in zip(model.configurations,self.z)])
            else:
                m.add(f == -1)
            m.add(f >= 0)
            m.add(f <= bisect_right(values, model.cap[q])-1)
            if fixed_y is not None:
                y = rational(fixed_y[q])
                m.add(f == values.index(y)) if y in values else m.add_bool_or([])
            useful = []
            for j, (c,z) in enumerate(zip(model.configurations,self.z)):
                upper = bisect_right(values,c.values[q]+model.tolerance[q])-1
                bound = m.new_bool_var(f'bound_{q}_{j}')
                m.add(f <= upper).only_enforce_if(bound)
                m.add(f > upper).only_enforce_if(bound.Not())
                t = m.new_bool_var(f't_{q}_{j}')
                m.add_implication(t,z);m.add_implication(t,bound)
                m.add_bool_or([t,z.Not(),bound.Not()])
                useful.append(t)
            for i in sorted(model.items):
                h = m.new_bool_var(f'h_{q}_{i}')
                ts = [useful[j] for j,c in enumerate(model.configurations) if i in c.support]
                for t in ts:
                    m.add_implication(t,h)
                m.add_bool_or(ts+[h.Not()])
                hs[i].append(h)
            g = m.new_bool_var('gain_'+str(q))
            j = bisect_left(values,f0[q]+model.gain[q]) if f0 else len(values)
            m.add(f >= j).only_enforce_if(g)
            m.add(f < j).only_enforce_if(g.Not())
            gains.append(g)
        for i in sorted(model.items):
            m.add(sum(w*h for w,h in zip(weights,hs[i])) >= rho).only_enforce_if(self.p[i])
        m.add(sum(w*g for w,g in zip(weights,gains)) >= gain_mass)
        self.build_seconds = time.perf_counter()-start
        self.contract_hash = model.digest

    def query(self, D=(), time_limit=60, *, strict_superset=None):
        start = time.perf_counter()
        D = frozenset(D)
        if not D <= self.data.items:
            raise ValueError('Unknown target item')
        if self.invalid:
            return {'status':'INVALID_INITIAL','elapsed_seconds':time.perf_counter()-start}
        if time_limit <= 0:
            return {'status':'UNKNOWN_TIMEOUT','elapsed_seconds':time.perf_counter()-start}
        m = self.model if strict_superset is None else self.model.clone()
        m.clear_assumptions()
        required = D | (frozenset(strict_superset) if strict_superset is not None else frozenset())
        m.add_assumptions([self.p[i] for i in sorted(required)])
        if strict_superset is not None:
            m.add_bool_or([self.p[i] for i in sorted(self.data.items-frozenset(strict_superset))])
        solver = self.cp.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = self.seed
        solver.parameters.max_time_in_seconds = max(1e-6,time_limit-(time.perf_counter()-start))
        status = solver.solve(m)
        native = solver.status_name(status)
        if status in (self.cp.OPTIMAL,self.cp.FEASIBLE):
            items = frozenset(i for i,p in self.p.items() if solver.value(p))
            result = _result(self.data,items,required,self.fixed_y)
        elif status == self.cp.INFEASIBLE:
            result = {'status':'NO','proof_checked':False}
        elif status == self.cp.MODEL_INVALID:
            raise RuntimeError('CP-SAT MODEL_INVALID: '+solver.response_stats())
        else:
            result = {'status':'UNKNOWN_TIMEOUT'}
        result.update(native_status=native,elapsed_seconds=time.perf_counter()-start,
                      solver_wall_seconds=solver.wall_time,conflicts=solver.num_conflicts,branches=solver.num_branches)
        return result

    def block_subsets(self,K):
        self.model.add_bool_or([self.p[i] for i in sorted(self.data.items-frozenset(K))])

    def close(self):
        pass


class IncrementalSAT:
    """One Glucose4 object per contract, assumptions and clauses persist correctly."""
    def __init__(self, model, fixed_y=None, seed=0):
        from pysat.formula import IDPool
        from pysat.pb import PBEnc
        from pysat.solvers import Glucose4
        start = time.perf_counter()
        self.data,self.fixed_y,self.seed = model,fixed_y,seed
        self.invalid = not initial_valid(model)
        self.pool = pool = IDPool()
        self.p = {i:pool.id(('p',i)) for i in sorted(model.items)}
        self.clauses = []
        add = self.clauses.append
        def make_or(inputs,label):
            h=pool.id(label)
            for t in inputs: add([-t,h])
            add([-h]+list(inputs))
            return h
        def make_and(inputs,label):
            h=pool.id(label)
            for t in inputs: add([-h,t])
            add([h]+[-t for t in inputs])
            return h
        for i in sorted(model.history): add([self.p[i]])
        z = [make_and([self.p[i] for i in sorted(c.support)],('z',j)) for j,c in enumerate(model.configurations)]
        weights,rho,gain_mass = integer_weights(model)
        f0=frontier(model,model.history)
        hs={i:[] for i in model.items};gains=[]
        for q in range(model.q):
            values=sorted({c.values[q] for c in model.configurations})
            rank={v:j for j,v in enumerate(values)}
            grouped=[[] for _ in values]
            for j,c in enumerate(model.configurations): grouped[rank[c.values[q]]].append(z[j])
            thresholds=[None]*len(values)
            above=pool.id(('above_all',q));add([-above])
            for j in reversed(range(len(values))):
                thresholds[j]=make_or(grouped[j]+[above],('threshold',q,j));above=thresholds[j]
            if thresholds: add([thresholds[0]])
            else: add([])
            cap_rank=bisect_right(values,model.cap[q])
            if cap_rank<len(values): add([-thresholds[cap_rank]])
            if fixed_y is not None:
                y=rational(fixed_y[q]);j=bisect_left(values,y)
                if j==len(values) or values[j]!=y: add([])
                else:
                    add([thresholds[j]])
                    if j+1<len(values): add([-thresholds[j+1]])
            ts=[]
            for j,c in enumerate(model.configurations):
                b=bisect_right(values,c.values[q]+model.tolerance[q])
                inputs=[z[j]]+([-thresholds[b]] if b<len(values) else [])
                ts.append(make_and(inputs,('useful',q,j)))
            for i in sorted(model.items):
                hs[i].append(make_or([ts[j] for j,c in enumerate(model.configurations) if i in c.support],('h',i,q)))
            j=bisect_left(values,f0[q]+model.gain[q]) if f0 else len(values)
            if j<len(values): gains.append(thresholds[j])
            else:
                g=pool.id(('gain_false',q));add([-g]);gains.append(g)
        def pb_atleast(lits,bound,conditional=None):
            pairs=[(lit,w) for lit,w in zip(lits,weights) if w]
            if bound<=0:return
            cnf=PBEnc.atleast(lits=[x for x,w in pairs],weights=[w for x,w in pairs],bound=bound,vpool=pool)
            for clause in cnf.clauses: add(([-conditional] if conditional else [])+clause)
        for i in sorted(model.items): pb_atleast(hs[i],rho,self.p[i])
        pb_atleast(gains,gain_mass)
        self.solver=Glucose4(bootstrap_with=self.clauses,incr=True)
        # Glucose4 API exposes no portable random seed option; seed is metadata.
        self.build_seconds=time.perf_counter()-start
        self.contract_hash=model.digest
        self.query_count=0

    def query(self,D=(),time_limit=60,*,strict_superset=None):
        start=time.perf_counter();D=frozenset(D)
        if not D<=self.data.items:raise ValueError('Unknown target item')
        if self.invalid:return {'status':'INVALID_INITIAL','elapsed_seconds':time.perf_counter()-start}
        if time_limit<=0:return {'status':'UNKNOWN_TIMEOUT','elapsed_seconds':time.perf_counter()-start}
        required=D|(frozenset(strict_superset) if strict_superset is not None else frozenset())
        assumptions=[self.p[i] for i in sorted(required)]
        gate=None
        if strict_superset is not None:
            gate=self.pool.id(('strict_superset',self.query_count))
            self.solver.add_clause([-gate]+[self.p[i] for i in sorted(self.data.items-frozenset(strict_superset))])
            assumptions.append(gate)
        self.query_count+=1
        self.solver.clear_interrupt()
        timer=Timer(max(1e-6,time_limit-(time.perf_counter()-start)),self.solver.interrupt)
        timer.daemon=True;timer.start()
        try:
            status=self.solver.solve_limited(assumptions=assumptions,expect_interrupt=True)
        finally:
            timer.cancel();timer.join();self.solver.clear_interrupt()
        if status is True:
            positives=set(x for x in self.solver.get_model() if x>0)
            items=frozenset(i for i,p in self.p.items() if p in positives)
            result=_result(self.data,items,required,self.fixed_y)
        elif status is False:
            core=self.solver.get_core() or []
            reverse={p:i for i,p in self.p.items()}
            result={'status':'NO','proof_checked':False,'unsat_core':[reverse[x] for x in core if x in reverse],
                    'core_includes_strict_superset_gate':gate in core if gate else False}
        else:result={'status':'UNKNOWN_TIMEOUT'}
        result.update(native_status='SAT' if status else 'UNSAT' if status is False else 'INTERRUPTED',
                      elapsed_seconds=time.perf_counter()-start,solver_cumulative_stats=self.solver.accum_stats())
        return result

    def block_subsets(self,K):
        self.solver.add_clause([self.p[i] for i in sorted(self.data.items-frozenset(K))])

    def close(self):
        self.solver.delete()


def compile_interface(method,model,time_limit=900,fixed_y=None,seed=0):
    """Enumerate maximal feasible sets using strict-superset queries, not 1-adds."""
    start=time.perf_counter()
    cls={'sat':IncrementalSAT,'cpsat':CPSatSolver}[method]
    solver=cls(model,fixed_y=fixed_y,seed=seed)
    kernels=[];maximal=[];queries=0;complete=False;status='UNKNOWN_TIMEOUT'
    try:
        if solver.invalid:return {'status':'INVALID_INITIAL','kernels':[],'complete':False,'elapsed_seconds':time.perf_counter()-start}
        while time.perf_counter()-start<time_limit:
            ans=solver.query(time_limit=time_limit-(time.perf_counter()-start));queries+=1
            if ans['status']=='NO':complete=True;status='COMPLETE';break
            if ans['status']!='YES':break
            p=frozenset(ans['items'])
            while True:
                # Preserve a valid witness even if maximality proof times out.
                kernels=[k for k in kernels if not frozenset(k)<=p]
                if not any(p<=frozenset(k) for k in kernels):kernels.append(sorted(p))
                ans=solver.query(time_limit=time_limit-(time.perf_counter()-start),strict_superset=p);queries+=1
                if ans['status']=='YES':
                    newer=frozenset(ans['items']);assert p<newer;p=newer;continue
                if ans['status']=='NO':
                    maximal.append(sorted(p));solver.block_subsets(p);break
                break
            if ans['status']!='NO':break
    finally:solver.close()
    return {'status':status,'complete':complete,'kernels':maximal if complete else kernels,
            'proven_maximal':maximal,'queries':queries,'elapsed_seconds':time.perf_counter()-start,
            'build_seconds':solver.build_seconds,'proof_checked':False}
