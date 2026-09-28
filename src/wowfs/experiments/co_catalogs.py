"""Outcome-blind native catalogue registration for completion oral extension.

Only database metadata, fixed source policies and declared deterministic draws
enter this module. No response cache, old winner list or simulated value is read.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from functools import lru_cache
from itertools import product
import json
from pathlib import Path
import random

from wowfs.experiments.fc_native import (
    CLASS_IDS, MAX_ARMOR, SLOTS, TYPES, contexts, define_alias, engine_root,
    make_input, native_database, validate_equipment,
)
from wowfs.experiments.r2_native import file_hash
from wowfs.paths import canonical_hash


SELECTION_SEED = 926202601
STRATA = (
    dict(id="warrior_weapon_skill", cls="Warrior", races=("Human", "Orc"),
         left="main_hand", right="hands", fixed={},
         sources=("sim/warrior/whirlwind.go", "sim/warrior/talents.go",
                  "sim/core/attack.go", "sim/common/item_effects.go"),
         mechanism="One-hand weapon damage/type/procs with glove weapon skill and dual-wield rage attacks.",
         limitations="Fixed native talent/APL; weapon skill and proc support follow this executable, not all live effects. Rage depends on base weapon speed in this engine."),
    dict(id="paladin_seal_twisting", cls="Paladin", races=("Human", "Undead"),
         left="main_hand", right="hands", fixed={"chest":11726, "off_hand":0},
         sources=("sim/paladin/soc.go", "sim/paladin/sor.go", "sim/paladin/judgement.go",
                  "ui/retribution_paladin/apls/basic_ret.apl.json"),
         mechanism="Two-hand weapon scaling and swing timing with native Command/Righteousness twisting and mixed physical/holy attacks.",
         limitations="Unchanged APL uses Command and Righteousness; fixed preset primarySeal option alone is not a description of executed spells. No survival or incoming damage."),
    dict(id="mage_timed_resources", cls="Mage", races=("Gnome", "Undead"),
         left="trinket1", right="shoulder", fixed={},
         sources=("sim/common/item_effects.go", "sim/mage/items.go",
                  "ui/mage/apls/forever_frost.apl.json"),
         mechanism="Timed power, mana cost reduction, mana regeneration and spellcast-triggered trinkets with shoulder statistics.",
         limitations="Finite source-supported trinket pool; Fire Ruby may be inactive under frost APL, Rune of the Dawn is target-type specific, and Second Wind terrain modifier is unimplemented."),
    dict(id="druid_passive_resources", cls="Druid", races=("Night Elf", "Tauren"),
         left="hands", right="feet", fixed={"finger1":19147},
         sources=("sim/druid/wrath.go", "sim/druid/starfire.go", "sim/druid/talents.go",
                  "sim/core/mana.go", "ui/balance_druid/apls/launch.apl.json"),
         mechanism="Passive mana/intellect/spirit/spell statistics with periodic upkeep and the native mana-guarded mixed-school balance APL.",
         limitations="APL guards do not imply that guarded Starfire executes; record actual decisions. Fixed okfUptime is unused upstream. No survival mechanics."),
)

# Every non-stat effect in this curated trinket pool has a corresponding source
# definition or an explicitly documented inactive condition. Selection is not
# based on the old trinket response outcomes.
MAGE_TRINKETS = (13968, 18820, 11832, 22268, 18371, 17064, 19288,
                 11819, 20036, 19959, 18468, 13965, 19812)


def _context(spec, ordinal):
    race = spec["races"][ordinal % 2]
    return next(c for c in contexts() if c["class"] == spec["cls"] and c["race_label"] == race)


def _native_base(spec, context):
    value = make_input(context, {"duration":30, "armor":3731}, seed=1, iterations=1)
    gear = value["request"]["raid"]["parties"][0]["players"][0]["equipment"]["items"]
    for slot, item_id in spec["fixed"].items():
        gear[SLOTS.index(slot)] = {"id":item_id}
    return value


def _legal_faction(value, context):
    faction = 1 if context["faction"] == "Alliance" else 2
    for row in value["request"]["raid"]["parties"][0]["players"][0]["equipment"]["items"]:
        if row.get("id") and native_database()[row["id"]].get("factionRestriction") not in (None, 0, faction):
            raise ValueError("faction restriction rejects " + str(row["id"]))


def _eligible(spec, context, slot, base):
    """Metadata-only pools; reject faction-specific acquisitions in varying slots."""
    db = native_database()
    fixed_ids = {r["id"] for i,r in enumerate(base["request"]["raid"]["parties"][0]["players"][0]["equipment"]["items"])
                 if SLOTS[i] not in (spec["left"],spec["right"])}
    counts = Counter()
    out = []
    for item_id,item in sorted(db.items()):
        reason = None
        if item["type"] != TYPES[SLOTS.index(slot)]: reason = "other_slot"
        elif item_id in fixed_ids: reason = "already_equipped_fixed_item"
        elif item.get("factionRestriction") not in (None,0): reason = "faction_tagged_not_in_common_pool"
        elif item.get("classAllowlist") and CLASS_IDS[spec["cls"]] not in item["classAllowlist"]: reason = "class_restricted"
        elif item.get("armorType",0) > MAX_ARMOR[spec["cls"]]: reason = "armor_restricted"
        elif not (52 <= item.get("ilvl",0) <= 75 and item.get("quality",0)>=3): reason = "outside_registered_level_quality"
        elif slot == "trinket1" and item_id not in MAGE_TRINKETS: reason = "outside_source_checked_trinket_pool"
        elif slot == "main_hand" and spec["cls"] == "Warrior" and item.get("handType") not in (1,2): reason = "not_one_hand"
        elif slot == "main_hand" and spec["cls"] == "Paladin" and (item.get("handType") != 4 or item.get("weaponType") not in (1,4,6,9)): reason = "not_legal_two_hand"
        elif spec["cls"] in ("Mage","Druid") and slot != "trinket1" and not (
            item.get("stats",[0]*44)[3] > 0 or item.get("stats",[0]*44)[12] > 0 or
            any(item.get("stats",[0]*44)[k] > 0 for k in (5,6,8,10,42))): reason = "no_registered_caster_stat"
        elif spec["cls"] in ("Warrior","Paladin") and slot != "main_hand" and not (
            any(item.get("stats",[0]*44)[k] > 0 for k in (0,1,17,18,19)) or any(item.get("weaponSkills",[]))): reason = "no_registered_melee_stat"
        if reason:
            counts[reason] += 1
        else:
            out.append(item_id)
    if len(out) < (10 if slot == spec["left"] else 5):
        raise ValueError(f"Insufficient metadata pool {spec['id']} {slot}: {len(out)}")
    return out, dict(counts)


def _draw(pool, count, extras, rng):
    # Sample membership, then use a deterministic metadata median as H's item.
    chosen = rng.sample(pool, count)
    db = native_database()
    ordered = sorted(chosen, key=lambda i:(db[i].get("ilvl",0), i))
    reference = ordered[len(ordered)//2]
    chosen = [reference] + sorted(set(chosen)-{reference})
    # Challenge additions are low-ilvl alternatives, not response-selected helpers.
    additions = sorted(set(pool)-set(chosen), key=lambda i:(db[i].get("ilvl",0),i))[:extras]
    return chosen + additions


def _alias(world_id, item_id, slot):
    item = native_database()[item_id]
    row = define_alias(f"{world_id}:item:{item_id}", item_id, slot, {})
    row.update(item_name=item["name"], source_id=f"native_item:{item_id}",
               parameter_scope="actual_catalog_items", native_item_record_sha256=canonical_hash(item),
               native_item_level=item.get("ilvl"), native_set_name=item.get("setName"),
               native_weapon_type=item.get("weaponType"))
    return row


def _tasks(spec, q4):
    if spec["cls"] in ("Warrior", "Paladin"):
        rows = [(90,2000),(90,10000)] if not q4 else [(30,2000),(30,10000),(180,2000),(180,10000)]
        return [dict(task_id=f"duration{d}_armor{a}",duration=d,armor=a,targets=1) for d,a in rows]
    durations = (30,180) if not q4 else (20,60,180,360)
    return [dict(task_id=f"duration{d}",duration=d,armor=3731,targets=1) for d in durations]


def _queries(rng):
    left = rng.sample([f"a{i:02}" for i in range(1,8)], 3)
    right = rng.sample([f"x{i}" for i in range(1,4)], 3)
    targets = [[left[0]],[left[1]],[right[0]],[right[1]],
               [left[0],right[0]],[left[1],right[1]],[left[2],right[2]],
               [left[0],left[2],right[2]]]
    return [dict(query_id=f"q{i:02}", required=sorted(x), selection="registered_seeded_slot_stratified_metadata")
            for i,x in enumerate(targets)]


@lru_cache(maxsize=1)
def _worlds_cached():
    result = []
    db = native_database()
    for si,spec in enumerate(STRATA):
        for ordinal in range(6):
            split = "development" if ordinal < 2 else "validation"
            local_id = ordinal if ordinal < 2 else ordinal-2
            expanded = split == "validation" and local_id < 2
            q4 = split == "validation" and local_id == 0
            wid = f"co_{spec['id']}__{split}_{local_id:02}"
            context = _context(spec, ordinal)
            base = _native_base(spec, context)
            seed = SELECTION_SEED + 1000*si + ordinal
            rng = random.Random(seed)
            lp,le = _eligible(spec,context,spec["left"],base)
            rp,re = _eligible(spec,context,spec["right"],base)
            li = _draw(lp,8,2 if expanded else 0,rng)
            ri = _draw(rp,4,1 if expanded else 0,rng)
            row = dict(schema=1, world_id=wid, mechanism_id=spec["id"], lineage_id=spec["id"],
                       context=context, split=split, stratum=spec["id"],
                       registration_seed=seed, candidate_sampling="metadata_only_without_response_or_winner_cache_access",
                       candidates=[_alias(wid,i,spec["left"]) for i in li],
                       partners=[_alias(wid,i,spec["right"]) for i in ri],
                       fixed_equipment=deepcopy(spec["fixed"]),
                       tasks=_tasks(spec,q4), policies=["native"], task_weights=[1/len(_tasks(spec,q4))]*len(_tasks(spec,q4)),
                       initial_candidate_ids=[0], initial_partner_ids=[0], history=["a00","x0"],
                       base_candidate_indices=list(range(8)),base_partner_indices=list(range(4)),
                       candidate_expansion_registered=expanded,queries=_queries(rng),
                       universe_variants=["base","expanded"] if expanded else ["base"],
                       model_scope="two_growing_slots_unrestricted_helpers", parameter_scope="actual_catalog_items",
                       source_unit="actual item identity in a registered equipment position",
                       hypothesis=spec["mechanism"],limitations=spec["limitations"],
                       old_catalog_overlap="Native item IDs and mechanism sources may overlap old work; exact menus, second-slot combinations and metadata draw are new. No old response outcomes used.",
                       eligible_pools={"left":lp,"right":rp},exclusion_counts={"left":le,"right":re},
                       expansion_selection="Lowest ilvl unselected metadata alternatives; no response screening",
                       history_selection="Upper median by (ilvl,item_id) among independently sampled base items in each slot",
                       all_physical_crosses_legal=True, initial_validity="not_assessed_until_native_observations",
                       support_status="source_and_equipment_checked_not_native_executed",
                       catalog_provenance={"db_json_sha256":file_hash(engine_root()/"assets/database/db.json"),
                         "source_hashes":{p:file_hash(engine_root()/p) for p in spec["sources"]},
                         "scope":"Pinned native database equipment rules, not live availability/acquisition verification"})
            row["world_sha256"] = canonical_hash(row)
            # This enumerates equipment only; no executable, subprocess or outcomes.
            jobs_for_world(row,"registration_legality",1,1)
            result.append(row)
    return tuple(result)


def worlds():
    return deepcopy(list(_worlds_cached()))


def jobs_for_world(world, phase, seed, iterations, selection="full", *, debug=False):
    if not isinstance(iterations,int) or iterations < 1:
        raise ValueError("positive integer iterations required")
    if selection == "full": selected = {}
    elif selection == "base": selected = dict(candidate_indices=world["base_candidate_indices"],partner_indices=world["base_partner_indices"])
    elif selection == "smoke": selected = dict(candidate_indices=[0],partner_indices=[0],task_indices=[0])
    elif isinstance(selection,dict): selected = selection
    else: raise ValueError("unknown selection")
    axes = [selected.get("candidate_indices",range(len(world["candidates"]))),
            selected.get("partner_indices",range(len(world["partners"]))),
            selected.get("task_indices",range(len(world["tasks"]))),
            selected.get("policy_indices",range(len(world["policies"])))]
    jobs = []
    for i,j,q,p in product(*axes):
        if p != 0: raise ValueError("only registered native policy")
        task = world["tasks"][q]
        value = make_input(world["context"],task,seed=seed,iterations=iterations,debug=debug)
        gear = value["request"]["raid"]["parties"][0]["players"][0]["equipment"]["items"]
        for slot,item in world["fixed_equipment"].items(): gear[SLOTS.index(slot)]={"id":item}
        aliases = [world["candidates"][i],world["partners"][j]]
        for a in aliases:
            if a["parameter_overrides"]: raise ValueError("unmodified native items required")
            gear[SLOTS.index(a["equipment_slot"]) ]={"id":a["native_base_item_id"]}
        value["research_variants"] = []
        validate_equipment(value)
        _legal_faction(value,world["context"])
        sources = [f"a{i:02}",f"x{j}"]
        meta = dict(world_id=world["world_id"],world_sha256=world["world_sha256"],
                    mechanism_id=world["mechanism_id"],lineage_id=world["lineage_id"],split=world["split"],
                    candidate_id=sources[0],partner_id=sources[1], candidate_index=i,partner_index=j,
                    task_index=q,policy_index=p,task_id=task["task_id"],policy_id="native",
                    configuration_id=f"a{i:02}__x{j}",source_ids=sources,component_incidence=sources,
                    native_source_item_ids=[a["native_base_item_id"] for a in aliases],
                    phase=phase,seed_block_id=f"{seed}:{iterations}",context_id=world["context"]["context_id"],
                    **{"class":world["context"]["class"],"race":world["context"]["race_label"],"faction":world["context"]["faction"]},
                    observed_or_reconstructed="observed",physical_legality="validated_actual_catalog_cross",
                    parameter_scope="actual_catalog_items", model_scope=world["model_scope"])
        jobs.append(dict(input=value,meta=meta))
    return jobs


def write_registry(output):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    rows = worlds()
    text = "".join(json.dumps(w,sort_keys=True)+"\n" for w in rows)
    path = output/"CATALOG_REGISTRY.jsonl"
    if path.exists() and path.read_text() != text: raise ValueError("registry is immutable; new version required")
    path.write_text(text)
    return dict(worlds=len(rows),development=sum(w["split"]=="development" for w in rows),
                validation=sum(w["split"]=="validation" for w in rows),
                expansion_units=sum(w["candidate_expansion_registered"] for w in rows),
                q4_units=sum(len(w["tasks"])==4 for w in rows),registry_sha256=canonical_hash(rows),
                native_observations=0)


def load_registry(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
