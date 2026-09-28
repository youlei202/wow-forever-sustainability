"""Portable bundle regression tests, including deliberate artifact tampering."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from wowfs.experiments.co_native_analysis import exact_queries, finite_bounds, certify_queries, save_moments
from wowfs.experiments.co_review_check import check_bundle, verify_manifest, replay_obligations
from wowfs.paths import canonical_hash


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def seal(root):
    records = [{'path': str(p.relative_to(root)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
               for p in sorted((root / 'data').rglob('*')) if p.is_file()]
    put(root / 'REVIEW_MANIFEST.json', {'files': records})


def make_bundle(root):
    native = root / 'data/native'; native.mkdir(parents=True)
    world = dict(world_id='portable_toy', split='validation', candidates=[{}, {}], partners=[{}, {}],
                 base_candidate_indices=[0, 1], base_partner_indices=[0, 1],
                 tasks=[{'task_id': 'long'}, {'task_id': 'short'}], task_weights=[.5, .5], history=['a00', 'x0'],
                 queries=[{'query_id': 'q0', 'required': ['a01']}, {'query_id': 'q1', 'required': ['x1']}],
                 universe_variants=['base'], candidate_expansion_registered=False)
    world['world_sha256'] = canonical_hash(world)
    registry = native / 'CATALOG_REGISTRY.jsonl'; registry.write_text(json.dumps(world) + '\n')
    rule = dict(tolerance='.3', headroom='.5', gain='.1', retention_mass='1/2', gain_mass='1/2')
    means = np.array([[10., 10.5, 11.2, 11.7], [10., 10.2, 10.7, 11.1]])
    pairs = [(0, 0), (0, 1), (1, 0), (1, 1)]
    moments = dict(world_id=world['world_id'], world_sha256=world['world_sha256'], N=1000, seed_block_id='toy:1000',
                   means=means, covariance=np.zeros((2, 4, 4)), reference_indices=[0, 0],
                   domain={'pairs': pairs, 'task_ids': ['long', 'short']})
    wdir = native / world['world_id']; save_moments(moments, wdir)
    bounds = finite_bounds(moments, rule, .0025)
    put(wdir / 'BOUNDS_MANIFEST.json', bounds['manifest'])
    exact = exact_queries(world, moments, rule, 'base')
    cert = certify_queries(world, moments, bounds, rule, 'base')
    value = certify_queries(world, moments, bounds, rule, 'base', retention=False)
    put(wdir / 'base/EXACT_QUERIES.json', exact)
    put(wdir / 'base/CONFIDENCE_CERTIFICATES.json', cert)
    put(wdir / 'base/VALUE_ONLY_CONFIDENCE.json', value)
    rows = []
    for i, result in enumerate(exact['queries']):
        rows.append(dict(world_id=world['world_id'], variant='base', query_id=result['query_id'], required=result['required'],
                         development_prediction=result['mean_answer']['status'], fresh_mean_answer=result['mean_answer']['status'],
                         value_only_mean_answer=result['value_only_answer']['status'], confidence_status=cert['queries'][i]['status'],
                         retention_decision_active_mean=result['mean_answer']['status']=='NO' and result['value_only_answer']['status']=='YES',
                         value_only_confidence=value['queries'][i]['status'],
                         retention_decision_active_confidence=cert['queries'][i]['status']=='NO' and value['queries'][i]['status']=='YES',
                         frozen_prediction_witness=None, prediction_changed_on_fresh_mean=False,
                         native_N=1000, seed_block_id='toy:1000'))
    put(native / 'NATIVE_DECISIONS.json', rows)
    put(native / 'ANALYSIS_MANIFEST.json', dict(mode='confirm', rule=rule, world_ids=[world['world_id']], alpha_per_unit=.0025,
        registry_sha256=hashlib.sha256(registry.read_bytes()).hexdigest()))
    seal(root)


class PortableReviewTests(unittest.TestCase):
    def test_complete_compact_recheck_needs_no_raw_data_or_engine(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make_bundle(root)
            result = check_bundle(root)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['primary_query_rows'], 2)
            self.assertEqual(result['new_native_calls'], 0)
            self.assertEqual(result['confidence_publications_recomputed'], 8)

    def test_manifest_tampering_is_rejected_before_computation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make_bundle(root)
            path = root / 'data/native/NATIVE_DECISIONS.json'
            path.write_text(path.read_text() + ' ')
            with self.assertRaisesRegex(AssertionError, 'SHA256 mismatch'):
                check_bundle(root)

    def test_resealed_false_decision_is_rejected_by_computation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make_bundle(root)
            path = root / 'data/native/NATIVE_DECISIONS.json'; rows = json.loads(path.read_text())
            rows[0]['confidence_status'] = 'NO'; put(path, rows); seal(root)
            with self.assertRaisesRegex(AssertionError, 'Flattened confidence status differs'):
                check_bundle(root)

    def test_manifest_cannot_escape_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            put(root / 'REVIEW_MANIFEST.json', {'files': [{'path': '../outside', 'sha256': '0'*64}]})
            with self.assertRaisesRegex(ValueError, 'bundle-relative'):
                verify_manifest(root)

    def test_declared_required_section_cannot_be_omitted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make_bundle(root)
            path = root / 'REVIEW_MANIFEST.json'; manifest = json.loads(path.read_text())
            manifest['required_sections'] = ['native', 'obligations']; put(path, manifest)
            with self.assertRaisesRegex(AssertionError, 'Required review section missing: obligations'):
                check_bundle(root)

    def test_optional_benchmark_section_requires_presence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make_bundle(root)
            path = root / 'REVIEW_MANIFEST.json'; manifest = json.loads(path.read_text())
            manifest['required_sections'] = ['native', 'benchmark']; put(path, manifest)
            with self.assertRaisesRegex(AssertionError, 'Required review section missing: benchmark'):
                verify_manifest(root)
            (root / 'data/benchmark').mkdir()
            self.assertEqual(verify_manifest(root)['status'], 'PASS')

    def test_prediction_table_requires_explicit_smoke_label(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make_bundle(root)
            path = root / 'data/native/ANALYSIS_MANIFEST.json'; manifest = json.loads(path.read_text())
            manifest['mode'] = 'predict'; put(path, manifest); seal(root)
            with self.assertRaisesRegex(AssertionError, 'Prediction tables cannot'):
                check_bundle(root)

    def test_extra_exact_query_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make_bundle(root)
            path = root / 'data/native/portable_toy/base/EXACT_QUERIES.json'
            exact = json.loads(path.read_text()); exact['queries'].append(exact['queries'][0])
            put(path, exact); seal(root)
            with self.assertRaisesRegex(AssertionError, 'Exact query denominator changed'):
                check_bundle(root)

    def test_inconsistent_frozen_prediction_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make_bundle(root)
            rows = json.loads((root / 'data/native/NATIVE_DECISIONS.json').read_text())
            rows[0]['development_prediction'] = 'NO'
            put(root / 'data/predictions/NATIVE_DECISIONS.json', rows); seal(root)
            with self.assertRaisesRegex(AssertionError, 'Frozen prediction status differs'):
                check_bundle(root)

    def test_independent_obligation_replay_matches_all_scopes(self):
        from wowfs.experiments.co_obligation_audit import audit
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make_bundle(root)
            cert = json.loads((root / 'data/native/portable_toy/base/CONFIDENCE_CERTIFICATES.json').read_text())
            expected = audit(cert)
            replay = replay_obligations(cert)
            for a, b in zip(expected['queries'], replay):
                self.assertEqual(a['diagnostic_labels'], b['labels'])
                for scope, status in b['statuses'].items():
                    self.assertEqual(a['scopes'][scope]['status'], status)
                    self.assertEqual(a['scopes'][scope]['exhaustive_counts'], b['counts'][scope])


if __name__ == '__main__':
    unittest.main()
