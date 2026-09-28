import unittest
import numpy as np
from wowfs.experiments.co_projection import project


class TaskProjectionTests(unittest.TestCase):
    def test_projection_reuses_original_event_not_a_smaller_family(self):
        world={"world_sha256":"original","tasks":[{"task_id":str(q)} for q in range(4)],"task_weights":[.25]*4}
        moments={"world_sha256":"original","means":np.arange(12).reshape(4,3),
                 "covariance":np.arange(36).reshape(4,3,3),"reference_indices":[0,0,0,0],
                 "domain":{"task_ids":[str(q) for q in range(4)]}}
        bounds={"cap_lower":np.arange(12).reshape(4,3),"manifest":{"alpha":.0025,"family_size":9312,"critical":5.1}}
        w,m,b=project(world,moments,bounds)
        self.assertEqual(w["task_weights"],[.5,.5])
        self.assertEqual([x["task_id"] for x in w["tasks"]],["0","3"])
        np.testing.assert_array_equal(m["means"],moments["means"][[0,3]])
        np.testing.assert_array_equal(b["cap_lower"],bounds["cap_lower"][[0,3]])
        for key in ("alpha","family_size","critical"):self.assertEqual(b["manifest"][key],bounds["manifest"][key])
        self.assertEqual(world["task_weights"],[.25]*4)


if __name__=="__main__":unittest.main()
