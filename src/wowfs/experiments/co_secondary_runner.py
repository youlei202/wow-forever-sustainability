"""Execute the frozen secondary tolerance plan from completed compact moments.

This orchestration module was added after statistical-plan freezing. It changes
no estimand, coefficient, solver, threshold, catalogue or sample count; all
scientific calculations are delegated to hash-verified frozen modules.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import csv
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np

from wowfs.experiments import co_native_sensitivity
from wowfs.experiments.co_review_check import load_moments
from wowfs.paths import SOURCE_ROOT, atomic_json, canonical_hash


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(analysis, registry, frozen_protocol, secondary_protocol, output, *, cpu=122, resume=False):
    analysis, registry, frozen_protocol, secondary_protocol, output = map(Path, (analysis, registry, frozen_protocol, secondary_protocol, output))
    start = time.time()
    if cpu not in os.sched_getaffinity(0):
        raise ValueError('Requested analysis CPU is outside current affinity')
    os.sched_setaffinity(0, {cpu})
    freeze = read(frozen_protocol); plan = read(secondary_protocol)
    if freeze['status'] != 'FROZEN':
        raise ValueError('Pre-sampling protocol is not frozen')
    rels = ['src/wowfs/experiments/' + name + '.py' for name in
            ('co_native_sensitivity', 'co_native_analysis', 'co_exact', 'co_generic')]
    verified_sources = {}
    for rel in rels:
        actual = sha(SOURCE_ROOT / rel)
        if actual != freeze['source_hashes'][rel]:
            raise ValueError('Scientific code differs from pre-sampling freeze: ' + rel)
        verified_sources[rel] = actual
    if sha(secondary_protocol) != freeze['secondary_plans']['SECONDARY_TOLERANCE_PROTOCOL.json']:
        raise ValueError('Secondary protocol differs from pre-sampling freeze')
    for key, value in co_native_sensitivity.PANEL_PROTOCOL.items():
        if plan[key] != value:
            raise ValueError('Secondary plan differs from frozen module: ' + key)
    primary = read(analysis / 'ANALYSIS_MANIFEST.json')
    progress = read(analysis / 'PROGRESS.json')
    if primary['mode'] != 'confirm' or progress['status'] != 'complete':
        raise ValueError('Complete fresh confirmation analysis required')
    if primary['registry_sha256'] != sha(registry):
        raise ValueError('Catalogue registry differs from fresh confirmation')
    unitmap = {unit['unit_id']: unit for unit in freeze['units']}
    if set(primary['world_ids']) != set(unitmap) or len(unitmap) != 16:
        raise ValueError('Secondary panel must include every one of 16 frozen units')
    worlds = {r['world_id']: r for r in (json.loads(line) for line in registry.read_text().splitlines() if line.strip())}
    identity = {'primary_manifest_sha256': sha(analysis / 'ANALYSIS_MANIFEST.json'), 'registry_sha256': sha(registry),
                'frozen_protocol_sha256': sha(frozen_protocol), 'secondary_protocol_sha256': sha(secondary_protocol),
                'verified_frozen_scientific_sources': verified_sources, 'wrapper_source_sha256': sha(__file__),
                'protocol': co_native_sensitivity.PANEL_PROTOCOL, 'cpu_affinity': [cpu]}
    if output.exists():
        if not resume:
            raise ValueError('New output directory required; use --resume for identical checkpoint identity')
        if read(output / 'MANIFEST.json')['identity'] != identity:
            raise ValueError('Secondary resume identity mismatch')
    else:
        output.mkdir(parents=True)
        atomic_json(output / 'MANIFEST.json', {'identity': identity, 'started_utc': datetime.now(timezone.utc).isoformat(),
                     'scope': 'Secondary deterministic consequence of the same fresh fixed-N paired-t events; no additional alpha or observations.',
                     'wrapper_scope': __doc__})
    flat = []; units_completed = []
    for world_id in primary['world_ids']:
        world = worlds[world_id]; wdir = analysis / world_id; destination = output / world_id
        moments = load_moments(wdir, world); unit = unitmap[world_id]
        if moments['N'] != unit['samples_per_cell'] or moments['seed_block_id'] != f"{unit['seed_interval_start']}:{unit['samples_per_cell']}":
            raise ValueError('Unit sample/seed identity differs from pre-sampling freeze')
        with np.load(wdir / 'BOUNDS.npz', allow_pickle=False) as z:
            bounds = {k: z[k] for k in z.files}
        bounds['manifest'] = read(wdir / 'BOUNDS_MANIFEST.json')
        if Fraction(str(bounds['manifest']['alpha'])) != Fraction(unit['alpha']):
            raise ValueError('Unit event alpha differs from pre-sampling freeze')
        if bounds['manifest']['N'] != unit['samples_per_cell']:
            raise ValueError('Event N differs from pre-sampling freeze')
        out = destination / 'TOLERANCE_RESULTS.json'
        provenance = {'world_id': world_id, 'moments_sha256': sha(wdir / 'MOMENTS.npz'),
                      'original_bounds_sha256': sha(wdir / 'BOUNDS.npz'),
                      'original_bounds_manifest_sha256': sha(wdir / 'BOUNDS_MANIFEST.json'),
                      'N': moments['N'], 'seed_block_id': moments['seed_block_id'],
                      'original_alpha': unit['alpha'], 'additional_alpha': 0., 'new_native_calls': 0,
                      'secondary_math_source_sha256': verified_sources['src/wowfs/experiments/co_native_sensitivity.py']}
        if out.exists():
            result = read(out)
            if read(destination / 'PROVENANCE.json') != provenance:
                raise ValueError('Secondary unit resume identity mismatch')
        else:
            result = co_native_sensitivity.analyze_catalogue(world, moments, bounds, primary['rule'], include_means=True)
            atomic_json(destination / 'TOLERANCE_RESULTS.json', result)
            atomic_json(destination / 'PROVENANCE.json', provenance)
        base_cert = read(wdir / 'base/CONFIDENCE_CERTIFICATES.json')
        value_cert = read(wdir / 'base/VALUE_ONLY_CONFIDENCE.json')
        for record in result['records']:
            for j, answer in enumerate(record['population_answers']['queries']):
                exact = record['mean_table_answers']['queries'][j]
                v = value_cert['queries'][j]['status']
                flat.append({'world_id': world_id, 'stratum': world['stratum'], 'query_id': answer['query_id'],
                    'required': answer['required'], 'multiplier': record['multiplier'], 'tolerance': record['tolerance'],
                    'confidence_status': answer['status'], 'mean_status': exact['mean_answer']['status'],
                    'value_only_confidence': v, 'value_only_mean': exact['value_only_answer']['status'],
                    'retention_essential_confidence': answer['status'] == 'NO' and v == 'YES',
                    'primary_base_confidence': base_cert['queries'][j]['status'],
                    'primary_obstruction_dissolved': base_cert['queries'][j]['status'] == 'NO' and answer['status'] == 'YES',
                    'witness': answer['witness'], 'N': moments['N'], 'original_event_alpha': unit['alpha'],
                    'evidence_level': 'FRESH_CONFIRMATION_EVENT_DERIVATION'})
        units_completed.append(world_id)
        atomic_json(output / 'PROGRESS.json', {'status': 'running', 'completed_worlds': units_completed,
                    'worlds_expected': 16, 'query_rows_written': len(flat)})
        print(json.dumps({'world_id': world_id, 'secondary_rows': 4 * len(world['queries']), 'status': 'complete'}), flush=True)
    summary = []
    for multiplier in co_native_sensitivity.PANEL_PROTOCOL['tolerance_multipliers']:
        selected = [r for r in flat if r['multiplier'] == multiplier]
        summary.append({'multiplier': multiplier, 'tolerance': selected[0]['tolerance'], 'queries': len(selected),
            'confidence_counts': dict(Counter(r['confidence_status'] for r in selected)),
            'mean_counts': dict(Counter(r['mean_status'] for r in selected)),
            'retention_essential_queries': sum(r['retention_essential_confidence'] for r in selected),
            'retention_essential_catalogues': len({r['world_id'] for r in selected if r['retention_essential_confidence']}),
            'primary_NO_to_supported_YES': sum(r['primary_obstruction_dissolved'] for r in selected),
            'by_stratum': {s: dict(Counter(r['confidence_status'] for r in selected if r['stratum'] == s)) for s in sorted({r['stratum'] for r in selected})}})
    # Optional tolerance relaxation is monotone for each fixed physical domain.
    # Statistical UNKNOWN is preserved and is never treated as a failed state.
    for world_id in primary['world_ids']:
        for query in worlds[world_id]['queries']:
            rows = [r for r in flat if r['world_id'] == world_id and r['query_id'] == query['query_id']]
            for a, b in zip(rows, rows[1:]):
                if a['confidence_status'] == 'YES' and b['confidence_status'] != 'YES':
                    raise AssertionError('Relaxing e lost a conservative witness')
                if a['mean_status'] == 'YES' and b['mean_status'] == 'NO':
                    raise AssertionError('Relaxing e lost an exact mean completion')
    atomic_json(output / 'TOLERANCE_DECISIONS.json', flat)
    with (output / 'TOLERANCE_DECISIONS.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(flat[0])); writer.writeheader()
        for row in flat:
            writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    atomic_json(output / 'SUMMARY.json', {'status': 'COMPLETE', 'catalogues': 16, 'base_queries_per_threshold': 128,
                'rows': len(flat), 'thresholds': summary, 'elapsed_seconds_this_invocation': time.time() - start,
                'original_main_event_alpha_total': '.04', 'additional_alpha': 0., 'new_native_calls': 0,
                'interpretation': 'All base queries included; nested threshold/target observations are not independent samples or a population prevalence estimate.'})
    atomic_json(output / 'PROGRESS.json', {'status': 'complete', 'completed_worlds': units_completed,
                'worlds_expected': 16, 'query_rows_written': len(flat)})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('analysis', 'registry', 'frozen-protocol', 'secondary-protocol', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--cpu', type=int, default=122)
    parser.add_argument('--resume', action='store_true')
    a = parser.parse_args()
    print(json.dumps(run(a.analysis, a.registry, a.frozen_protocol, a.secondary_protocol, a.output, cpu=a.cpu, resume=a.resume), indent=2))


if __name__ == '__main__':
    main()
