"""Independent finite-domain checks for directions, incidence and real timeouts."""
from dataclasses import replace, asdict
from functools import lru_cache
from itertools import combinations, count
import json
import unittest
from unittest.mock import patch
import numpy as np
from wowfs.experiments.oe_solver import Problem,Configuration,fixed_partner_problem
from wowfs.experiments.oe_inference import FiniteBounds
from wowfs.experiments.oe_confidence_planner import confidence_capacity


def constant_bounds(p,utilities=None):
    values=np.array([c.utilities for c in p.configurations]) if utilities is None else np.asarray(utilities)
    samples=np.repeat(values[:,:,None],8,axis=2)
    reference=np.repeat(np.asarray(p.reference)[:,None],8,axis=1)
    return FiniteBounds(samples,reference,p.gain,p.tolerance,p.cap,.05)


def independent_capacity(p,B):
    """Population checker written without either production evaluator."""
    allitems=set(p.items);base=set(p.initial_items);weights=np.array(p.task_weights)
    reference=np.array(p.reference)
    def legal(published):
        configs=[c for c in p.configurations if c.items<=published]
        if not configs:return False,None
        values=np.array([c.utilities for c in configs])/reference
        frontier=values.max(axis=0)
        if np.any(values>p.cap+1e-12):return False,frontier
        for item in published:
            uses=[c for c in configs if item in c.items]
            if not uses:return False,frontier
            source=np.array([c.utilities for c in uses]).max(axis=0)/reference
            if weights[source-frontier+p.tolerance>=-1e-12].sum()<p.retention_mass-1e-12:
                return False,frontier
        return True,frontier
    if not legal(base)[0]:return None
    @lru_cache(None)
    def visit(published):
        present=set(published);frontier=legal(present)[1];best=0
        for size in range(1,min(B,len(allitems-present))+1):
            for batch in combinations(sorted(allitems-present),size):
                future=present|set(batch)
                if p.total_item_budget is not None and len(future-base)>p.total_item_budget:continue
                valid,f=legal(future)
                if valid and weights[f-frontier>=p.gain-1e-12].sum()>=p.gain_mass-1e-12:
                    best=max(best,1+visit(tuple(sorted(future))))
        return best
    return visit(tuple(sorted(base)))


def repair_problem():
    table=np.array([[[100.],[96.]],[[104.],[97.]],[[99.],[102.]]])
    return fixed_partner_problem(table,row_ids=['old','growth','repair'],partner_ids=['x','y'],
        initial_rows=['old'],task_weights=[1.],reference=[100.],gain=.03,cap=1.1,
        tolerance=.05,gain_mass=1.,retention_mass=1.,epsilon=0.)


def ladder(n=6):
    items=tuple('a'+str(i) for i in range(n+1))
    configs=tuple(Configuration(x,frozenset([x]),(100.+3*i,)) for i,x in enumerate(items))
    return Problem(items,frozenset(['a0']),configs,(1.,),(100.,),.02,5.,1.,1.,1.,epsilon=0.)


