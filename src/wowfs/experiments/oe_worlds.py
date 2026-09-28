"""Immutable, source-grounded native worlds for the 2026-09-26 exploration.

This module constructs requests only. The campaign runner owns all execution,
raw-output retention, budgets, statistical selection and frozen confirmations.
No response is interpolated and no power-violating physical cross is removed.
"""
from copy import deepcopy
from functools import lru_cache
from itertools import product
import csv
import json
from pathlib import Path

from wowfs.experiments.fc_native import (contexts, make_input, instantiate,
    define_alias, native_database, SLOTS, engine_root, validate_equipment)
from wowfs.paths import canonical_hash

SCHEMA = 1
# A hypothesis is a search family, not a claim that its mechanism causes a result.
FAMILIES = {
 'mana_regen': ('Resource regeneration versus damage', 'MP5 can change the number of affordable casts and task preference.', 'sim/core/mana.go', 'StatMP5,StatSpellPower', 'supported_source', 'Duration and mana recovery; no incoming damage.'),
 'melee_hit': ('Dual-wield hit saturation', 'Hit can alter rage/action availability and saturate differently across partners.', 'sim/core/spell_outcome.go:675', 'StatMeleeHit,StatAttackPower', 'supported_source', 'Forever equipment hit is universal; dual-wield miss penalty is 0.19.'),
 'spell_hit': ('Spell hit saturation', 'Universal hit has different returns on spell tables and source retention.', 'sim/core/spell_result.go:195', 'StatSpellHit,StatSpellPower', 'supported_source', 'Miss probability retains a 0.01 floor; no separate generic melee/spell gear pools.'),
 'crit_flurry': ('Critical strike and action feedback', 'Warrior Flurry can turn crit into more swings and indirectly more rage.', 'sim/warrior/talents.go:269', 'StatMeleeCrit,StatAttackPower', 'supported_source', 'Rogue is a non-rage control. Forever crit/damage do not directly increase white-hit rage.'),
 'weapon_cadence': ('Cadence and normalized skills', 'Fixed-base-DPS speeds change timing and ability damage despite matched weapon DPS.', 'sim/core/attack.go', 'weapon_speed_seconds,speed_mode=hold_base_dps', 'supported_source', 'Timing and rage thresholds are observed; equal base DPS is not equal total DPS.'),
 'periodic_refresh': ('Periodic refresh and truncation', 'Blood Talon PPM and duration can lose useful ticks through refresh or combat end.', 'sim/common/item_effects.go:681', 'item12795.proc_ppm,periodic_damage_per_tick', 'supported_source', 'Blood Talon is main-hand only; refresh and tick outputs must be checked.'),
 'nature_proc': ('Nature proc and resistance debuff', 'Thunderfury mixes physical attacks with nature procs and resistance reduction.', 'sim/common/item_effects.go:2222', 'item19019.proc_ppm,weapon_damage_scale', 'supported_source', 'Bounce damage is ZERO; bounce applies a debuff, not chain AoE damage.'),
 'shadow_proc': ('Physical versus shadow composition', 'Deathbringer trades physical base DPS against a magic proc under armor changes.', 'sim/common/item_effects.go:777', 'item17068.proc_ppm,weapon_damage_scale', 'supported_source', 'Deathbringer is an axe and cannot be equipped by Rogue.'),
 'onuse_shared_cd': ('Shared cooldown and burst windows', 'Two on-use trinkets can compete for a shared timer and change task optima.', 'sim/core/item_effects.go:132', 'items18820,22268,11832,policy priority', 'supported_source', 'Native item effects remain unmodified. Burst of Knowledge has a different resource effect.'),
 'policy_resource': ('Resource policy and equipment substitution', 'Changing a recovery trigger can reverse resource-versus-damage choices.', 'sim/warlock/lifetap.go;ui/mage/apls/forever_frost.apl.json', 'APL recovery threshold;StatMP5,StatSpellPower', 'supported_with_limitations', 'Life Tap does not subtract health in these non-tanking requests; no survival claim.'),
 'resistance_penetration': ('Task resistance and penetration', 'Resistance floors can make penetration equipment useful only in specific tasks.', 'sim/core/spell_resistances.go:147', 'StatSpellPenetration,target resistance', 'supported_source', 'Explicit target school resistance enters existing native formulas.'),
 'joint_slots': ('New-new combinations across slots', 'Individually admitted components can combine across two updated slots.', 'sim/core/ruleset.go;sim/core/character.go', 'neck and back stat budgets; explicit incidence', 'supported_source', 'Both slots can update: fixed-old-partner retention algorithms are inapplicable without an incidence-aware model.'),
}


