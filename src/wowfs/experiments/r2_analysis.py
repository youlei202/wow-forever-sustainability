"""Paired-seed estimates, with an explicitly frozen scalar family."""
from __future__ import annotations
import numpy as np
from scipy.stats import t

def factorial(cells, effects=2, family=6, alpha=.05):
    if set(cells) != set(range(2**effects)):
        raise ValueError('complete factorial cells required')
    arrays={k:np.asarray(v,dtype=float) for k,v in cells.items()}
    shapes={v.shape for v in arrays.values()}
    if len(shapes)!=1 or next(iter(shapes))[0]<2 or any(v.ndim!=1 or not np.isfinite(v).all() for v in arrays.values()):
        raise ValueError('equal finite per-seed arrays of length >=2 required')
    contrast=sum((-1)**(effects-m.bit_count())*v for m,v in arrays.items())
    return interval(contrast,family,alpha)

def interval(values,family=1,alpha=.05):
    values=np.asarray(values,dtype=float)
    if values.ndim!=1 or len(values)<2 or not np.isfinite(values).all():
        raise ValueError('finite one-dimensional sample required')
    mean=float(values.mean());se=float(values.std(ddof=1)/np.sqrt(len(values)))
    margin=float(t.ppf(1-alpha/(2*family),len(values)-1))*se
    degenerate=se<1e-10
    return {'estimate':mean,'se':se,'ci_low':mean-margin,'ci_high':mean+margin,
            'iterations':len(values),'family':family,'alpha':alpha,
            'degenerate_observed_variance':degenerate,
            'direction':'unresolved' if degenerate or mean-margin<=0<=mean+margin else ('positive' if mean>0 else 'negative'),
            'coverage':'paired Student-t, approximate for nonnormal seed-level contrasts'}

def group_factorials(rows):
    groups={}
    for row in rows:
        if row and 'case' in row:
            key=(row['case'],row['task'],row['strategy'],row['race'])
            groups.setdefault(key,{})[row['mask']]=row
    return groups
