import unittest
import numpy as np

from wowfs.experiments.co_exact import exhaustive, evaluate
from wowfs.experiments.co_native_analysis import finite_bounds, certify_queries, model_from_moments, heuristic_queries, verify_replay_publication


def toy_world(nleft=4,nright=3,q=2):
    return dict(world_id="toy",world_sha256="toy",candidates=[{}]*nleft,partners=[{}]*nright,
                base_candidate_indices=list(range(nleft)),base_partner_indices=list(range(nright)),
                tasks=[{"task_id":f"q{i}"} for i in range(q)],task_weights=[1/q]*q,
                history=["a00","x0"],queries=[{"query_id":"target","required":["a01"]},
                {"query_id":"two_helpers","required":["a02","x1"]}])


def toy_moments(world,means,cov=None,n=100):
    pairs=[(i,j) for i in range(len(world["candidates"])) for j in range(len(world["partners"]))]
    q,m=means.shape
    return dict(means=means,covariance=np.zeros((q,m,m)) if cov is None else cov,N=n,
                reference_indices=[0]*q,domain={"pairs":pairs})


class NativeCertificateTests(unittest.TestCase):
    def test_heuristic_success_verified_and_failure_is_unknown(self):
        world=toy_world()
        means=np.array([[10,10.6,11,10.2,10.9,11.1,10.1,10.6,11.2,10.3,11,11.3]]*2)
        moments=toy_moments(world,means)
        rule=dict(tolerance="0.2",headroom="0.5",gain="0.01",retention_mass="1/2",gain_mass="1/2")
        model=model_from_moments(world,moments,rule,"base")
        rows=heuristic_queries(model,world["queries"])
        self.assertEqual(len(rows),10)
        for row in rows:
            self.assertIn(row["status"],("YES","UNKNOWN"))
            if row["status"]=="YES":self.assertTrue(evaluate(model,row["verifier"]["items"])["valid"])

    def test_zero_noise_exhaustion_agrees_independent_exact_oracle(self):
        rng=np.random.default_rng(4109)
        world=toy_world()
        rule=dict(tolerance="0.037",headroom="0.18",gain="0.013",retention_mass="1/2",gain_mass="1/2")
        for _ in range(40):
            means=rng.uniform(8,13,(2,12));means[:,0]=10
            moments=toy_moments(world,means)
            bounds=finite_bounds(moments,rule,.0025)
            answers=certify_queries(world,moments,bounds,rule,"base")
            model=model_from_moments(world,moments,rule,"base")
            for query,answer in zip(world["queries"],answers["queries"]):
                self.assertEqual(answer["status"],exhaustive(model,query["required"])["status"])
                if answer["witness"] is not None:
                    self.assertTrue(verify_replay_publication(answers,answer["witness"])["valid"])

    def test_nonfinite_moments_are_rejected(self):
        world=toy_world();means=np.ones((2,12));means[0,4]=np.nan
        rule=dict(tolerance="0.01",headroom="0.1",gain="0.01",retention_mass="1/2",gain_mass="1/2")
        with self.assertRaises(ValueError):finite_bounds(toy_moments(world,means),rule,.0025)

    def test_wide_uncertainty_never_certifies_a_false_mean_negative(self):
        world=toy_world()
        means=np.array([[10,10.6,11,10.2,10.9,11.1,10.1,10.6,11.2,10.3,11,11.3]]*2)
        moments=toy_moments(world,means,np.array([np.eye(12)*100]*2),n=4)
        rule=dict(tolerance="0.2",headroom="0.5",gain="0.01",retention_mass="1/2",gain_mass="1/2")
        answers=certify_queries(world,moments,finite_bounds(moments,rule,.0025),rule,"base")
        self.assertTrue(all(a["status"].startswith("UNKNOWN") for a in answers["queries"]))

    def test_optional_menu_expansion_preserves_supported_completion(self):
        world=toy_world(4,3)
        world["base_candidate_indices"]=[0,1,2]
        world["base_partner_indices"]=[0,1]
        means=np.array([[10,10.7,30,10.2,10.8,40,10.1,10.9,50,60,70,80]]*2)
        moments=toy_moments(world,means)
        rule=dict(tolerance="0.2",headroom="0.5",gain="0.01",retention_mass="1/2",gain_mass="1/2")
        bounds=finite_bounds(moments,rule,.0025)
        base=certify_queries(world,moments,bounds,rule,"base")
        expanded=certify_queries(world,moments,bounds,rule,"expanded")
        self.assertTrue(all(x["status"]=="YES" for x in base["queries"]))
        self.assertTrue(all(x["status"]=="YES" for x in expanded["queries"]))
        self.assertEqual(base["bounds_manifest"],expanded["bounds_manifest"])


if __name__=="__main__": unittest.main()
