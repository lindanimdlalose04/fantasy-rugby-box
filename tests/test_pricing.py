"""The pricing stage.

Prices are modelled from the same projections the optimiser maximises, so
the two could cancel and leave every player equally good value. These tests
pin the properties that stop that: the curve is convex, the budget genuinely
binds, and value for money varies enough to choose on.
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
from rules import DEFAULT  # noqa: E402


@pytest.fixture(scope="module")
def pricing():
    spec = importlib.util.spec_from_file_location("price", SRC / "04_price.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def priced():
    path = ROOT / cfg.PROCESSED / "priced.parquet"
    if not path.exists():
        pytest.skip("prices not built; run stages 02 to 04")
    return pd.read_parquet(path)


# --- the curve ------------------------------------------------------------

def test_price_rises_with_projected_points(pricing):
    projection = pd.Series([1.0, 5.0, 12.0, 30.0])
    price = pricing.price_from(projection)
    assert price.is_monotonic_increasing


def test_price_stays_within_its_bounds(pricing):
    projection = pd.Series(np.linspace(0, 40, 50))
    price = pricing.price_from(projection)
    assert price.min() == pytest.approx(cfg.PRICE_MIN)
    assert price.max() == pytest.approx(cfg.PRICE_MAX)


def test_the_curve_is_convex(pricing):
    """Each extra projected point must cost more than the last.

    A straight line would let the optimiser buy the best players and leave
    the budget doing nothing.
    """
    projection = pd.Series(np.linspace(0, 30, 40))
    price = pricing.price_from(projection)
    steps = np.diff(price.to_numpy())
    assert (np.diff(steps) > -1e-9).all(), "the price curve bends the wrong way"
    assert steps[-1] > steps[0] * 2, "the curve is barely convex"


def test_identical_projections_price_the_same(pricing):
    flat = pd.Series([7.0, 7.0, 7.0])
    assert pricing.price_from(flat).nunique() == 1


# --- the budget -----------------------------------------------------------

def test_the_cheapest_legal_squad_is_affordable(pricing, priced):
    cheapest = pricing.cheapest_legal(priced, DEFAULT)
    assert len(cheapest) == DEFAULT.squad_size
    assert cheapest.price.sum() <= DEFAULT.budget, (
        "no legal squad fits the budget, so there is no answer to find"
    )


def test_the_strongest_squad_is_not_affordable(pricing, priced):
    """If it were, the budget would be decoration."""
    strongest = pricing.best_affordable_ignoring_budget(priced, DEFAULT)
    assert len(strongest) == DEFAULT.squad_size
    assert strongest.price.sum() > DEFAULT.budget


def test_the_budget_leaves_room_to_choose(pricing, priced):
    """Somewhere between forced and unconstrained is where the decision is."""
    cheapest = pricing.cheapest_legal(priced, DEFAULT).price.sum()
    assert cheapest < DEFAULT.budget * 0.9, (
        "fielding a legal squad already eats the budget, leaving nothing to decide"
    )


def test_every_position_can_be_filled(priced):
    for role, needed in DEFAULT.quota.items():
        assert (priced.role == role).sum() >= needed, role


# --- the circularity ------------------------------------------------------

def test_value_for_money_is_not_flat(priced):
    """Price and projection must not simply cancel.

    If every player were the same value for money the optimiser would be
    picking at random inside the budget, and the model would mean nothing.
    """
    vfm = priced.projected_points / priced.price
    assert vfm.std() / vfm.mean() > 0.15


def test_the_best_value_is_not_the_most_expensive(priced):
    """A convex curve should make the premium players worse value."""
    vfm = (priced.projected_points / priced.price)
    dearest = priced.nlargest(10, "price").index
    assert vfm.loc[dearest].mean() < vfm.max(), (
        "the most expensive players are also the best value, "
        "so the budget is not a real trade-off"
    )


def test_prices_recorded_match_the_curve(pricing, priced):
    rebuilt = pricing.price_from(priced.projected_points)
    assert rebuilt.values == pytest.approx(priced.price.values, abs=1e-9)
