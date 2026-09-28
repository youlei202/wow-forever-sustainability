"""Catalog protocol checks only: no combat simulation is executed."""
import pytest

from wowfs.experiments.fc_native import SLOTS, engine_root, native_database
from wowfs.experiments.oe_catalog_worlds import worlds, jobs_for_world, _check_faction


@pytest.fixture(scope="module")
def catalog():
    if not (engine_root() / "assets/database/db.json").exists():
        pytest.skip("Pinned native catalog is an external dependency")
    return worlds()


def test_catalog_has_complete_legal_crosses_without_physical_overrides(catalog):
    assert len(catalog) == 12
    count = 0
    database = native_database()
    for world in catalog:
        assert world["parameter_scope"] == "actual_catalog_items"
        assert world["initial_candidate_ids"] == [0]
        assert len(world["partners"]) == 4
        assert len(world["tasks"]) == 2
        aliases = world["candidates"] + world["partners"]
        assert all(a["parameter_overrides"] == {} for a in aliases)
        assert all(a["distance_to_native_base"]["distance"] == 0 for a in aliases)
        jobs = jobs_for_world(world, "protocol_test", 926499991, 1)
        assert len(jobs) == len(world["candidates"]) * 4 * 2
        for job in jobs:
            value = job["input"]
            assert value["research_variants"] == []
            assert value["disable_item_effects"] == []
            assert value["disable_set_bonuses"] == []
            gear = value["request"]["raid"]["parties"][0]["players"][0]["equipment"]["items"]
            assert len(gear) == 17
            assert all(x.get("id", 0) == 0 or x["id"] in database for x in gear)
            count += 1
    assert count == 1344


@pytest.mark.parametrize("family,set_name,minimum,threshold", [
    ("catalog_heroism_threshold", "Battlegear of Heroism", 2, 4),
    ("catalog_magister_threshold", "Magister's Regalia", 3, 5),
])
def test_actual_set_threshold_requires_the_declared_combination(catalog, family, set_name, minimum, threshold):
    database = native_database()
    world = next(w for w in catalog if w["mechanism_id"] == family)
    jobs = jobs_for_world(world, "protocol_test", 926499991, 1,
                          {"task_indices": [0]})
    levels, baseline = set(), []
    crossings = []
    for job in jobs:
        gear = job["input"]["request"]["raid"]["parties"][0]["players"][0]["equipment"]["items"]
        count = sum(database[x["id"]].get("setName") == set_name for x in gear if x.get("id"))
        levels.add(count)
        if job["meta"]["candidate_index"] == 0:
            baseline.append(count)
        if count >= threshold:
            crossings.append(job["meta"]["native_source_item_ids"])
    assert levels == {minimum, minimum + 1, threshold}
    assert max(baseline) == threshold - 1
    assert len(crossings) == 1


def test_real_weapon_types_and_unmodified_catalog_shortfall_are_explicit(catalog):
    for family in ("catalog_warrior_weapon_type", "catalog_rogue_weapon_type"):
        world = next(w for w in catalog if w["mechanism_id"] == family)
        types = {a["native_weapon_type"] for a in world["candidates"]}
        assert 2 in types and 9 in types  # Native dagger and sword types.
        assert len(types) >= 4
    trinkets = [w for w in catalog if w["mechanism_id"] == "catalog_mage_trinkets"]
    assert all(w["candidate_shortfall"]["actual_new_candidates"] == 11 for w in trinkets)


def test_catalog_rejects_a_real_cross_faction_item(catalog):
    world = next(w for w in catalog if w["mechanism_id"] == "catalog_warlock_weapons"
                 and w["context"]["faction"] == "Horde")
    job = jobs_for_world(world, "protocol_test", 926499991, 1,
                         {"candidate_indices": [0], "partner_indices": [0], "task_indices": [0]})[0]
    gear = job["input"]["request"]["raid"]["parties"][0]["players"][0]["equipment"]["items"]
    assert gear[SLOTS.index("finger2")]["id"] == 19147
    gear[SLOTS.index("finger2")] = {"id": 12543}  # Songstone of Ironforge, Alliance only.
    with pytest.raises(ValueError, match="faction restriction"):
        _check_faction(job["input"], world["context"])
