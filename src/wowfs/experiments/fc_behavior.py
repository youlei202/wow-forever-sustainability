"""Native behavior profiles; interpolate physical numerators before ratios.

Caller must validate controls, channel affinity and the requested interpolation
domain. DPS affinity alone is insufficient. No confidence claim is made here.
"""
from __future__ import annotations

import json
import math

WARRIOR_CHANNELS = ['white', 'execute', 'whirlwind_cleave', 'bloodthirst', 'other']
GENERIC_CHANNELS = ['owner_auto', 'owner_periodic', 'owner_direct_physical',
                    'owner_direct_other', 'pet_all']
RESOURCE_NAMES = {0:'ResourceTypeNone',1:'ResourceTypeMana',2:'ResourceTypeEnergy',
                  3:'ResourceTypeRage',4:'ResourceTypeComboPoints',5:'ResourceTypeFocus',6:'ResourceTypeHealth'}


def _numerators(output, duration, class_name):
    n = int(output['iterationsDone'])
    if n <= 0 or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Positive completed iterations and duration required')
    enemies = {t['unitIndex'] for t in output['encounterMetrics']['targets']}
    if not enemies:
        raise ValueError('Enemy target indices required; cannot classify self damage by guess')
    channels = [0.]*5; resources = {}
    warrior = class_name == 'Warrior'

    def unit(player, path, pet=False):
        for action in player.get('actions', []):
            ts = [t for t in action['targets'] if t['unitIndex'] in enemies]
            damage = sum(t.get('damage', 0.) for t in ts)/(n*duration)
            periodic = sum(t.get('tickDamage', 0.) for t in ts)/(n*duration)
            ident = action['id']; spell = ident.get('spellId')
            if warrior:
                # Original seven-coordinate Warrior definition is owner-only.
                if pet:
                    continue
                group = (0 if ident.get('otherId') in ('OtherActionAttack',7)
                         else 1 if spell == 20662 else 2 if spell in (1680,20569)
                         else 3 if spell == 23894 else 4)
                channels[group] += damage
            elif pet:
                channels[4] += damage
            elif ident.get('otherId') in ('OtherActionAttack','OtherActionShoot',7,8):
                channels[0] += damage
            else:
                channels[1] += periodic
                channels[2 if action.get('spellSchool') == 2 else 3] += damage-periodic
        for record in player.get('resources', []):
            typ = RESOURCE_NAMES.get(record['type'], str(record['type']))
            key = json.dumps([path,typ,record['id']], sort_keys=True)
            resources[key] = {'unit':path,'type':typ,
                              **{k:float(record.get(k,0))/(n*duration)
                                 for k in ('events','gain','actualGain')}}
        for index, child in enumerate(player.get('pets', [])):
            child_path = path+'/pet:'+str(child.get('unitIndex',index))+':'+child.get('name','unnamed')
            unit(child, child_path, True)

    unit(output['raidMetrics']['parties'][0]['players'][0], 'owner')
    return channels, resources


def _profile(channels, records, class_name, interpolation):
    if any(not math.isfinite(v) or v < -1e-8 for v in channels):
        raise ValueError('Invalid negative/nonfinite predicted damage channel')
    channels = [max(0.,v) for v in channels]
    total = sum(channels)
    fractions = [v/total for v in channels] if total else [0.]*5
    typed = {}; rage_gain = rage_waste = 0.
    for record in records.values():
        if any(not math.isfinite(record[k]) for k in ('gain','actualGain','events')):
            raise ValueError('Nonfinite resource numerator')
        key = record['unit']+':'+record['type']
        aggregate = typed.setdefault(key, {'positive_gain_per_second':0., 'waste_per_second':0.,
                                           'spent_per_second':0., 'events_per_second':0.})
        gain, actual = record['gain'], record['actualGain']
        aggregate['positive_gain_per_second'] += max(0.,gain)
        aggregate['waste_per_second'] += max(0.,gain-actual) if gain > 0 else 0.
        aggregate['spent_per_second'] += max(0.,-actual)
        aggregate['events_per_second'] += record['events']
        if record['unit']=='owner' and record['type']=='ResourceTypeRage' and gain > 0:
            rage_gain += gain; rage_waste += max(0.,gain-actual)
    warrior = class_name == 'Warrior'
    profile = fractions+[rage_gain/20.,rage_waste/rage_gain if rage_gain else 0.] if warrior else fractions
    return {'profile':profile,
            'profile_kind':'original_warrior_seven' if warrior else 'generic_five_diagnostic',
            'channel_names':WARRIOR_CHANNELS if warrior else GENERIC_CHANNELS,
            'raw_channels':channels, 'channel_units':'mean_enemy_damage_per_second',
            'warrior_resource_numerators':[rage_gain,rage_waste] if warrior else None,
            'typed_resources':dict(sorted(typed.items())),
            'damage_sum':total, 'interpolation':interpolation,
            'validation_required':bool(interpolation),
            'validation_scope':'Interpolation caller must validate unnormalized channel/resource response and control kernel at requested points; normalized fractions are not affine.',
            'inference_scope':'Empirical profile, no native behavioral-D confidence certificate.'}


def profile_from_output(output, duration, class_name):
    """Direct raw native profile, including nonlinear classes/configurations."""
    channels, records = _numerators(output, duration, class_name)
    return _profile(channels, records, class_name, None)


def profile_from_outputs(raw0, raw1, total_z, span_z, duration, class_name):
    """Anchors at z=0/span_z; extrapolation flagged, never silently certified."""
    if not math.isfinite(span_z) or span_z <= 0 or not math.isfinite(total_z):
        raise ValueError('Finite requested total and positive finite anchor span required')
    a, ra = _numerators(raw0, duration, class_name)
    b, rb = _numerators(raw1, duration, class_name)
    ratio = total_z/span_z
    channels = [x+ratio*(y-x) for x,y in zip(a,b)]
    records = {}
    for key in ra.keys() | rb.keys():
        template = ra.get(key, rb.get(key))
        record = {'unit':template['unit'],'type':template['type']}
        for field in ('gain','actualGain','events'):
            lo = ra.get(key,{}).get(field,0.); hi = rb.get(key,{}).get(field,0.)
            record[field] = lo+ratio*(hi-lo)
        records[key] = record
    return _profile(channels, records, class_name,
                    {'total_z':total_z,'span_z':span_z,'ratio':ratio,'extrapolated':not 0 <= ratio <= 1})
