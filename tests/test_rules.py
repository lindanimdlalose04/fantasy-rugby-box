"""The rules object.

Two jobs. Reject a ruleset that could not describe a real game, and apply the
scoring correctly. The second matters most, because a scoring error is
invisible: every number downstream still looks plausible.
"""

import pandas as pd
import pytest

import rules
from rules import DEFAULT, EVENTS, POSITIONS, Rules


def a_ruleset(**overrides):
    """A valid minimal ruleset, with fields overridden for each test."""
    base = dict(
        name="test",
        points={"tries": 10.0},
        squad_size=3,
        quota={"prop": 1, "hooker": 1, "lock": 1},
    )
    base.update(overrides)
    return Rules(**base)


# --- validation -----------------------------------------------------------

def test_quotas_must_add_up_to_the_squad_size():
    with pytest.raises(ValueError, match="quotas add to"):
        a_ruleset(quota={"prop": 1, "hooker": 1})


def test_unknown_scoring_events_are_rejected():
    with pytest.raises(ValueError, match="unknown scoring events"):
        a_ruleset(points={"scrums_won": 5.0})


def test_unknown_positions_are_rejected():
    with pytest.raises(ValueError, match="unknown positions"):
        a_ruleset(quota={"prop": 1, "hooker": 1, "winger": 1})


@pytest.mark.parametrize("bad", [
    {"club_cap": 0},
    {"budget": 0},
    {"budget": -5},
    {"captain_multiplier": 0.5},
])
def test_impossible_settings_are_rejected(bad):
    with pytest.raises(ValueError):
        a_ruleset(**bad)


def test_a_valid_ruleset_is_accepted():
    r = a_ruleset()
    assert r.squad_size == sum(r.quota.values())


# --- the default ruleset --------------------------------------------------

def test_the_default_is_a_legal_rugby_fifteen():
    assert DEFAULT.squad_size == 15
    assert sum(DEFAULT.quota.values()) == 15
    assert set(DEFAULT.quota) == set(POSITIONS), "every position must be covered"
    forwards = sum(n for p, n in DEFAULT.quota.items() if p in rules.FORWARDS)
    assert forwards == 8, "a rugby XV fields eight forwards"
    assert DEFAULT.squad_size - forwards == 7, "and seven backs"


def test_the_default_rewards_scoring_more_than_anything_else():
    assert DEFAULT.points["tries"] > DEFAULT.points["try_assists"]
    assert DEFAULT.points["try_assists"] > DEFAULT.points["turnovers_won"]


def test_indiscipline_costs_points():
    for event in ("penalties_conceded", "yellow_cards", "red_cards"):
        assert DEFAULT.points[event] < 0, event
    assert DEFAULT.points["red_cards"] < DEFAULT.points["yellow_cards"]


def test_the_default_is_immutable():
    """Rules are shared; one caller must not be able to change them."""
    with pytest.raises(Exception):
        DEFAULT.budget = 200.0


# --- scoring --------------------------------------------------------------

def test_scoring_adds_up_by_hand():
    """One appearance, worked through by hand against the default values."""
    row = pd.DataFrame([{e: 0.0 for e in EVENTS}])
    row.loc[0, "tries"] = 2
    row.loc[0, "tackles_made"] = 10
    row.loc[0, "metres_carried"] = 50
    row.loc[0, "yellow_cards"] = 1

    #  2 appearance + 2*10 tries + 10*1.5 tackles + 50*0.1 metres - 5 card
    expected = 2 + 20 + 15 + 5 - 5
    assert DEFAULT.score(row).iloc[0] == pytest.approx(expected)


def test_a_blank_appearance_is_worth_only_the_appearance_points():
    row = pd.DataFrame([{e: 0.0 for e in EVENTS}])
    assert DEFAULT.score(row).iloc[0] == pytest.approx(DEFAULT.appearance_points)


def test_missing_event_counts_are_treated_as_zero():
    row = pd.DataFrame([{e: 0.0 for e in EVENTS}])
    row.loc[0, "tries"] = None
    row.loc[0, "tackles_made"] = 4
    assert DEFAULT.score(row).iloc[0] == pytest.approx(2 + 4 * 1.5)


def test_a_missing_column_is_an_error_not_a_silent_zero():
    """A scoring rule that quietly stops applying is the worst failure mode."""
    row = pd.DataFrame([{e: 0.0 for e in EVENTS}]).drop(columns=["turnovers_won"])
    with pytest.raises(KeyError, match="turnovers_won"):
        DEFAULT.score(row)


def test_scoring_is_additive_across_appearances():
    rows = pd.DataFrame([{e: 0.0 for e in EVENTS} for _ in range(3)])
    rows["tries"] = [1, 0, 2]
    scored = DEFAULT.score(rows)
    assert len(scored) == 3
    assert scored.sum() == pytest.approx(3 * 2 + 3 * 10)


def test_a_ruleset_scoring_nothing_still_works():
    r = a_ruleset(points={}, appearance_points=1.0)
    rows = pd.DataFrame([{e: 5.0 for e in EVENTS} for _ in range(2)])
    assert list(r.score(rows)) == [1.0, 1.0]


# --- balance --------------------------------------------------------------

def test_balance_reports_every_position_present():
    rows = []
    for position in POSITIONS:
        for _ in range(3):
            row = {e: 1.0 for e in EVENTS}
            row["role"] = position
            rows.append(row)
    out = DEFAULT.balance(pd.DataFrame(rows))

    assert set(out.index) == set(POSITIONS)
    assert (out.appearances == 3).all()
    assert out["mean"].notna().all()
