"""Statistical interface reuse: helper cycles, status direction and contracts."""
from copy import deepcopy
from itertools import combinations
import unittest
import numpy as np

from wowfs.experiments.co_native_analysis import certify_queries,finite_bounds
from wowfs.experiments.co_certificate_service import compile_certificate,query_interface,seal_interface
from test_co_native_analysis import toy_world,toy_moments


def cyclic_certificate(gain='.15',covariance=None,helper_response=22,headroom='.25'):
    w=toy_world(3,2,1);means=np.array([[20,16,24,16,16,helper_response]],dtype=float)
    m=toy_moments(w,means,covariance,n=100)
    rule=dict(tolerance='.25',headroom=headroom,gain=gain,retention_mass='1',gain_mass='1')
    return certify_queries(w,m,finite_bounds(m,rule,.0025),rule,'base')


class CertificateServiceTests(unittest.TestCase):
    def test_mutually_supporting_helpers_enter_maximal_completion(self):
        c=cyclic_certificate();interface=compile_certificate(c)
        self.assertEqual(interface['modes']['supported']['maximal_masks'],['0x1f'])
        answer=query_interface(interface,['a01'])
        self.assertEqual(answer['status'],'YES')
        self.assertEqual(set(answer['witness']),set(c['replay_certificate']['items']))
        # Either helper alone fails, although both together are retained.
        from wowfs.experiments.co_native_analysis import verify_replay_publication
        self.assertFalse(verify_replay_publication(c,['a00','x0','a01','a02'])['valid'])
        self.assertFalse(verify_replay_publication(c,['a00','x0','a01','x1'])['valid'])

    def test_target_monotonicity(self):
        interface=compile_certificate(cyclic_certificate(helper_response=30))
        names=interface['items']
        answers={frozenset(t):query_interface(interface,t)['status'] for n in range(len(names)+1) for t in combinations(names,n)}
        self.assertEqual(set(answers.values()),{'YES','NO'})
        for a,sa in answers.items():
            for b,sb in answers.items():
                if a<=b:
                    if sb=='YES':self.assertEqual(sa,'YES')
                    if sa=='NO':self.assertEqual(sb,'NO')

    def test_incomplete_possible_interface_never_issues_no(self):
        interface=compile_certificate(cyclic_certificate(gain='1'))
        self.assertEqual(query_interface(interface,[])['status'],'NO')  # Empty D still requires gain.
        for partial in ('whole','possible'):
            changed=deepcopy(interface)
            if partial=='whole':changed['complete']=False
            else:changed['modes']['possible']['complete']=False
            self.assertEqual(query_interface(seal_interface(changed),[])['status'],'UNKNOWN')

    def test_uncertain_initial_is_not_query_no(self):
        c=cyclic_certificate(covariance=np.array([np.eye(6)*1e8]));interface=compile_certificate(c)
        self.assertEqual(query_interface(interface,[])['status'],'UNKNOWN_INITIAL')

    def test_invalid_initial_is_retained(self):
        interface=compile_certificate(cyclic_certificate(headroom='-.1'))
        self.assertEqual(query_interface(interface,['a01'])['status'],'INVALID_INITIAL')

    def test_unknown_item_contract_change_and_tampering_are_rejected(self):
        interface=compile_certificate(cyclic_certificate())
        with self.assertRaisesRegex(ValueError,'INVALID_QUERY'):query_interface(interface,['new_unmeasured_gear'])
        with self.assertRaisesRegex(ValueError,'Requested contract'):query_interface(interface,[],expected_contract_sha256='wrong')
        changed=deepcopy(interface);changed['items'].append('unmeasured')
        with self.assertRaisesRegex(ValueError,'content hash'):query_interface(changed,[])


if __name__=='__main__':unittest.main()
