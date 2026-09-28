from wowfs.reporting.report import success_prefix

def test_success_prefix_does_not_reset_and_unresolved_is_distinct():
    rows = [{"round": 1, "status": "pass"}, {"round": 2, "status": "unresolved"},
            {"round": 3, "status": "pass"}, {"round": 4, "status": "violation"}, {"round": 5, "status": "pass"}]
    assert success_prefix(rows) == (1, 3)

def test_missing_round_cannot_silently_count_as_success():
    assert success_prefix([{"round": 1, "status": "pass"}, {"round": 3, "status": "pass"}]) == (1, 1)