def _context(cls, race):
    return next(c for c in contexts() if c['class'] == cls and c['race_label'] == race)


def _four(family):
    if family in ('melee_hit','crit_flurry','weapon_cadence','periodic_refresh','nature_proc'):
        return [('Warrior','Human'),('Warrior','Orc'),('Rogue','Human'),('Rogue','Orc')]
    if family == 'shadow_proc':
        return [('Warrior','Human'),('Warrior','Orc'),('Hunter','Night Elf'),('Hunter','Orc')]
    if family in ('onuse_shared_cd','policy_resource'):
        return [('Mage','Gnome'),('Mage','Undead'),('Warlock','Human'),('Warlock','Orc')]
    if family in ('spell_hit','mana_regen'):
        return [('Mage','Gnome'),('Mage','Undead'),('Druid','Night Elf'),('Druid','Tauren')]
    if family == 'resistance_penetration':
        return [('Mage','Gnome'),('Mage','Undead'),('Shaman','Tauren'),('Shaman','Orc')]
    return [('Warrior','Human'),('Warrior','Orc'),('Mage','Gnome'),('Mage','Undead')]


def _tasks(family, stratum):
    a = {'task_id':'short', 'duration':30 if stratum==0 else 60, 'armor':3731, 'targets':1}
    b = {'task_id':'long', 'duration':180 if stratum==0 else 360, 'armor':3731, 'targets':1}
    if family in ('melee_hit','crit_flurry','shadow_proc','joint_slots'):
        a.update(task_id='low_armor', duration=90, armor=2000)
        b.update(task_id='high_armor', duration=90, armor=8000 if stratum==0 else 12000)
    if family == 'nature_proc':
        a.update(task_id='nature0_single', duration=90, nature_resistance=0)
        b.update(task_id='nature75_multi', duration=90, targets=3, nature_resistance=75 if stratum==0 else 150)
    if family == 'resistance_penetration':
        a.update(task_id='resistance0', duration=90, all_magic_resistance=0)
        b.update(task_id='resistance75', duration=90, all_magic_resistance=75 if stratum==0 else 150)
    return [a,b]


def _alias(label, item, slot, **params):
    alias=define_alias(label,item,slot,params)
    database=native_database()[item]
    names=['Strength','Agility','Stamina','Intellect','Spirit','SpellPower','ArcanePower',
           'FirePower','FrostPower','HolyPower','NaturePower','ShadowPower','MP5',
           'SpellHit','SpellCrit','SpellHaste','SpellPenetration','AttackPower',
           'MeleeHit','MeleeCrit','MeleeHaste','ArmorPenetration','Expertise','Mana',
           'Energy','Rage','Armor','RangedAttackPower','Defense','Block','BlockValue',
           'Dodge','Parry','Resilience','Health','ArcaneResistance','FireResistance',
           'FrostResistance','NatureResistance','ShadowResistance','BonusArmor',
           'HealingPower','SpellDamage','FeralAttackPower']
    changes={}
    for stat,value in params.get('stats',{}).items():
        native=database['stats'][names.index(stat.removeprefix('Stat'))]
        changes[stat]={'native':native,'research':value,'difference':value-native}
    native_parameters={'weapon_damage_scale':1.,'weapon_speed_seconds':database.get('weaponSpeed'),
                       'proc_ppm':6. if item==19019 else 1.,'periodic_damage_per_tick':10.}
    for name,value in params.items():
        if name in native_parameters:
            native=native_parameters[name]
            changes[name]={'native':native,'research':value,'difference':value-native}
    alias['distance_to_native_base']={'base_item_name':database['name'],
        'changed_parameters':changes,
        'interpretation':'Raw coordinate distances; these overrides are research designs, not claimed actual obtainable items.'}
    return alias


