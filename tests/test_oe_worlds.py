"""Structural checks on the exploration input contract, without native execution."""
from copy import deepcopy
import unittest
from wowfs.experiments.oe_worlds import worlds, jobs_for_world, FAMILIES


class OpenWorldsTests(unittest.TestCase):
    def test_registry_is_unique_and_mutation_isolated(self):
        first=worlds(); second=worlds()
        self.assertEqual(len(first),96)
        self.assertEqual(len({w['world_id'] for w in first}),96)
        self.assertEqual(len({w['mechanism_id'] for w in first}),12)
        first[0]['tasks'][0]['duration']=999
        self.assertNotEqual(first[0],second[0])
        self.assertEqual(first[0]['initial_validity'],'not_assessed_until_native_observations')

    def test_every_full_physical_cross_survives_generation(self):
        count=0
        for w in worlds():
            jobs=jobs_for_world(w,'test',1000,2,'full')
            expected=17*4*2*len(w['policies'])
            self.assertEqual(len(jobs),expected)
            self.assertEqual(len({(j['meta']['candidate_index'],j['meta']['partner_index'],
                j['meta']['task_id'],j['meta']['policy_id']) for j in jobs}),expected)
            for job in jobs:
                self.assertEqual(len(job['meta']['component_incidence']),2)
                self.assertEqual(job['input']['request']['simOptions']['iterations'],2)
                self.assertEqual(job['input']['request']['simOptions']['randomSeed'],'1000')
            count+=len(jobs)
        self.assertEqual(count,15232)

    def test_actual_task_and_policy_interventions(self):
        w=next(w for w in worlds() if w['mechanism_id']=='resistance_penetration')
        jobs=jobs_for_world(w,'test',1,1,{'candidate_indices':[0],'partner_indices':[0]})
        resistance=[j['input']['request']['encounter']['targets'][0]['stats'][37] for j in jobs]
        self.assertEqual(resistance,[0,75])
        w=next(w for w in worlds() if w['mechanism_id']=='policy_resource' and w['context']['class']=='Warlock')
        jobs=jobs_for_world(w,'test',1,1,{'candidate_indices':[0],'partner_indices':[0],'task_indices':[0]})
        def recovery(job):
            rows=job['input']['request']['raid']['parties'][0]['players'][0]['rotation']['priorityList']
            return next(r['action']['condition'] for r in rows if r['action'].get('castSpell',{}).get('spellId',{}).get('spellId')==11689)
        self.assertNotEqual(recovery(jobs[0]),recovery(jobs[1]))
        self.assertEqual(recovery(jobs[1])['cmp']['rhs']['const']['val'],'35%')

    def test_joint_slots_do_not_mislabel_future_columns_as_old(self):
        w=next(w for w in worlds() if w['mechanism_id']=='joint_slots')
        self.assertEqual(w['initial_partner_ids'],[0])
        self.assertEqual(w['model_scope'],'joint_two_update_slots')
        w=next(w for w in worlds() if w['mechanism_id']=='mana_regen')
        self.assertEqual(w['initial_partner_ids'],[0,1,2,3])

    def test_raw_distance_and_native_variant_identity(self):
        w=next(w for w in worlds() if w['mechanism_id']=='periodic_refresh')
        a=w['candidates'][0]
        self.assertEqual(a['native_base_item_id'],12795)
        distance=a['distance_to_native_base']['changed_parameters']
        self.assertEqual(distance['proc_ppm']['native'],1.)
        self.assertEqual(distance['periodic_damage_per_tick']['native'],10.)
        self.assertEqual(a['parameter_overrides']['proc_ppm'],distance['proc_ppm']['research'])


if __name__=='__main__':
    unittest.main()
