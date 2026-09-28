"""Audit physical execution/provenance separately from scientific outcomes."""
import gzip
import hashlib
import json
from pathlib import Path
from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=setup_paths(); stage='final-completion-capacity'; runs=root/'runs'/stage
    out=root/'artifacts'/stage; errors=[]; records=[]; unique={}
    for path in sorted(runs.glob('*/PROGRESS.json')):
        run=path.parent; progress=json.loads(path.read_text()); protocol=json.loads((run/'PROTOCOL.json').read_text())
        jobs=json.loads((run/'JOBS.json').read_text()); results=json.loads((run/'RESULTS.json').read_text())
        if progress['status']!='complete' or progress['errors'] or results['errors']:
            errors.append(run.name+': incomplete or failed run')
        if canonical_hash(jobs)!=protocol['jobs_sha256']:errors.append(run.name+': job hash')
        if digest(run/'native.frozen')!=protocol['binary_sha256']:errors.append(run.name+': binary hash')
        for relative,expected in protocol['source_hashes'].items():
            if digest(run/'source'/relative)!=expected:errors.append(run.name+': frozen source '+relative)
        for relative,expected in protocol['imported_input_hashes'].items():
            if digest(run/'inputs'/relative)!=expected:errors.append(run.name+': imported artifact '+relative)
        if len(jobs)!=len(results['rows']):errors.append(run.name+': row denominator')
        for job,row in zip(jobs,results['rows']):
            if row is None:errors.append(run.name+': missing native row');continue
            expected=canonical_hash({'binary':protocol['binary_sha256'],'input':job['input']})
            if expected!=row['cache_key']:errors.append(run.name+': physical input identity')
            if row['iterations']!=job['input']['request']['simOptions']['iterations']:
                errors.append(run.name+': battle denominator')
            unique[row['cache_key']]=Path(row['cache_directory'])
        records.append({'run':run.name,**progress,'logical_cells':len(jobs),
                        'protocol_sha256':digest(run/'PROTOCOL.json'),'frozen_source_files':len(protocol['source_hashes']),
                        'freeze_time':json.loads((run/'FREEZE_TIME.json').read_text())['utc']})
    total_seconds=0.
    for index,(key,folder) in enumerate(unique.items()):
        summary=json.loads((folder/'summary.json').read_text())
        with gzip.open(folder/'output.json.gz','rb') as f:raw=f.read()
        if hashlib.sha256(raw).hexdigest()!=summary['output_sha256']:errors.append(key+': raw output digest')
        invocation=json.loads((folder/'invocation.json').read_text());total_seconds+=invocation['elapsed_seconds']
        if invocation['returncode']!=0:errors.append(key+': failed invocation')
        if index and index%5000==0:print('Verified native cache entries',index,flush=True)
    plan=json.loads((out/'FUTURE_SEQUENCE_DESIGN.json').read_text())
    if digest(SOURCE_ROOT/'src/wowfs/experiments/fc_theory.py')!=plan['theory_helper_sha256']:
        errors.append('Planner theory helper changed')
    receipt={'status':'pass' if not errors else 'fail','errors':errors,'physical_runs':records,
             'new_calls':sum(r['new_calls'] for r in records),'new_battles':sum(r['new_fights'] for r in records),
             'unique_verified_native_cache_entries':len(unique),'aggregate_native_process_elapsed_seconds':total_seconds,
             'compute_scope':'Each native invocation GOMAXPROCS=1; at most64 concurrent workers (32 main plus32 mechanisms), no GPU. Process elapsed sum includes scheduling time and is not measured CPU time.',
             'host_cpu':'AMD EPYC 9535 64-Core Processor; host exposes256 logical CPUs, study does not use all of them.',
             'memory_limit_requested_GB':192,'peak_memory_measured':False,
             'scientific_scope':'Checks provenance and physical denominators, not mathematical validity or statistical conclusions.'}
    atomic_json(out/'EXECUTION_AUDIT.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k!='physical_runs'},indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
