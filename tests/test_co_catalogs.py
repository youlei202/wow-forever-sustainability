import unittest

from wowfs.experiments.co_catalogs import jobs_for_world, worlds
from wowfs.experiments.fc_native import SLOTS, native_database, validate_equipment


class CatalogueRegistrationTests(unittest.TestCase):
    def test_declared_denominators_and_independence_unit(self):
        rows = worlds()
        self.assertEqual(len(rows),24)
        self.assertEqual(sum(w["split"]=="development" for w in rows),8)
        self.assertEqual(sum(w["split"]=="validation" for w in rows),16)
        self.assertEqual(sum(w["candidate_expansion_registered"] for w in rows),8)
        self.assertEqual(sum(len(w["tasks"])==4 for w in rows),4)
        self.assertEqual(len({w["stratum"] for w in rows}),4)
        self.assertEqual(len({w["world_sha256"] for w in rows}),24)
        menus = {(tuple(a["native_base_item_id"] for a in w["candidates"]),
                  tuple(a["native_base_item_id"] for a in w["partners"])) for w in rows}
        self.assertEqual(len(menus),24)

    def test_complete_crosses_and_optional_expansion(self):
        for w in worlds():
            jobs = jobs_for_world(w,"test",1300000001,1)
            self.assertEqual(len(jobs),len(w["candidates"])*len(w["partners"])*len(w["tasks"]))
            base = jobs_for_world(w,"test",1300000001,1,"base")
            expanded_by_key = {(j["meta"]["configuration_id"],j["meta"]["task_index"]):j["input"] for j in jobs}
            for job in base:
                self.assertEqual(job["input"], expanded_by_key[(job["meta"]["configuration_id"],job["meta"]["task_index"])])
            for j in jobs:
                self.assertEqual(j["input"]["research_variants"],[])
                validate_equipment(j["input"])
            self.assertEqual(w["history"],["a00","x0"])
            self.assertEqual([len(q["required"]) for q in w["queries"]],[1,1,1,1,2,2,2,3])
            for q in w["queries"]:
                self.assertFalse(set(q["required"]) & set(w["history"]))
                self.assertTrue(set(q["required"]) <= {f"a{i:02}" for i in range(8)}|{f"x{i}" for i in range(4)})

    def test_registry_has_no_observation_based_selection(self):
        for w in worlds():
            self.assertIn("metadata_only",w["candidate_sampling"])
            self.assertEqual(w["support_status"],"source_and_equipment_checked_not_native_executed")
            self.assertEqual(sum(w["task_weights"]),1)
            for a in w["candidates"]+w["partners"]:
                self.assertFalse(a["parameter_overrides"])
                self.assertIn(a["native_base_item_id"],native_database())


if __name__ == "__main__":
    unittest.main()
