"""Frozen-path native inference; no outcome-dependent admission or new physics."""
import argparse
import csv
from copy import deepcopy
import json
from pathlib import Path
import shutil
import numpy as np
from scipy.stats import t as student_t
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json,canonical_hash
from wowfs.experiments.fc_native import STAGE
from wowfs.experiments.fc_calibration import all_controls,damage_channels
from wowfs.experiments.fc_behavior import profile_from_output,profile_from_outputs
from wowfs.experiments.r3_affine import raw,trace_events
from wowfs.experiments.r2_native import file_hash

TOL=1e-10


def point(p,x):return round(float(p),14),round(float(x),14)


def clean(value):
    if isinstance(value,np.ndarray):return clean(value.tolist())
    if isinstance(value,(np.integer,np.floating,np.bool_)):return clean(value.item())
    if isinstance(value,float) and not np.isfinite(value):return None
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [clean(v) for v in value]
    return value


def write_csv(path,rows):
    if not rows:
        path.write_text('status\nnot_run\n');return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for row in rows:
            row=clean(row)
            writer.writerow({k:json.dumps(v,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in row.items()})


def cover(masks,weights,target=.95):
    solutions={0:()}
    for i,mask in enumerate(masks):
        for previous,indices in list(solutions.items()):
            combined=previous|int(mask);candidate=indices+(i,)
            if combined not in solutions or len(candidate)<len(solutions[combined]):solutions[combined]=candidate
    valid=[v for m,v in solutions.items() if sum(w for q,w in enumerate(weights) if m&(1<<q))>=target-TOL]
    return min(valid,key=len) if valid else None


def task_masks(near):
    return [sum(1<<q for q,v in enumerate(row) if v) for row in near]


class PairedBounds:
    """Simultaneous finite contrast family shared by every frozen path."""
    def __init__(self,samples,reference,alpha=.05):
        self.samples=samples;self.reference=reference
        self.means=samples.mean(axis=2);self.ref=reference.mean(axis=1)
        count,tasks,n=samples.shape;self.n=n
        # Every ordered cross pair for gain and relevance, plus paired and
        # absolute numeric cap contrasts. Reusing them across paths adds none.
        self.family_size=tasks*(2*count*count+2*count)
        self.critical=float(student_t.ppf(1-alpha/(2*self.family_size),n-1))
        self.pairs={}
        for offset in (.01,-.05):
            low=np.empty((tasks,count,count));high=np.empty_like(low)
            for q in range(tasks):
                centered=samples[:,q]-self.means[:,q,None]
                covariance=centered@centered.T/(n-1)
                rc=reference[q]-self.ref[q]
                cross=centered@rc/(n-1);rv=float(rc@rc/(n-1))
                variance=np.diag(covariance)[:,None]+np.diag(covariance)[None,:]-2*covariance
                variance+=offset*offset*rv-2*offset*cross[:,None]+2*offset*cross[None,:]
                se=np.sqrt(np.maximum(0.,variance)/n)
                mean=self.means[:,q,None]-self.means[None,:,q]-offset*self.ref[q]
                low[q]=mean-self.critical*se;high[q]=mean+self.critical*se
            self.pairs[offset]=(low,high)
        contrasts=samples-1.05*reference[None,:,:]
        self.cap_mean=contrasts.mean(axis=2)
        cap_se=contrasts.std(axis=2,ddof=1)/np.sqrt(n)
        self.cap_low=self.cap_mean-self.critical*cap_se
        self.cap_high=self.cap_mean+self.critical*cap_se
        self.absolute_se=samples.std(axis=2,ddof=1)/np.sqrt(n)

    def frontier_contrast(self,left,right,offset):
        """Bounds max(left)-max(right)-offset*fixed_reference, per task."""
        if not len(left) or not len(right):
            return np.full(len(self.ref),-np.inf),np.full(len(self.ref),np.inf)
        lo,hi=self.pairs[offset]
        l=lo[:,left][:,:,right];h=hi[:,left][:,:,right]
        # Lower: choose a left witness then protect against every right gear.
        # Upper: any right witness bounds all left gears; choose the best bound.
        return l.min(axis=2).max(axis=1),h.max(axis=1).min(axis=1)

    def gear_relevance_lowers(self,gears):
        return self.pairs[-.05][0][:,gears][:,:,gears].min(axis=2).T


def context_table(ctx,rows,tasks):
    grouped={(point(r['primary_coefficient'],r['partner_coefficient']),r['task']):r for r in rows}
    raw_cache={};validation=[];affine=bool(ctx['affinity_validated'])
    per_task={}
    for task in tasks:
        q=task['id'];zero=grouped[point(0,0),q];high=grouped[point(.148,0),q]
        a=np.asarray(zero['dps_samples']);slope=(np.asarray(high['dps_samples'])-a)/(.148*ctx['U'])
        r0=raw(zero);r1=raw(high);raw_cache[point(0,0),q]=r0;raw_cache[point(.148,0),q]=r1
        num0=damage_channels(r0,task['duration']);num1=damage_channels(r1,task['duration'])
        reference_control=canonical_hash(all_controls(r0));reference_trace=canonical_hash(trace_events(r0.get('logs','')))
        for (key,task_id),row in grouped.items():
            if task_id!=q:continue
            output=raw_cache.get((key,q))
            if output is None:output=raw(row);raw_cache[key,q]=output
            total=sum(key)*ctx['U'];pred=a+slope*total
            residual=float(np.max(abs(np.asarray(row['dps_samples'])-pred)))
            channel_residual=float(np.max(abs(damage_channels(output,task['duration'])-(num0+(num1-num0)*total/(.148*ctx['U'])))))
            same_control=canonical_hash(all_controls(output))==reference_control
            same_trace=canonical_hash(trace_events(output.get('logs','')))==reference_trace
            validation.append({'context_id':ctx['context_id'],'task':q,'primary_coefficient':key[0],
                'partner_coefficient':key[1],'max_per_seed_affine_residual':residual,
                'max_channel_residual':channel_residual,'recursive_controls_identical':same_control,
                'first_seed_trace_identical':same_trace,'cache_key':row['cache_key']})
            if affine and (residual>1e-8 or channel_residual>1e-8 or not same_control or not same_trace):affine=False
        per_task[q]=(a,slope,r0,r1)
    # The full declared configurations are represented even when their source
    # alias is never selected as a frontier witness.
    points=set([point(0,0),point(.148,0),point(0,.044),point(.104,0)])
    for seq in ctx['sequences']:
        if not ctx['affinity_validated'] and seq['variant']=='exact':continue
        for p in [0.]+seq['primary_coefficients']:
            for x in seq['partner_coefficients']:points.add(point(p,x))
    keys=[];samples=[];profiles=[];physical=[];missing=[]
    for key in sorted(points):
        values=[];behavior=[];statuses=[]
        for task in tasks:
            q=task['id'];row=grouped.get((key,q));a,slope,r0,r1=per_task[q]
            if row is not None:
                values.append(row['dps_samples']);statuses.append('physical')
                behavior.append(profile_from_output(raw_cache[key,q],task['duration'],ctx['class'])['profile'])
            elif affine:
                total=sum(key)*ctx['U'];values.append(a+slope*total);statuses.append('validated_affine_interpolation')
                behavior.append(profile_from_outputs(r0,r1,total,.148*ctx['U'],task['duration'],ctx['class'])['profile'])
            else:
                values.append(None);statuses.append('not_run');behavior.append(None)
        if any(v is None for v in values):missing.append({'point':key,'statuses':statuses});continue
        keys.append(key);samples.append(values);profiles.append(behavior);physical.append(statuses)
    reference=np.array([grouped[point(0,.044),t['id']]['dps_samples'] for t in tasks])
    return {'keys':keys,'index':{key:i for i,key in enumerate(keys)},'samples':np.asarray(samples),
        'profiles':np.asarray(profiles),'physical_status':physical,'reference':reference,
        'affinity_development':ctx['affinity_validated'],'affinity_confirmation':affine,
        'validation':validation,'missing':missing,'actual_rows':len(rows),
        'max_per_seed_residual':max(v['max_per_seed_affine_residual'] for v in validation),
        'max_channel_residual':max(v['max_channel_residual'] for v in validation)}


def sequence_analysis(ctx,seq,table,bounds,weights,old):
    metadata={k:ctx[k] for k in ('context_id','class','faction','race','native_racial_incomplete')}
    metadata.update(sequence=seq['name'],regime=seq['regime'],variant=seq['variant'],ecology=seq['ecology'],rule=seq['rule'])
    if not ctx['affinity_validated'] and seq['variant']=='exact':
        return [],[],[],[],{**metadata,'status':'not_run_nonaffine_exact_path','mean_successful_prefix':None,'ci_supported_prefix':None}
    xs=seq['partner_coefficients'];index=table['index'];means=bounds.means;scale=bounds.ref
    needed=[point(p,x) for p in [0.]+seq['primary_coefficients'] for x in xs]
    missing=[key for key in needed if key not in index]
    if missing:
        return [],[],[],[],{**metadata,'status':'unresolved_affine_mapping_missing_physics','missing_points':missing,
                            'mean_successful_prefix':None,'ci_supported_prefix':None}
    previous=np.array([index[point(0,x)] for x in xs],dtype=int)
    history_mask=np.ones((1,len(xs)),dtype=bool)
    rows=[];legacy=[];portfolios=[];costs=[];point_prefix=ci_prefix=joint_prefix=0
    failed=uncertain=joint_failed=False
    for step,p in enumerate(seq['primary_coefficients'],1):
        frozen=seq['rows'][step-1];mask=np.asarray(frozen['admission_mask'],bool)
        primaries=[0.]+seq['primary_coefficients'][:step]
        lookup=np.array([[index[point(a,x)] for x in xs] for a in primaries],dtype=int)
        current=lookup[mask];new=lookup[-1][mask[-1]]
        frontier=means[current].max(axis=0);before=means[previous].max(axis=0)
        gain=(frontier-before)/scale
        gain_lower,gain_upper=bounds.frontier_contrast(new,previous,.01)
        gain_mass=float(weights[gain>=.01-TOL].sum())
        gain_mass_lower=float(weights[gain_lower>=-TOL].sum());gain_mass_upper=float(weights[gain_upper>=-TOL].sum())
        source_gears={'old_primary':lookup[0][mask[0]]}
        source_gears.update({f'primary_{i}':lookup[i][mask[i]] for i in range(1,step+1)})
        source_gears.update({f'partner_{j}':lookup[:,j][mask[:,j]] for j in range(len(xs))})
        source_metrics={}
        for source,gears in source_gears.items():
            best=means[gears].max(axis=0) if len(gears) else np.full(len(scale),-np.inf)
            gap=(best-frontier)/scale;lo,hi=bounds.frontier_contrast(gears,current,-.05)
            mass=float(weights[gap>=-.05-TOL].sum());lower_mass=float(weights[lo>=-TOL].sum());upper_mass=float(weights[hi>=-TOL].sum())
            record={**metadata,'round':step,'source_id':source,'source_is_new':source==f'primary_{step}',
                'conditional_best':best.tolist(),'relative_gap_to_frontier':gap.tolist(),'source_use_mass':mass,
                'source_use_mass_lower':lower_mass,'source_use_mass_upper':upper_mass,
                'mean_relevant':mass>=.05-TOL,'ci_relevant':lower_mass>=.05-TOL,
                'paired_relevance_contrast_lower':lo.tolist(),'paired_relevance_contrast_upper':hi.tolist()}
            source_metrics[source]=record;legacy.append(record)
        N=source_metrics[f'primary_{step}']['mean_relevant'];Nci=source_metrics[f'primary_{step}']['ci_relevant']
        L=all(r['mean_relevant'] for s,r in source_metrics.items() if s!=f'primary_{step}')
        Lci=all(r['ci_relevant'] for s,r in source_metrics.items() if s!=f'primary_{step}')
        H=bool(np.all(mask[:-1][history_mask]) and np.all(mask[0]))
        near=means[current]>=frontier-.05*scale-TOL
        near_ci=bounds.gear_relevance_lowers(current)>=-TOL
        chosen=cover(task_masks(near),weights);chosen_ci=cover(task_masks(near_ci),weights)
        K=None if chosen is None else len(chosen);Kci=None if chosen_ci is None else len(chosen_ci)
        P=bool(np.all(bounds.cap_mean[current]<=TOL));Pci=bool(np.all(bounds.cap_high[current]<=TOL))
        numeric_caps=np.asarray(old['caps']);absolute=means[current]-numeric_caps
        numeric_P=bool(np.all(absolute<=TOL))
        numeric_Pci=bool(np.all(absolute+bounds.critical*bounds.absolute_se[current]<=TOL))
        # D is a mean behavior diagnostic only. All previously allowed old-only
        # configurations are compared, not merely prior frontier witnesses.
        distances=[];novel_tasks=[]
        for q in range(len(scale)):
            available=new[means[new,q]>=frontier[q]-.05*scale[q]-TOL]
            if len(available):
                d=np.max(np.abs(table['profiles'][available,q,None,:]-table['profiles'][None,previous,q,:]),axis=2)
                maximum=float(d.min(axis=1).max())
            else:maximum=0.
            distances.append(maximum);novel_tasks.append(maximum>=.05-TOL)
        behavior_mass=float(weights[np.asarray(novel_tasks)].sum())
        D=behavior_mass>=.05-TOL if ctx['class']=='Warrior' else None
        checks={'P':P,'N':N,'L':L,'H':H,'C':K is not None and K<=4,'G':gain_mass>=.125-TOL}
        ci_checks={'P':Pci,'N':Nci,'L':Lci,'H':H,'C':Kci is not None and Kci<=4,'G':gain_mass_lower>=.125-TOL}
        passed=all(checks.values());supported=all(ci_checks.values())
        failed|=not passed;uncertain|=not supported
        if not failed:point_prefix+=1
        if not uncertain:ci_prefix+=1
        if ctx['class']=='Warrior':
            joint_failed|=not(passed and D)
            if not joint_failed:joint_prefix+=1
        conditions={**{k:v for k,v in checks.items()},**{k+'_ci':v for k,v in ci_checks.items()}}
        row={**metadata,'round':step,'primary_coefficient':p,'primary_stat':p*ctx['U'],
            'status':'assessed','affinity_confirmed':table['affinity_confirmation'],
            'data_mode':'fresh_anchor_validated_interpolation' if table['affinity_confirmation'] else 'full_native_crosses',
            'complete_configurations':int(mask.size),'admitted_configurations':int(mask.sum()),
            'physical_configuration_task_cells':sum(s=='physical' for i in lookup.ravel() for s in table['physical_status'][i]),
            'interpolated_configuration_task_cells':sum(s=='validated_affine_interpolation' for i in lookup.ravel() for s in table['physical_status'][i]),
            'frontier':frontier.tolist(),'previous_frontier':before.tolist(),'fixed_reference_scale':scale.tolist(),
            'normalized_gains':gain.tolist(),'gain_mass':gain_mass,'gain_mass_lower':gain_mass_lower,'gain_mass_upper':gain_mass_upper,
            'maximum_gain':float(gain.max()),'gain_contrast_lower':gain_lower.tolist(),'gain_contrast_upper':gain_upper.tolist(),
            'minimum_cap_margin':float(np.min((1.05*scale-frontier)/scale)),
            'paired_cap_upper_max':float(bounds.cap_high[current].max()),
            'absolute_development_numeric_P':numeric_P,'absolute_development_numeric_P_ci':numeric_Pci,
            'absolute_development_numeric_cap_margin':float(np.min(numeric_caps-frontier)),
            'minimum_source_use_mass':min(r['source_use_mass'] for r in source_metrics.values()),
            'minimum_source_use_mass_lower':min(r['source_use_mass_lower'] for r in source_metrics.values()),
            'K':K,'K_ci':Kci,'original_Warrior_D':D,'behavior_diagnostic_mass':behavior_mass,
            'behavior_max_min_distances':distances,'behavior_kind':'original_Warrior7' if ctx['class']=='Warrior' else 'physical5_diagnostic',
            'joint_ci':'not_established_behavior_inference_not_provided',
            **conditions,'value_legacy_mean_pass':passed,'value_legacy_ci_pass':supported,
            'mean_successful_prefix':point_prefix,'ci_supported_prefix':ci_prefix,
            'after_failed_mean_prefix':failed and not(not passed and point_prefix==step-1),
            'frozen_predicted_value_legacy_pass':frozen['value_legacy_pass']}
        rows.append(row)
        portfolios.append({**metadata,'round':step,'K':K,'K_ci':Kci,
            'mean_selected_points':[table['keys'][current[i]] for i in chosen] if chosen is not None else [],
            'ci_selected_points':[table['keys'][current[i]] for i in chosen_ci] if chosen_ci is not None else [],
            'coverage_requirement':.95,'K_max':4,'unchanged_policy_count':1})
        predicted=np.asarray(old['B'])+np.asarray(old['c'])*(ctx['U']*(np.asarray(primaries)[:,None]+np.asarray(xs)[None,:]))[:,:,None]
        natural=np.all(predicted<=numeric_caps+1e-9,axis=2)
        removed=natural&~mask
        native_natural_frontier=means[lookup[natural]].max(axis=0)
        costs.append({**metadata,'round':step,'new_naturally_safe_pairs':int(natural[-1].sum()),
            'new_safe_pairs_removed':int(removed[-1].sum()),'cumulative_safe_pairs_removed':int(removed.sum()),
            'old_pairs_removed':int((~mask[0]).sum()),
            'immediate_opportunity_loss':((native_natural_frontier-frontier)/scale).tolist(),
            'additional_admission_rule_rows':1 if seq['rule']=='budget12' else 0,
            'item_specific_exceptions':0,'same_dimension_generic_can_represent_rule':True,
            'natural_cost_domain':'Frozen old-model cap-safe complete crosses; evaluated on held-out responses without changing masks.'})
        previous=current;history_mask=mask
    summary={**metadata,'status':'assessed','planned_rounds':len(seq['primary_coefficients']),
        'mean_successful_prefix':point_prefix,'ci_supported_prefix':ci_prefix,
        'Warrior_joint_mean_prefix':joint_prefix if ctx['class']=='Warrior' else None,
        'T_joint':'mean_diagnostic_only' if ctx['class']=='Warrior' else 'not_assessed_original_behavior_not_defined',
        'continuous_utility_upper':seq['continuous_utility_upper'] if table['affinity_confirmation'] else None,
        'continuous_upper_scope':'Conditional fitted-scalar bound, not a native population exactness claim.' if table['affinity_confirmation'] else 'not_established',
        'predicted_value_legacy_prefix':seq['fitted_value_legacy_successful_prefix'],
        'prediction_status':seq['prediction_status'],'affinity_confirmed':table['affinity_confirmation'],
        'native_mapping':'validated_at_executed_points' if table['affinity_confirmation'] else 'nonaffine_full_finite_table',
        'final_K':rows[-1]['K'] if rows else None,'final_gain_mass':rows[-1]['gain_mass'] if rows else None,
        'all_rounds_mean_pass':bool(rows) and point_prefix==len(rows),'all_rounds_ci_pass':bool(rows) and ci_prefix==len(rows),
        'failed_path_not_global_impossibility':True}
    summary.update(conditional_upper=summary['continuous_utility_upper'],
        empirical_prefix=point_prefix,confirmed_prefix=ci_prefix,T_joint_status=summary['T_joint'],
        minimum_legacy_mass=min((r['minimum_source_use_mass'] for r in rows),default=None),
        K=max((r['K'] for r in rows if r['K'] is not None),default=None),
        cap_margin=min((r['minimum_cap_margin'] for r in rows),default=None),
        gain_margin=min((r['maximum_gain']-.01 for r in rows),default=None))
    return rows,legacy,portfolios,costs,summary


def aggregation(summaries):
    classes=[];factions=[]
    groups={}
    for r in summaries:groups.setdefault((r['class'],r['faction'],r['sequence']),[]).append(r)
    for (cls,faction,seq),rows in sorted(groups.items()):
        valid=[r for r in rows if r['status']=='assessed']
        classes.append({'class':cls,'faction':faction,'sequence':seq,'contexts_total':len(rows),
            'contexts_assessed':len(valid),'contexts_not_assessed':len(rows)-len(valid),
            'mean_prefix':float(np.mean([r['mean_successful_prefix'] for r in valid])) if valid else None,
            'mean_ci_prefix':float(np.mean([r['ci_supported_prefix'] for r in valid])) if valid else None,
            'all_rounds_mean_pass_rate':float(np.mean([r['all_rounds_mean_pass'] for r in valid])) if valid else None,
            'all_rounds_ci_pass_rate':float(np.mean([r['all_rounds_ci_pass'] for r in valid])) if valid else None})
    groups={}
    for row in classes:groups.setdefault((row['faction'],row['sequence']),[]).append(row)
    for (faction,seq),rows in sorted(groups.items()):
        valid=[r for r in rows if r['contexts_assessed']]
        factions.append({'faction':faction,'sequence':seq,'classes_target':len(rows),'classes_assessed':len(valid),
            'contexts_assessed':sum(r['contexts_assessed'] for r in rows),
            'aggregation':'Equal weight per assessed class; missing class strata excluded and counted, never zero-filled.',
            'class_equal_mean_prefix':float(np.mean([r['mean_prefix'] for r in valid])) if valid else None,
            'class_equal_ci_prefix':float(np.mean([r['mean_ci_prefix'] for r in valid])) if valid else None,
            'class_equal_all_rounds_mean_rate':float(np.mean([r['all_rounds_mean_pass_rate'] for r in valid])) if valid else None,
            'class_equal_all_rounds_ci_rate':float(np.mean([r['all_rounds_ci_pass_rate'] for r in valid])) if valid else None})
    return classes,factions


def analyze():
    root=setup_paths();run=root/'runs'/STAGE/'capacity-confirmation-v1';out=root/'artifacts'/STAGE
    progress=json.loads((run/'PROGRESS.json').read_text())
    if progress['status']!='complete':raise ValueError('Native confirmation must finish before inference')
    data=json.loads((run/'RESULTS.json').read_text());plan=json.loads((run/'inputs/FUTURE_SEQUENCE_DESIGN.json').read_text())
    old=json.loads((run/'inputs/OLD_ECOLOGY_ANALYSIS.json').read_text());cfg=json.loads((run/'inputs/FROZEN_MAIN_PROTOCOL.json').read_text())
    tasks=cfg['tasks'];weights=np.asarray(cfg['task_weights']);olds={c['context_id']:c for c in old['contexts']}
    bycontext={}
    for row in data['rows']:bycontext.setdefault(row['context_id'],[]).append(row)
    round_rows=[];legacy=[];portfolios=[];costs=[];summaries=[];validations=[];mapping=[]
    for count,ctx in enumerate(plan['contexts'],1):
        table=context_table(ctx,bycontext[ctx['context_id']],tasks);bounds=PairedBounds(table['samples'],table['reference'])
        validations.extend(table['validation'])
        mapping.append({k:ctx[k] for k in ('context_id','class','faction','race')}|{
            'development_affinity':ctx['affinity_validated'],'confirmation_affinity':table['affinity_confirmation'],
            'native_calls':table['actual_rows'],'derived_configuration_count':len(table['keys']),
            'max_per_seed_affine_residual':table['max_per_seed_residual'],
            'max_channel_residual':table['max_channel_residual'],
            'simultaneous_contrast_family_size':bounds.family_size,'student_t_critical':bounds.critical,
            'confidence_scope':'Approximate95% within this context, across all frozen sequences and pairs; not simultaneous across56contexts.'})
        for seq in ctx['sequences']:
            r,l,p,c,s=sequence_analysis(ctx,seq,table,bounds,weights,olds[ctx['context_id']])
            round_rows.extend(r);legacy.extend(l);portfolios.extend(p);costs.extend(c);summaries.append(s)
        print(json.dumps({'analyzed_contexts':count,'total_contexts':len(plan['contexts']),'context':ctx['context_id'],
                          'affinity_confirmed':table['affinity_confirmation']}),flush=True)
    class_rows,factions=aggregation(summaries);wide=[]
    for context in plan['contexts']:
        rows=[s for s in summaries if s['context_id']==context['context_id']]
        record={k:context[k] for k in ('context_id','class','faction','race','race_label','native_racial_incomplete')}
        record['development_affinity']=context['affinity_validated']
        for row in rows:
            for key in ('status','mean_successful_prefix','ci_supported_prefix','continuous_utility_upper','final_K'):
                record[row['sequence']+'_'+key]=row.get(key)
        wide.append(record)
    analysis=root/'runs'/STAGE/'capacity-analysis-v1'
    if (analysis/'PROTOCOL.json').exists():raise ValueError('Frozen analysis already exists; use explicit revision')
    sources=[Path(__file__),SOURCE_ROOT/'src/wowfs/experiments/fc_behavior.py']
    provenance={'analysis_only':True,'new_native_calls':0,'source_results_sha256':file_hash(run/'RESULTS.json'),
        'source_plan_sha256':file_hash(run/'inputs/FUTURE_SEQUENCE_DESIGN.json'),
        'source_hashes':{str(p.relative_to(SOURCE_ROOT)):file_hash(p) for p in sources}}
    atomic_json(analysis/'PROTOCOL.json',provenance)
    for p in sources:shutil.copy2(p,analysis/p.name)
    output={'schema':1,'physical_run':str(run),'analysis_run':str(analysis),'provenance':provenance,
        'native_progress':progress,'native_errors':data['errors'],'new_analysis_native_calls':0,
        'contexts':mapping,'sequences':summaries,'rounds':round_rows,
        'confidence':'Paired Student-t approximate simultaneous bands within context, Bonferroni over all ordered finite gear-pair task gain/relevance contrasts and paired/absolute caps. No distribution-free or across-context confidence claim.',
        'D_scope':'OriginalWarrior7 mean diagnostic only; otherclassesphysical5diagnostic does not establish original D; T_jointconfidence not established.',
        'capacity_scope':'Successful tested prefixes are achieved lower bounds. A failed path is not zero optimal capacity. Conditional continuous scalar upper bounds require validated mapping and are separate.',
        'aggregation':'Matched ecology/family is the scientific unit; class-equal faction summaries. Combat seeds quantify native Monte Carlo uncertainty.'}
    atomic_json(analysis/'SUMMARY.json',clean(output));atomic_json(out/'SUMMARY.json',clean(output))
    atomic_json(out/'CONFIRMATION_AFFINITY_CHECKS.json',clean({'contexts':mapping,'checks':validations}))
    for filename,rows in [('NATIVE_CAPACITY_RESULTS.csv',round_rows),('DIRECT_REDESIGN_ESCAPE.csv',[r for r in round_rows if r['regime']=='weaker_direct']),
        ('COMPATIBILITY_ESCAPE.csv',[r for r in round_rows if r['regime']=='fixed_budget']),('LEGACY_RELEVANCE.csv',legacy),
        ('PORTFOLIO_COMPLEXITY.csv',portfolios),('RACE_CLASS_56_RESULTS.csv',wide),('CLASS_FACTION_RESULTS.csv',class_rows),
        ('FACTION_SUMMARY.csv',factions),('COSTS.csv',costs),('SEQUENCE_CAPACITY_SUMMARY.csv',summaries)]:write_csv(out/filename,rows)
    print(json.dumps({'context_count':len(mapping),'affine_confirmation_contexts':sum(c['confirmation_affinity'] for c in mapping),
                      'sequence_count':len(summaries),'round_count':len(round_rows),'native_calls':progress['new_calls']}),flush=True)


if __name__=='__main__':analyze()
