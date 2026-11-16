"""The cleaning stage, and the guards that decide what the data is worth.

The duplication check is the important one. It is what found that two
columns in the source hold copies of a third, and it has to keep working:
flagging a column that has been overwritten, and staying quiet about
ordinary statistics that merely happen to agree sometimes.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import config as cfg  # noqa: E402


@pytest.fixture(scope="module")
def clean():
    spec = importlib.util.spec_from_file_location("clean", SRC / "02_clean.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the duplication check ------------------------------------------------

def test_a_copied_column_is_caught(clean):
    """The corruption actually present in the source."""
    rng = np.random.default_rng(1)
    carries = pd.Series(rng.integers(0, 20, 2000).astype(float))
    copied = carries.copy()
    assert clean.duplication_ratio(carries, copied) > cfg.SUSPECT_RATIO_LIMIT


def test_a_partly_copied_column_is_still_caught(clean):
    """Only some fixtures were affected, so a partial copy must register."""
    rng = np.random.default_rng(2)
    carries = pd.Series(rng.integers(0, 20, 2000).astype(float))
    other = pd.Series(rng.integers(0, 20, 2000).astype(float))
    half = other.copy()
    half[:1000] = carries[:1000]          # half the rows overwritten
    assert clean.duplication_ratio(carries, half) > cfg.SUSPECT_RATIO_LIMIT


def test_independent_columns_are_not_flagged(clean):
    rng = np.random.default_rng(3)
    a = pd.Series(rng.integers(0, 20, 3000).astype(float))
    b = pd.Series(rng.integers(0, 20, 3000).astype(float))
    ratio = clean.duplication_ratio(a, b)
    assert ratio == pytest.approx(1.0, abs=0.35)
    assert ratio < cfg.SUSPECT_RATIO_LIMIT


def test_small_counts_agreeing_by_chance_are_not_flagged(clean):
    """Tries of 1 equals offloads of 1 constantly, and means nothing.

    This is the false positive the check has to avoid: both columns are
    mostly zero or one, so they agree often without either being a copy.
    """
    rng = np.random.default_rng(4)
    tries = pd.Series(rng.choice([0, 0, 0, 1, 1, 2], 3000).astype(float))
    offloads = pd.Series(rng.choice([0, 0, 0, 1, 1, 2], 3000).astype(float))
    assert clean.duplication_ratio(tries, offloads) < cfg.SUSPECT_RATIO_LIMIT


def test_rows_where_both_are_zero_do_not_count(clean):
    """Most appearances record zero for most events.

    Counting those agreements swamps the comparison and made a clean column
    look as duplicated as a corrupted one.
    """
    rng = np.random.default_rng(5)
    a = pd.Series(rng.integers(0, 12, 1200).astype(float))
    b = pd.Series(rng.integers(0, 12, 1200).astype(float))
    padding = pd.Series(np.zeros(4000))

    without = clean.duplication_ratio(a, b)
    with_zeros = clean.duplication_ratio(
        pd.concat([a, padding], ignore_index=True),
        pd.concat([b, padding], ignore_index=True),
    )
    assert without == pytest.approx(with_zeros, abs=0.4), (
        "adding all-zero rows should not change the verdict"
    )


def test_too_little_data_gives_no_verdict(clean):
    a = pd.Series([1.0, 2.0, 3.0])
    assert np.isnan(clean.duplication_ratio(a, a))


# --- rate contamination ---------------------------------------------------

def test_a_fraction_in_a_count_column_condemns_the_fixture(clean):
    frame = pd.DataFrame({
        "match_id": ["a", "a", "b", "b"],
        "tackles_made": [8.0, 0.08, 11.0, 6.0],
        "tries": [0.0, 1.0, 0.0, 0.0],
    })
    assert clean.rate_contaminated_fixtures(frame) == {"a"}


def test_whole_numbers_are_left_alone(clean):
    frame = pd.DataFrame({
        "match_id": ["a", "a", "b"],
        "tackles_made": [8.0, 12.0, 11.0],
        "tries": [0.0, 1.0, 0.0],
    })
    assert clean.rate_contaminated_fixtures(frame) == set()


def test_missing_values_are_not_mistaken_for_fractions(clean):
    frame = pd.DataFrame({
        "match_id": ["a", "a"],
        "tackles_made": [np.nan, 9.0],
        "tries": [1.0, 0.0],
    })
    assert clean.rate_contaminated_fixtures(frame) == set()


# --- plausibility caps ----------------------------------------------------

def test_impossible_values_are_clipped_and_reported(clean):
    frame = pd.DataFrame({
        "tries": [1.0, 99.0],
        "red_cards": [0.0, 2.0],
    })
    out, bound = clean.cap_implausible(frame)
    assert out.tries.max() == cfg.PLAUSIBLE_MAX["tries"]
    assert out.red_cards.max() == 1
    assert bound == {"tries": 1, "red_cards": 1}


def test_believable_values_pass_through_untouched(clean):
    frame = pd.DataFrame({"tries": [0.0, 1.0, 3.0], "tackles_made": [5.0, 20.0, 0.0]})
    out, bound = clean.cap_implausible(frame)
    assert bound == {}
    assert out.tries.tolist() == [0.0, 1.0, 3.0]


def test_a_sent_off_player_cannot_be_sent_off_twice():
    assert cfg.PLAUSIBLE_MAX["red_cards"] == 1


# --- derived measures -----------------------------------------------------

def test_recorded_minutes_are_preferred_to_derived(clean):
    frame = pd.DataFrame({
        "minutes_played": [60.0, np.nan],
        "carries_per_minute": [0.5, 0.2],
        "carries": [5.0, 10.0],
    })
    out = clean.reconstruct_minutes(frame)
    assert out.iloc[0] == 60.0
    assert out.iloc[1] == 50.0


def test_minutes_never_exceed_a_full_match(clean):
    frame = pd.DataFrame({
        "minutes_played": [np.nan],
        "carries_per_minute": [0.01],
        "carries": [20.0],
    })
    assert clean.reconstruct_minutes(frame).iloc[0] == cfg.FULL_MATCH_MINUTES


def test_bench_labels_do_not_classify_a_player(clean):
    """Coming on as a replacement says nothing about where someone plays."""
    frame = pd.DataFrame({
        "player_id": ["p1"] * 4,
        "position": ["front_row_sub", "front_row_sub", "hooker", "default"],
    })
    assert clean.classify_positions(frame).loc["p1"] == "hooker"


def test_a_player_is_classified_by_his_most_common_position(clean):
    frame = pd.DataFrame({
        "player_id": ["p1"] * 3,
        "position": ["flanker", "flanker", "lock"],
    })
    assert clean.classify_positions(frame).loc["p1"] == "loose_forward"


# --- the scored columns must be trustworthy -------------------------------

def test_no_known_corrupted_column_is_scored():
    """The whole point of the investigation that produced these guards."""
    from rules import DEFAULT
    for column in cfg.KNOWN_CORRUPTED:
        assert column not in DEFAULT.points, (
            f"{column} is corrupted in the source and must not be scored"
        )
