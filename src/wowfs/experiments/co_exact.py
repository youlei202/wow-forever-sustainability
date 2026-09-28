"""Exact finite-table completion contract and independent subset oracle.

Numbers are parsed as rational decimal strings, never rounded to solver units.
This module makes no population-mean or native-execution claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
import time


def rational(value):
    if isinstance(value, (float, bool)):
        raise TypeError('Use explicit decimal/rational strings, not float or bool')
    return value if isinstance(value, Fraction) else Fraction(str(value))


@dataclass(frozen=True)
class Configuration:
    support: frozenset[str]
    values: tuple[Fraction, ...]

    def __post_init__(self):
        object.__setattr__(self, 'support', frozenset(self.support))
        object.__setattr__(self, 'values', tuple(map(rational, self.values)))


@dataclass(frozen=True)
class Model:
    slots: dict[str, int]
    configurations: tuple[Configuration, ...]
    weights: tuple
    tolerance: tuple
    required_mass: object
    history: frozenset[str]
    cap: tuple
    gain: tuple
    gain_mass: object

    def __post_init__(self):
        object.__setattr__(self, 'configurations', tuple(self.configurations))
        object.__setattr__(self, 'history', frozenset(self.history))
        for name in ('weights', 'tolerance', 'cap', 'gain'):
            object.__setattr__(self, name, tuple(map(rational, getattr(self, name))))
        for name in ('required_mass', 'gain_mass'):
            object.__setattr__(self, name, rational(getattr(self, name)))
        if not self.q or any(len(getattr(self, n)) != self.q for n in ('tolerance', 'cap', 'gain')):
            raise ValueError('Task dimension mismatch')
        if any(w < 0 for w in self.weights) or sum(self.weights) != 1:
            raise ValueError('Weights must be nonnegative and sum exactly to one')
        if not 0 <= self.required_mass <= 1 or not 0 < self.gain_mass <= 1:
            raise ValueError('Invalid task mass')
        if any(x < 0 for x in self.tolerance) or any(x <= 0 for x in self.gain):
            raise ValueError('Tolerance must be nonnegative and gains positive')
        if not self.history <= self.items:
            raise ValueError('Unknown history item')
        for c in self.configurations:
            if len(c.support) != 2 or not c.support <= self.items or {self.slots[i] for i in c.support} != {0, 1}:
                raise ValueError('Two-slot physical configurations required')
            if len(c.values) != self.q:
                raise ValueError('Configuration task dimension mismatch')

    @property
    def q(self):
        return len(self.weights)

    @property
    def items(self):
        return frozenset(self.slots)

    @classmethod
    def from_dict(cls, raw):
        return cls(dict(raw['slots']), tuple(Configuration(frozenset(c['support']), tuple(c['values'])) for c in raw['configurations']),
                   tuple(raw['weights']), tuple(raw['tolerance']), raw['required_mass'], frozenset(raw['history']),
                   tuple(raw['cap']), tuple(raw['gain']), raw['gain_mass'])

    def to_dict(self):
        return {'slots': dict(sorted(self.slots.items())), 'configurations': [
            {'support': sorted(c.support), 'values': list(map(str, c.values))} for c in self.configurations],
            **{n: list(map(str, getattr(self, n))) for n in ('weights', 'tolerance', 'cap', 'gain')},
            'required_mass': str(self.required_mass), 'gain_mass': str(self.gain_mass), 'history': sorted(self.history)}

    @property
    def digest(self):
        return sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def frontier(model, items):
    active = [c for c in model.configurations if c.support <= items]
    return tuple(max(c.values[q] for c in active) for q in range(model.q)) if active else None


def evaluate(model, items, *, require_gain=True, fixed_y=None):
    """Independent full witness check; each helper is a source obligation."""
    items = frozenset(items)
    if not model.history <= items <= model.items:
        return {'valid': False, 'reason': 'history_or_unknown_item'}
    active = [j for j, c in enumerate(model.configurations) if c.support <= items]
    if not active:
        return {'valid': False, 'reason': 'no_active_configuration'}
    f = tuple(max(model.configurations[j].values[q] for j in active) for q in range(model.q))
    if any(f[q] > model.cap[q] for q in range(model.q)):
        return {'valid': False, 'reason': 'cap', 'frontier': list(map(str, f))}
    if fixed_y is not None and f != tuple(map(rational, fixed_y)):
        return {'valid': False, 'reason': 'unattained_frontier'}
    witnesses = {}
    for i in sorted(items):
        by_task = [[j for j in active if i in model.configurations[j].support and model.configurations[j].values[q] >= f[q] - model.tolerance[q]] for q in range(model.q)]
        mass = sum(w for w, rows in zip(model.weights, by_task) if rows)
        if mass < model.required_mass:
            return {'valid': False, 'reason': 'retention', 'source': i, 'available_mass': str(mass)}
        witnesses[i] = {'mass': str(mass), 'rows_by_task': by_task}
    f0 = frontier(model, model.history)
    gain_tasks = [q for q in range(model.q) if f0 is not None and f[q]-f0[q] >= model.gain[q]]
    if require_gain and sum(model.weights[q] for q in gain_tasks) < model.gain_mass:
        return {'valid': False, 'reason': 'gain'}
    return {'valid': True, 'items': sorted(items), 'active_rows': active, 'frontier': list(map(str, f)),
            'source_witnesses': witnesses, 'gain_tasks': gain_tasks}


def initial_valid(model):
    return evaluate(model, model.history, require_gain=False)['valid']


def exhaustive(model, D=(), fixed_y=None, all_solutions=False):
    """Every subset, with no solver preprocessing; small-domain truth only."""
    start = time.perf_counter()
    mandatory = model.history | frozenset(D)
    if not mandatory <= model.items:
        raise ValueError('Unknown target item')
    if not initial_valid(model):
        return {'status': 'INVALID_INITIAL', 'elapsed_seconds': time.perf_counter()-start}
    optional = sorted(model.items-mandatory)
    solutions = []
    for width in range(len(optional)+1):
        for subset in combinations(optional, width):
            p = mandatory | frozenset(subset)
            # Direct definition independent of both encodings and reference deletion.
            rows = [c for c in model.configurations if c.support <= p]
            if not rows:
                continue
            f = tuple(max(c.values[q] for c in rows) for q in range(model.q))
            if fixed_y is not None and f != tuple(map(rational, fixed_y)):
                continue
            if any(a > b for a, b in zip(f, model.cap)):
                continue
            if any(sum(model.weights[q] for q in range(model.q) if any(i in c.support and c.values[q] >= f[q]-model.tolerance[q] for c in rows)) < model.required_mass for i in p):
                continue
            history_rows = [c for c in rows if c.support <= model.history]
            if sum(model.weights[q] for q in range(model.q) if f[q]-max(c.values[q] for c in history_rows) >= model.gain[q]) < model.gain_mass:
                continue
            solutions.append(p)
            if not all_solutions:
                break
        if solutions and not all_solutions:
            break
    result = {'status': 'YES' if solutions else 'NO', 'elapsed_seconds': time.perf_counter()-start}
    if solutions:
        result.update(items=sorted(solutions[0]), verifier=evaluate(model, solutions[0], fixed_y=fixed_y))
    if all_solutions:
        result['solutions'] = [sorted(p) for p in solutions]
        result['kernels'] = [sorted(p) for p in solutions if not any(p < t for t in solutions)]
    return result


def interface_query(interface, D):
    if interface.get('status') == 'INVALID_INITIAL':
        return {'status': 'INVALID_INITIAL'}
    d = frozenset(D)
    for k in interface.get('kernels', []):
        if d <= frozenset(k):
            return {'status': 'YES', 'items': list(k)}
    return {'status': 'NO' if interface.get('complete', False) else 'UNKNOWN_TIMEOUT'}