def _stats_alias(label,item,slot,stats):
    return _alias(label,item,slot,stats=stats)


def _candidate_points():
    # Includes both weaker alternatives and larger budgets, fixed before outcomes.
    return [(.5,.75)] + [(allocation,budget) for budget in (.65,.8,.95,1.1)
                         for allocation in (0.,1/3,2/3,1.)]


def _build(family, cls, race, stratum):
    context = _context(cls,race)
    wid=f'{family}__{context["context_id"]}__s{stratum}'
    base=make_input(context,{'duration':30},seed=1,iterations=1)
    items=base['request']['raid']['parties'][0]['players'][0]['equipment']['items']
    ids={s:items[i]['id'] for i,s in enumerate(SLOTS)}
    ranged=cls=='Hunter'; caster=cls in ('Mage','Warlock','Druid','Shaman','Priest')
    damage='StatSpellPower' if caster else ('StatRangedAttackPower' if ranged else 'StatAttackPower')
    scale=1. if stratum==0 else 2.
    primary_slot,partner_slot='neck','back'
    candidates=[]; partners=[]
    points=_candidate_points()
    if family in ('weapon_cadence','periodic_refresh','nature_proc','shadow_proc'):
        primary_slot='main_hand'
        special={'periodic_refresh':12795,'nature_proc':19019,'shadow_proc':17068}
        item=special.get(family,ids['main_hand'])
        for i,(t,budget) in enumerate(points):
            if family=='weapon_cadence':
                params={'weapon_speed_seconds':1.3+2*t, 'speed_mode':'hold_base_dps', 'weapon_damage_scale':.8+.25*budget}
            else:
                nominal=6 if family=='nature_proc' else 1
                params={'proc_ppm':nominal*(.25+1.5*t)*scale,'weapon_damage_scale':1.15-.25*t+.15*(budget-.75)}
                if family=='periodic_refresh':
                    params['periodic_damage_per_tick']=10.*scale
            candidates.append(_alias(f'{wid}:a{i:02}',item,primary_slot,**params))
        for j,t in enumerate((0.,1/3,2/3,1.)):
            partners.append(_stats_alias(f'{wid}:x{j}',ids[partner_slot],partner_slot,
                {damage:50*scale*(1-t),'StatMeleeHaste':4*scale*t}))
    elif family=='onuse_shared_cd':
        primary_slot,partner_slot='trinket1','trinket2'
        # Baseline is passive; every future active/passive design stays in public domain.
        for i,(t,budget) in enumerate(points):
            item=13968 if i==0 or i%2==0 else 18820
            candidates.append(_stats_alias(f'{wid}:a{i:02}',item,primary_slot,
                {'StatSpellPower':40*scale*budget*t,'StatMP5':12*scale*budget*(1-t)}))
        for j,item in enumerate((22268,12930,11832,13965)):
            partners.append(_alias(f'{wid}:x{j}',item,partner_slot))
    else:
        axis={'mana_regen':'StatMP5','melee_hit':'StatMeleeHit','spell_hit':'StatSpellHit',
              'crit_flurry':'StatMeleeCrit','policy_resource':'StatMP5',
              'resistance_penetration':'StatSpellPenetration','joint_slots':'StatSpellCrit' if caster else 'StatMeleeCrit'}[family]
        limit={'StatMP5':40,'StatMeleeHit':12,'StatSpellHit':12,'StatMeleeCrit':6,
               'StatSpellCrit':6,'StatSpellPenetration':100}[axis]*scale
        dmax=(80 if caster else 160)*scale
        for i,(t,budget) in enumerate(points):
            stats={axis:limit*budget*t,damage:dmax*budget*(1-t)}
            # Universal crit/hit should not inherit an unrecorded second gear pool.
            if axis in ('StatMeleeHit','StatSpellHit'):
                stats['StatSpellHit' if axis=='StatMeleeHit' else 'StatMeleeHit']=0
            if axis in ('StatMeleeCrit','StatSpellCrit'):
                stats['StatSpellCrit' if axis=='StatMeleeCrit' else 'StatMeleeCrit']=0
            candidates.append(_stats_alias(f'{wid}:a{i:02}',ids[primary_slot],primary_slot,stats))
        for j,t in enumerate((0.,1/3,2/3,1.)):
            stats={axis:limit*.5*t,damage:dmax*.5*(1-t)}
            if axis in ('StatMeleeHit','StatSpellHit'):
                stats['StatSpellHit' if axis=='StatMeleeHit' else 'StatMeleeHit']=0
            if axis in ('StatMeleeCrit','StatSpellCrit'):
                stats['StatSpellCrit' if axis=='StatMeleeCrit' else 'StatMeleeCrit']=0
            partners.append(_stats_alias(f'{wid}:x{j}',ids[partner_slot],partner_slot,stats))
    policies=['native']
    if family=='policy_resource': policies+=['early_recovery']
    if family=='onuse_shared_cd': policies+=['reverse_trinket_priority']
    world={'schema':SCHEMA,'world_id':wid,'mechanism_id':family,'lineage_id':family,
        'context':context,'stratum':stratum,'tasks':_tasks(family,stratum),'policies':policies,
        'candidates':candidates,'partners':partners,'initial_candidate_ids':[0],
        'initial_partner_ids':[0] if family=='joint_slots' else list(range(4)),
        'model_scope':'joint_two_update_slots' if family=='joint_slots' else 'fixed_partners_multi_task',
        'objective_branches':['V','H'],'source_unit':'research component alias; not dungeon-level provenance',
        'task_weights':[.5,.5],'parameter_scope':'research_variant_moderate' if stratum==0 else 'research_variant_stress',
        'candidate_parameter_design':'Baseline allocation .5,budget .75; 4 allocations x4 budgets .65,.8,.95,1.1; native trinket alternation where specified.',
        'all_physical_crosses_legal':True,'power_cap_filters_cells':False,
        'randomization':'Same seed block within a task creates coupled native labeled RNG streams across configurations; not independent worlds.',
        'initial_validity':'not_assessed_until_native_observations',
        'support_status':FAMILIES[family][4], 'limitations':FAMILIES[family][5]}
    world['world_sha256']=canonical_hash(world)
    return world


