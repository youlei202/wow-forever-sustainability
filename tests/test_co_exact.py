"""Campaign correctness gate; --audit-out executes the complete frozen-seed battery."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import argparse
import hashlib
import json
import random
import time
import unittest

from wowfs.experiments.co_exact import Configuration, Model, evaluate, exhaustive, interface_query, rational
from wowfs.experiments.co_generic import CPSatSolver, IncrementalSAT, compile_interface
from wowfs.experiments.co_reference import ReferenceSolver, compile_interface as ref_compile, latent_repair_instance


def tiny(index):
    rng = random.Random(926270000+index)
    nl,nr,q = rng.randrange(2,5),rng.randrange(2,4),rng.randrange(1,4)
    slots = {f'l{i}':0 for i in range(nl)}|{f'r{i}':1 for i in range(nr)}
    if index%3==0:
        weights = (F(1),) if q==1 else tuple([F(0)]+[F(1,q-1)]*(q-1))
    else:
        nums = [rng.randrange(1,5) for _ in range(q)];weights=tuple(F(n,sum(nums)) for n in nums)
    configs=[]
    for l in range(nl):
        for r in range(nr):
            if (l,r)!=(0,0) and rng.random()<.15:continue
            for policy in range(2 if index%7==0 else 1):
                values=tuple(F(rng.randrange(-4,7),2) for _ in range(q))
                configs.append(Configuration(frozenset((f'l{l}',f'r{r}')),values))
    h={'l0','r0'}
    if index%11==0:h|={'l1','r1'}
    history_rows=[c for c in configs if c.support<=h]
    f0=tuple(max(c.values[t] for c in history_rows) for t in range(q))
    tolerance=tuple(F(rng.randrange(0,9),2) for _ in range(q))
    cap=tuple(f+F(rng.randrange(0,7),2) for f in f0)
    # Explicit invalid histories remain in denominators.
    if index%13==0:cap=tuple(x-F(1,2) for x in f0)
    rho=F(rng.randrange(1,11),10)
    if index%29==0:rho=F(0)
    return Model(slots,tuple(configs),weights,tolerance,rho,frozenset(h),cap,(F(1,2),)*q,F(rng.randrange(1,11),10))


def cyclic():
    slots={'old':0,'target':0,'helper_l':0,'base':1,'helper_r':1}
    rows=[('old','base',20),('old','helper_r',16),('target','base',24),('target','helper_r',16),('helper_l','base',16),('helper_l','helper_r',22)]
    return Model(slots,tuple(Configuration(frozenset((l,r)),(v,)) for l,r,v in rows),(1,),(5,),1,frozenset(('old','base')),(25,),(3,),1)


def renamed(model):
    mapping={i:'renamed_'+str(j) for j,i in enumerate(sorted(model.items))}
    return replace(model,slots={mapping[i]:s for i,s in model.slots.items()},
                   configurations=tuple(Configuration(frozenset(mapping[i] for i in c.support),c.values) for c in model.configurations),
                   history=frozenset(mapping[i] for i in model.history)),mapping


def audit(output,count=1200):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter();records=[];comparisons=0;interface_count=0;metamorphic=0
    feature_counts={'instances':count,'negative_response_tables':0,'multiple_policy_tables':0,'zero_weight_tables':0,'invalid_initial':0,'yes_queries':0,'no_queries':0}
    # Persist full deterministic inputs before observing solver outputs.
    models=[tiny(i) for i in range(count)]
    models[:1]=[cyclic()]
    for j,which in enumerate(('bad','good'),1):
        ref,h,_=latent_repair_instance(2)
        models[j]=Model(ref.slots,tuple(Configuration(c.support,c.values) for c in ref.configurations),ref.weights,ref.tolerance,ref.required_mass,h|{which},(F(103,100),)*2,(F(1,100),)*2,F(1,2))
    fixture_bytes=''.join(json.dumps(m.to_dict(),sort_keys=True)+'\n' for m in models).encode()
    (output/'CORRECTNESS_INPUTS.jsonl').write_bytes(fixture_bytes)
    for index,m in enumerate(models):
        optional=sorted(m.items-m.history)
        D=frozenset(optional[j] for j in range(len(optional)) if (index+3*j)%4==0)
        fixed_y=tuple(sorted({c.values[q] for c in m.configurations})[(index+q)%len({c.values[q] for c in m.configurations})] for q in range(m.q))
        if index%17==0:fixed_y=tuple(v+F(1,13) for v in fixed_y)
        feature_counts['negative_response_tables']+=any(v<0 for c in m.configurations for v in c.values)
        feature_counts['zero_weight_tables']+=0 in m.weights
        feature_counts['multiple_policy_tables']+=len({c.support for c in m.configurations})<len(m.configurations)
        row={'index':index,'hash':m.digest,'queries':[]}
        try:
            for y in (None,fixed_y):
                truth=exhaustive(m,all_solutions=True,fixed_y=y)
                if y is None:feature_counts['invalid_initial']+=truth['status']=='INVALID_INITIAL'
                expected_k={frozenset(k) for k in truth.get('kernels',[])}
                classes=(ReferenceSolver,CPSatSolver,IncrementalSAT)
                solvers=[cls(m,fixed_y=y) for cls in classes]
                try:
                    for target in (frozenset(),D,frozenset(optional),frozenset(optional[:1])):
                        expected='INVALID_INITIAL' if truth['status']=='INVALID_INITIAL' else ('YES' if any(target<=frozenset(k) for k in truth.get('solutions',[])) else 'NO')
                        feature_counts['yes_queries']+=expected=='YES';feature_counts['no_queries']+=expected=='NO'
                        for solver in solvers:
                            ans=solver.query(target,time_limit=10);comparisons+=1
                            assert ans['status']==expected,(index,type(solver).__name__,y,target,expected,ans)
                            if ans['status']=='YES':assert evaluate(m,ans['items'],fixed_y=y)['valid']
                        row['queries'].append({'fixed_y':list(map(str,y)) if y else None,'target':sorted(target),'status':expected})
                finally:
                    for solver in solvers:solver.close()
                for name in ('reference','sat','cpsat'):
                    ans=ref_compile(m,time_limit=10,fixed_y=y) if name=='reference' else compile_interface(name,m,time_limit=10,fixed_y=y)
                    interface_count+=1
                    if truth['status']=='INVALID_INITIAL':assert ans['status']=='INVALID_INITIAL'
                    else:
                        assert ans['complete'],(index,name,ans)
                        assert {frozenset(k) for k in ans['kernels']}==expected_k,(index,name,y,expected_k,ans)
            if index<200 and exhaustive(m)['status']!='INVALID_INITIAL':
                old=exhaustive(m,D)
                ren,mapping=renamed(m)
                assert exhaustive(ren,[mapping[i] for i in D])['status']==old['status'];metamorphic+=1
                relaxed=replace(m,cap=tuple(v+1 for v in m.cap),tolerance=tuple(v+1 for v in m.tolerance),gain=tuple(v/2 for v in m.gain))
                assert old['status']!='YES' or exhaustive(relaxed,D)['status']=='YES';metamorphic+=1
                sup=exhaustive(m,m.items)
                assert old['status']!='NO' or sup['status']=='NO';metamorphic+=1
                # New optional source, with all old rows untouched, cannot erase witness.
                clone=next(i for i,s in m.slots.items() if s==0)
                extension=replace(m,slots=m.slots|{'new_optional':0},configurations=m.configurations+tuple(Configuration((c.support-{clone})|{'new_optional'},c.values) for c in m.configurations if clone in c.support))
                assert old['status']!='YES' or exhaustive(extension,D)['status']=='YES';metamorphic+=1
            records.append(row)
        except Exception as exc:
            (output/'COUNTEREXAMPLE.json').write_text(json.dumps({'index':index,'model':m.to_dict(),'target':sorted(D),'fixed_y':list(map(str,fixed_y)),'error':repr(exc)},indent=2))
            raise
        if (index+1)%100==0:
            (output/'PROGRESS.json').write_text(json.dumps({'completed_instances':index+1,'comparisons':comparisons,'interfaces':interface_count,'elapsed_seconds':time.perf_counter()-started}))
    report={'status':'PASS','features':feature_counts,'decision_comparisons':comparisons,'complete_interface_comparisons':interface_count,'metamorphic_checks':metamorphic,
            'input_sha256':hashlib.sha256(fixture_bytes).hexdigest(),'elapsed_seconds':time.perf_counter()-started,
            'seed_rule':'random.Random(926270000+index); first three cases are cyclic and latent bad/good',
            'no_formal_unsat_proof_checker':True}
    (output/'CORRECTNESS_RESULTS.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in records))
    (output/'CORRECTNESS_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


class ContractTests(unittest.TestCase):
    def test_float_rejected(self):
        with self.assertRaises(TypeError):rational(.1)
        with self.assertRaises(TypeError):rational(True)

    def test_gain_mass_checked(self):
        with self.assertRaises(ValueError):replace(cyclic(),gain_mass=0)

    def test_cycles_require_joint_extension(self):
        m=cyclic();base=m.history|{'target'}
        self.assertTrue(evaluate(m,base)['valid'])
        for h in ('helper_l','helper_r'):self.assertFalse(evaluate(m,base|{h})['valid'])
        self.assertTrue(evaluate(m,m.items)['valid'])
        for method in ('sat','cpsat'):
            ans=compile_interface(method,m)
            self.assertEqual(ans['kernels'],[sorted(m.items)])

    def test_partial_never_excludes(self):
        self.assertEqual(interface_query({'complete':False,'kernels':[]},[])['status'],'UNKNOWN_TIMEOUT')
        self.assertEqual(interface_query({'complete':False,'kernels':[['x']]},['x'])['status'],'YES')
        self.assertEqual(interface_query({'status':'INVALID_INITIAL','complete':False,'kernels':[]},[])['status'],'INVALID_INITIAL')

    def test_reference_saves_kernel_before_branch_timeout(self):
        from unittest.mock import patch
        from wowfs.experiments import co_reference
        original=co_reference.fixed_frontier
        def interrupted(*args,**kwargs):
            callback=kwargs['on_kernel']
            def save_then_interrupt(k):
                callback(k)
                raise co_reference.DeadlineExceeded()
            kwargs['on_kernel']=save_then_interrupt
            return original(*args,**kwargs)
        with patch.object(co_reference,'fixed_frontier',interrupted):
            result=co_reference.compile_interface(cyclic())
        self.assertFalse(result['complete'])
        self.assertTrue(result['kernels'])
        self.assertEqual(interface_query(result,['target'])['status'],'YES')
        self.assertTrue(all(evaluate(cyclic(),k)['valid'] for k in result['kernels']))

    def test_assumptions_clear_and_persist(self):
        m=cyclic();m=replace(m,slots=m.slots|{'isolated':0})
        s=IncrementalSAT(m)
        identity=id(s.solver)
        try:
            self.assertEqual(s.query(['isolated'])['status'],'NO')
            self.assertEqual(s.query(['target'])['status'],'YES')
            self.assertEqual(id(s.solver),identity)
            self.assertGreaterEqual(s.solver.accum_stats()['restarts'],1)
        finally:s.close()

    def test_policy_expansion_is_not_optional_candidate(self):
        m=cyclic();self.assertEqual(exhaustive(m)['status'],'YES')
        expanded=replace(m,configurations=m.configurations+(Configuration(frozenset(('old','base')),(26,)),))
        self.assertEqual(exhaustive(expanded)['status'],'INVALID_INITIAL')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--audit-out');parser.add_argument('--count',type=int,default=1200)
    args,remaining=parser.parse_known_args()
    if args.audit_out:print(json.dumps(audit(args.audit_out,args.count),indent=2))
    else:unittest.main(argv=['test_co_exact.py']+remaining)
