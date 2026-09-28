"""Post-confirmation estimand sensitivity; never changes frozen native inputs.

Preserves the original numeric-cap results. Adds a paired population-old-
reference functional, using the identical candidate set, masks and planned path.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import t as student_t

from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.fc_native import STAGE
from wowfs.experiments.fc_mechanism_capacity import RUN_ID, DESIGN_NAME, finite_oracle, csv_write
from wowfs.experiments.r2_native import file_hash


def paired_bounds(samples, reference_samples, coefficient, critical):
    """Bounds for every E[U_a-U_b+coefficient*S], retaining paired covariance."""
    n = samples.shape[-1]
    means = samples.mean(axis=1); mean_ref = reference_samples.mean()
    centered = samples-means[:,None]; ref_centered = reference_samples-mean_ref
    covariance = centered @ centered.T/(n-1)
    ref_cov = centered @ ref_centered/(n-1)
    ref_var = ref_centered @ ref_centered/(n-1)
    variances = np.diag(covariance)
    diff_variance = (variances[:,None]+variances[None,:]-2*covariance+
                     coefficient**2*ref_var+2*coefficient*(ref_cov[:,None]-ref_cov[None,:]))
    mean = means[:,None]-means[None,:]+coefficient*mean_ref
    radius = critical*np.sqrt(np.maximum(0,diff_variance)/n)
    return mean-radius, mean+radius


def main():
    root=setup_paths();run=root/'runs'/STAGE/RUN_ID;out=root/'artifacts'/STAGE
    design=json.loads((run/'inputs'/DESIGN_NAME).read_text())
    results=json.loads((run/'RESULTS.json').read_text())['rows']
    cfg=design['main_protocol'];task_ids=[t['id'] for t in cfg['tasks']]
    lookup={(r['design_id'],r['task'],r['primary_index'],r['partner_index']):r for r in results}
    # Two estimands, all design/task primary-partner pair comparisons for G/L,
    # plus all power cells. This deliberately includes pairs not selected later.
    family=2*len(design['designs'])*len(task_ids)*(2*30*30+30)
    n=design['confirmation_iterations'];critical=float(student_t.ppf(1-.05/(2*family),n-1))
    summaries=[];details=[]
    for d in design['designs']:
        samples=np.array([[[lookup[d['design_id'],q,i,j]['dps_samples'] for q in task_ids]
                           for j in range(5)] for i in range(6)])
        utility=samples.mean(axis=3); mask=np.array(d['frozen_admission_mask']);ref=d['reference_primary_index']
        baseline=samples[ref,4]
        if not np.all(utility[ref,4]>=utility[ref]-1e-9):
            raise ValueError('Frozen reference endpoint is not the measured old optimum')
        for estimand in ('frozen_numeric_calibration_cap','paired_population_old_reference_sensitivity'):
            scale=np.array(d['scale']) if estimand.startswith('frozen') else baseline.mean(axis=1)
            reference=np.repeat(scale[:,None],n,axis=1) if estimand.startswith('frozen') else baseline
            cap=(1+cfg['fixed_headroom'])*scale
            oracle,inspect=finite_oracle(utility,mask,ref,scale,cfg,True)
            utility_oracle,_=finite_oracle(utility,mask,ref,scale,cfg,False)
            planned,prefix,_=inspect(d['predicted_value_legacy']['path'])
            bounds={}
            for coefficient in (-cfg['meaningful_gain'],cfg['legacy_epsilon']):
                bounds[coefficient]=[paired_bounds(samples[:,:,q,:].reshape(30,n),reference[q],coefficient,critical)
                                     for q in range(len(task_ids))]
            power_samples=(1+cfg['fixed_headroom'])*reference[None,None,:,:]-samples
            power_margin=power_samples.mean(axis=3)
            power_lower=power_margin-critical*power_samples.std(axis=3,ddof=1)/np.sqrt(n)
            weights=np.array(cfg['task_weights']);previous=[ref];step_rows=[];confidence_prefix=0;conf_ok=True
            for step in planned:
                current=previous+[step['primary_index']]
                old_ids=[p*5+j for p in previous for j in range(5) if mask[p,j]]
                new_ids=[p*5+j for p in current for j in range(5) if mask[p,j]]
                gain_margin_lower=[];gain_margin_upper=[]
                for q,(low,high) in enumerate(bounds[-cfg['meaningful_gain']]):
                    lo=float(np.max(np.min(low[np.ix_(new_ids,old_ids)],axis=1)))
                    hi=float(np.max(np.min(high[np.ix_(new_ids,old_ids)],axis=1)))
                    gain_margin_lower.append(lo);gain_margin_upper.append(hi)
                gain_pass=float(weights @ (np.array(gain_margin_lower)>=-1e-10))>=cfg['gain_required_mass']-1e-10
                source_lowers={}
                for source,ids in ([(f'primary_{p}',[p*5+j for j in range(5) if mask[p,j]]) for p in current]+
                                   [(f'partner_{j}',[p*5+j for p in current if mask[p,j]]) for j in range(5)]):
                    margins=[]
                    for q,(low,_) in enumerate(bounds[cfg['legacy_epsilon']]):
                        margins.append(float(np.max(np.min(low[np.ix_(ids,new_ids)],axis=1))) if ids else float('-inf'))
                    source_lowers[source]={'competitive_margin_lower':margins,
                                           'competitive_margin_units':'DPS',
                                           'scaled_margin_lower_display':(np.array(margins)/scale).tolist(),
                                           'task_mass_lower':float(weights @ (np.array(margins)>=-1e-10))}
                nl_pass=all(s['task_mass_lower']>=cfg['legacy_required_mass']-1e-10 for s in source_lowers.values())
                pairs=[(p,j) for p in current for j in range(5) if mask[p,j]]
                p_pass=all(np.all(power_lower[p,j]>=-1e-10) for p,j in pairs)
                conf_ok=conf_ok and step['pass'] and gain_pass and nl_pass and p_pass
                confidence_prefix+=int(conf_ok)
                step_rows.append({**step,'paired_approx_gain_threshold_margin_lower':gain_margin_lower,
                                  'paired_approx_gain_threshold_margin_upper':gain_margin_upper,
                                  'gain_threshold_margin_units':'DPS',
                                  'gain_lower_scaled_display':(cfg['meaningful_gain']+np.array(gain_margin_lower)/scale).tolist(),
                                  'gain_upper_scaled_display':(cfg['meaningful_gain']+np.array(gain_margin_upper)/scale).tolist(),
                                  'scaled_display_scope':'Threshold margins divided by point-estimated scale, then shifted by g. These are gain-ratio bounds only for the fixed numeric scale, not for the population-reference estimand.',
                                  'paired_approx_G_lower_pass':bool(gain_pass),'paired_approx_NL_lower_pass':bool(nl_pass),
                                  'paired_approx_P_lower_pass':bool(p_pass),'source_competitive_bounds':source_lowers,
                                  'scope':'Planned step, including counterfactual later steps if the preceding frozen prefix failed.'})
                previous=current
            summary={'design_id':d['design_id'],'family':d['family'],'context_id':d['context']['context_id'],
                'faction':d['context']['faction'],'ecology':d['ecology'],'estimand':estimand,
                'native_finite_T_utility':utility_oracle['capacity'],'native_finite_T_value_legacy':oracle['capacity'],
                'frozen_path_empirical_prefix':prefix,'frozen_path_approx_PGNL_prefix':confidence_prefix,
                'old_baseline_power_pass':bool(oracle['initial_checks']['P']),
                'old_baseline_all_value_checks_pass':all(oracle['initial_checks'].values()),
                'min_all_admitted_power_margin':float(np.min(power_margin[mask]/scale)),
                'all_admitted_power_approx_lower_pass':bool(np.all(power_lower[mask]>=-1e-10)),
                'reference_scale_definition':'Calibrated numeric initial means' if estimand.startswith('frozen') else
                    'Expected utility of the same preregistered old primary and maximum old partner; estimated with fresh paired old samples',
                'timing':'Original estimand, new post-confirmation paired interval analysis' if estimand.startswith('frozen') else
                    'Post-confirmation sensitivity analysis choice; not the original prospective mechanism estimand'}
            summaries.append(summary)
            details.append({'summary':summary,'scale':scale.tolist(),'native_finite_oracle':oracle,
                            'planned_steps':step_rows,'native_power_margin':power_margin.tolist(),
                            'approx_power_margin_lower':power_lower.tolist()})
    artifact={'schema':2,'scope':'Post-confirmation estimand sensitivity with unchanged physical outcomes, masks, candidates and planned sequences.',
        'run':str(run),'design_sha256':file_hash(run/'inputs'/DESIGN_NAME),
        'original_confirmation_sha256':file_hash(out/'MECHANISM_CAPACITY_CONFIRMATION.json'),
        'analysis_source_sha256':file_hash(Path(__file__)),'comparison_family':family,'student_t_critical':critical,
        'confidence':'Approximate simultaneous paired t margins for all G/L comparisons and power cells, both estimands. No distribution-free or behavioral-D claim.',
        'selection':'Only the original frozen path receives prospective-prefix labels. Complete-table finite capacities remain empirical reoptimizations.',
        'summaries':summaries,'details':details,'new_native_calls':0}
    atomic_json(out/'MECHANISM_CAPACITY_SENSITIVITY_V2.json',artifact)
    csv_write(out/'MECHANISM_CAPACITY_SENSITIVITY_V2.csv',summaries)
    print(json.dumps({'new_native_calls':0,'critical':critical,'summaries':summaries},indent=2),flush=True)


if __name__=='__main__':main()
