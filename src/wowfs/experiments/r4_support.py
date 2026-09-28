"""Necessary release-support bounds and conservative old-only retention boxes.

These exact finite-table deductions are not new hypergraph/coverage theory.
They do not promote Monte Carlo means into population guarantees.
"""
from __future__ import annotations
from itertools import combinations
from dataclasses import replace

import numpy as np

from wowfs.experiments.r2_sequence_analysis import portfolio_cover
from wowfs.experiments.r4_feasibility import evaluate_admission


def qualifying_supports(problem):
    p = problem
    old_frontier = p.best[p.protected].max(axis=0)
    threshold = np.maximum(old_frontier[None, :], p.best) - p.tol_vector
    eligible = ((p.values >= threshold[:, None, :] - p.tolerance)
                & (p.distances >= p.delta-p.tolerance)
                & p.safe[:, None, None] & ~p.protected[:, None, None])
    result = []
    for g in np.flatnonzero(eligible.any(axis=(1,2))):
        result.append({'gear_index':int(g), 'gear_id':p.gear_ids[g],
            'support':sorted(set(p.sources[g]) & set(p.new_sources)),
            'tasks':np.flatnonzero(eligible[g].any(axis=0)).tolist(),
            'triples':np.argwhere(eligible[g]).tolist()})
    return result


def minimum_support_bound(problem):
    """Exact relaxed D-support minimum; feasibility can require strictly more."""
    p = problem
    records = qualifying_supports(p)
    for size in range(1, len(p.new_sources)+1):
        releases = []
        for release in combinations(p.new_sources, size):
            covered = np.zeros(len(p.scale), bool)
            for record in records:
                if set(record['support']) <= set(release):
                    covered[record['tasks']] = True
            if p.weights @ covered >= p.min_mass-p.tolerance:
                releases.append(list(release))
        if releases:
            return {'minimum_release_size_lower_bound':size, 'attaining_relaxed_releases':releases,
                    'qualifying_supports':records, 'D_relaxation_infeasible':False}
    return {'minimum_release_size_lower_bound':None, 'attaining_relaxed_releases':[],
            'qualifying_supports':records, 'D_relaxation_infeasible':True}


def old_retention_box(problem):
    """Build one sufficient box, with no access to candidate response values.

    Greedy selection of each source's old task witnesses is a construction,
    not an optimal-volume claim.  Returning no box does not prove infeasibility.
    """
    p = problem
    old = np.flatnonzero(p.protected)
    old_best = p.best[old]
    frontier = old_best.max(axis=0)
    if np.any(frontier > p.cap+p.tolerance):
        return {'constructed':False, 'reason':'protected_power'}
    cover = portfolio_cover(old_best, frontier, p.scale, p.epsilon, p.weights, p.coverage)
    if cover['K'] is None or cover['K'] > p.k_max:
        return {'constructed':False, 'reason':'old_portfolio_too_large'}
    portfolio = old[np.asarray(cover['indices'],int)]
    portfolio_best = p.best[portfolio].max(axis=0)
    covered = portfolio_best >= frontier-p.tol_vector-p.tolerance
    upper = p.cap.copy()
    upper[covered] = np.minimum(upper[covered], portfolio_best[covered]+p.tol_vector[covered])
    source_witnesses = {}
    for source in p.protected_sources:
        indices = [g for g in old if source in p.sources[g]]
        if not indices:
            return {'constructed':False, 'reason':'protected_source_absent_from_H:'+source}
        value = p.best[indices].max(axis=0)
        viable = value >= frontier-p.tol_vector-p.tolerance
        if p.weights @ viable < p.min_mass-p.tolerance:
            return {'constructed':False, 'reason':'protected_source_not_useful_in_H:'+source}
        # Prefer tasks with the least restrictive source ceiling.
        ordered = sorted(np.flatnonzero(viable), key=lambda t: (-(value[t]+p.tol_vector[t]-frontier[t]),int(t)))
        chosen = []; mass = 0.
        for task in ordered:
            chosen.append(int(task)); mass += p.weights[task]
            upper[task] = min(upper[task], value[task]+p.tol_vector[task])
            if mass >= p.min_mass-p.tolerance:
                break
        source_witnesses[source] = {'tasks':chosen,'task_mass':float(mass),
            'rewards':[float(value[t]) for t in chosen]}
    assert np.all(upper >= frontier-p.tolerance)
    return {'constructed':True,'upper':upper.tolist(),'old_frontier':frontier.tolist(),
            'portfolio_gears':[p.gear_ids[g] for g in portfolio],
            'portfolio_tasks':np.flatnonzero(covered).tolist(),'source_witnesses':source_witnesses}


