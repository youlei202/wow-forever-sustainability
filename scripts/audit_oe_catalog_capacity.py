"""Independent read-only moment/finite-prefix audit; imports no campaign solver.

Run after sourcing scripts/env.sh. This verifies the frozen finite-domain
optimistic upper bounds for B=2 after the bad first release, and supported
returned retaining/value paths for both first releases and B=1/2. No new
statistical family, native samples or threshold choice is introduced.
"""
from collections import Counter
from itertools import combinations, product
from pathlib import Path
import hashlib
import json
import time

import numpy as np
from scipy.stats import t

ROOT = Path('/work/Users/leiyo/wow-forever-sustainability-work/artifacts/open-exploration-2026-09-26/campaign-v1')
DEST = ROOT / 'checks/SECONDARY_CATALOG_CAPACITY_CHECK.json'
assert not DEST.exists(), 'Never overwrite a completed secondary audit.'
manifest_path = ROOT / 'CONFIRMATION_MANIFEST_V2.json'
manifest = json.loads(manifest_path.read_text())
moment_path = ROOT / 'analysis/confirm-v2-compact-moments/MOMENTS.npz'
moments = np.load(moment_path)
moment_manifest_path = moment_path.with_name('MOMENTS_MANIFEST.json')
moment_manifest = json.loads(moment_manifest_path.read_text())
worlds = {x['world_id']: x for x in manifest['worlds']}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class IndependentAudit:
    def __init__(self, ordinal):
        self.ordinal = ordinal
        self.claim = manifest['claims'][ordinal-1]
        self.path = ROOT / f'analysis/confirm-v2-results/CLAIM_{ordinal:02}.json'
        self.saved = json.loads(self.path.read_text())
        self.meta = moment_manifest['worlds'][ordinal-1]
        assert self.claim['claim_id'] == self.saved['claim_id'] == self.meta['claim_id']
        prefix = self.meta['array_prefix']
        self.mu = moments[prefix+'_mean']
        self.cov = moments[prefix+'_covariance']
        self.n = int(moments[prefix+'_N'])
        self.order = [tuple(c) for c in self.meta['configuration_order']]
        assert ['|'.join(c) for c in self.order] == self.saved['configuration_order']
        self.c, self.q = self.mu.shape
        world = worlds[self.claim['world_id']]
        expected_a = [f'a{i:02}' for i in range(len(world['candidates']))]
        expected_x = [f'x{i}' for i in range(len(world['partners']))]
        domain = self.saved['domain']
        assert expected_a == domain['candidate_ids']
        assert expected_x == domain['partner_ids']
        assert self.order == list(product(expected_a, expected_x, domain['policy_ids']))
        assert world['all_physical_crosses_legal'] and not world['power_cap_filters_cells']
        self.items = tuple(expected_a + expected_x)
        self.initial = frozenset(self.claim['initial_items'])
        self.supports = [frozenset(c[:2]) for c in self.order]
        self.weights = np.array([self.claim['task_weight_mapping'][q] for q in self.meta['task_order']])
        assert abs(self.weights.sum()-1) < 1e-12
        self.refs = self.meta['reference_configuration_indices_by_task']
        assert self.n == self.claim['iterations'] == self.meta['N']
        self.alpha = self.saved['core_bounds_manifest']['alpha']
        self.family = self.q * (2*self.c*self.c + self.c)
        self.critical = float(t.isf(self.alpha / (2*self.family), self.n-1))
        assert self.family == self.saved['core_bounds_manifest']['family_size']
        assert self.critical == self.saved['core_bounds_manifest']['critical_value']
        self.negative_variances = []
        self.smallest_variance = float('inf')
        self.minimum_abs_decision_margin = float('inf')
        self.pair = {}
        for offset in (self.claim['gain'], -self.claim['tolerance']):
            lo = np.empty((self.q, self.c, self.c)); hi = lo.copy()
            for q, i, j in product(range(self.q), range(self.c), range(self.c)):
                lo[q,i,j], hi[q,i,j] = self.linear(q, [(i,1.),(j,-1.),(self.refs[q],-offset)])
            self.pair[offset] = (lo,hi)
        self.cap = (np.empty((self.c,self.q)),np.empty((self.c,self.q)))
        for i,q in product(range(self.c),range(self.q)):
            self.cap[0][i,q],self.cap[1][i,q] = self.linear(q,[(self.refs[q],1+self.claim['headroom']),(i,-1.)])
        self.cache = {}
        self.path_checks = 0
        self.source_checks = 0
        self.largest_saved_margin_discrepancy = 0.

    def linear(self, q, terms):
        # Merge repeated indices before covariance multiplication: i=j is not
        # subtraction of two independently estimated quantities.
        a = np.zeros(self.c)
        for i,v in terms: a[i] += v
        index = np.flatnonzero(a)
        aa = a[index]; cc = self.cov[q][np.ix_(index,index)]
        mean = float(aa @ self.mu[index,q])
        variance = float(aa @ cc @ aa)
        scale = float(np.abs(aa) @ np.abs(cc) @ np.abs(aa))
        self.smallest_variance = min(self.smallest_variance,variance)
        if variance < 0:
            self.negative_variances.append({'q':q,'variance':variance,'absolute_term_scale':scale})
            assert variance >= -1e-11*max(1.,scale), 'material covariance non-PSD discrepancy'
        radius = self.critical*np.sqrt(max(variance,0.)/self.n)
        return mean-radius,mean+radius

    def contrast(self,left,right,offset):
        lo,hi = self.pair[offset]
        a=lo[:,left][:,:,right]; b=hi[:,left][:,:,right]
        # max_i min_j lower bounds the max difference from below; min_j
        # max_i upper is an optimistic bound from above, including all i/j.
        return a.min(axis=2).max(axis=1), b.max(axis=1).min(axis=1)

    def mass(self,margin,required):
        self.minimum_abs_decision_margin=min(self.minimum_abs_decision_margin,float(np.min(np.abs(margin))))
        return float(self.weights[np.asarray(margin)>=0].sum()) >= required-1e-12

    def state(self,published):
        published=frozenset(published)
        if published in self.cache:return self.cache[published]
        active=[i for i,s in enumerate(self.supports) if s <= published]
        assert self.initial <= published and active
        capm=tuple(v[active].min(axis=0) for v in self.cap)
        capok=tuple(bool(np.all(v>=0)) for v in capm)
        sources={}
        for source in sorted(published):
            use=[i for i in active if source in self.supports[i]]
            if use:
                margins=self.contrast(use,active,-self.claim['tolerance'])
                flags=tuple(self.mass(v,self.claim['retention_mass']) for v in margins)
            else:
                margins=(np.repeat(-np.inf,self.q),)*2;flags=(False,False)
            sources[source]={'flags':flags,'margins':margins,'indices':use}
            self.source_checks += 1
        retainok=tuple(all(v['flags'][i] for v in sources.values()) for i in (0,1))
        result={'active':active,'cap':capok,'cap_margins':capm,'retention':retainok,'sources':sources}
        self.cache[published]=result
        return result

    def edge(self,before,after,mode,retention=True):
        i=0 if mode=='lower' else 1
        assert before < after
        b=self.state(before);s=self.state(after)
        if len(after-self.initial)>self.claim['total_item_budget']:return False,'budget'
        if not s['cap'][i]:return False,'power'
        if retention and not s['retention'][i]:return False,'retention'
        gain=self.contrast(s['active'],b['active'],self.claim['gain'])[i]
        return (True,'feasible') if self.mass(gain,self.claim['gain_mass']) else (False,'gain')

    def audit_path(self,first,solution,B,retention):
        current=self.initial|{first}
        assert self.edge(self.initial,current,'lower',retention)[0]
        assert set(solution['remaining_candidates']) == set(self.items)-current
        assert solution['remaining_item_budget']==self.claim['total_item_budget']-1
        assert solution['configuration_order']==self.saved['configuration_order']
        assert len(solution['batches'])==len(solution['path_checks'])
        for batch,saved in zip(solution['batches'],solution['path_checks']):
            new=frozenset(batch)
            assert 1<=len(new)<=B and not new&current
            nxt=current|new
            assert self.edge(current,nxt,'lower',retention)[0]
            state=self.state(nxt)
            assert state['active']==saved['stateconfig_indices']
            assert set(saved['sources'])==set(nxt), 'source omitted from a returned prefix'
            for source in nxt:
                x=state['sources'][source];y=saved['sources'][source]
                assert x['indices']==y['configuration_indices']
                assert x['flags']==(y['lower'],y['upper'])
                for i,key in enumerate(('lower','upper')):
                    discrepancy=float(np.max(np.abs(x['margins'][i]-np.asarray(y['task_margins'][key]))))
                    self.largest_saved_margin_discrepancy=max(self.largest_saved_margin_discrepancy,discrepancy)
                    assert discrepancy<1e-6
            self.path_checks+=1;current=nxt

    def run(self):
        started=time.monotonic()
        bad=self.claim['first_pair'][0];good=self.claim['expected_better_first']
        assert bad!=good
        target=1 if self.claim['finding_id']=='magister_history' else 0
        start=self.initial|{bad}
        assert self.edge(self.initial,start,'lower')[0]
        levels=[{start}];counts=[];rejections=Counter();all_possible_first=[]
        # Every longer feasible history has a feasible prefix of target+1
        # releases. Exhausting that level proves a finite upper bound without
        # claiming a deeper search was performed.
        for depth in range(target+1):
            following=set();considered=0
            for state in sorted(levels[-1],key=lambda s:sorted(s)):
                remaining=[x for x in self.items if x not in state]
                for width in (1,2):
                    for batch in combinations(remaining,width):
                        considered+=1;following_state=state|set(batch)
                        ok,reason=self.edge(state,following_state,'upper')
                        rejections[reason]+=1
                        if ok:
                            following.add(frozenset(following_state))
                            if depth==0:all_possible_first.append(list(batch))
            counts.append({'rounds_after_forced_first':depth+1,'source_states':len(levels[-1]),'candidate_edges_checked':considered,'distinct_possible_states':len(following)})
            levels.append(following)
        assert not levels[-1], 'counterexample to reported finite upper bound'
        assert (bool(levels[1]) if target else not levels[1])
        for field,retention in [('continuations',True),('value_only_continuations',False)]:
            for first in self.claim['first_pair']:
                for B in (1,2):
                    solution=self.saved['matched_first'][field][first][str(B)]['lower']
                    self.audit_path(first,solution,B,retention)
        for B in (1,2):
            solution=self.saved['matched_first']['continuations'][bad][str(B)]['upper']
            assert solution['graph_search_complete']
            assert solution['capacity_upper']==target
            assert set(solution['remaining_candidates'])==set(self.items)-start
        return {'claim_id':self.claim['claim_id'],'status':'passed','reference_claim_sha256':digest(self.path),
            'full_configuration_count':self.c,'complete_physical_cells':self.c*self.q,
            'original_unpublished_count':len(self.items)-len(self.initial),'forced_bad_first':bad,
            'remaining_candidates':sorted(set(self.items)-start),'unselected_first_retained':good in set(self.items)-start,
            'B2_bad_continuation_upper_bound':target,'B1_inherits_upper_bound':target,
            'prefix_enumeration':counts,'edge_outcomes':dict(rejections),'all_possible_first_continuations_B2':all_possible_first,
            'supported_path_prefixes_independently_verified':self.path_checks,
            'state_evaluations':len(self.cache),'published_source_evaluations':self.source_checks,
            'maximum_saved_source_margin_difference_DPS':self.largest_saved_margin_discrepancy,
            'minimum_absolute_mass_decision_margin_DPS':self.minimum_abs_decision_margin,
            'smallest_covariance_quadratic_form':self.smallest_variance,'negative_variance_clamps':self.negative_variances,
            'critical_value_recomputed':self.critical,'elapsed_seconds':time.monotonic()-started}


assert digest(manifest_path)==moment_manifest['manifest_sha256']
results=[IndependentAudit(i).run() for i in range(1,5)]
output={'status':'passed','scope':'Independent coefficient/covariance construction and exhaustive B2 short-prefix upper-bound check; retained and value lower paths verified. No imported campaign inference or solver code, no new observations, no new alpha. Conditional on supplied compact moments and their independent raw-output/provenance audit. Finite domains and approximate Student-t assumptions remain unchanged.',
 'manifest_sha256':digest(manifest_path),'moments_sha256':digest(moment_path),'moments_manifest_sha256':digest(moment_manifest_path),'audit_source_sha256':digest(Path(__file__)),'results':results}
DEST.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
