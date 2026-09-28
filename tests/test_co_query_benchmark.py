"""Query-driven maximal completion caches preserve exact answers and budgets."""
from fractions import Fraction
import unittest
from unittest.mock import patch

from wowfs.experiments.co_exact import evaluate, exhaustive
from wowfs.experiments.co_generic import IncrementalSAT
from wowfs.experiments.co_query_benchmark import maximal_sat_query, compute, BudgetExpired
from test_co_exact import tiny, cyclic


class MaximalCacheTests(unittest.TestCase):
    def test_cycles_and_later_assumptions(self):
        model=cyclic();solver=IncrementalSAT(model)
        try:
            first=maximal_sat_query(solver,['target'],5)
            self.assertEqual(first['status'],'YES');self.assertTrue(first['maximality_proved'])
            self.assertEqual(set(first['items']),model.items)
            second=maximal_sat_query(solver,['helper_l'],5)
            self.assertEqual(second['status'],'YES')
            self.assertTrue(evaluate(model,second['items'])['valid'])
        finally:solver.close()

    def test_growth_timeout_keeps_verified_yes(self):
        model=cyclic();items=sorted(model.history|{'target'})
        class Fake:
            def __init__(self):self.calls=0
            def query(self,*args,**kwargs):
                self.calls+=1
                if self.calls==1:return {'status':'YES','items':items,'verifier':evaluate(model,items)}
                return {'status':'UNKNOWN_TIMEOUT'}
        answer=maximal_sat_query(Fake(),['target'],5)
        self.assertEqual(answer['status'],'YES');self.assertEqual(answer['items'],items)
        self.assertFalse(answer['maximality_proved']);self.assertEqual(answer['maximization_status'],'UNKNOWN_TIMEOUT')

    def test_history_alarm_keeps_yes_and_requires_stop(self):
        model=cyclic();items=sorted(model.history|{'target'})
        class Fake:
            def __init__(self):self.calls=0
            def query(self,*args,**kwargs):
                self.calls+=1
                if self.calls==1:return {'status':'YES','items':items,'verifier':evaluate(model,items)}
                raise BudgetExpired('test alarm')
        answer=maximal_sat_query(Fake(),['target'],5)
        self.assertEqual(answer['status'],'YES');self.assertTrue(answer['stop_after_query'])
        job={'instance':{'instance_id':'unit_test_only',**model.to_dict()},'method':'sat_maximal_cache',
             'workflow':'repeat_queries','budget_seconds':5,'per_query_seconds':1,
             'query_stream':{'queries':[{'query_index':1,'target':['target'],'query_kind':'singleton'},
                                        {'query_index':2,'target':['helper_l'],'query_kind':'singleton'}],'prefixes':[1,2]}}
        with patch('wowfs.experiments.co_query_benchmark.maximal_sat_query',return_value=answer):
            result,interface,text=compute(job)
        self.assertEqual(result['status'],'UNKNOWN_TIMEOUT');self.assertEqual(result['queries_answered'],1)
        self.assertEqual(len(text.splitlines()),1)

    def test_initial_no_only_core(self):
        class Fake:
            def query(self,*args,**kwargs):return {'status':'NO','unsat_core':['impossible']}
        result=maximal_sat_query(Fake(),['impossible'],5)
        self.assertEqual(result,{'status':'NO','unsat_core':['impossible']})

    def test_300_models_against_all_subsets(self):
        for index in range(300):
            model=tiny(index);truth=exhaustive(model,all_solutions=True)
            solutions=[frozenset(s) for s in truth.get('solutions',[])]
            optional=sorted(model.items-model.history)
            targets=[[],optional[:1],optional]
            solver=IncrementalSAT(model)
            try:
                for target in targets:
                    result=maximal_sat_query(solver,target,5)
                    expected='INVALID_INITIAL' if truth['status']=='INVALID_INITIAL' else 'YES' if any(set(target)<=s for s in solutions) else 'NO'
                    self.assertEqual(result['status'],expected,(index,target,result))
                    if expected=='YES':
                        p=frozenset(result['items'])
                        self.assertTrue(result['maximality_proved'])
                        self.assertIn(p,solutions)
                        self.assertFalse(any(p<s for s in solutions),(index,p))
            finally:solver.close()


if __name__=='__main__':unittest.main()
