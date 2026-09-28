"""Checks essential evidence distinctions in the synthetic coefficient study."""
import importlib.util
from pathlib import Path
import sys


_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_SPEC = importlib.util.spec_from_file_location("statistics_verifier", _SCRIPTS / "verify_statistics.py")
assert _SPEC is not None and _SPEC.loader is not None
statistics = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = statistics
_SPEC.loader.exec_module(statistics)
sys.path.remove(str(_SCRIPTS))


def test_same_features_tie_with_physical_costs_separate():
    rows, _, _ = statistics.run(statistics.Protocol(repeats=2, budgets=(256,)))
    grouped = {(r["scenario"], r["replicate"], r["method"]): r for r in rows}
    for scenario in ("correct_model", "hidden_legal_interaction"):
        for replicate in range(2):
            shared = grouped[scenario, replicate, "shared_channel_coefficients"]
            generic = grouped[scenario, replicate, "generic_same_features"]
            separate = grouped[scenario, replicate, "separate_configuration_contrasts"]
            assert shared["hazards_certified"] == generic["hazards_certified"]
            assert shared["training_physical_simulations"] == separate["training_physical_simulations"] == 256
            assert generic["new_training_physical_simulations"] == 0
            assert generic["shared_training_cache_observations"] == 256


def test_independent_holdout_exposes_missing_feature():
    protocol = statistics.Protocol(repeats=1)
    model = statistics.Instance()
    original = statistics.holdout(model, "correct_model", protocol, 0)
    stress = statistics.holdout(model, "hidden_legal_interaction", protocol, 0)
    assert original["truth_max_legal_excess"] == 0
    assert original["holdout_status"] == "unresolved"
    assert stress["truth_max_legal_excess"] > 0.079
    assert stress["holdout_status"] == "violation"
    assert stress["holdout_physical_simulations"] == original["holdout_physical_simulations"]


def test_reproducible_seeds():
    protocol = statistics.Protocol(repeats=1, budgets=(256,))
    assert statistics.run(protocol) == statistics.run(protocol)