def one_gear_box_candidates(problem, box):
    """Return sufficient H+gear witnesses with all batch items co-equipped."""
    if not box['constructed']:
        return []
    p = problem; upper = np.asarray(box['upper'])
    supports = qualifying_supports(p)
    result = []
    for record in supports:
        g = record['gear_index']
        if (set(record['support']) == set(p.new_sources)
                and np.all(p.best[g] <= upper+p.tolerance)
                and sum(p.weights[record['tasks']]) >= p.min_mass-p.tolerance):
            result.append(record)
    return result


def sparsify_feasible_release(problem, admitted):
    """Elementary witness sparsification under one-task-suffices semantics.

    The returned subrelease has at most s*(|L|+1+K) current-new item IDs,
    regardless of the candidate catalogue size. Optional subsets must be legal.
    """
    p = problem; admitted = np.asarray(admitted,bool)
    positive = p.weights > 0
    if np.any(p.weights[positive] < p.min_mass-p.tolerance):
        raise ValueError('A positive task must individually meet minimum mass')
    if p.require_D_each_new:
        raise ValueError('The bound is for the main batch-existential D convention')
    metrics = evaluate_admission(p,admitted)
    if not metrics['joint_pass']:
        raise ValueError('Input admission must already satisfy the complete joint predicate')
    frontier = p.best[admitted].max(axis=0)
    close = (p.best >= frontier-p.tol_vector-p.tolerance) & positive
    novel = (p.novel_best >= frontier-p.tol_vector-p.tolerance) & positive
    chosen = set(np.flatnonzero(p.protected))
    witnesses = []
    for source in p.protected_sources:
        options = [g for g in np.flatnonzero(admitted)
                   if source in p.sources[g] and close[g].any()]
        gear = options[0]; chosen.add(gear)
        witnesses.append({'type':'L','source':source,'gear_index':int(gear)})
    options = [g for g in np.flatnonzero(admitted & ~p.protected)
               if set(p.sources[g]) & set(p.new_sources) and novel[g].any()]
    gear = options[0]; chosen.add(gear)
    witnesses.append({'type':'D','gear_index':int(gear)})
    portfolio = [g for g in metrics['portfolio_indices'] if close[g].any()]
    chosen.update(portfolio)
    witnesses += [{'type':'C','gear_index':int(g)} for g in portfolio]
    new = sorted(set.union(set(),*(set(p.sources[g]) & set(p.new_sources) for g in chosen)))
    original_new = set(p.new_sources)
    domain = [g for g in range(len(p.sources)) if p.protected[g] or
              (bool(set(p.sources[g]) & set(new)) and (set(p.sources[g]) & original_new) <= set(new))]
    q = replace(p,values=p.values[domain],behavior=p.behavior[domain],
                sources=[p.sources[g] for g in domain],protected=p.protected[domain],
                new_sources=new,gear_ids=[p.gear_ids[g] for g in domain])
    reduced = np.array([g in chosen for g in domain])
    verified = evaluate_admission(q,reduced)
    assert verified['joint_pass']
    s = max(len(set(ss)&original_new) for ss in p.sources)
    bound = s*(len(p.protected_sources)+1+p.k_max)
    assert len(new) <= bound
    return {'new_sources':new,'original_new_source_count':len(p.new_sources),
            'selected_indices':sorted(map(int,chosen)), 'witnesses':witnesses,
            'support_per_gear':s,'upper_bound':bound,'metrics':verified}
