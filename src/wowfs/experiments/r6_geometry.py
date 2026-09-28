"""Explicit affine response geometry for the supplied R5 Theorem 3.

These certificates concern fitted finite native response models. They do not
turn Monte Carlo coefficients into population identities or safety guarantees.
"""
from __future__ import annotations

import itertools
import math
import re
import numpy as np


def damage_channels(row, duration):
    """Native action damage per second; no item identity enters the features."""
    result = np.zeros(5)
    for key, action in row['actions'].items():
        match = re.search(r'(?:^|/)spellId:(\d+)(?:/|$)', key)
        spell = int(match.group(1)) if match else None
        group = (0 if 'otherId:OtherActionAttack' in key else
                 1 if spell == 20662 else 2 if spell in (1680, 20569) else
                 3 if spell == 23894 else 4)
        result[group] += action['damage'] / duration
    if not np.isclose(result.sum(), row['dps_mean'], atol=1e-8, rtol=1e-10):
        raise ValueError('Native action damage and DPS disagree')
    return result


def affine_fit(points, responses):
    points, responses = np.asarray(points, float), np.asarray(responses, float)
    design = np.c_[np.ones(len(points)), points]
    if design.shape[0] != design.shape[1]:
        raise ValueError('Use exactly independent native calibration anchors')
    return np.linalg.solve(design, responses)


def polygon_vertices(a, b, tolerance=1e-8):
    a, b = np.asarray(a, float), np.asarray(b, float)
    found = []
    for i, j in itertools.combinations(range(len(b)), 2):
        matrix = a[[i, j]]
        if abs(np.linalg.det(matrix)) < 1e-12:
            continue
        point = np.linalg.solve(matrix, b[[i, j]])
        if np.all(a @ point <= b + tolerance) and not any(
                np.max(np.abs(point - x)) < tolerance for x in found):
            found.append(point)
    if not found:
        return np.empty((0, 2))
    found = np.asarray(found)
    center = found.mean(axis=0)
    return found[np.argsort(np.arctan2(found[:, 1]-center[1], found[:, 0]-center[0]))]


def line_segment(a, b, utility, target):
    """Intersect an affine utility level with every declared halfspace."""
    a, b, utility = np.asarray(a), np.asarray(b), np.asarray(utility)
    if abs(utility[2]) < 1e-12:
        raise ValueError('Periodic reward must supply a nonzero utility direction')
    origin = np.array([0., (target-utility[0])/utility[2]])
    direction = np.array([1., -utility[1]/utility[2]])
    lower, upper = -np.inf, np.inf
    for row, rhs in zip(a, b):
        slope, slack = row @ direction, rhs-row @ origin
        if abs(slope) < 1e-12:
            if slack < -1e-9:
                raise ValueError('Requested utility line lies outside the polytope')
        elif slope > 0:
            upper = min(upper, slack/slope)
        else:
            lower = max(lower, slack/slope)
    if not np.isfinite([lower, upper]).all() or lower > upper:
        raise ValueError('No bounded nonempty frontier-neutral segment')
    return np.stack([origin+lower*direction, origin+upper*direction])


def segment_certificate(a, b, endpoints, behavior_coefficients, delta, m0, p):
    """R5 cube with r=1, h=1/2, V=end-start; exact global linear gain."""
    endpoints = np.asarray(endpoints, float)
    center, direction = endpoints.mean(axis=0), endpoints[1]-endpoints[0]
    h = .5
    image = direction @ np.asarray(behavior_coefficients)[1:]
    beta = float(np.max(np.abs(image)))
    if delta <= 0 or p < 1 or m0 < 0 or beta <= 0:
        raise ValueError('Invalid R5 packing parameters')
    slack = np.asarray(b) - (np.asarray(a) @ center+h*np.abs(np.asarray(a) @ direction))
    if min(slack) < -1e-8:
        raise ValueError('Embedded cube violates a primitive response constraint')
    side = 1+math.floor(2*h*beta/(3*delta))
    guarantee = math.ceil(max(0, side-m0)/p)
    coordinates = [-h+i*3*delta/beta for i in range(side)]
    return {'r':1, 'h':h, 'beta':beta, 'delta':delta, 'M0':int(m0), 'p':int(p),
            'cube_center':center.tolist(), 'V':direction.tolist(),
            'behavior_BV':image.tolist(), 'minimum_cube_constraint_slack':float(min(slack)),
            'grid_side':side, 'grid_candidates':side, 'T_guaranteed':guarantee,
            'grid_z':coordinates,
            'grid_theta':[(center+direction*z).tolist() for z in coordinates],
            'scope':'Exact numeric certificate for fitted affine coefficients; empirical native model.'}


def greedy_grid(certificate, behavior_coefficients, old_profiles):
    archive = [np.asarray(x, float) for x in old_profiles]
    records = []
    for index, theta in enumerate(certificate['grid_theta']):
        profile = np.r_[1., theta] @ behavior_coefficients
        distance = min(float(np.max(np.abs(profile-x))) for x in archive)
        accept = distance > certificate['delta']
        records.append({'grid_index':index, 'theta':theta, 'behavior':profile.tolist(),
                        'nearest_full_archive_distance':distance, 'accepted':accept})
        if accept:
            archive.append(profile)
    return records
