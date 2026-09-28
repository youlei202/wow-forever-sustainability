"""Solver-free exact rational audit of every finite publication (at most 18 items).

This review-only implementation compiles rational comparisons into integer row
and source masks. It uses no SAT/CP/MILP package and never quantizes responses.
The resulting list includes every valid publication, not just maximal ones.
"""
from __future__ import annotations

from fractions import Fraction
from math import lcm

from wowfs.experiments.co_exact import evaluate, rational


class ExactMaskOracle:
    def __init__(self, model, *, fixed_y=None):
        self.model = model
        self.names = sorted(model.items)
        if len(self.names) > 18:
            raise ValueError('Portable exhaustive audit supports at most 18 items')
        self.index = {name: i for i, name in enumerate(self.names)}
        self.history = self.mask(model.history)
        rows = model.configurations
        self.supports = [self.mask(row.support) for row in rows]
        self.incident = [[] for _ in self.names]
        for r, support in enumerate(self.supports):
            for i in range(len(self.names)):
                if support >> i & 1:
                    self.incident[i].append((r, support & ~(1 << i)))
        self.capbad = sum(1 << r for r, row in enumerate(rows)
                          if any(row.values[q] > model.cap[q] for q in range(model.q)))
        history_rows = [r for r, support in enumerate(self.supports) if support & self.history == support]
        self.history_active = sum(1 << r for r in history_rows)
        self.history_frontier = (tuple(max(rows[r].values[q] for r in history_rows) for q in range(model.q))
                                 if history_rows else None)
        self.gain_good = [sum(1 << r for r, row in enumerate(rows)
                              if self.history_frontier is not None and row.values[q] >= self.history_frontier[q] + model.gain[q])
                          for q in range(model.q)]
        self.bad = [[sum(1 << d for d, other in enumerate(rows)
                         if other.values[q] > row.values[q] + model.tolerance[q])
                     for row in rows] for q in range(model.q)]
        denominator = lcm(*(x.denominator for x in model.weights), model.required_mass.denominator, model.gain_mass.denominator)
        weights = [int(x * denominator) for x in model.weights]
        masses = [sum(weights[q] for q in range(model.q) if mask >> q & 1) for mask in range(1 << model.q)]
        self.retention_enough = {m for m, weight in enumerate(masses) if weight >= model.required_mass * denominator}
        self.gain_enough = {m for m, weight in enumerate(masses) if weight >= model.gain_mass * denominator}
        self.fixed_y = None if fixed_y is None else tuple(map(rational, fixed_y))
        if self.fixed_y is not None and len(self.fixed_y) != model.q:
            raise ValueError('Fixed frontier task dimension mismatch')
        self.fixed_above = 0 if self.fixed_y is None else sum(1 << r for r, row in enumerate(rows)
                                if any(row.values[q] > self.fixed_y[q] for q in range(model.q)))
        self.fixed_equal = [] if self.fixed_y is None else [sum(1 << r for r, row in enumerate(rows) if row.values[q] == self.fixed_y[q]) for q in range(model.q)]
        self.initial_value_valid = bool(self.history_active) and not self.history_active & self.capbad
        self.initial_valid = self.initial_value_valid and self.retention_ok(self.history, self.history_active)
        self.valid = []
        self.value_valid = []
        optional = [i for i in range(len(self.names)) if not (self.history >> i) & 1]
        size = 1 << len(optional)
        publications, activated = [self.history] * size, [self.history_active] * size
        for mask in range(size):
            if mask:
                low = mask & -mask; previous = mask ^ low; i = optional[low.bit_length() - 1]
                p = publications[previous] | 1 << i
                active = activated[previous]
                for r, other in self.incident[i]:
                    if other & p == other:
                        active |= 1 << r
                publications[mask], activated[mask] = p, active
            else:
                p, active = self.history, self.history_active
            if not active or active & self.capbad:
                continue
            if self.fixed_y is not None and (active & self.fixed_above or any(not active & eq for eq in self.fixed_equal)):
                continue
            gain_mask = sum(1 << q for q, good in enumerate(self.gain_good) if active & good)
            if gain_mask not in self.gain_enough:
                continue
            if self.initial_value_valid:
                self.value_valid.append(p)
            if self.initial_valid and self.retention_ok(p, active):
                self.valid.append(p)
        self.examined_publications = size

    def mask(self, names):
        unknown = set(names) - set(self.index)
        if unknown:
            raise ValueError('Unknown target items: ' + repr(sorted(unknown)))
        return sum(1 << self.index[name] for name in set(names))

    def retention_ok(self, publication, active):
        if self.model.required_mass == 0:
            return True
        source_tasks = [0] * len(self.names)
        for q, bad in enumerate(self.bad):
            supported_sources = 0
            remaining = active
            while remaining:
                bit = remaining & -remaining; remaining ^= bit; r = bit.bit_length() - 1
                if not active & bad[r]:
                    supported_sources |= self.supports[r]
            while supported_sources:
                bit = supported_sources & -supported_sources; supported_sources ^= bit
                source_tasks[bit.bit_length() - 1] |= 1 << q
        return all(source_tasks[i] in self.retention_enough for i in range(len(self.names)) if publication >> i & 1)

    def query(self, required=(), *, retention=True):
        target = self.mask(required)
        if not (self.initial_valid if retention else self.initial_value_valid):
            return {'status': 'INVALID_INITIAL'}
        for p in self.valid if retention else self.value_valid:
            if p & target == target:
                return {'status': 'YES', 'items': [name for i, name in enumerate(self.names) if p >> i & 1]}
        return {'status': 'NO'}


def exact_queries(world, moments, rule, variant='expanded'):
    """Drop-in review result contract, with an independent exhaustive oracle."""
    from wowfs.experiments.co_native_analysis import model_from_moments
    model = model_from_moments(world, moments, rule, variant)
    oracle = ExactMaskOracle(model)
    queries = []
    for query in world['queries']:
        answer = oracle.query(query['required'])
        value = oracle.query(query['required'], retention=False)
        queries.append(dict(query_id=query['query_id'], required=query['required'], mean_answer=answer,
            value_only_answer=value, direct_release=evaluate(model, model.history | frozenset(query['required'])),
            retention_decision_active=answer['status'] == 'NO' and value['status'] == 'YES'))
    return dict(world_id=world['world_id'], variant=variant, model=model.to_dict(), model_sha256=model.digest,
                evidence_level='NATIVE_MEAN_TABLE', queries=queries,
                audit_method='Independent exact-rational all-publication bitmask oracle; no solver dependency.',
                examined_publications=oracle.examined_publications)
