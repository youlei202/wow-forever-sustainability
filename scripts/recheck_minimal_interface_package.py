"""Replay a sealed minimal-interface package using only its contained inputs.

Output is external to the package. The caller configures caches with env.sh.
This wrapper only relocates the theory proof input; it does not edit any code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def extract(archive, destination):
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            p = Path(info.filename)
            if p.is_absolute() or '..' in p.parts or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe archive member: ' + info.filename)
        if not destination.exists():
            destination.mkdir(parents=True)
            z.extractall(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    package, output = args.package.resolve(), args.output.resolve()
    if output.is_relative_to(package):
        raise ValueError('Recheck output must be outside the sealed package')
    output.mkdir(parents=True, exist_ok=True)
    manifest = read(package / 'PACKAGE_MANIFEST.json')
    for row in manifest['files']:
        path = package / row['path']
        if not path.resolve().is_relative_to(package) or sha(path) != row['sha256']:
            raise ValueError('Package manifest mismatch: ' + row['path'])
    identity = {'package_manifest_sha256': sha(package / 'PACKAGE_MANIFEST.json'),
                'runner_source_sha256': sha(__file__), 'package': str(package), 'output': str(output)}
    freeze = output / 'RECHECK_CONFIG.json'
    if freeze.exists():
        if not args.resume or read(freeze) != identity:
            raise ValueError('Recheck resume source/config identity mismatch')
    else:
        freeze.write_text(json.dumps(identity, indent=2) + '\n')
    extract(package / 'inputs/review-v2.zip', output / 'inputs/review')
    extract(package / 'inputs/WoW_Minimal_Interface_Codex_Handoff.zip', output / 'inputs/handoff')
    bundle = output / 'inputs/review/review-v2'
    handoff = output / 'inputs/handoff/WoW_Minimal_Interface_Codex_Handoff'
    extract(handoff / 'WoW_Future_Targets_AISTATS2027_LaTeX.zip', output / 'inputs/manuscript')
    manuscript = output / 'inputs/manuscript/WoW_Future_Targets_AISTATS2027'
    prior = manuscript / 'evidence/gold/checked_outputs'
    # Ensure the replay cannot accidentally fall back to the live repo or old
    # frozen inputs. Python dependencies under the external environment remain
    # available. Reading the newly extracted package and replay tree is allowed.
    before = read(package / 'PREFLIGHT.json')
    blocked = [Path(before['source_root']), Path(before['review_bundle']),
               Path(before['work_root']) / 'inputs/minimal-interface-2026-09-27']
    def guard(event, arguments):
        if event != 'open' or not arguments or not isinstance(arguments[0], (str, bytes)):
            return
        p = Path(arguments[0].decode() if isinstance(arguments[0], bytes) else arguments[0]).resolve()
        if any(p == root or p.is_relative_to(root) for root in blocked):
            raise RuntimeError('Original source/input fallback forbidden: ' + str(p))
    sys.addaudithook(guard)
    sys.path.insert(0, str(package / 'code'))
    from wowfs.experiments import mi_native, mi_druid, mi_theory
    assert all(Path(m.__file__).resolve().is_relative_to(package / 'code') for m in (mi_native, mi_druid, mi_theory))
    summary = mi_native.run(bundle, output / 'native', args.resume)
    # JSON serializes integer histogram keys as strings. Compare the recorded
    # JSON form on both sides instead of an in-memory dict to its serialization.
    assert read(output / 'native/NATIVE_SUMMARY.json') == read(package / 'NATIVE_SUMMARY.json')
    print(json.dumps({'native': 'PASS', 'contracts': summary['contracts']}), flush=True)
    druid = mi_druid.run(bundle, output / 'druid', args.resume,
                         str(prior / 'TRIPLE_SOURCE_CERTIFICATE_v2.json'), str(prior / 'TRIPLE_INDEPENDENT_CERTIFICATES.json'))
    original = read(package / 'DRUID_TRIPLE_RECHECK.json')
    for key in ['endpoints', 'all_physical_cap_safe', 'minimum_physical_cap_lower_margin_DPS', 'exact_finite_mean_queries',
                'whole_interval', 'attribution', 'validation']:
        assert druid[key] == original[key], key
    print(json.dumps({'druid': 'PASS'}), flush=True)
    mi_theory.PROOF_PATH = handoff / 'wow_minimal_interface_proof.pdf'
    mi_theory.run(output / 'theory', resume=args.resume)
    theory = read(output / 'theory/UNIVERSAL_CONSTRUCTION_CHECKS.json')
    original = read(package / 'UNIVERSAL_CONSTRUCTION_CHECKS.json')
    for key in ['checks', 'boundary_corners', 'high_order_pairs', 'check_count', 'expected_guarantee_failure_count']:
        assert theory[key] == original[key], key
    for name in ['SYMBOLIC_VS_ANTICHAIN.csv', 'SEMANTIC_MINIMALITY_CHECKS.json']:
        assert (output / 'theory' / name).read_bytes() == (package / name).read_bytes(), name
    result = {'status': 'PASS', 'new_native_battles': 0, 'additional_alpha': 0,
              'source_modules': {m.__name__: str(m.__file__) for m in (mi_native, mi_druid, mi_theory)},
              'original_source_and_inputs_read_blocked': list(map(str, blocked)),
              'manifest_files_checked': len(manifest['files']), 'native_contracts': summary['contracts'],
              'target_queries': summary['total_target_queries'], 'druid': 'PASS', 'theory_checks': theory['check_count'],
              'scientific_results_equal_saved_outputs': True}
    (output / 'PORTABLE_RECHECK.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
