"""Read-only analysis of the frozen complete old native completion ecologies."""
import csv
from itertools import combinations
import json
from pathlib import Path
import numpy as np
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.fc_native import STAGE
from wowfs.experiments.r2_native import file_hash


def write_csv(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def portfolio(values,scale,weights,epsilon=.05,coverage=.95):
    frontier=values.max(axis=0)
    close=values>=frontier-epsilon*scale-1e-10
    for k in range(1,len(values)+1):
        for chosen in combinations(range(len(values)),k):
            if float(weights[np.any(close[list(chosen)],axis=0)].sum())>=coverage-1e-12:
                return k,list(chosen)
    raise ValueError('full old domain cannot cover its own frontier')


def analyze():
    root=setup_paths();run=root/'runs'/STAGE/'old-ecologies-v1';out=root/'artifacts'/STAGE
    design=json.loads((run/'inputs/MATCHED_DESIGN.json').read_text())
    result=json.loads((run/'RESULTS.json').read_text());progress=json.loads((run/'PROGRESS.json').read_text())
    cfg=json.loads((run/'source/configs/final_completion_capacity.json').read_text())
    tasks=[t['id'] for t in design['tasks']];weights=np.asarray(cfg['task_weights'],float)
    rows={}
    for row in result['rows']:
        if row is not None:rows[(row['context_id'],row['task'],row['partner_coefficient'])]=row
    contexts=[];matched=[];spectrum=[]
    for original in design['contexts']:
        context=original['context_id'];unit=original['stat_unit'];task_fits=[];regimes={}
        for task in tasks:
            point_rows={co:r for (ct,t,co),r in rows.items() if ct==context and t==task}
            points=sorted(point_rows)
            if points!=[0.,.0001,.0002,.0003,.011,.022,.033,.044]:
                raise ValueError('Old complete domain missing/wrong partner cells:'+context+':'+task)
            base=np.asarray(point_rows[0.]['dps_samples']);end=np.asarray(point_rows[.044]['dps_samples'])
            slope=(end-base)/(.044*unit)
            max_residual=max(float(np.max(np.abs(np.asarray(row['dps_samples'])-(base+x*unit*slope))))
                             for x,row in point_rows.items())
            means={x:float(np.mean(row['dps_samples'])) for x,row in point_rows.items()}
            frontiers={reg:max(means[x] for x in design[reg]) for reg in ('large_gap','dense')}
            scale=max(frontiers.values())
            task_fits.append({'task':task,'B':float(base.mean()),'c':float(slope.mean()),
                'B_over_c':float(base.mean()/slope.mean()) if slope.mean()>0 else None,
                's_q':scale,'cap':(1+cfg['fixed_headroom'])*scale,
                'old_frontiers':frontiers,'matched_frontier_absolute_difference':abs(frontiers['large_gap']-frontiers['dense']),
                'coefficients':[float(base.mean()),float(slope.mean())],
                'sample_coefficients':[base.tolist(),slope.tolist()],
                'max_per_seed_affine_residual':max_residual,
                'max_mean_affine_residual':max(abs(mean-(base.mean()+x*unit*slope.mean())) for x,mean in means.items()),
                'max_affine_residual_normalized':max_residual/scale,
                'positive_slope':bool(slope.mean()>0),'affine_grid_validated_1e_8':max_residual<=1e-8,
                'native_cells':len(points),'iterations_per_cell':len(base),
                'mean_response_by_partner':{str(x):means[x] for x in points},
                'anchor_cache_directories':[point_rows[x]['cache_directory'] for x in (0.,.044)]})
        B=np.array([f['B'] for f in task_fits]);c=np.array([f['c'] for f in task_fits]);scale=np.array([f['s_q'] for f in task_fits])
        positive=bool(np.all(c>0));effective=float(np.min(scale/c)) if positive else None
        for reg in ('large_gap','dense'):
            coefficients=np.asarray(design[reg]);values=np.array([[rows[context,t,float(x)]['dps_mean'] for t in tasks] for x in coefficients])
            frontier=values.max(axis=0);near=values>=frontier-cfg['legacy_epsilon']*scale-1e-10
            masses=near@weights;relevant=masses>=cfg['legacy_required_mass']-1e-12
            k,selected=portfolio(values,scale,weights,cfg['legacy_epsilon'],cfg['portfolio_coverage'])
            actual_sorted=np.sort(values/scale,axis=0);gaps=np.diff(actual_sorted,axis=0)
            scalar=coefficients*unit/effective if effective is not None else np.full(5,np.nan)
            scalar_gaps=np.diff(scalar)
            regimes[reg]={'partner_coefficients':coefficients.tolist(),'partner_stats':(coefficients*unit).tolist(),
                'values':values.tolist(),'relative_values':(values/scale).tolist(),'old_frontier':frontier.tolist(),
                'source_ids':['old_primary']+[reg+':partner_'+str(i) for i in range(5)],
                'source_use_masses':masses.tolist(),'source_relevance':relevant.tolist(),
                'source_conditional_best':values.tolist(),'initial_primary_use_mass':1.,
                'all_sources_relevant':bool(relevant.all()),'relevant_partner_count':int(relevant.sum()),
                'retained_old_source_count':6,'retained_old_partner_count':5,'full_old_configurations':5,
                'H_all_old_configurations_allowed':True,'P_all_old_configurations_under_common_caps':bool(np.all(values<=1.05*scale+1e-10)),
                'portfolio_K':k,'portfolio_partner_indices':selected,
                'max_consecutive_response_gap_by_task':gaps.max(axis=0).tolist(),
                'completion_span_by_task':(actual_sorted[-1]-actual_sorted[0]).tolist(),
                'completion_points_U_eff':scalar.tolist(),'consecutive_gaps_U_eff':scalar_gaps.tolist(),
                'largest_gap_U_eff':float(scalar_gaps.max()),
                'scalar_gap_scope':'Physical component spacing divided by effective native response unit. Exact response-spectrum interpretation conditional on affine validation.'}
            matched.append({'context_id':context,'class':original['class'],'faction':original['faction'],'race':original['race'],
                'regime':reg,'old_partner_count':5,'old_source_count':6,'U':unit,'U_eff':effective,
                'old_grid_affine':all(f['affine_grid_validated_1e_8'] for f in task_fits),
                'prior_affinity_validated':original['affinity_development_validated'],
                'max_per_seed_affine_residual':max(f['max_per_seed_affine_residual'] for f in task_fits),
                'matched_frontier_max_difference':max(f['matched_frontier_absolute_difference'] for f in task_fits),
                'all_sources_relevant':bool(relevant.all()),'relevant_partners':int(relevant.sum()),
                'minimum_source_use_mass':float(masses.min()),'portfolio_K':k,
                'largest_gap_U_eff':float(scalar_gaps.max()),
                'largest_actual_task_gap':float(gaps.max()),'H_all_old_allowed':True,
                'known_racial_incomplete':original['native_racial_incomplete']})
            for q,task in enumerate(tasks):
                order=np.argsort(values[:,q],kind='stable')
                for rank,i in enumerate(order):
                    spectrum.append({'context_id':context,'class':original['class'],'faction':original['faction'],
                        'race':original['race'],'task':task,'regime':reg,'source_partner_index':int(i),
                        'response_order':rank,'partner_coefficient':float(coefficients[i]),'partner_stat':float(coefficients[i]*unit),
                        'native_mean_dps':float(values[i,q]),'initial_task_frontier':float(scale[q]),
                        'common_fixed_cap':float(1.05*scale[q]),'response_relative_frontier':float(values[i,q]/scale[q]),
                        'completion_response_relative_baseline':float((values[i,q]-B[q])/scale[q]),
                        'next_response_gap_normalized':float((values[order[rank+1],q]-values[i,q])/scale[q]) if rank<4 else '',
                        'within_legacy_epsilon':bool(near[i,q]),'source_use_mass':float(masses[i]),
                        'source_relevant':bool(relevant[i]),'affine_grid_validated':task_fits[q]['affine_grid_validated_1e_8']})
        contexts.append({k:original[k] for k in ('context_id','class','faction','race','race_label','native_racial_incomplete','physical_stat')} | {
            'tasks':tasks,'U':unit,'U_eff':effective,'stat_unit':unit,'B':B.tolist(),'c':c.tolist(),
            'B_over_c':(B/c).tolist(),'s_q':scale.tolist(),'caps':(1.05*scale).tolist(),
            'binding_effective_task':tasks[int(np.argmin(scale/c))] if positive else None,
            'calibration_affinity_validated':original['affinity_development_validated'],
            'old_grid_affinity_validated':all(f['affine_grid_validated_1e_8'] for f in task_fits),
            'affinity_validated':original['affinity_development_validated'] and positive and all(f['affine_grid_validated_1e_8'] for f in task_fits),
            'all_positive_slopes':positive,'max_per_seed_affine_residual':max(f['max_per_seed_affine_residual'] for f in task_fits),
            'task_fits':task_fits,'regimes':regimes,'native_errors':[]})
    output={'schema':1,'tasks':tasks,'task_definitions':design['tasks'],'task_weights':weights.tolist(),
        'contexts':contexts,'context_count':len(contexts),'affine_contexts':sum(c['affinity_validated'] for c in contexts),
        'old_grid_affine_contexts':sum(c['old_grid_affinity_validated'] for c in contexts),
        'matched_frontiers_identical_contexts':sum(max(f['matched_frontier_absolute_difference'] for f in c['task_fits'])<=1e-10 for c in contexts),
        'all_sources_relevant_ecologies':sum(r['all_sources_relevant'] for c in contexts for r in c['regimes'].values()),
        'native_errors':result['errors'],'native_error_count':len(result['errors']),
        'successful_native_calls':progress['new_calls'],'physical_battles':progress['new_fights'],
        'analysis_added_native_calls':0,'source_run':str(run),
        'source_results_sha256':file_hash(run/'RESULTS.json'),'source_protocol_sha256':file_hash(run/'PROTOCOL.json'),
        'matched_design_sha256':file_hash(run/'inputs/MATCHED_DESIGN.json'),
        'analysis_source_sha256':file_hash(Path(__file__)),
        'definitions':{'U':'Frozen physical stat unit from scalar calibration.',
          'B_c':'Matched old-grid endpoint fit: u_q(z)=B_q+c_q*z. All8old points validate perseed fit; nonlinear rows preserved.',
          'U_eff':'min_q(s_q/c_q) from current actual fully reoptimized initial old task frontiers, not future outcomes.',
          'source_use':'Each old partner is relevant on tasks where its conditional-best native gear is within frozen epsilon*s_q of its ecology frontier. Source requires mass>=.05. Initial primary is common to every old gear.',
          'source_counts':'One shared old primary plus five distinct old partner research aliases in each ecology.',
          'portfolio':'Exact enumeration of all5old gears, within epsilon=.05 of own frontier, taskcoverage>=.95; no futuregearornewDclaim.',
          'caps':'Common taskwise1.05*max(large_gap_oldfrontier,dense_oldfrontier).',
          'nonaffine':'U_eff and scalar gaps in failed-affinity contexts are descriptive endpoint-fit statistics; not exact scalar-theorem mappings.'}}
    analysis=root/'runs'/STAGE/'old-ecology-analysis-v1'
    if (analysis/'PROTOCOL.json').exists():raise ValueError('analysis run already frozen; choose explicit new revision')
    atomic_json(analysis/'PROTOCOL.json',{'analysis_only':True,'new_native_calls':0,
        'input_results_sha256':output['source_results_sha256'],'source_sha256':output['analysis_source_sha256']})
    (analysis/'fc_old_analysis.py').write_text(Path(__file__).read_text())
    atomic_json(analysis/'OLD_ECOLOGY_ANALYSIS.json',output);atomic_json(out/'OLD_ECOLOGY_ANALYSIS.json',output)
    write_csv(out/'MATCHED_ECOLOGIES.csv',matched);write_csv(out/'COMPLETION_SPECTRA.csv',spectrum)
    print(json.dumps({k:v for k,v in output.items() if k not in ('contexts','definitions','task_definitions')},indent=2))


if __name__=='__main__':analyze()
