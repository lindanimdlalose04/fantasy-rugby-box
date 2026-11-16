"""Stage D: put a price on every player.

This project has its own scoring system, so there is no published price list
to read. Prices are modelled from projected points. See decision 0002.

The shape matters more than the scale. If price rose in step with points, the
best players would be affordable and the budget would never bind, leaving the
optimiser to rank rather than choose. The mapping is therefore convex: each
extra projected point costs more than the last, so a squad of stars is out of
reach and the real decision is where to spend.

Two things are checked here rather than assumed.

  the budget binds      the best squad the quotas allow, priced without
                        regard to budget, must cost more than the budget
  prices are not        projected points are what the optimiser maximises
  circular              and also what sets the price, so an error in a
                        projection moves both together. The spread of value
                        for money across players is what stops that
                        cancelling out, and it is reported.

Run from the project root, after stage 03:  python src\\04_price.py
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from rules import DEFAULT  # noqa: E402


def price_from(projection: pd.Series) -> pd.Series:
    """A convex mapping from projected points to price."""
    lo, hi = projection.min(), projection.max()
    if hi <= lo:
        return pd.Series(cfg.PRICE_MIN, index=projection.index)

    scaled = ((projection - lo) / (hi - lo)) ** cfg.PRICE_CURVE
    return cfg.PRICE_MIN + (cfg.PRICE_MAX - cfg.PRICE_MIN) * scaled


def best_affordable_ignoring_budget(players: pd.DataFrame, rules) -> pd.DataFrame:
    """The strongest squad the quotas allow, with no regard to cost.

    Not the answer to anything, but it is what the budget has to be measured
    against: if this costs less than the budget, the budget is decoration.
    """
    picks = [
        group.nlargest(rules.quota[role], "projected_points")
        for role, group in players.groupby("role")
        if role in rules.quota
    ]
    return pd.concat(picks)


def cheapest_legal(players: pd.DataFrame, rules) -> pd.DataFrame:
    picks = [
        group.nsmallest(rules.quota[role], "price")
        for role, group in players.groupby("role")
        if role in rules.quota
    ]
    return pd.concat(picks)


def main() -> None:
    rules = DEFAULT
    projections = pd.read_parquet(f"{cfg.PROCESSED}/projections.parquet")

    selectable = projections[projections.selectable].copy()
    selectable["price"] = price_from(selectable.projected_points)
    selectable["value_for_money"] = (
        selectable.projected_points / selectable.price
    )

    missing = [r for r in rules.quota if (selectable.role == r).sum() < rules.quota[r]]
    if missing:
        raise SystemExit(
            f"not enough players to fill {missing}; the squad cannot be built"
        )

    selectable.to_parquet(f"{cfg.PROCESSED}/priced.parquet", index=False)

    # --- does the budget bind? --------------------------------------------
    strongest = best_affordable_ignoring_budget(selectable, rules)
    cheapest = cheapest_legal(selectable, rules)

    print("--- is the budget a real constraint? ---")
    print(f"budget                            {rules.budget:>8.1f}")
    print(f"cheapest legal squad              {cheapest.price.sum():>8.1f}")
    print(f"strongest squad, ignoring cost    {strongest.price.sum():>8.1f}")

    binds = cheapest.price.sum() <= rules.budget < strongest.price.sum()
    if not binds:
        raise SystemExit(
            "\n  The budget does not sit between the two. Either every squad is "
            "affordable,\n  in which case the optimiser has nothing to decide, or "
            "none is, in which case\n  there is no answer. Adjust PRICE_CURVE or "
            "the budget in config.py."
        )
    headroom = strongest.price.sum() - rules.budget
    print(f"  the budget binds: the strongest squad is {headroom:.1f} over it, "
          f"{headroom / rules.budget:.0%} of the budget")
    print()

    # --- is value for money flat? ------------------------------------------
    # Price comes from the same projection the optimiser maximises, so the two
    # could cancel and leave every player equally good value. If that happened
    # the optimiser would be choosing at random inside the budget.
    vfm = selectable.value_for_money
    print("--- do prices tell the optimiser anything? ---")
    print(f"points per unit of price: {vfm.min():.2f} to {vfm.max():.2f}, "
          f"spread {vfm.std() / vfm.mean():.2f} of the mean")
    print("  a convex price curve makes cheap players better value, which is")
    print("  what gives the optimiser a reason to prefer one squad over another.")
    print()
    print("best value for money:")
    cols = ["name", "role", "appearances", "projected_points", "price",
            "value_for_money"]
    print(selectable.nlargest(8, "value_for_money")[cols].round(2).to_string(index=False))
    print()
    print("most expensive:")
    print(selectable.nlargest(8, "price")[cols].round(2).to_string(index=False))
    print()
    print("price by position:")
    summary = selectable.groupby("role").price.agg(
        players="size", cheapest="min", median="median", dearest="max"
    )
    print(summary.round(2).to_string())


if __name__ == "__main__":
    main()
