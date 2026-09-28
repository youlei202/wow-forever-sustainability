"""Secondary, lossless-float moment export from completed frozen native cells.

No simulation or primary claim adjudication is performed. Source scripts/env.sh
first; write only to a new artifact directory under WOWFS_WORK_ROOT.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
from itertools import product
import json
from pathlib import Path
import numpy as np
from wowfs.paths import canonical_hash
from wowfs.experiments.r2_native import summarize


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def export(batch,manifest_path,output):
    if output.exists():raise ValueError('New export directory required')
    progress=json.loads((batch/'PROGRESS.json').read_text())
    if progress.get('status')!='completed' or progress.get('failed_inputs'):
        raise ValueError('Complete successful batch required')
    manifest=json.loads(manifest_path.read_text());protocol=json.loads((batch/'PROTOCOL.json').read_text())
    if protocol['science']['confirmation_manifest_sha256']!=sha(manifest_path):
        raise ValueError('Frozen batch manifest mismatch')
    jobs=json.loads((batch/'JOBS.json').read_text());index=json.loads((batch/'OBSERVATION_INDEX.json').read_text())
    if canonical_hash(jobs)!=protocol['jobs_sha256'] or len(jobs)!=len(index):raise ValueError('Frozen jobs mismatch')
    worlds={w['world_id']:w for w in manifest['worlds']};arrays={};readable=[];metadata=[];means_rows=[];cache_rows=[]
    max_mean_error=0.;max_se_error=0.;raw_checked=0
    for number,claim in enumerate(manifest['claims'],1):
        world=worlds[claim['world_id']];prefix=f'claim_{number:02}'
        configurations=list(product([f'a{i:02}' for i in range(len(world['candidates']))],
                                    [f'x{i}' for i in range(len(world['partners']))],sorted(world['policies'])))
        tasks=sorted(t['task_id'] for t in world['tasks']);n=claim['iterations']
        samples=np.empty((len(configurations),len(tasks),n));seen=set();records={}
        for job,row in zip(jobs,index):
            if row['world_id']!=claim['world_id']:continue
            key=(row['candidate_id'],row['partner_id'],row['policy_id']);q=tasks.index(row['task_id']);i=configurations.index(key)
            if (i,q) in seen:raise ValueError('Duplicate physical cell')
            if canonical_hash(job['input'])!=row['input_sha256'] or row['binary_sha256']!=protocol['binary_sha256']:
                raise ValueError('Observed cell identity mismatch')
            if row['seed_block_id']!=claim['seed_block_id'] or row['iterations']!=n:raise ValueError('Seed/N mismatch')
            folder=Path(row['cache_directory']);request=json.loads((folder/'input.json').read_text())
            if request!=job['input']:raise ValueError('Cached request differs')
            with gzip.open(folder/'output.json.gz','rb') as stream:raw=stream.read()
            if hashlib.sha256(raw).hexdigest()!=row['output_sha256']:raise ValueError('Native raw hash mismatch')
            measured=summarize(json.loads(raw),request)
            if any(measured[k]!=row[k] for k in ('iterations','dps_mean','dps_se')):raise ValueError('Raw moments differ from row')
            samples[i,q]=measured['dps_samples'];seen.add((i,q));records[i,q]=row;raw_checked+=1
            cache_rows.append({'claim_id':claim['claim_id'],'world_id':claim['world_id'],'configuration_index':i,'task_index':q,
                'input_sha256':row['input_sha256'],'raw_output_sha256':row['output_sha256'],'cache_key':row['cache_key'],
                'cache_directory':str(folder.resolve()),'raw_input':str((folder/'input.json').resolve()),
                'raw_native_output_gzip':str((folder/'output.json.gz').resolve())})
        if len(seen)!=len(configurations)*len(tasks):raise ValueError('Incomplete physical tensor')
        means=samples.mean(axis=2);covariance=np.empty((len(tasks),len(configurations),len(configurations)))
        for q in range(len(tasks)):
            centered=samples[:,q]-means[:,q,None];covariance[q]=centered@centered.T/(n-1)
        refs={ref['task_id']:ref for ref in claim['reference_mapping']}
        ref_indices=[configurations.index((refs[q]['candidate_id'],refs[q]['partner_id'],refs[q]['policy_id'])) for q in tasks]
        checks=[]
        for q,ref_index in enumerate(ref_indices):
            if records[ref_index,q]['input_sha256']!=refs[tasks[q]]['input_sha256']:raise ValueError('Reference identity changed')
            for i,j in ((0,0),(0,len(configurations)-1),(len(configurations)//2,0),(len(configurations)-1,len(configurations)//2)):
                for offset in (claim['gain'],-claim['tolerance'],claim.get('match_tolerance',.0025)):
                    coefficients=np.zeros(len(configurations));coefficients[i]+=1;coefficients[j]-=1;coefficients[ref_index]-=offset
                    direct=samples[i,q]-samples[j,q]-offset*samples[ref_index,q]
                    delta_mean=abs(float(coefficients@means[:,q])-float(direct.mean()))
                    variance=float(coefficients@covariance[q]@coefficients)
                    delta_se=abs(float(np.sqrt(max(0.,variance)/n))-float(direct.std(ddof=1)/np.sqrt(n)))
                    max_mean_error=max(max_mean_error,delta_mean);max_se_error=max(max_se_error,delta_se)
                    checks.append({'q':q,'i':i,'j':j,'offset':offset,'mean_absolute_error':delta_mean,'se_absolute_error':delta_se})
        arrays[prefix+'_mean']=means;arrays[prefix+'_covariance']=covariance;arrays[prefix+'_N']=np.array(n,dtype=np.int64)
        info={'claim_id':claim['claim_id'],'world_id':claim['world_id'],'array_prefix':prefix,'N':n,
              'seed_block_id':claim['seed_block_id'],'configuration_order':[list(c) for c in configurations],
              'task_order':tasks,'reference_configuration_indices_by_task':ref_indices,
              'mean_shape':list(means.shape),'sample_covariance_shape':list(covariance.shape),
              'covariance_denominator':'N-1','units':{'mean':'native owner DPS','covariance':'DPS squared'},
              'paired_linear_check_errors':checks}
        metadata.append(info);readable.append({**info,'mean':means.tolist(),'sample_covariance':covariance.tolist()})
        for i,cfg in enumerate(configurations):
            for q,task in enumerate(tasks):means_rows.append({'claim_id':claim['claim_id'],'configuration_index':i,
                'candidate_id':cfg[0],'partner_id':cfg[1],'policy_id':cfg[2],'task_index':q,'task_id':task,
                'N':n,'mean_DPS':means[i,q],'sample_variance_DPS2':covariance[q,i,i],
                'is_physical_reference':i==ref_indices[q]})
        print(json.dumps({'exported_claim':claim['claim_id'],'cells':len(seen),'N':n}),flush=True)
    output.mkdir(parents=True);np.savez_compressed(output/'MOMENTS.npz',**arrays)
    (output/'MOMENTS_READABLE.json').write_text(json.dumps(readable,separators=(',',':'),allow_nan=False)+'\n')
    for name,rows in [('MEANS.csv',means_rows),('RAW_CACHE_INDEX.csv',cache_rows)]:
        with (output/name).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report={'status':'completed_secondary_export','not_new_native_observations':True,
        'manifest_reference_json':str(manifest_path.resolve()),'manifest_sha256':sha(manifest_path),
        'frozen_protocol_sha256':sha(batch/'PROTOCOL.json'),'jobs_sha256':sha(batch/'JOBS.json'),
        'observation_index_sha256':sha(batch/'OBSERVATION_INDEX.json'),'primary_results_sha256':sha(batch/'RESULTS.json'),
        'exporter_source_sha256':sha(Path(__file__)),'raw_cells_independently_verified':raw_checked,
        'array_file':'MOMENTS.npz','readable_array_file':'MOMENTS_READABLE.json','mean_csv':'MEANS.csv',
        'full_absolute_raw_index_csv':'RAW_CACHE_INDEX.csv','worlds':metadata,
        'max_checked_linear_mean_absolute_error':max_mean_error,'max_checked_linear_SE_absolute_error':max_se_error,
        'reproduction':'For task q and coefficient vector a: mean=a@mean[:,q], SE=sqrt(a@covariance[q]@a/N); df=N-1. Reference is the indicated physical C index. Use the frozen family alpha/count and t critical value; then the original max/min and graph algorithms.',
        'scope':'These first/second moments reproduce paired linear-t contrasts up to float64 roundoff. They do not reproduce trajectories, higher moments, tail diagnostics, or alternative post-hoc estimands. They are summaries of the same observations, never extra independent data.',
        'numerics':'Centered float64 sample covariance. Tiny negative quadratic variances from cancellation require an explicit roundoff check; do not reinterpret them as native determinism.',
        'file_sha256':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}
    (output/'MOMENTS_MANIFEST.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (output/'README.md').write_text('# Compact paired native moments\n\nSecondary export of the frozen confirmation; no new observations. Read MOMENTS_MANIFEST.json for provenance, array orders, N and physical reference indices. MOMENTS.npz and MOMENTS_READABLE.json contain the same float64 means and unbiased sample covariance; MEANS.csv is a readable row table. RAW_CACHE_INDEX.csv retains full absolute raw input/output paths and hashes.\n\nFor each task, a paired contrast with coefficient vector a has mean `a @ mean[:, q]` and standard error `sqrt(a @ covariance[q] @ a / N)`. Apply the original fixed-N t critical value and the manifest’s simultaneous family allocation. Covariance is over seed indices within each task; cross-task covariance is unnecessary for the frozen taskwise families. Every reference is a measured configuration, so its uncertainty and correlations remain included.\n\nThe files suffice for the frozen linear-t arithmetic up to floating-point rounding, then its max/min comparisons. They do not validate approximate t assumptions or replace raw trajectories for new estimands. The primary analysis and adjudication remain unchanged.\n')
    print(json.dumps({'output':str(output),'raw_verified':raw_checked,'max_mean_error':max_mean_error,'max_se_error':max_se_error}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('batch','manifest','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();export(args.batch,args.manifest,args.output)
