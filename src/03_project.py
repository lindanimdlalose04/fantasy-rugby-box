"""Stage C: what each player is expected to score in the next gameweek.

Three parts, kept separate because they answer different questions and fail
in different ways.

  points per appearance   how much he scores when he plays, shrunk toward
                          his position's baseline by how much evidence
                          stands behind it
  availability            how often he plays at all, as a share of his
                          club's fixtures
  projected points        the two multiplied: what he is worth to a squad
                          over a gameweek

Separating them matters. A replacement who scores well in twenty minutes has
a high rate and low availability, and a fantasy squad full of such players
scores nothing. Collapsing the two into one number hides that.

The shrinkage is the lesson from RugbyBox. A mean over two appearances is
mostly noise, and ranking on it puts fringe players top. See docs/lineage.md.

Run from the project root, after stage 02:  python src\\03_project.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402


def stabilisation_appearances(appearances: pd.DataFrame):
    """Appearances at which a player's scoring rate is half signal, half noise.

    Each player's appearances are split at random into two halves and the
    mean points of each computed. The correlation between the halves across
    players is how much of a half-record is real. Rearranging

        reliability(n) = n / (n + K)

    at the mean half-record length gives K.

    Returns (K, mean half length, correlation), or None if the estimate
    cannot be made.
    """
    counts = appearances.groupby("player_id").size()
    eligible = counts[counts >= 4].index
    usable = appearances[appearances.player_id.isin(eligible)]
    if usable.player_id.nunique() < 30:
        return None

    rng = np.random.default_rng(cfg.SPLIT_SEED)
    correlations, lengths = [], []

    for _ in range(cfg.SPLIT_REPEATS):
        side = rng.integers(0, 2, size=len(usable))
        halves = [
            usable[side == s].groupby("player_id").fantasy_points.agg(["mean", "size"])
            for s in (0, 1)
        ]
        a, b = halves
        shared = a.index.intersection(b.index)
        if len(shared) < 30:
            continue
        if a.loc[shared, "mean"].std() == 0 or b.loc[shared, "mean"].std() == 0:
            continue

        correlations.append(
            float(np.corrcoef(a.loc[shared, "mean"], b.loc[shared, "mean"])[0, 1])
        )
        lengths.append(
            float(pd.concat([a.loc[shared, "size"], b.loc[shared, "size"]]).mean())
        )

    if not correlations:
        return None

    r = float(np.mean(correlations))
    n = float(np.mean(lengths))
    if not 0 < r < 1:
        return None
    return n * (1 - r) / r, n, r


def main() -> None:
    appearances = pd.read_parquet(f"{cfg.PROCESSED}/appearances.parquet")
    players = pd.read_parquet(f"{cfg.PROCESSED}/players.parquet")
    appearances = appearances.dropna(subset=["role"])

    # --- how much evidence is a record worth? -----------------------------
    k = cfg.STABILISATION_APPEARANCES
    note = f"assumed {k}"
    if cfg.ESTIMATE_STABILISATION:
        estimate = stabilisation_appearances(appearances)
        if estimate is not None:
            k, half, r = estimate
            note = (f"estimated {k:.1f} from split-half reliability {r:.2f} "
                    f"at {half:.1f} appearances a half")
    print(f"stabilisation point: {note}")

    # --- the baseline a thin record is shrunk toward ----------------------
    established = players[players.appearances >= cfg.MIN_APPEARANCES_FOR_BASELINE]
    baseline = established.groupby("role").mean_points.mean()
    print(f"position baselines taken from {len(established)} players with "
          f"{cfg.MIN_APPEARANCES_FOR_BASELINE}+ appearances")

    out = players.copy()
    out["baseline"] = out.role.map(baseline)
    # A position with nobody established falls back to the overall mean.
    out["baseline"] = out.baseline.fillna(established.mean_points.mean())

    out["evidence"] = out.appearances / (out.appearances + k)
    out["points_per_appearance"] = (
        out.evidence * out.mean_points + (1 - out.evidence) * out.baseline
    )

    # --- how often does he actually play? ---------------------------------
    # Counted against his club's fixtures, not the competition's, because
    # clubs have played different numbers of games.
    club_fixtures = (
        appearances.groupby("team_id").match_id.nunique().rename("club_fixtures")
    )
    out = out.merge(club_fixtures, left_on="team_id", right_index=True, how="left")
    out["availability"] = (out.appearances / out.club_fixtures).clip(upper=1.0)

    out["projected_points"] = out.points_per_appearance * out.availability

    out.to_parquet(f"{cfg.PROCESSED}/projections.parquet", index=False)

    # --- checkpoint --------------------------------------------------------
    print()
    print("--- checkpoint ---")
    print(f"players projected: {len(out)}")
    print(f"projected points:  {out.projected_points.min():.1f} "
          f"to {out.projected_points.max():.1f}")
    print()
    print("does the projection still reward players who barely play?")
    for label, column in [
        ("raw mean points per appearance", "mean_points"),
        ("after shrinkage", "points_per_appearance"),
        ("times availability (used downstream)", "projected_points"),
    ]:
        r = out.appearances.corr(out[column])
        print(f"  {label:<38} corr with appearances {r:+.3f}")
    print()
    print("baseline for each position:")
    print(baseline.round(1).sort_values().to_string())
    print()
    cols = ["name", "role", "appearances", "mean_points", "evidence",
            "points_per_appearance", "availability", "projected_points"]
    print("highest projected:")
    print(out.nlargest(10, "projected_points")[cols].round(2).to_string(index=False))
    print()
    print("thinnest evidence, and where the shrinkage put them:")
    print(out.nsmallest(5, "appearances")[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