@lru_cache(maxsize=1)
def _world_tuple():
    return tuple(_build(family,cls,race,stratum) for family in FAMILIES
                 for cls,race in _four(family) for stratum in (0,1))


def worlds():
    """Return 96 registered settings, not 96 independently validated mechanisms."""
    return deepcopy(list(_world_tuple()))


def _apply_policy(value,world,policy):
    if policy=='native': return
    player=value['request']['raid']['parties'][0]['players'][0]
    rows=player['rotation'].get('priorityList',[])
    if policy=='early_recovery':
        sid=11689 if world['context']['class']=='Warlock' else 12051
        found=False
        for row in rows:
            action=row.get('action',{})
            if action.get('castSpell',{}).get('spellId',{}).get('spellId')==sid:
                action['condition']={'cmp':{'op':'OpLt','lhs':{'currentManaPercent':{}},'rhs':{'const':{'val':'35%'}}}}
                found=True
        if not found: raise ValueError('Recovery action missing in native preset')
    elif policy=='reverse_trinket_priority':
        # Native spells, existing shared timers; no invented cooldown mechanics.
        equip=player['equipment']['items']
        first=equip[SLOTS.index('trinket1')]['id']; second=equip[SLOTS.index('trinket2')]['id']
        active=[i for i in (second,first) if i in (18820,22268,11832)]
        priority=[{'action':{'castSpell':{'spellId':{'itemId':i}}}} for i in active]
        player['rotation']['priorityList']=priority+rows
    else: raise ValueError('Unknown policy '+policy)


