"""Source-selected actual-catalog controls; no stat, weapon or proc overrides.

The candidate lists are selected from engine data and mechanism source, not
campaign outcomes. Requests preserve native item effects and native APLs.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import product
import json
from pathlib import Path

from wowfs.experiments.fc_native import (
    SLOTS, contexts, define_alias, engine_root, make_input, native_database,
    validate_equipment,
)
from wowfs.experiments.r2_native import file_hash
from wowfs.paths import canonical_hash


CATALOG_POOLS = {
    "catalog_warrior_weapon_type": {
        "class": "Warrior", "races": ["Human", "Orc"],
        "primary_slot": "main_hand", "partner_slot": "hands",
        "candidates": [17075, 12940, 18832, 17068, 12798, 18816, 17112, 19019,
                       12795, 17103, 18805, 17071, 19324, 13964, 17719, 18372],
        "partners": [14551, 18823, 19143, 15063],
        "fixed_equipment": {"off_hand": 12939},
        "hypothesis": "Actual dagger/sword/axe/mace/fist types change normalized attacks, weapon-skill gloves and procs.",
        "source_files": ["sim/core/attack.go", "sim/warrior/whirlwind.go",
                         "sim/common/item_effects.go", "sim/common/item_sets/item_sets_pve.go"],
        "new_relative_to_v1": "Actual weapon-type and weapon-skill interactions; v1 varied speed on a fixed base type.",
        "limitations": "Different catalog weapons also differ in stats and procs; type is not an isolated causal intervention. Dal'Rend pairing can activate its actual set bonus.",
        "task_family": "armor",
    },
    "catalog_rogue_weapon_type": {
        "class": "Rogue", "races": ["Human", "Orc"],
        "primary_slot": "main_hand", "partner_slot": "hands",
        "candidates": [12940, 17075, 18832, 18816, 17112, 19019, 12795, 17103,
                       18805, 17071, 19324, 13964, 17719, 18372, 17780],
        "partners": [16712, 18823, 15063, 13957],
        "fixed_equipment": {"off_hand": 12939, "shoulder": 16708, "chest": 16721},
        "hypothesis": "Actual weapon type interacts with dagger expertise, preset talent specialization and normalized abilities.",
        "source_files": ["sim/core/attack.go", "sim/rogue/sinister_strike.go",
                         "sim/rogue/talents.go", "sim/common/item_effects.go"],
        "new_relative_to_v1": "Actual weapon-type interface; race repetitions do not add mechanisms.",
        "limitations": "Native preset talent/APL remains fixed across weapons; optimal respec is not claimed. Neutral Shadowcraft pieces replace faction-named PvP preset pieces and can activate native set effects.",
        "task_family": "armor",
    },
    "catalog_heroism_threshold": {
        "class": "Warrior", "races": ["Human", "Orc"],
        "primary_slot": "hands", "partner_slot": "legs",
        "candidates": [14551, 21998, 13072, 18823, 19143, 15063, 15070,
                       16712, 18527, 16863, 13162, 18344, 13957, 18326],
        "partners": [14554, 22000, 15062, 18380],
        "fixed_equipment": {"waist": 21994, "wrist": 21996},
        "hypothesis": "Actual Heroism gloves and legs jointly cross the four-piece native rage-return threshold; alternative gloves remain available.",
        "source_files": ["sim/warrior/item_sets_pve.go",
                         "sim/common/item_sets/crafted.go"],
        "new_relative_to_v1": "Actual catalog set-threshold control; Heroism itself was already investigated in historical R6 and is not a newly discovered mechanism.",
        "limitations": "Heroism three-piece health regeneration and five-piece disarm break are not simulated here. This is not the old R6 two-set cascade test. Full stat differences accompany set membership.",
        "set_threshold": {"set_name": "Battlegear of Heroism", "pieces": 4,
                          "fixed_pieces": 2, "effect_spell_ids": [450587, 450589]},
        "task_family": "duration",
    },
    "catalog_magister_threshold": {
        "class": "Mage", "races": ["Gnome", "Undead"],
        "primary_slot": "hands", "partner_slot": "legs",
        "candidates": [13253, 16684, 14146, 18407, 18730, 16801, 18808,
                       18408, 14043, 13870, 14543, 18387, 22256, 22066],
        "partners": [13170, 16687, 16915, 18386],
        "fixed_equipment": {"head": 16686, "wrist": 16683, "waist": 16685},
        "hypothesis": "Actual Magister gloves and legs jointly cross five-piece Sudden Insight, giving spellcast-triggered mana restoration.",
        "source_files": ["sim/common/item_sets/dungeon_set_1.go"],
        "new_relative_to_v1": "A genuine native five-piece resource-proc threshold, distinct from a continuously overridden MP5 stat.",
        "limitations": "Forever Magister's four-piece root-on-attacker is unmodelled; three-piece gives 18 spell power, five-piece has 5% spellcast chance of 200 mana, six-piece gives 8 MP5. Only three-to-five pieces occur here.",
        "set_threshold": {"set_name": "Magister's Regalia", "pieces": 5,
                          "fixed_pieces": 3, "effect_spell_ids": [450527]},
        "task_family": "duration",
    },
    "catalog_mage_trinkets": {
        "class": "Mage", "races": ["Gnome", "Undead"],
        "primary_slot": "trinket1", "partner_slot": "off_hand",
        "candidates": [13968, 18820, 11832, 22268, 18371, 17064, 19288,
                       11819, 20036, 19959, 18468, 13965],
        "partners": [10796, 11904, 19310, 18695],
        "fixed_equipment": {},
        "hypothesis": "Actual on-use, mana-regeneration and spellcast-proc trinkets trade short and sustained performance without tuned effect amplitudes.",
        "source_files": ["sim/common/item_effects.go", "sim/mage/items.go",
                         "sim/core/ruleset.go"],
        "new_relative_to_v1": "Broader untouched catalog reference, not a new mechanism for every item ID.",
        "limitations": "Only eleven nonbaseline candidates are retained because unsupported movement/summon/knockback trinkets were not invented as combat effects. Fire Ruby's fire-specific effect may be unused by the fixed frost APL. Universal crit may make Eye of the Beast and Blackhand's Breadth response-equivalent. Second Wind's mountainous modifier is not simulated.",
        "task_family": "duration",
    },
    "catalog_warlock_weapons": {
        "class": "Warlock", "races": ["Human", "Orc"],
        "primary_slot": "main_hand", "partner_slot": "off_hand",
        "candidates": [13964, 17103, 17070, 17710, 18396, 18491, 18878,
                       20647, 20698, 20720, 22266, 17780, 18372],
        "partners": [10796, 11904, 19309, 18695],
        "fixed_equipment": {"finger2": 19147},
        "hypothesis": "Untouched caster weapons/offhands test source uses under real school bonuses and the Blade of Eternal Darkness damage/mana proc.",
        "source_files": ["sim/common/item_effects.go", "sim/warlock/lifetap.go"],
        "new_relative_to_v1": "Actual-catalog control with a spell-triggered weapon proc; variation is not automatically a new mechanism.",
        "limitations": "Life Tap health loss and pet owner-stat inheritance have known engine limitations. No survival or live-server accuracy claim. Only one-hand weapons are included so all four offhands remain physically legal. A neutral Ring of Spell Power replaces the Alliance-restricted Songstone preset ring in both factions.",
        "task_family": "duration",
    },
}


def _catalog_alias(world_id, item_id, slot):
    item = native_database()[item_id]
    value = define_alias(f"{world_id}:item:{item_id}", item_id, slot, {})
    value.update(
        item_name=item["name"], source_id=f"native_item:{item_id}",
        parameter_scope="actual_catalog_items", native_item_record_sha256=canonical_hash(item),
        native_set_name=item.get("setName"), native_weapon_type=item.get("weaponType"),
        native_item_level=item.get("ilvl"),
        distance_to_native_base={"base_item_name": item["name"], "changed_parameters": {},
                                 "distance": 0, "interpretation": "Untouched native database item; no parameter override."},
    )
    return value


def _tasks(family):
    if family == "armor":
        return [{"task_id": "low_armor", "duration": 90, "armor": 2000, "targets": 1},
                {"task_id": "high_armor", "duration": 90, "armor": 10000, "targets": 1}]
    return [{"task_id": "short", "duration": 30, "armor": 3731, "targets": 1},
            {"task_id": "long", "duration": 180, "armor": 3731, "targets": 1}]


def _check_faction(value, context):
    required = 1 if context["faction"] == "Alliance" else 2
    items = value["request"]["raid"]["parties"][0]["players"][0]["equipment"]["items"]
    for entry in items:
        if entry.get("id") and native_database()[entry["id"]].get("factionRestriction") not in (None, 0, required):
            raise ValueError("Native database faction restriction rejects " + str(entry["id"]))


def worlds():
    database = native_database()
    database_hash = file_hash(engine_root() / "assets/database/db.json")
    result = []
    for family, pool in CATALOG_POOLS.items():
        for race in pool["races"]:
            context = next(c for c in contexts() if c["class"] == pool["class"] and c["race_label"] == race)
            world_id = f'{family}__{context["context_id"]}__catalog_v1'
            world = {
                "schema": 1, "world_id": world_id, "mechanism_id": family,
                "lineage_id": family, "context": context, "stratum": "catalog",
                "tasks": _tasks(pool["task_family"]), "policies": ["native"],
                "candidates": [_catalog_alias(world_id, i, pool["primary_slot"]) for i in pool["candidates"]],
                "partners": [_catalog_alias(world_id, i, pool["partner_slot"]) for i in pool["partners"]],
                "fixed_equipment": deepcopy(pool["fixed_equipment"]),
                "fixed_equipment_records": {slot: {"item_id": i, "name": database[i]["name"],
                                             "native_item_record_sha256": canonical_hash(database[i])}
                                            for slot, i in pool["fixed_equipment"].items()},
                "initial_candidate_ids": [0], "initial_partner_ids": list(range(4)),
                "model_scope": "fixed_partners_multi_task", "objective_branches": ["V", "H"],
                "source_unit": "actual native catalog item ID in the two varying slots; not dungeon provenance",
                "task_weights": [.5, .5], "parameter_scope": "actual_catalog_items",
                "candidate_parameter_design": "Source-selected explicit IDs before observing these worlds; no outcome-based filtering or numerical overrides.",
                "all_physical_crosses_legal": True, "power_cap_filters_cells": False,
                "initial_validity": "not_assessed_until_native_observations",
                "support_status": "source_checked_not_native_executed",
                "hypothesis": pool["hypothesis"], "limitations": pool["limitations"],
                "new_relative_to_v1": pool["new_relative_to_v1"],
                "set_threshold": deepcopy(pool.get("set_threshold")),
                "catalog_provenance": {"db_json_sha256": database_hash,
                    "source_hashes": {p: file_hash(engine_root() / p) for p in pool["source_files"]},
                    "scope": "Pinned engine catalog and encoded class/faction restrictions, not independently verified live acquisition or phase availability."},
                "candidate_shortfall": None if len(pool["candidates"]) >= 13 else
                    {"target_new_candidates": 12, "actual_new_candidates": len(pool["candidates"])-1,
                     "reason": "Source-supported combat-relevant catalog pool; no artificial padding."},
                "randomization": "Common seed blocks within task couple native RNG across configurations; races are coverage repeats.",
            }
            world["world_sha256"] = canonical_hash(world)
            result.append(world)
    return result


def jobs_for_world(world, phase, seed, iterations, selection="full", *, debug=False):
    if selection == "full":
        selected = {}
    elif selection in ("anchors", "smoke"):
        selected = {"candidate_indices": sorted({0, 1, len(world["candidates"])//2, len(world["candidates"])-1})}
    elif isinstance(selection, dict):
        selected = selection
    else:
        raise ValueError("Unknown catalog selection")
    if not isinstance(iterations, int) or iterations < 1:
        raise ValueError("iterations must be a positive integer")
    indices = [selected.get("candidate_indices", range(len(world["candidates"]))),
               selected.get("partner_indices", range(len(world["partners"]))),
               selected.get("task_indices", range(len(world["tasks"]))),
               selected.get("policy_indices", range(len(world["policies"])))]
    jobs = []
    for i, j, k, q in product(*indices):
        if q != 0:
            raise ValueError("Catalog v1 uses the unchanged native policy only")
        task = world["tasks"][k]
        value = make_input(world["context"], task, seed=seed, iterations=iterations, debug=debug)
        gear = value["request"]["raid"]["parties"][0]["players"][0]["equipment"]["items"]
        for slot, item_id in world["fixed_equipment"].items():
            gear[SLOTS.index(slot)] = {"id": item_id}
        aliases = [world["candidates"][i], world["partners"][j]]
        for alias in aliases:
            if alias["parameter_overrides"]:
                raise ValueError("Actual-catalog worlds forbid parameter overrides")
            gear[SLOTS.index(alias["equipment_slot"])] = {"id": alias["native_base_item_id"]}
        # Do not even emit no-op research-variant records to the native bridge.
        value["research_variants"] = []
        validate_equipment(value)
        _check_faction(value, world["context"])
        sources = [a["research_alias"] for a in aliases]
        meta = {"world_id": world["world_id"], "mechanism_id": world["mechanism_id"],
                "lineage_id": world["lineage_id"], "candidate_id": f"a{i:02}", "partner_id": f"x{j}",
                "candidate_index": i, "partner_index": j, "task_index": k, "policy_index": q,
                "configuration_id": f"a{i:02}__x{j}", "source_ids": sources,
                "component_incidence": sources, "native_source_item_ids": [a["native_base_item_id"] for a in aliases],
                "task_id": task["task_id"], "policy_id": "native", "seed_block_id": f"{seed}:{iterations}",
                "phase": phase, "world_sha256": world["world_sha256"], "model_scope": world["model_scope"],
                "observed_or_reconstructed": "observed", "context_id": world["context"]["context_id"],
                "class": world["context"]["class"], "race": world["context"]["race_label"],
                "faction": world["context"]["faction"], "physical_legality": "all_validated_catalog_crosses",
                "parameter_scope": "actual_catalog_items"}
        jobs.append({"input": value, "meta": meta})
    return jobs


def write_registry(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = worlds()
    serialized = "".join(json.dumps(w, sort_keys=True) + "\n" for w in rows)
    path = output / "WORLD_REGISTRY_CATALOG.jsonl"
    if path.exists() and path.read_text() != serialized:
        raise ValueError("Frozen catalog registry differs; create a new version")
    path.write_text(serialized)
    return {"worlds": len(rows), "catalog_lineages": len(CATALOG_POOLS),
            "native_observations": 0, "registry_sha256": canonical_hash(rows)}
