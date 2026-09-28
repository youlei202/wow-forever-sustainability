"""Synthetic assembly and budget/direction tests; no native simulations are run."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from wowfs.paths import canonical_hash
from wowfs.experiments.oe_confirmation import (
    assemble,analyze_claim,analyze,_validate_claim_scope,_expected_seed_block)


def fixture(policies=('native',)):
    domain={'candidate_ids':['a00','a01','a02'],'partner_ids':['x0','x1'],
            'task_ids':['task_z','task_a'],'policy_ids':list(policies)}
    values={('a00','x0'):100.,('a00','x1'):104.,('a01','x0'):104.,
            ('a01','x1'):112.,('a02','x0'):104.,('a02','x1'):106.}
    rows=[]
    for a,x,q,k in product(domain['candidate_ids'],domain['partner_ids'],domain['task_ids'],domain['policy_ids']):
        rows.append({'world_id':'toy','candidate_id':a,'partner_id':x,'task_id':q,'policy_id':k,
            'observed_or_reconstructed':'observed','seed_block_id':'4000:8','iterations':8,
            'dps_samples':[values[a,x]]*8,'input_sha256':'synthetic-'+a+x+q+k,'cache_key':'fixture'})
    claim={'claim_id':'toy_decision','kind':'joint_and_first','world_id':'toy','model_scope':'joint_two_update_slots',
        'initial_items':['a00','x0'],
        'reference_mapping':[{'task_id':q,'candidate_id':'a00','partner_id':'x0','policy_id':'native'} for q in domain['task_ids']],
        'gain':.01,'headroom':.1,'tolerance':.2,'task_weights':[.5,.5],
        'gain_mass':.5,'retention_mass':.5,'alpha':.02,'first_pair':['a01','a02'],'joint_pair':['a01','x1'],
        'batch_limits':[1,2],'max_candidates':19,'timeout_seconds':10.,
        'frozen_paths':{'safe':[['a02'],['x1']],'unsafe':[['a01'],['x1']]}}
    return rows,claim,domain


class ConfirmationTests(unittest.TestCase):
    def test_order_and_fixed_reference_are_identified_without_reselection(self):
        rows,claim,domain=fixture(policies=('native','alternative'))
        table=assemble(list(reversed(rows)),claim,domain)
        self.assertEqual(table['task_order'],['task_a','task_z'])
        self.assertEqual(table['configuration_order'][0],('a00','x0','alternative'))
        self.assertEqual(table['samples'].shape,(12,2,8))
        np.testing.assert_array_equal(table['reference'],100.)
        self.assertTrue(all(r['policy_id']=='native' for r in table['reference_identity']))
        self.assertEqual(table['problem'].initial_items,{'a00','x0'})

    def test_complete_domain_and_samples_fail_closed(self):
        rows,claim,domain=fixture()
        with self.assertRaises(ValueError):assemble(rows[:-1],claim,domain)
        with self.assertRaises(ValueError):assemble(rows+[rows[0]],claim,domain)
        changed=deepcopy(rows);changed[0]['observed_or_reconstructed']='interpolated'
        with self.assertRaises(ValueError):assemble(changed,claim,domain)
        changed=deepcopy(rows);changed[0]['seed_block_id']='4001:8'
        with self.assertRaises(ValueError):assemble(changed,claim,domain)
        changed=deepcopy(rows);changed[0]['dps_samples']=changed[0]['dps_samples'][:-1]
        with self.assertRaises(ValueError):assemble(changed,claim,domain)
        changed=deepcopy(claim);changed['reference_mapping'][0]['candidate_id']='a01'
        with self.assertRaises(ValueError):assemble(rows,changed,domain)

    def test_joint_five_contrasts_and_equivalent_first_updates(self):
        rows,claim,domain=fixture()
        result=analyze_claim(rows,claim,domain)
        self.assertIsNone(result['claim_supported'])
        allocation=result['alpha_allocation']
        self.assertEqual(allocation['core_family'],.01)
        self.assertEqual(allocation['matched_first_family'],.005)
        self.assertEqual(allocation['joint_linear_family'],.005)
        self.assertAlmostEqual(sum(v for k,v in allocation.items() if k!='claim_total'),.02)
        self.assertTrue(result['matched_first']['equivalence_supported'])
        self.assertTrue(result['matched_first']['first_prefixes']['a01']['steps'][0]['lower'])
        self.assertEqual(result['matched_first']['continuations']['a01'][1]['upper']['capacity_upper'],0)
        self.assertEqual(result['matched_first']['continuations']['a02'][1]['lower']['capacity_lower'],1)
        self.assertIn('value_only_continuations',result['matched_first'])
        self.assertEqual(result['matched_first']['value_only_alpha_additional'],0.)
        self.assertFalse(result['matched_first']['value_only_continuations']['a01'][1]['upper']['retention_enforced'])
        joint=result['joint']
        self.assertEqual(joint['family_size'],10)
        self.assertTrue(joint['both_single_component_pairs_cap_supported'])
        self.assertTrue(joint['joint_pair_cap_excluded'])
        self.assertTrue(joint['separable_prediction_cap_supported'])
        self.assertTrue(joint['positive_mixed_interaction_supported_any_task'])
        self.assertEqual(joint['contrasts']['mixed_interaction']['mean'],[4.,4.])
        self.assertEqual(result['frozen_paths']['safe']['prefix_lengths']['lower'],2)
        self.assertEqual(result['frozen_paths']['unsafe']['prefix_lengths']['upper'],1)
        json.dumps(result,allow_nan=False)

    def test_joint_negative_control_reuses_an_expanded_single_family(self):
        rows,claim,domain=fixture()
        claim.pop('first_pair')
        claim['joint_negative_controls']=[{'control_id':'weaker_pair','joint_pair':['a02','x1']}]
        result=analyze_claim(rows,claim,domain)
        self.assertEqual(result['joint']['family_size'],20)
        control=result['joint']['negative_controls'][0]
        self.assertEqual(control['family_size'],20)
        self.assertEqual(control['alpha'],result['joint']['alpha'])
        self.assertEqual(control['contrasts']['mixed_interaction']['mean'],[-2.,-2.])
        self.assertFalse(control['positive_mixed_interaction_supported_any_task'])
        self.assertEqual(result['alpha_allocation']['joint_linear_family'],.01)

    def test_no_equivalence_from_merely_uncertain_difference_and_policy_scope(self):
        rows,claim,domain=fixture()
        for row in rows:
            if row['candidate_id']=='a01' and row['partner_id']=='x0':
                row['dps_samples']=[50.,150.,50.,150.,50.,150.,50.,150.]
        result=analyze_claim(rows,claim,domain)
        self.assertFalse(result['matched_first']['equivalence_supported'])
        rows,claim,domain=fixture(policies=('native','alternative'))
        result=analyze_claim(rows,claim,domain)
        self.assertEqual(result['joint']['status'],'not_evaluated_scope_limitation')
        claim['aux_policy_id']='native'
        result=analyze_claim(rows,claim,domain)
        self.assertEqual(result['joint']['status'],'evaluated_fixed_policy')

    def test_unknown_kind_still_runs_core_and_unused_alpha_is_not_recycled(self):
        rows,claim,domain=fixture()
        claim.pop('first_pair');claim.pop('joint_pair');claim['kind']='future_new_branch'
        result=analyze_claim(rows,claim,domain)
        self.assertIn(1,result['capacity'])
        self.assertEqual(result['alpha_allocation']['core_family'],.01)
        self.assertEqual(result['alpha_allocation']['reserved_unused_auxiliary'],.01)

    def test_registry_initial_and_weight_override_and_seed_contract(self):
        _,claim,domain=fixture()
        world={**domain,'initial_candidate_ids':[0],'initial_partner_ids':[0,1],
               'task_weights':[.2,.8]}
        with self.assertRaises(ValueError):_validate_claim_scope({'worlds':{'toy':world}},claim,
            {**domain,'task_ids':sorted(domain['task_ids'])})
        claim['initial_override_reason']='Frozen research history with only x0 initially published'
        claim['task_weight_override_reason']='Frozen equal task measure'
        _validate_claim_scope({'worlds':{'toy':world}},claim,{**domain,'task_ids':sorted(domain['task_ids'])})
        with self.assertRaises(ValueError):_expected_seed_block({},claim)
        self.assertEqual(_expected_seed_block({'seed':4000,'iterations':8},claim),'4000:8')
        with self.assertRaises(ValueError):_expected_seed_block({'seed':0,'iterations':8},claim)
        with self.assertRaises(ValueError):_expected_seed_block({'seed_block_id':'4000:8','iterations':9},claim)

    def test_end_to_end_freeze_hash_seed_binary_and_new_output_guards(self):
        rows,claim,domain=fixture();claim.pop('first_pair');claim.pop('joint_pair')
        jobs=[]
        for row in rows:
            meta={k:row[k] for k in ('world_id','candidate_id','partner_id','task_id','policy_id')}
            physics={'request':{'simOptions':{'randomSeed':'4000','iterations':8}},'fixture_identity':meta}
            jobs.append({'input':physics,'meta':meta})
            row['input_sha256']=canonical_hash(physics);row['binary_sha256']='fixture-binary'
        manifest={'claims':[claim],'worlds':{'toy':domain},'seed_block_id':'4000:8'}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);batch=root/'batch';batch.mkdir();manifest_path=root/'manifest.json'
            manifest_path.write_text(json.dumps(manifest))
            (batch/'RESULTS.json').write_text(json.dumps({'status':'completed','errors':[],'rows':rows}))
            (batch/'JOBS.json').write_text(json.dumps(jobs))
            protocol={'phase':'confirm','binary_sha256':'fixture-binary','jobs_sha256':canonical_hash(jobs),
                      'science':{'confirmation_manifest_sha256':canonical_hash(manifest)}}
            (batch/'PROTOCOL.json').write_text(json.dumps(protocol))
            result=analyze(batch,manifest_path,root/'analysis')
            self.assertTrue(result['pre_outcome_freeze_verified'])
            self.assertEqual(result['status'],'completed')
            with self.assertRaises(ValueError):analyze(batch,manifest_path,root/'analysis')
            protocol['jobs_sha256']='altered'
            (batch/'PROTOCOL.json').write_text(json.dumps(protocol))
            with self.assertRaises(ValueError):analyze(batch,manifest_path,root/'bad_jobs')
            protocol['jobs_sha256']=canonical_hash(jobs);protocol['binary_sha256']='other'
            (batch/'PROTOCOL.json').write_text(json.dumps(protocol))
            with self.assertRaises(ValueError):analyze(batch,manifest_path,root/'bad_binary')
            protocol['binary_sha256']='fixture-binary';manifest['seed_block_id']='9999:8'
            manifest_path.write_text(json.dumps(manifest))
            protocol['science']['confirmation_manifest_sha256']=canonical_hash(manifest)
            (batch/'PROTOCOL.json').write_text(json.dumps(protocol))
            with self.assertRaises(ValueError):analyze(batch,manifest_path,root/'bad_seed')
            manifest['claims'][0]['alpha']=.06;manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):analyze(batch,manifest_path,root/'bad_alpha')


if __name__=='__main__':unittest.main()
