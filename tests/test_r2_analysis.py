"""Native-output accounting checks; fixtures are not combat observations."""
from copy import deepcopy

import numpy as np
import pytest
from scipy.stats import t

from wowfs.experiments.r2_analysis import factorial, group_factorials, interval
from wowfs.experiments.r2_native import summarize


def _native_output():
    return {
        "iterationsDone": 4,
        "error": None,
        "raidMetrics": {"parties": [{"players": [{
            "dps": {"allValues": [10.0, 16.0, 12.0, 14.0], "avg": 13.0},
            "actions": [
                {"id": {"spellId": 123, "tag": 1},
                 "targets": [{"casts": 12, "damage": 6000.0}]},
                {"id": {"spellId": 123, "tag": 2},
                 "targets": [{"casts": 4, "damage": 3360.0}]},
            ],
            "resources": [{"id": {"spellId": 456}, "type": "ResourceTypeRage",
                           "events": 8, "gain": 80.0, "actualGain": 60.0}],
            "auras": [{"id": {"spellId": 789}, "uptimeSecondsAvg": 20.0,
                       "uptimeSecondsStdev": 2.0, "procsAvg": 3.0}],
        }]}]},
    }


def _request():
    return {"request": {"simOptions": {"iterations": 4}}}


def test_native_summary_preserves_seed_order_and_normalizes_each_metric_once():
    raw = _native_output()
    original = deepcopy(raw)
    summary = summarize(raw, _request())
    assert summary["dps_samples"] == [10.0, 16.0, 12.0, 14.0]
    assert summary["dps_mean"] == 13.0
    assert summary["dps_se"] == pytest.approx((20.0 / 3.0 / 4.0) ** 0.5)
    assert summary["actions"]["spellId:123/tag:1"]["casts"] == 3.0
    assert summary["actions"]["spellId:123/tag:2"]["damage"] == 840.0
    assert sum(a["fraction"] for a in summary["actions"].values()) == pytest.approx(1.0)
    assert summary["resources"][0]["gain"] == 20.0
    assert summary["resources"][0]["actualGain"] == 15.0
    assert summary["auras"][0]["uptimeSecondsAvg"] == 20.0
    assert summary["auras"][0]["procsAvg"] == 3.0
    assert raw == original


@pytest.mark.parametrize("change", [
    {"iterationsDone": 3},
    {"error": {"type": "ErrorOutcomeAborted", "message": "aborted"}},
])
def test_partial_or_failed_native_batch_is_not_performance_data(change):
    raw = _native_output()
    raw.update(change)
    with pytest.raises(ValueError, match="native incomplete"):
        summarize(raw, _request())


@pytest.mark.parametrize("values", [
    [10.0, 16.0, 12.0],
    [10.0, 16.0, 12.0, float("nan")],
    [10.0, 16.0, 12.0, float("inf")],
])
def test_missing_or_nonfinite_seed_values_cannot_be_silently_paired(values):
    raw = _native_output()
    raw["raidMetrics"]["parties"][0]["players"][0]["dps"]["allValues"] = values
    with pytest.raises(ValueError, match="samples missing or nonfinite"):
        summarize(raw, _request())


def test_sample_summary_disagreement_is_preserved_as_failure():
    raw = _native_output()
    raw["raidMetrics"]["parties"][0]["players"][0]["dps"]["avg"] = 20.0
    with pytest.raises(ValueError, match="sample mean mismatch"):
        summarize(raw, _request())


def test_factorial_retains_common_seed_covariance_instead_of_marginal_errors():
    common = np.arange(16, dtype=float) * 1000.0
    interaction = np.tile([-3.0, -1.0, 1.0, 3.0], 4) + 2.0
    result = factorial({0: common, 1: common + 2, 2: common + 3,
                        3: common + 5 + interaction}, effects=2, family=6)
    expected_se = interaction.std(ddof=1) / 4
    assert result["estimate"] == pytest.approx(2.0)
    assert result["se"] == pytest.approx(expected_se)
    expected_margin = t.ppf(1 - 0.05 / 12, 15) * expected_se
    assert result["ci_low"] == pytest.approx(2.0 - expected_margin)
    assert result["ci_high"] == pytest.approx(2.0 + expected_margin)
    # Ignoring covariance gives a standard error thousands of times larger.
    assert common.std(ddof=1) / 4 > 1000 * result["se"]


def test_three_way_contrast_removes_all_lower_order_terms():
    signal = np.array([-2.0, 1.0, 3.0, 6.0])
    cells = {}
    for mask in range(8):
        a, b, c = (int(bool(mask & (1 << bit))) for bit in range(3))
        cells[mask] = (np.arange(4) * 1000 + 50 + 2 * a + 3 * b + 4 * c
                       + 5 * a * b + 6 * a * c + 7 * b * c + signal * a * b * c)
    result = factorial(cells, effects=3)
    assert result["estimate"] == pytest.approx(signal.mean())
    assert result["se"] == pytest.approx(signal.std(ddof=1) / 2)


@pytest.mark.parametrize("missing_mask", [0, 4, 7])
def test_incomplete_three_way_factorial_is_not_a_zero_interaction(missing_mask):
    cells = {mask: [1.0, 2.0, 3.0] for mask in range(8) if mask != missing_mask}
    with pytest.raises(ValueError, match="complete factorial"):
        factorial(cells, effects=3)


def test_unequal_seed_counts_cannot_be_broadcast_or_truncated():
    with pytest.raises(ValueError, match="equal finite per-seed"):
        factorial({0: [1.0, 2.0], 1: [1.0, 2.0, 3.0],
                   2: [1.0, 2.0], 3: [1.0, 2.0]})


@pytest.mark.parametrize("sample", [np.ones(128), np.array([1e-14, 2e-14] * 64)])
def test_degenerate_precision_does_not_produce_significance(sample):
    result = interval(sample, family=6)
    assert result["degenerate_observed_variance"]
    assert result["direction"] == "unresolved"


def test_family_adjustment_widens_intervals():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    single = interval(values, family=1)
    multiple = interval(values, family=6)
    assert multiple["ci_low"] < single["ci_low"]
    assert multiple["ci_high"] > single["ci_high"]


def test_grouping_keeps_contexts_and_policies_distinct():
    rows = [{"case": "a", "task": "b", "strategy": strategy, "race": race,
             "mask": mask, "dps_samples": [1.0, 2.0]}
            for strategy in ("s1", "s2") for race in ("r1", "r2")
            for mask in range(4)]
    grouped = group_factorials([None, *rows])
    assert len(grouped) == 4
    assert all(set(cells) == set(range(4)) for cells in grouped.values())
