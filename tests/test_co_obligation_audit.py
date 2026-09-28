import unittest
import numpy as np
from wowfs.experiments.co_native_analysis import finite_bounds,certify_queries
from wowfs.experiments.co_obligation_audit import audit,obligations


class ObligationAuditTests(unittest.TestCase):
    def test_scope_partition_excludes_history_and_target_from_helpers(self):
        p,h,d=0b11111,0b00011,0b00100
        self.assertEqual(obligations("only_helpers",p,h,d),0b11000)
        self.assertEqual(obligations("drop_helpers",p,h,d),0b00111)
        self.assertEqual(obligations("drop_history",p,h,d),0b11100)

    def test_old_sources_really_can_be_the_essential_block(self):
        w=dict(world_id="toy",candidates=[{}]*3,partners=[{}]*2,
               base_candidate_indices=[0,1,2],base_partner_indices=[0,1],
               tasks=[{"task_id":"q0"},{"task_id":"q1"}],task_weights=[.5,.5],history=["a00","x0"],
               queries=[{"query_id":"target","required":["a01"]}])
        mean=np.array([[10,13,12,12.6,11,11.5]]*2)
        moments=dict(means=mean,covariance=np.zeros((2,6,6)),N=100,reference_indices=[0,0],
                     domain={"pairs":[(i,j) for i in range(3) for j in range(2)]})
        rule=dict(tolerance=".05",headroom=".5",gain=".01",retention_mass="1/2",gain_mass="1/2")
        cert=certify_queries(w,moments,finite_bounds(moments,rule,.0025),rule,"base")
        result=audit(cert)["queries"][0]
        self.assertEqual(result["scopes"]["all"]["status"],"NO")
        self.assertEqual(result["scopes"]["drop_history"]["status"],"YES")
        self.assertTrue(result["diagnostic_labels"]["legacy_necessary_for_obstruction"])
        self.assertTrue(result["diagnostic_labels"]["legacy_alone_sufficient"])
        self.assertFalse(result["diagnostic_labels"]["targets_alone_sufficient"])


if __name__=="__main__":unittest.main()