class ConfidencePlannerTests(unittest.TestCase):
    def test_matched_first_source_capacity_differs_while_value_capacity_agrees(self):
        table=np.array([[[100.],[99.]],[[102.],[97.]],[[102.],[102.]],
                        [[103.],[98.]],[[104.],[99.]],[[105.],[99.]]])
        p=fixed_partner_problem(table,row_ids=['a0','A','B','c','d','e'],partner_ids=['x','y'],
            initial_rows=['a0'],task_weights=[1.],reference=[100.],gain=.01,cap=1.05,
            tolerance=.05,gain_mass=1.,retention_mass=1.,epsilon=0.)
        b=constant_bounds(p)
        for first,retention_capacity in [('A',2),('B',3)]:
            initial=set(p.initial_items)|{first}
            kept=confidence_capacity(p,b,'upper',initial_items=initial)
            value=confidence_capacity(p,b,'upper',initial_items=initial,retention=False)
            witness=confidence_capacity(p,b,'lower',initial_items=initial,retention=False)
            self.assertEqual(kept.capacity_upper,retention_capacity)
            self.assertEqual(value.capacity_upper,3)
            self.assertEqual(witness.capacity_lower,3)
            self.assertFalse(value.retention_enforced)
            self.assertEqual(value.bounds_manifest,kept.bounds_manifest) # exact same alpha family
            self.assertIn('B' if first=='A' else 'A',value.remaining_candidates)
            self.assertFalse(value.path_checks[-1]['checks']['retention']['enforced'])
            if first=='A':
                self.assertFalse(value.path_checks[-1]['checks']['retention']['upper'])
                self.assertTrue(value.path_checks[-1]['upper'])
                self.assertIn('y',value.path_checks[-1]['sources'])

    def test_value_only_orphan_is_diagnostic_but_power_and_gain_remain_enforced(self):
        p=replace(ladder(3),items=ladder(3).items+('orphan',),
                  initial_items=ladder(3).initial_items|{'orphan'})
        b=constant_bounds(p)
        kept=confidence_capacity(p,b,'upper')
        value=confidence_capacity(p,b,'upper',retention=False)
        self.assertEqual(kept.status,'initial_excluded')
        self.assertEqual(value.capacity_upper,3)
        self.assertFalse(value.initial_checks['sources']['orphan']['upper'])
        self.assertTrue(value.initial_checks['upper'])
        narrow=replace(p,cap=1.05)
        result=confidence_capacity(narrow,constant_bounds(narrow),'upper',retention=False)
        self.assertEqual(result.capacity_upper,1) # 106 remains physically over cap
        no_initial=replace(p,configurations=p.configurations[1:])
        result=confidence_capacity(no_initial,constant_bounds(no_initial),'upper',retention=False)
        self.assertEqual(result.status,'initial_excluded')

    def test_coordination_graphs_against_independent_population_oracle(self):
        p=repair_problem();b=constant_bounds(p)
        for B,capacity in [(1,0),(2,1),(4,1)]:
            self.assertEqual(independent_capacity(p,B),capacity)
            lower=confidence_capacity(p,b,'lower',B)
            upper=confidence_capacity(p,b,'upper',B)
            self.assertEqual(lower.capacity_lower,capacity)
            self.assertEqual(lower.capacity_upper,2) # lower graph is not a true UB
            self.assertEqual(upper.capacity_upper,capacity)
            self.assertEqual(upper.capacity_lower,0) # optimistic path proves no LB
            self.assertEqual(lower.graph_capacity_upper,capacity)
            self.assertEqual(upper.graph_capacity_lower,capacity)
            self.assertTrue(lower.graph_search_complete)
            self.assertTrue(upper.graph_search_complete)
            self.assertIn('optimistic',upper.path_kind)
            if B>1:
                self.assertEqual(set(lower.batches[0]),{'growth','repair'})
                self.assertEqual(set(lower.path_checks[0]['sources']),set(p.items))
            json.dumps(asdict(upper),allow_nan=False)

    def test_random_small_multitask_tables_match_independent_exhaustive_search(self):
        rng=np.random.default_rng(792)
        for _ in range(10):
            table=rng.integers(97,114,size=(4,2,2)).astype(float)
            table[0]=[[100,100],[98,99]]
            p=fixed_partner_problem(table,row_ids=['a0','a1','a2','a3'],partner_ids=['x','y'],
                initial_rows=['a0'],task_weights=[.5,.5],reference=[100.,100.],gain=.03,
                cap=1.12,tolerance=.07,gain_mass=.5,retention_mass=.5,epsilon=0.)
            b=constant_bounds(p)
            for B in (1,2,4):
                target=independent_capacity(p,B)
                lower=confidence_capacity(p,b,'lower',B)
                upper=confidence_capacity(p,b,'upper',B)
                self.assertEqual(lower.capacity_lower,target)
                self.assertEqual(upper.capacity_upper,target)

    def test_new_new_cross_is_activated_and_rejects_joint_overpower(self):
        items=('a0','b0','a1','b1')
        configs=tuple(Configuration(str(i),frozenset(pair),(u,)) for i,(pair,u) in enumerate([
            (('a0','b0'),100.),(('a1','b0'),104.),(('a0','b1'),104.),(('a1','b1'),112.)]))
        p=Problem(items,frozenset(['a0','b0']),configs,(1.,),(100.,),.03,1.1,.05,1.,1.,epsilon=0.)
        b=constant_bounds(p)
        for B in (1,2,4):
            result=confidence_capacity(p,b,'upper',B)
            self.assertEqual(result.capacity_upper,1)
            self.assertEqual(len(result.batches),1)
            self.assertEqual(len(result.batches[0]),1)

    def test_point_utilities_and_reference_headroom_do_not_reject_states(self):
        p=repair_problem();b=constant_bounds(p)
        # The point table claims every config is overpowered and every reference
        # is huge. Neither is allowed to decide confidence graph membership.
        poison=replace(p,configurations=tuple(replace(c,utilities=(1e9,)) for c in p.configurations),
                       reference=(1e8,))
        result=confidence_capacity(poison,b,'upper',2)
        self.assertEqual(result.capacity_upper,1)
        self.assertEqual(set(result.batches[0]),{'growth','repair'})

    def test_uncertain_initial_is_not_mislabeled_invalid_or_zero(self):
        p=ladder(1)
        p=replace(p,gain=.005,cap=1.05,tolerance=.5)
        samples=np.array([[[10.,190.,10.,190.]],[[101.,101.,101.,101.]]])
        b=FiniteBounds(samples,np.full((1,4),100.),p.gain,p.tolerance,p.cap,.05)
        low=confidence_capacity(p,b,'lower')
        self.assertEqual(low.status,'initial_unresolved')
        self.assertIsNone(low.capacity_lower)
        self.assertEqual(low.capacity_upper,1)
        high=confidence_capacity(p,b,'upper')
        self.assertEqual(high.initial_status,'unresolved')
        self.assertEqual(high.capacity_upper,1)
        self.assertIsNone(high.capacity_lower)
        excluded=FiniteBounds(np.full((2,1,4),200.),np.full((1,4),100.),p.gain,p.tolerance,p.cap,.05)
        result=confidence_capacity(p,excluded,'upper')
        self.assertEqual(result.status,'initial_excluded')
        self.assertIsNone(result.capacity_upper)
        self.assertIsNone(result.capacity_lower)

    def test_optimistic_gain_path_survives_mean_gain_failure(self):
        p=replace(ladder(1),gain=.1,tolerance=.5,cap=10.)
        samples=np.array([[[100.,100.,100.,100.]],[[90.,110.,90.,130.]]])
        b=FiniteBounds(samples,samples[0],p.gain,p.tolerance,p.cap,.05)
        lo=confidence_capacity(p,b,'lower')
        hi=confidence_capacity(p,b,'upper')
        self.assertEqual(lo.capacity_lower,0)
        self.assertEqual(lo.capacity_upper,1)
        self.assertEqual(hi.capacity_upper,1)
        self.assertEqual(hi.capacity_lower,0)
        self.assertFalse(hi.path_checks[0]['checks']['gain']['mean'])
        self.assertTrue(hi.path_checks[0]['checks']['gain']['upper'])

    def test_zero_timeout_and_interrupted_incumbent_keep_safe_bounds(self):
        p=ladder();b=constant_bounds(p)
        for mode in ('lower','upper'):
            result=confidence_capacity(p,b,mode,timeout_seconds=0.)
            self.assertEqual(result.status,'timeout')
            self.assertFalse(result.graph_search_complete)
            self.assertEqual(result.capacity_upper,6)
            self.assertEqual(result.capacity_lower,0)
        times=count(0.,.1)
        with patch('wowfs.experiments.oe_confidence_planner.time.monotonic',side_effect=lambda:next(times)):
            result=confidence_capacity(p,b,'lower',timeout_seconds=.45)
        self.assertEqual(result.status,'timeout')
        self.assertGreater(result.capacity_lower,0)
        self.assertLess(result.capacity_lower,6)
        self.assertEqual(result.capacity_lower,len(result.batches))
        self.assertEqual(result.capacity_upper,6)
        self.assertTrue(all(row['lower'] for row in result.path_checks))

    def test_continuation_budget_and_missing_published_source(self):
        p=replace(ladder(3),total_item_budget=1)
        b=constant_bounds(p)
        result=confidence_capacity(p,b,'upper',initial_items=['a0','a1'])
        self.assertEqual(result.capacity_upper,0)
        self.assertEqual(result.remaining_item_budget,0)
        missing=replace(p,items=p.items+('orphan',),initial_items=p.initial_items|{'orphan'})
        result=confidence_capacity(missing,b,'upper')
        self.assertEqual(result.status,'initial_excluded')
        self.assertFalse(result.initial_checks['sources']['orphan']['upper'])

    def test_limits_and_threshold_identity_fail_loudly(self):
        p=ladder(2);b=constant_bounds(p)
        with self.assertRaises(ValueError): confidence_capacity(p,b,max_candidates=1)
        with self.assertRaises(ValueError): confidence_capacity(p,b,max_candidates=20)
        with self.assertRaises(ValueError): confidence_capacity(p,b,batch_limit=0)
        with self.assertRaises(ValueError): confidence_capacity(p,b,timeout_seconds=-1)
        with self.assertRaises(ValueError): confidence_capacity(replace(p,gain=.03),b)
        with self.assertRaises(ValueError): confidence_capacity(replace(p,tolerance=.3),b)
        with self.assertRaises(ValueError): confidence_capacity(p,b,initial_items=['a1'])


if __name__=='__main__':unittest.main()
