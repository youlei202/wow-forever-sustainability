from wowfs.experiments.r4_causal import disabled_effects


def test_absent_effects_canonicalize_without_changing_loadout():
    gear = {"main_hand": 18203, "off_hand": 871, "trinket1": 11815}
    original = dict(gear)
    assert disabled_effects(gear, (18203, 19951), 0) == [18203]
    assert disabled_effects(gear, (18203, 19951), 2) == [18203]
    assert disabled_effects(gear, (18203, 19951), 1) == []
    assert disabled_effects(gear, (18203, 19951), 3) == []
    assert gear == original


def test_enabled_bits_have_correct_factorial_semantics():
    gear = {"main_hand": 18203, "off_hand": 19019}
    assert [disabled_effects(gear, (18203, 19019), mask) for mask in range(4)] == [
        [18203, 19019], [19019], [18203], []]