def jobs_for_world(world,phase,seed,iterations,selection='anchors',*,debug=False):
    """Construct native jobs with full incidence and actual physical requests.

    anchors: a00,a01,a04,a09,a16 x all4 partners x all tasks/policies.
    full: all17 x4 xall tasks/policies.
    dict: candidate_indices,partner_indices,task_indices,policy_indices.
    No selection is conditioned on observed power; filtering is a scheduling act.
    """
    if selection in ('anchors','smoke'):
        choices={'candidate_indices':[0,1,4,9,16], 'partner_indices':list(range(4))}
    elif selection=='full': choices={}
    elif isinstance(selection,dict): choices=selection
    else: raise ValueError('Unknown selection')
    ci=choices.get('candidate_indices',list(range(len(world['candidates']))))
    pi=choices.get('partner_indices',list(range(len(world['partners']))))
    ti=choices.get('task_indices',list(range(len(world['tasks']))))
    qi=choices.get('policy_indices',list(range(len(world['policies']))))
    if not isinstance(iterations,int) or iterations<1: raise ValueError('iterations must be positive integer')
    jobs=[]
    for k,q in product(ti,qi):
        task=world['tasks'][k]; policy=world['policies'][q]
        base=make_input(world['context'],task,seed=seed,iterations=iterations,debug=debug)
        for target in base['request']['encounter']['targets']:
            if 'nature_resistance' in task: target['stats'][38]=task['nature_resistance']
            if 'all_magic_resistance' in task:
                for r in range(35,40): target['stats'][r]=task['all_magic_resistance']
        for i,j in product(ci,pi):
            aliases=[world['candidates'][i],world['partners'][j]]
            value=instantiate(base,aliases)
            _apply_policy(value,world,policy)
            validate_equipment(value)
            config_id=f'a{i:02}__x{j}'
            sources=[a['research_alias'] for a in aliases]
            meta={'world_id':world['world_id'],'mechanism_id':world['mechanism_id'],
                'lineage_id':world['lineage_id'],'candidate_id':f'a{i:02}','partner_id':f'x{j}',
                'candidate_index':i,'partner_index':j,'task_index':k,'policy_index':q,
                'configuration_id':config_id,'source_ids':sources,'component_incidence':sources,
                'task_id':task['task_id'],'policy_id':policy,'seed_block_id':f'{seed}:{iterations}',
                'phase':phase,'world_sha256':world['world_sha256'],
                'model_scope':world['model_scope'],'observed_or_reconstructed':'observed',
                'context_id':world['context']['context_id'],'class':world['context']['class'],
                'race':world['context']['race_label'],'faction':world['context']['faction'],
                'physical_legality':'all_validated_crosses','parameter_scope':world['parameter_scope']}
            jobs.append({'input':value,'meta':meta})
    return jobs


def write_registry(output):
    """Write newly generated protocol inputs; refuse changes to an existing registry."""
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    rows=worlds()
    registry=''.join(json.dumps(w,sort_keys=True)+'\n' for w in rows)
    path=output/'WORLD_REGISTRY.jsonl'
    if path.exists() and path.read_text()!=registry: raise ValueError('Existing registry differs; use a new campaign version')
    path.write_text(registry)
    fields=['mechanism_id','mechanism_label','hypothesis','native_source','hooks','support_status','limitations']
    matrix=[dict(zip(fields,(family,*entry))) for family,entry in FAMILIES.items()]
    with (output/'ENGINE_SUPPORT_MATRIX.csv').open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(matrix)
    with (output/'HYPOTHESIS_REGISTER.csv').open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(matrix)
    with (output/'CANDIDATE_LINEAGES.jsonl').open('w') as f:
        for w in rows:
            for kind,aliases in [('candidate',w['candidates']),('partner',w['partners'])]:
                for index,alias in enumerate(aliases):
                    f.write(json.dumps({'world_id':w['world_id'],'mechanism_id':w['mechanism_id'],
                        'kind':kind,'index':index,**alias},sort_keys=True)+'\n')
    return {'worlds':len(rows),'hypothesis_families':len(FAMILIES), 'native_observations':0,
            'registry_sha256':canonical_hash(rows)}
