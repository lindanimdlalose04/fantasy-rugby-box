"""The projection stage.

The thing being guarded against is the mistake RugbyBox made: ranking players
on a rate computed from almost no evidence. A fantasy squad built that way
fills up with fringe players who had one good afternoon.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import config as cfg  # noqa: E402


@pytest.fixture(scope="module")
def project():
    spec = importlib.util.spec_from_file_location("project", SRC / "03_project.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def projections():
    path = ROOT / cfg.PROCESSED / "projections.parquet"
    if not path.exists():
        pytest.skip("projections not built; run stages 02 and 03")
    return pd.read_parquet(path)


# --- the stabilisation estimate -------------------------------------------

def test_a_consistent_player_gives_a_low_stabilisation_point(project):
    """If records are reliable, little shrinkage is needed."""
    rng = np.random.default_rng(1)
    rows = []
    for p in range(120):
        true_rate = rng.uniform(5, 45)          # players genuinely differ
        for _ in range(10):
            rows.append({
                "player_id": f"p{p}",
                "fantasy_points": true_rate + rng.normal(0, 1),
            })
    k, half, r = project.stabilisation_appearances(pd.DataFrame(rows))
    assert r > 0.9, "near noiseless records should correlate strongly"
    assert k < 2, "and so should need almost no shrinkage"


def test_pure_noise_gives_a_high_stabilisation_point(project):
    """If records carry no signal, everything should be shrunk away."""
    rng = np.random.default_rng(2)
    rows = [
        {"player_id": f"p{p}", "fantasy_points": rng.normal(20, 15)}
        for p in range(120) for _ in range(10)
    ]
    result = project.stabilisation_appearances(pd.DataFrame(rows))
    if result is None:
        return                                   # no verdict is also honest
    k, half, r = result
    assert r < 0.35
    assert k > 10, "noise should demand heavy shrinkage"


def test_too_few_players_gives_no_estimate(project):
    rows = [
        {"player_id": f"p{p}", "fantasy_points": 20.0}
        for p in range(5) for _ in range(6)
    ]
    assert project.stabilisation_appearances(pd.DataFrame(rows)) is None


# --- the shrinkage --------------------------------------------------------

def test_shrinkage_is_a_weighted_average(projections):
    rebuilt = (
        projections.evidence * projections.mean_points
        + (1 - projections.evidence) * projections.baseline
    )
    assert rebuilt.values == pytest.approx(
        projections.points_per_appearance.values, abs=1e-9
    )


def test_evidence_rises_with_appearances(projections):
    ordered = projections.sort_values("appearances")
    assert ordered.evidence.is_monotonic_increasing
    assert ordered.evidence.between(0, 1).all()


def test_a_thin_record_is_pulled_toward_the_baseline(projections):
    thin = projections.nsmallest(10, "appearances")
    for _, player in thin.iterrows():
        to_baseline = abs(player.points_per_appearance - player.baseline)
        to_own = abs(player.mean_points - player.baseline)
        assert to_baseline <= to_own + 1e-9, player["name"]


def test_a_full_record_mostly_keeps_its_own_rate(projections):
    thick = projections.nlargest(5, "appearances")
    assert (thick.evidence > 0.6).all()


# --- availability ---------------------------------------------------------

def test_availability_is_a_share(projections):
    assert projections.availability.between(0, 1).all()


def test_projection_is_rate_times_availability(projections):
    rebuilt = projections.points_per_appearance * projections.availability
    assert rebuilt.values == pytest.approx(
        projections.projected_points.values, abs=1e-9
    )


def test_a_player_who_barely_plays_is_not_near_the_top(projections):
    """The failure this whole stage exists to prevent."""
    top = projections.nlargest(20, "projected_points")
    assert top.appearances.min() >= 8, (
        "a near-absent player has reached the top of the projection"
    )


def test_rate_and_availability_are_kept_apart(projections):
    """Collapsing them would hide a high scorer who never plays."""
    for column in ("points_per_appearance", "availability", "projected_points"):
        assert column in projections.columns
    sub = projections[
        (projections.availability < 0.3) & (projections.appearances >= 1)
    ]
    if len(sub):
        assert (sub.projected_points < sub.points_per_appearance).all()
