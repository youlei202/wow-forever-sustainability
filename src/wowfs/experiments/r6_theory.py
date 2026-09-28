"""Native-facing checks for the supplied R5 theory, not replacement theorems.

Authority: WOWFS_WORK_ROOT/inputs/r5-theory/THEORY.md, Theorems 1 and 3,
and section 6.1. The closure recurrence follows supplied check_theory.py.
Native response matrices must separately satisfy its unique-repair model.
"""
from __future__ import annotations
from fractions import Fraction
from math import ceil


def least_repair_closure(f0, core, thresholds, repairs):
    """R5 section 2.3; equality remains competitive, hence strict '<'."""
    if len(thresholds)!=len(repairs):
        raise ValueError('One threshold and designated repair are required per source')
    chosen=set();trace=[]
    while True:
        frontier=max([f0,core]+[repairs[i] for i in chosen])
        forced={i for i,value in enumerate(thresholds) if value<frontier}
        nxt=chosen|forced
        trace.append({'frontier':frontier,'repairs':sorted(chosen),'newly_forced':sorted(nxt-chosen)})
        if nxt==chosen:
            return {'repairs':sorted(chosen),'frontier':frontier,'trace':trace,
                    'minimum_release_size_conditional_on_R5_model':1+len(chosen)}
        chosen=nxt


def interval_repair_closures(f0,core_interval,threshold_intervals,repair_intervals):
    """R5 section6.1, conditional on fixed f0 and simultaneous input intervals."""
    intervals=[core_interval,*threshold_intervals,*repair_intervals]
    if any(len(x)!=2 or x[0]>x[1] for x in intervals):
        raise ValueError('Every interval needs ordered lower/upper endpoints')
    if len(threshold_intervals)!=len(repair_intervals):
        raise ValueError('Threshold/repair interval counts differ')
    lower=least_repair_closure(f0,core_interval[0],
        [x[1] for x in threshold_intervals],[x[0] for x in repair_intervals])
    upper=least_repair_closure(f0,core_interval[1],
        [x[0] for x in threshold_intervals],[x[1] for x in repair_intervals])
    assert set(lower['repairs'])<=set(upper['repairs'])
    return {'forced':lower,'possible':upper,'identified':lower['repairs']==upper['repairs'],
            'scope':'R5 unique-repair model and simultaneous input intervals; stable witness/P/N/D/H/C assumptions checked separately.'}


def stable_witness_assumptions(f0,epsilon,cap,source_values,core,repairs):
    """Numeric assumptions of R5 section2.1; source-selectivity is separate."""
    checks={'nonnegative_epsilon':epsilon>=0,
            'cap_within_old_frontier_epsilon':f0<=cap<=f0+epsilon,
            'old_sources_initially_relevant':all(f0-epsilon<=v<=f0 for v in source_values),
            'core_at_least_old_frontier':core>=f0,
            'core_and_repairs_stably_near_cap':all(cap-epsilon<=v<=cap for v in [core,*repairs]),
            'one_repair_per_source':len(source_values)==len(repairs)}
    return {'checks':checks,'all_numeric_assumptions':all(checks.values())}


def audit_unique_repair_responses(source_values,core_source_values,repair_matrix,tolerance=0.):
    """Check full legal cross-coequipment against R5's exact source-value map.

    matrix[i][j] is the best response using old source i with repair j.
    core_source_values contains each source's best core-containing response;
    use -inf only when that source/core combination is physically unavailable.
    A legal alternative repair cannot be hidden by its designated source label.
    """
    m=len(source_values)
    if len(core_source_values)!=m or len(repair_matrix)!=m or any(len(row)!=m for row in repair_matrix):
        raise ValueError('Expected complete m×m source/repair response matrix')
    core_leaks=[{'source':i,'old_value':source_values[i],'core_source_value':core_source_values[i]}
                for i in range(m) if core_source_values[i]>source_values[i]+tolerance]
    off_diagonal=[{'source':i,'repair':j,'old_value':source_values[i],'alternative_value':repair_matrix[i][j]}
                  for i in range(m) for j in range(m) if i!=j and repair_matrix[i][j]>source_values[i]+tolerance]
    return {'core_alternative_restoration':core_leaks,'off_diagonal_alternative_restoration':off_diagonal,
            'unique_source_value_mapping_holds':not core_leaks and not off_diagonal,
            'scope':'Source-value part only; all frontier-maximizing configurations and stable witnesses require separate checks.'}


def frontier_neutral_grid_bound(h,beta,dimension,delta,initial_profiles,profiles_per_item):
    """Exact arithmetic on supplied decimal/rational certificate quantities.

    Floats are interpreted as their displayed decimal values; obtaining a
    valid beta/lower model certificate is the caller's scientific obligation.
    """
    def rational(value):
        return value if isinstance(value,Fraction) else Fraction(str(value))
    h,beta,delta=map(rational,(h,beta,delta))
    if h<0 or beta<=0 or delta<=0 or dimension<0 or int(dimension)!=dimension:
        raise ValueError('Need h>=0, beta/delta>0 and a nonnegative integer dimension')
    if int(initial_profiles)!=initial_profiles or initial_profiles<0 or int(profiles_per_item)!=profiles_per_item or profiles_per_item<1:
        raise ValueError('M0 must be nonnegative and p must include at least the accepted witness')
    side=1+int((2*h*beta)/(3*delta))
    count=side**int(dimension)
    available=max(0,count-int(initial_profiles))
    guarantee=(available+int(profiles_per_item)-1)//int(profiles_per_item)
    step=3*delta/beta
    return {'grid_side':side,'grid_points':count,'M0':int(initial_profiles),'p':int(profiles_per_item),
            'guaranteed_updates':guarantee,'grid_spacing':str(step),
            'intrinsic_axis_coordinates':[str(-h+i*step) for i in range(side)],
            'scope':'R5 Theorem3 conditional on every affine/interface/geometric/source-retention assumption; formula alone is not a native guarantee.'}
