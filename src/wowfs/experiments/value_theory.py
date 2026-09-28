"""Exact rational checks for an abstract additive completion class.

These are mathematical examples, never native simulations or coverage.
"""
from fractions import Fraction


def rational(value):
    return value if isinstance(value, Fraction) else Fraction(str(value))


def completion_sequence(headroom, gain, distance, relevance=None, partner_damage=None):
    h, g, delta = map(rational, (headroom, gain, distance))
    e = h if relevance is None else rational(relevance)
    c = (1+h)/2 if partner_damage is None else rational(partner_damage)
    if not (0 < h < c < 1 and g > 0 and 0 < delta <= 1 and e >= h):
        raise ValueError('Require 0<h<c<1, g>0, 0<delta<=1 and relevance>=headroom')
    count = min(h//g, 1//delta)
    primary = {'old_primary': (1-c, Fraction(0))}
    partner = {'old_partner': (c, Fraction(0)), 'weak_partner': (Fraction(0), Fraction(0))}
    for t in range(1, count+1):
        utility = 1+t*g
        primary['primary_'+str(t)] = (utility*(1-t*delta), utility*t*delta)
    return {'scope':'abstract_exact_rational_not_native', 'headroom':h, 'gain':g,
            'delta':delta, 'relevance':e, 'partner_damage':c, 'count':count,
            'primaries':primary, 'partners':partner,
            'batches':[('primary_1','weak_partner')] + [('primary_'+str(t),) for t in range(2,count+1)] if count else []}


def inspect_completion_sequence(model):
    h, g, delta, e = (model[k] for k in ('headroom','gain','delta','relevance'))
    present={'old_primary','old_partner'}
    old_gears={('old_primary','old_partner')}
    old_profiles={(Fraction(1),Fraction(0))}
    previous=Fraction(1); records=[]
    for t,batch in enumerate(model['batches'],1):
        present.update(batch)
        legal={}; admitted={}
        for p,x in model['primaries'].items():
            if p not in present:continue
            for q,y in model['partners'].items():
                if q not in present:continue
                channel=tuple(a+b for a,b in zip(x,y));legal[(p,q)]=channel
                if sum(channel)<=1+h:admitted[(p,q)]=channel
        optimum=max(sum(x) for x in admitted.values())
        usefulness={source:max(sum(x) for gear,x in admitted.items() if source in gear)
                    for source in present}
        current=('primary_'+str(t),'weak_partner')
        phi=tuple(x/sum(admitted[current]) for x in admitted[current])
        novelty=min(max(abs(x-y) for x,y in zip(phi,old)) for old in old_profiles)
        checks={'P':optimum<=1+h,'N':all(usefulness[s]>=optimum-e for s in batch),
                'D':novelty>=delta,'L':all(v>=optimum-e for s,v in usefulness.items() if s not in batch),
                'H':old_gears<=set(admitted),'C':Fraction(1)>=optimum-e,'G':optimum-previous>=g}
        # Physical gear availability stays complete under the same single cap.
        old_gears=set(admitted)
        old_profiles.update(tuple(x/sum(channel) for x in channel) for channel in admitted.values())
        records.append({'round':t,'batch':batch,'optimum':optimum,'gain':optimum-previous,
                        'novelty':novelty,'legal_gears':len(legal),'admitted_gears':len(admitted),
                        'rule_rows':1,'portfolio_size':1,'checks':checks})
        previous=optimum
    return records
