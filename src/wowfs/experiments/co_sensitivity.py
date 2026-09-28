"""Deterministic propagation of the frozen native simultaneous contrast event.

No threshold-specific t interval is formed here. Old diagonal contrasts bound
the reference on the same event; every changed coefficient is an interval sum.
All-width exclusions retain every optional item and every activated physical row.
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.stats import t as student_t


ROUNDOUT = 1e-10  # DPS; explicit conservative numerical padding, not a CI.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def shift_interval(lower, upper, coefficient, ref_lower, ref_upper):
    """C_new = C_old + coefficient*S, on one common event."""
    lo = lower + np.minimum(coefficient * ref_lower, coefficient * ref_upper)
    hi = upper + np.maximum(coefficient * ref_lower, coefficient * ref_upper)
    return lo, hi


class InheritedTable:
    def __init__(self, mean, covariance, record, claim):
        self.mean = np.asarray(mean)
        self.covariance = np.asarray(covariance)
        self.record = record
        self.claim = claim
        self.base = claim['core_bounds_manifest']
        self.rows = record['configuration_order']
        self.items = sorted({i for row in self.rows for i in row[:2]})
        self.index = {i: j for j, i in enumerate(self.items)}
        self.masks = np.array([self.mask(row[:2]) for row in self.rows], dtype=np.int64)
        self.allmask = (1 << len(self.items)) - 1
        self.nc, self.nq = self.mean.shape
        self.n = record['N']
        self.refs = record['reference_configuration_indices_by_task']
        self.reference = np.array([self.mean[self.refs[q], q] for q in range(self.nq)])
        self.weights = np.full(self.nq, 1 / self.nq)
        b = self.base
        assert self.n == b['paired_seeds'] and self.nc == b['configurations']
        assert self.nq == b['tasks']
        assert b['family_size'] == self.nq * (2 * self.nc**2 + self.nc)
        critical = student_t.isf(b['alpha'] / (2 * b['family_size']), self.n - 1)
        assert abs(critical - b['critical_value']) < 1e-12
        self.critical = float(critical)
        self.old = {}
        for name, coefficient in [('gain', -b['gain']), ('retention', b['tolerance'])]:
            lo = np.empty((self.nq, self.nc, self.nc)); hi = np.empty_like(lo)
            for q, i, j in itertools.product(range(self.nq), range(self.nc), range(self.nc)):
                a = np.zeros(self.nc); a[i] += 1; a[j] -= 1
                a[self.refs[q]] += coefficient
                lo[q, i, j], hi[q, i, j] = self.old_interval(q, a)
            self.old[name] = (lo, hi)
        lo = np.empty((self.nc, self.nq)); hi = np.empty_like(lo)
        for i, q in itertools.product(range(self.nc), range(self.nq)):
            a = np.zeros(self.nc); a[self.refs[q]] += b['cap']; a[i] -= 1
            lo[i, q], hi[i, q] = self.old_interval(q, a)
        self.old['cap'] = (lo, hi)
        self.reference_records = []
        lower = []; upper = []
        for q in range(self.nq):
            entries = []
            for i in range(self.nc):
                for name, coefficient in [('gain', -b['gain']), ('retention', b['tolerance'])]:
                    if coefficient == 0:
                        continue
                    l, u = (x[q, i, i] / coefficient for x in self.old[name])
                    if coefficient < 0:
                        l, u = u, l
                    entries.append({'interval_id': self.interval_id(name, q, i, i),
                                    'coefficient': coefficient, 'lower': float(l), 'upper': float(u)})
            if not entries:
                raise ValueError('UNSUPPORTED_BY_OLD_EVENT: no nonzero diagonal coefficient')
            l = max(x['lower'] for x in entries) - ROUNDOUT
            u = min(x['upper'] for x in entries) + ROUNDOUT
            assert l <= u and l > 0
            lower.append(l); upper.append(u)
            self.reference_records.append({'task': record['task_order'][q], 'q': q,
                                           'lower': l, 'upper': u, 'derived_from': entries})
        self.ref_lower = np.array(lower); self.ref_upper = np.array(upper)
        self._active_cache = {}

    def old_interval(self, q, coefficients):
        mean = float(coefficients @ self.mean[:, q])
        variance = float(coefficients @ self.covariance[q] @ coefficients)
        if variance < -ROUNDOUT:
            raise ValueError(f'Negative variance {variance}')
        radius = self.critical * math.sqrt(max(0., variance) / self.n)
        return mean - radius - ROUNDOUT, mean + radius + ROUNDOUT

    def interval_id(self, kind, q, i, j=None):
        return f"{self.record['claim_id']}:{kind}:q{q}:c{i}" + ('' if j is None else f':d{j}')

    def mask(self, items):
        return sum(1 << self.index[i] for i in set(items))

    def names(self, mask):
        return [i for j, i in enumerate(self.items) if (mask >> j) & 1]

    def active(self, mask):
        if mask not in self._active_cache:
            self._active_cache[mask] = np.flatnonzero((self.masks & mask) == self.masks)
        return self._active_cache[mask]

    def bounds(self, e, h, g):
        rlo, rhi = self.ref_lower[:, None, None], self.ref_upper[:, None, None]
        return {
            'gain': shift_interval(*self.old['gain'], -(g - self.base['gain']), rlo, rhi),
            'retention': shift_interval(*self.old['retention'], e - self.base['tolerance'], rlo, rhi),
            'cap': shift_interval(*self.old['cap'], h - (self.base['cap'] - 1), self.ref_lower, self.ref_upper),
            'e': e, 'h': h, 'g': g,
        }

    @staticmethod
    def extrema(bounds, left, right):
        lo, hi = bounds
        if not len(left):
            q = lo.shape[0]
            return np.full(q, -np.inf), np.full(q, -np.inf)
        # max-left/min-right is sound on both endpoints because the true
        # contrast separates into left_value - right_value + common_offset.
        return tuple(a[:, left][:, :, right].min(axis=2).max(axis=1) for a in (lo, hi))

    def assess(self, mask, bounds, rho=.5, previous=None, details=False):
        ids = self.active(mask)
        if not len(ids):
            return {'supported': False, 'possible': False, 'mean': False, 'reason': 'no_active_configuration'}
        lo, hi = bounds['cap']
        supported = bool(np.all(lo[ids] >= 0)); possible = bool(np.all(hi[ids] >= 0))
        cap_mean = (1 + bounds['h']) * self.reference - self.mean[ids]
        mean_ok = bool(np.all(cap_mean >= 0))
        checks = {'cap_lower': lo[ids].min(axis=0).tolist(), 'cap_upper': hi[ids].min(axis=0).tolist(), 'sources': {}}
        for j, name in enumerate(self.items):
            if not (mask >> j) & 1:
                continue
            src = ids[((self.masks[ids] >> j) & 1) == 1]
            low, high = self.extrema(bounds['retention'], src, ids)
            ml = float(self.weights[low >= 0].sum()); mu = float(self.weights[high >= 0].sum())
            mm = 0. if not len(src) else float(self.weights[(self.mean[src].max(axis=0) - self.mean[ids].max(axis=0) + bounds['e'] * self.reference) >= 0].sum())
            supported &= ml >= rho; possible &= mu >= rho; mean_ok &= mm >= rho
            if details:
                checks['sources'][name] = {'witness_rows': src.tolist(), 'comparison_rows': ids.tolist(),
                    'lower': [None if not np.isfinite(v) else float(v) for v in low],
                    'upper': [None if not np.isfinite(v) else float(v) for v in high],
                    'supported_mass': ml, 'possible_mass': mu, 'mean_mass': mm}
        if previous is not None:
            prev = self.active(previous)
            low, high = self.extrema(bounds['gain'], ids, prev)
            supported &= float(self.weights[low >= 0].sum()) >= .5
            possible &= float(self.weights[high >= 0].sum()) >= .5
            mg = self.mean[ids].max(axis=0) - self.mean[prev].max(axis=0) - bounds['g'] * self.reference
            mean_ok &= float(self.weights[mg >= 0].sum()) >= .5
            checks['gain_lower'] = low.tolist(); checks['gain_upper'] = high.tolist()
        result = {'supported': bool(supported), 'possible': bool(possible), 'mean': bool(mean_ok)}
        if details:
            result.update(items=self.names(mask), active_rows=ids.tolist(), checks=checks)
        return result

    def prune(self, mandatory, bounds, rho):
        """Remove only items absent from every valid completion of mandatory."""
        cap_upper = bounds['cap'][1]
        mids = self.active(mandatory)
        if np.any(cap_upper[mids] < 0):
            return mandatory, {'reason': 'mandatory_cap', 'rows': mids.tolist()}
        ambient = mandatory; removed = []
        for j, name in enumerate(self.items):
            bit = 1 << j
            if mandatory & bit:
                continue
            ids = self.active(mandatory | bit)
            bad = np.argwhere(cap_upper[ids] < 0)
            if len(bad):
                r, q = bad[0]; c = int(ids[r]); q = int(q)
                removed.append({'item': name, 'reason': 'cap', 'interval_id': self.interval_id('cap', q, c), 'upper': float(cap_upper[c, q])})
            else:
                ambient |= bit
        while True:
            ids = self.active(ambient); deleted = 0
            for j, name in enumerate(self.items):
                if not (ambient >> j) & 1:
                    continue
                src = ids[((self.masks[ids] >> j) & 1) == 1]
                _, upper = self.extrema(bounds['retention'], src, mids)
                if self.weights[upper >= 0].sum() >= rho:
                    continue
                proof = {'item': name, 'reason': 'source', 'witness_rows': src.tolist(), 'mandatory_rows': mids.tolist(),
                         'upper': [None if not np.isfinite(x) else float(x) for x in upper]}
                removed.append(proof)
                if mandatory & (1 << j):
                    return ambient, {'reason': 'mandatory_source', 'deletions': removed, 'lost_source': name}
                deleted |= 1 << j
            if not deleted:
                return ambient, {'reason': 'not_excluded', 'deletions': removed}
            ambient &= ~deleted

    def decide(self, history, targets, bounds, rho=.5):
        initial = self.assess(history, bounds, rho)
        if not initial['possible']:
            return {'status': 'INVALID_INITIAL', 'initial': initial}
        if not initial['supported']:
            return {'status': 'UNKNOWN_INITIAL', 'initial': initial}
        mandatory = history | targets
        ambient, proof = self.prune(mandatory, bounds, rho)
        if proof['reason'] != 'not_excluded':
            return {'status': 'NO', 'certificate': proof}
        old = self.active(history); ids = self.active(ambient)
        # Every positive-mass gain completion contains one row gaining on at
        # least one task. One row need not witness all jointly required tasks.
        gains = bounds['gain'][1][:, ids][:, :, old].min(axis=2)
        witnesses = [int(c) for k, c in enumerate(ids) if np.any(gains[:, k] >= 0)]
        branches = []; seen = set(); unresolved = 0; checked = 0; mean_witness = None
        for c in witnesses:
            required = mandatory | int(self.masks[c])
            available, branch = self.prune(required, bounds, rho)
            branch['gain_witness'] = c
            if branch['reason'] != 'not_excluded':
                branches.append(branch); continue
            optional = [j for j in range(len(self.items)) if (available >> j) & 1 and not (required >> j) & 1]
            possible_count = 0
            for k in range(len(optional) + 1):
                for chosen in itertools.combinations(optional, k):
                    mask = required | sum(1 << j for j in chosen)
                    if mask in seen:
                        continue
                    seen.add(mask); checked += 1
                    ans = self.assess(mask, bounds, rho, previous=history)
                    if ans['mean'] and mean_witness is None:
                        mean_witness = self.names(mask)
                    if ans['supported']:
                        return {'status': 'YES', 'witness': self.assess(mask, bounds, rho, previous=history, details=True), 'checked_subsets': checked}
                    possible_count += ans['possible']
            unresolved += possible_count
            branch['optimistic_survivors'] = possible_count; branches.append(branch)
        return {'status': 'UNKNOWN' if unresolved else 'NO', 'checked_subsets': checked,
                'optimistic_survivors': unresolved, 'mean_witness': mean_witness,
                'certificate': {'mandatory': self.names(mandatory), 'initial_pruning': proof,
                                'gain_witnesses': witnesses, 'branches': branches,
                                'all_optional_subsets_covered': True}}


def run(old_root, paper_root, output):
    started = time.time(); output.mkdir(parents=True, exist_ok=True)
    manifest_path = old_root / 'CONFIRMATION_MANIFEST_V2.json'
    manifest = json.loads(manifest_path.read_text())
    mp = old_root / 'analysis/confirm-v2-compact-moments'
    meta = json.loads((mp / 'MOMENTS_MANIFEST.json').read_text())
    arrays = np.load(mp / 'MOMENTS.npz')
    paper_arrays = np.load(paper_root / 'theory/data/TRINKET_MOMENTS.npz')
    equal = {k: bool(np.array_equal(arrays[k], paper_arrays[k])) for k in paper_arrays.files}
    assert all(equal.values())
    source = Path(__file__).with_name('oe_inference.py')
    source_verified = sha(source) == manifest['analysis_hashes']['src/wowfs/experiments/oe_inference.py']
    assert source_verified
    audit = {'status': 'INHERITED_EVENT_VERIFIED', 'new_native_battles': 0,
             'new_alpha_spent': 0., 'old_campaign_alpha': .05,
             'statistical_guarantee': 'Approximate fixed-N paired Student-t with original Bonferroni family; not distribution-free.',
             'original_source_hash_matches_freeze': source_verified, 'original_source_sha256': sha(source),
             'diagonal_evidence': 'FiniteBounds.__init__ loops q and i and subtracts samples[:,q,:], so every ordered j including j=i is in both offset arrays. family_size=Q*(2*C*C+C).',
             'frozen_manifest_sha256': sha(manifest_path), 'old_moments_sha256': sha(mp / 'MOMENTS.npz'),
             'paper_trinket_moments_identical_to_old': equal,
             'numerical_roundout_DPS': ROUNDOUT,
             'derivation': 'R_e(c,c)=e*S and G_g(c,c)=-g*S; intersect scaled original bounds, then C_new=C_old+a*S, with sign-aware endpoint sums.',
             'uniformity': 'Deterministic for every real e,h,g (including data-selected rectangles) on the same original event; no new critical values.',
             'records': []}
    grid = []; certificates = []; reference_records = []; derivations = []; regions = []
    multipliers = [.8, .9, 1., 1.1, 1.2]
    for index, rec in enumerate(meta['worlds'][:4], 1):
        claim_path = old_root / f'analysis/confirm-v2-results/CLAIM_{index:02d}.json'
        claim = json.loads(claim_path.read_text())
        table = InheritedTable(arrays[rec['array_prefix'] + '_mean'], arrays[rec['array_prefix'] + '_covariance'], rec, claim)
        initial = table.mask(claim['initial_items'])
        glove = rec['claim_id'].startswith('magister')
        bad, good = ('a05', 'a13') if glove else ('a07', 'x3')
        target_items = ['a01', 'x1'] if glove else ['a03']
        history_bad = initial | table.mask([bad]); history_good = initial | table.mask([good])
        reference_records.append({'claim_id': rec['claim_id'], 'tasks': table.reference_records})
        audit['records'].append({'claim_id': rec['claim_id'], 'family': table.base,
                                 'claim_sha256': sha(claim_path), 'configuration_count': table.nc,
                                 'diagonals_in_each_offset': table.nq * table.nc,
                                 'old_event_ids': {'cap': 'q,c', 'gain': 'q,c,d including c=d', 'retention': 'q,c,d including c=d'}})
        cache = {}
        for em, hm, gm in itertools.product(multipliers, repeat=3):
            e = table.base['tolerance'] * em; h = (table.base['cap'] - 1) * hm; g = table.base['gain'] * gm
            bounds = table.bounds(e, h, g)
            key = (em, hm, gm)
            entry = {'claim_id': rec['claim_id'], 'e_multiplier': em, 'h_multiplier': hm, 'g_multiplier': gm,
                     'e': e, 'h': h, 'g': g, 'rho_regime': '0<rho<=0.5', 'evidence': 'INHERITED_SIMULTANEOUS_EVENT'}
            original = table.assess(initial, bounds, details=True)
            first_bad = table.assess(history_bad, bounds, previous=initial, details=True)
            first_good = table.assess(history_good, bounds, previous=initial, details=True)
            statuses = {}
            for query_name, targets in [('any_gain', []), ('registered_target', target_items)]:
                for which, history in [('bad', history_bad), ('good', history_good)]:
                    statuses[query_name + '_' + which] = table.decide(history, table.mask(targets), bounds)
            valid = original['supported'] and first_bad['supported'] and first_good['supported']
            possible = original['possible'] and first_bad['possible'] and first_good['possible']
            entry.update(initial_supported=original['supported'], first_bad_supported=first_bad['supported'], first_good_supported=first_good['supported'],
                         first_bad_possible=first_bad['possible'], first_good_possible=first_good['possible'],
                         **{k: v['status'] for k, v in statuses.items()})
            pair = (entry['registered_target_good'], entry['registered_target_bad'])
            entry['status'] = ('INVALID_ORIGINAL_OR_FIRST' if not possible else 'UNRESOLVED_ORIGINAL_OR_FIRST' if not valid else
                              'GOOD_YES_BAD_NO' if pair == ('YES', 'NO') else 'BOTH_YES' if pair == ('YES', 'YES') else
                              'BOTH_NO' if pair == ('NO', 'NO') else 'OTHER_OR_UNRESOLVED')
            grid.append(entry); cache[key] = entry
            cert_id = f"{rec['claim_id']}:e{em}:h{hm}:g{gm}"
            certificates.append({'id': cert_id, **entry, 'targets': target_items, 'original': original,
                                 'first_bad': first_bad, 'first_good': first_good, 'queries': statuses})
            derivations.append({'certificate_id': cert_id, 'claim_id': rec['claim_id'], 'e': e, 'h': h, 'g': g,
                'old_family': table.base, 'reference_bound_record': rec['claim_id'],
                'all_original_interval_ids': {'cap': {'q': [0, table.nq - 1], 'c': [0, table.nc - 1]}, 'gain_and_retention': {'q': [0, table.nq - 1], 'c': [0, table.nc - 1], 'd': [0, table.nc - 1]}},
                'added_reference_coefficient': {'cap': h - (table.base['cap'] - 1), 'gain': -(g - table.base['gain']), 'retention': e - table.base['tolerance']},
                'formula': 'Lnew=Lold+min(a*SL,a*SU); Unew=Uold+max(a*SL,a*SU)'})
            if key == (1., 1., 1.):
                for rho, regime in [(1., '0.5<rho<=1'), (0., 'retention_disabled_ablation')]:
                    ab = table.assess(history_bad, bounds, rho, previous=initial, details=True)
                    ag = table.assess(history_good, bounds, rho, previous=initial, details=True)
                    certificates.append({'id': rec['claim_id'] + ':' + regime, 'rho': rho, 'rho_regime': regime,
                                         'first_bad': ab, 'first_good': ag, 'interpretation': 'Invalid first state is not zero completion capacity.'})
        # Maximal normalized-volume nondegenerate grid-aligned box, explicitly
        # within the predeclared display cube. This is not a global maximality claim.
        candidates = []
        intervals = list(itertools.combinations(multipliers, 2))
        for er, hr, gr in itertools.product(intervals, repeat=3):
            strict = (er[0], hr[0], gr[1]); loose = (er[1], hr[1], gr[0])
            s, l = cache[strict], cache[loose]
            if s['initial_supported'] and s['first_bad_supported'] and s['first_good_supported'] and s['registered_target_good'] == 'YES' and l['registered_target_bad'] == 'NO':
                candidates.append((math.prod(r[1] - r[0] for r in (er, hr, gr)), er, hr, gr, strict, loose))
        selected = max(candidates, default=None)
        regions.append({'claim_id': rec['claim_id'], 'targets': target_items, 'status': 'CERTIFIED' if selected else 'NO_NONDEGENERATE_GRID_BOX_CERTIFIED',
                        'box_search_class': 'All 1000 nondegenerate axis-aligned boxes with endpoints in {0.8,0.9,1,1.1,1.2}^3; no claim outside display cube.',
                        'boxes_certified': len(candidates),
                        'selected_multiplier_box': None if selected is None else {'e': selected[1], 'h': selected[2], 'g': selected[3]},
                        'strict_good_and_state_corner': None if selected is None else selected[4],
                        'loose_bad_exclusion_corner': None if selected is None else selected[5],
                        'proof': 'Positive inherited S bounds. e,h increase and g decreases relax every constraint. Good completion and original/both first releases supported at strict corner; all-width bad target excluded at loose corner.'})
        print(json.dumps({'claim_id': rec['claim_id'], 'grid_complete': 125, 'base': cache[(1., 1., 1.)], 'region': regions[-1]}), flush=True)
    audit['elapsed_seconds'] = time.time() - started
    dump(output / 'INHERITED_EVENT_AUDIT.json', audit)
    dump(output / 'REFERENCE_BOUNDS.json', reference_records)
    dump(output / 'CERTIFIED_REGIONS.json', regions)
    with (output / 'SENSITIVITY_GRID.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(grid[0])); writer.writeheader(); writer.writerows(grid)
    for filename, rows in [('THRESHOLD_DERIVATIONS.jsonl', derivations), ('SENSITIVITY_CERTIFICATES.jsonl', certificates)]:
        with (output / filename).open('w') as f:
            for row in rows:
                f.write(json.dumps(row, allow_nan=False) + '\n')
    np.savez_compressed(output / 'INHERITED_MOMENTS.npz', **{k: arrays[k] for rec in meta['worlds'][:4] for k in [rec['array_prefix'] + s for s in ['_mean', '_covariance', '_N']]})
    dump(output / 'INHERITED_MOMENTS_METADATA.json', meta['worlds'][:4])
    dump(output / 'INHERITED_BASE_CLAIMS.json', [json.loads((old_root / f'analysis/confirm-v2-results/CLAIM_{i:02d}.json').read_text()) for i in range(1, 5)])


def independent_subsets(table, history_items, target_items, bounds):
    """Second full-domain evaluator: no pruning, no calls to assess/decide.

    Uses the original weaker min-right/max-left upper bound as an independent
    exclusion challenge. Full subset and physical row coverage is explicit.
    """
    history = set(history_items); mandatory = history | set(target_items)
    optional = sorted(set(table.items) - mandatory)
    rows = [set(row[:2]) for row in table.rows]
    previous = [i for i, row in enumerate(rows) if row <= history]
    counts = dict(all_subsets=0, cap_possible=0, gain_possible=0, retention_possible=0, supported=0, mean_feasible=0)
    examples = []
    failures = {}
    for bits in range(1 << len(optional)):
        selected = mandatory | {item for j, item in enumerate(optional) if (bits >> j) & 1}
        ids = [i for i, row in enumerate(rows) if row <= selected]
        counts['all_subsets'] += 1
        cl, cu = bounds['cap']; gl, gu = bounds['gain']; rl, ru = bounds['retention']
        if np.any(cu[ids] < 0):
            continue
        counts['cap_possible'] += 1
        gain_upper = gu[:, ids][:, :, previous].max(axis=1).min(axis=1)
        if np.count_nonzero(gain_upper >= 0) == 0:
            continue
        counts['gain_possible'] += 1
        supported = bool(np.all(cl[ids] >= 0) and np.any(gl[:, ids][:, :, previous].min(axis=2).max(axis=1) >= 0))
        possible = True
        f = table.mean[ids].max(axis=0); f0 = table.mean[previous].max(axis=0)
        mean_ok = bool(np.all(f <= (1 + bounds['h']) * table.reference) and np.any(f - f0 >= bounds['g'] * table.reference))
        for name in sorted(selected):
            source = [i for i in ids if name in rows[i]]
            if not source:
                possible = False; supported = False; mean_ok = False
                failures[name] = failures.get(name, 0) + 1
                break
            upper = ru[:, source][:, :, ids].max(axis=1).min(axis=1)
            lower = rl[:, source][:, :, ids].min(axis=2).max(axis=1)
            if not np.any(upper >= 0):
                possible = False; failures[name] = failures.get(name, 0) + 1
            supported &= bool(np.any(lower >= 0))
            mean_ok &= bool(np.any(table.mean[source].max(axis=0) >= f - bounds['e'] * table.reference))
        counts['retention_possible'] += int(possible)
        counts['supported'] += int(supported)
        counts['mean_feasible'] += int(mean_ok)
        if supported and len(examples) < 2:
            examples.append(sorted(selected))
    return {'counts': counts, 'supported_examples': examples, 'source_failure_counts_nonexclusive': failures,
            'upper_direction': 'min_right max_left U, original weaker optimistic direction',
            'all_candidates_retained': True, 'all_physical_crosses_retained': True}


def glove_source_certificate(table):
    """Four right-slot cases prove exclusion without cap or gain assumptions.

    For a fixed published right set, a05's entire response menu is fixed.
    Adding any other left item cannot improve a05 but can raise the frontier.
    This checks all optional right subsets, so no left-item subset is omitted.
    """
    bounds = table.bounds(.006, .12, .008)
    branches = []; tolerance_limits = []
    for bits in range(4):
        right = ['x0', 'x1'] + [x for j, x in enumerate(['x2', 'x3']) if bits >> j & 1]
        mandatory = ['a00', 'a01', 'a05'] + right
        ids = table.active(table.mask(mandatory))
        source = np.array([i for i, row in enumerate(table.rows) if row[0] == 'a05' and row[1] in right])
        _, upper = table.extrema(bounds['retention'], source, ids)
        assert np.all(upper < 0)
        limits = .006 - upper / table.ref_upper
        tolerance_limits.extend(limits.tolist())
        branches.append({'right_slot_items': right, 'source_rows': source.tolist(), 'mandatory_rows': ids.tolist(),
                         'source_upper_DPS_at_e_006': upper.tolist(), 'strict_tolerance_limits': limits.tolist()})
    # At larger e the exact same retained pairwise contrasts shift by at most
    # (e-.006)*SU. max/min therefore shift by at most that common quantity.
    limit = min(tolerance_limits)
    assert .0095 < limit
    return {'claim_id': table.record['claim_id'], 'source': 'a05', 'required_target': ['a01', 'x1'],
            'right_subset_branches': branches, 'strict_tolerance_limit': limit,
            'domain': 'Full 14 gloves x 4 leggings catalogue; every optional left subset covered by frontier monotonicity.',
            'conclusion': 'For 0<=e<strict_tolerance_limit and any rho>0, no retaining completion containing the target exists after a05, regardless of cap/gain requirements.',
            'extension_beyond_primary_grid': {'status': 'POST_HOC_INHERITED_EVENT_CONSEQUENCE', 'e_upper_certified': .0095,
                'new_alpha_spent': 0., 'reason': 'Uniform deterministic coefficient propagation covers continuous parameters, including selected consequences.'},
            'proof': 'Fix one of four right-slot supersets containing x0,x1. All possible a05 witnesses are now listed. Against mandatory left items a00,a01,a05, its upper retention margin is negative on both tasks. Extra left items cannot improve a05 and cannot lower the frontier. Four cases exhaust every publication.'}


def verify_bundle(bundle, output):
    """Recompute headline certificates using only files included in review-v2."""
    started = time.time()
    records = json.loads((bundle / 'INHERITED_MOMENTS_METADATA.json').read_text())
    claims = json.loads((bundle / 'INHERITED_BASE_CLAIMS.json').read_text())
    arrays = np.load(bundle / 'INHERITED_MOMENTS.npz')
    certificates = [json.loads(line) for line in (bundle / 'SENSITIVITY_CERTIFICATES.jsonl').read_text().splitlines()]
    regions = json.loads((bundle / 'CERTIFIED_REGIONS.json').read_text())
    tables = {r['claim_id']: InheritedTable(arrays[r['array_prefix'] + '_mean'], arrays[r['array_prefix'] + '_covariance'], r, c)
              for r, c in zip(records, claims)}
    replay_count = 0; independent = []; old_margin_checks = []
    for cert in certificates:
        if 'e_multiplier' not in cert:
            continue
        d = tables[cert['claim_id']]; b = d.bounds(cert['e'], cert['h'], cert['g'])
        initial = d.mask(d.claim['initial_items'])
        for which in ('bad', 'good'):
            history = d.mask(cert['first_' + which]['items'])
            for kind, targets in [('any_gain', []), ('registered_target', cert['targets'])]:
                ans = d.decide(history, d.mask(targets), b)
                assert ans['status'] == cert['queries'][kind + '_' + which]['status']
                replay_count += 1
        # Direct reproduction of original paired contrasts, allowing the
        # disclosed outward numerical padding. No changed threshold direction.
        if cert['e_multiplier'] == cert['h_multiplier'] == cert['g_multiplier'] == 1:
            errors = []
            for path in d.claim['frozen_paths'].values():
                for step in path['steps']:
                    ids = step['stateconfig_indices']; prev = step['previous_stateconfig_indices']
                    expected = step['checks']['power']['individual_margins']
                    for k, a in [('lower', d.old['cap'][0]), ('upper', d.old['cap'][1])]:
                        errors.append(float(np.max(np.abs(a[ids] - np.asarray(expected[k])))))
                    for source in step['sources'].values():
                        src = source['configuration_indices']
                        low, high = d.old['retention']
                        lo = low[:, src][:, :, ids].min(axis=2).max(axis=1)
                        hi = high[:, src][:, :, ids].max(axis=1).min(axis=1)
                        for k, a in [('lower', lo), ('upper', hi)]:
                            errors.append(float(np.max(np.abs(a - source['task_margins'][k]))))
                    lo, hi = d.old['gain']
                    for k, a in [('lower', lo[:, ids][:, :, prev].min(axis=2).max(axis=1)),
                                 ('upper', hi[:, ids][:, :, prev].max(axis=1).min(axis=1))]:
                        errors.append(float(np.max(np.abs(a - step['checks']['gain']['task_margins'][k]))))
            maximum = max(errors)
            assert maximum < 2e-9, maximum
            old_margin_checks.append({'claim_id': cert['claim_id'], 'compared_endpoint_groups': len(errors), 'max_absolute_DPS_error_including_padding': maximum})
    for region in regions:
        if region['status'] != 'CERTIFIED':
            continue
        d = tables[region['claim_id']]; glove = region['claim_id'].startswith('magister')
        bad, good = ('a05', 'a13') if glove else ('a07', 'x3')
        for name, which in [('loose_bad_exclusion_corner', bad), ('strict_good_and_state_corner', good)]:
            em, hm, gm = region[name]
            b = d.bounds(d.base['tolerance'] * em, (d.base['cap'] - 1) * hm, d.base['gain'] * gm)
            res = independent_subsets(d, d.claim['initial_items'] + [which], region['targets'], b)
            if name.startswith('loose'):
                assert res['counts']['retention_possible'] == 0, (region['claim_id'], res)
            else:
                assert res['counts']['supported'] > 0, (region['claim_id'], res)
                initial = d.mask(d.claim['initial_items'])
                for first in (bad, good):
                    assert d.assess(initial | d.mask([first]), b, previous=initial)['supported']
            independent.append({'claim_id': region['claim_id'], 'corner': name, 'multipliers': [em, hm, gm], **res})
    glove_certificates = [glove_source_certificate(d) for key, d in tables.items() if key.startswith('magister')]
    result = {'status': 'PASS', 'replayed_query_decisions': replay_count, 'original_margin_reproduction': old_margin_checks,
              'independent_complete_subset_challenges': independent, 'new_battles': 0, 'new_alpha': 0,
              'glove_four_branch_source_certificates': glove_certificates,
              'elapsed_seconds': time.time() - started, 'source_sha256': sha(__file__),
              'bundle_hashes': {p.name: sha(p) for p in bundle.iterdir() if p.is_file() and p.suffix in ('.json', '.jsonl', '.npz', '.csv')}}
    dump(output, result)
    print(json.dumps({'status': 'PASS', 'replayed_decisions': replay_count,
                      'exhaustive_subsets': sum(x['counts']['all_subsets'] for x in independent),
                      'elapsed_seconds': result['elapsed_seconds']}))


def export_benchmark_models(bundle, output):
    from wowfs.experiments.co_exact import Model, initial_valid
    records = json.loads((bundle / 'INHERITED_MOMENTS_METADATA.json').read_text())
    claims = json.loads((bundle / 'INHERITED_BASE_CLAIMS.json').read_text())
    arrays = np.load(bundle / 'INHERITED_MOMENTS.npz')
    results = []
    for record, claim in zip(records, claims):
        mean = arrays[record['array_prefix'] + '_mean']
        b = claim['core_bounds_manifest']
        refs = [Fraction(repr(float(mean[index, q]))) for q, index in enumerate(record['reference_configuration_indices_by_task'])]
        glove = record['claim_id'].startswith('magister')
        slots = {row[0]: 0 for row in record['configuration_order']} | {row[1]: 1 for row in record['configuration_order']}
        configurations = [{'support': row[:2], 'values': [repr(float(v)) for v in mean[i]]} for i, row in enumerate(record['configuration_order'])]
        for role, first in [('bad', 'a05' if glove else 'a07'), ('good', 'a13' if glove else 'x3')]:
            model = Model.from_dict({'slots': slots, 'configurations': configurations, 'weights': ['1/2', '1/2'],
                'tolerance': [str(Fraction(str(b['tolerance'])) * r) for r in refs],
                'cap': [str(Fraction(str(b['cap'])) * r) for r in refs],
                'gain': [str(Fraction(str(b['gain'])) * r) for r in refs],
                'required_mass': '1/2', 'gain_mass': '1/2', 'history': claim['initial_items'] + [first]})
            assert initial_valid(model)
            results.append({**model.to_dict(), 'instance_id': f"inherited__{record['claim_id']}__{role}",
                'data_kind': 'INHERITED_NATIVE_MEAN', 'family': 'inherited_glove' if glove else 'inherited_trinket',
                'claim_id': record['claim_id'], 'first_role': role, 'first_item': first,
                'registered_target': ['a01', 'x1'] if glove else ['a03'], 'model_sha256': model.digest,
                'source_moments_sha256': sha(bundle / 'INHERITED_MOMENTS.npz'), 'original_reference_DPS_exact': list(map(str, refs)),
                'scope': 'Exact rational encoding of retained decimal sample means; inherited regression domain, not new native evidence. Gain is relative to F(current history); thresholds use fixed original S.',
                'unrestricted_helpers': True})
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError('Refuse to overwrite an exported benchmark model file')
    output.write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in results))
    print(json.dumps({'models': len(results), 'output': str(output), 'sha256': sha(output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-root', type=Path)
    parser.add_argument('--paper-root', type=Path)
    parser.add_argument('--verify-bundle', type=Path, help='Self-contained replay, with output JSON outside the frozen bundle')
    parser.add_argument('--export-models', type=Path, help='Export eight inherited mean models from a compact sensitivity bundle')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.export_models:
        export_benchmark_models(args.export_models, args.output)
    elif args.verify_bundle:
        verify_bundle(args.verify_bundle, args.output)
    else:
        if not args.old_root or not args.paper_root:
            parser.error('--old-root and --paper-root required unless --verify-bundle is used')
        run(args.old_root, args.paper_root, args.output)


if __name__ == '__main__':
    main()
