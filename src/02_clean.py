"""Stage B: build the appearance table, rejecting corrupted fixtures.

Produces one row per player per match inside the competition window, with a
position, reconstructed minutes, the scoring events, and what the appearance
was worth under the rules.

Two corruptions in the source are rejected here, both at fixture level
because both affect whole fixtures. Each guard reports what it caught, so a
change in the source shows up as a change in that count rather than as a
silent change in the answers. See
docs/decisions/0004-guarding-against-corrupted-source-rows.md.

Run from the project root, after stage 01:  python src\\02_clean.py
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from rules import DEFAULT, EVENTS  # noqa: E402


# --- the guards -----------------------------------------------------------

def rate_contaminated_fixtures(frame: pd.DataFrame) -> set:
    """Fixtures where a per-minute rate sits in a count column.

    A count cannot be fractional. Where one is, rates have been written where
    counts belong, and the rest of that fixture's columns are wrong too.
    """
    suspect = pd.Series(False, index=frame.index)
    for column in cfg.COUNT_COLUMNS:
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        suspect |= values.notna() & (values % 1 != 0)
    return set(frame.loc[suspect, "match_id"])


def duplication_ratio(a: pd.Series, b: pd.Series) -> float:
    """How much more often two columns match than chance alone would give.

    Raw equality rates say nothing on their own, because small count columns
    coincide constantly: a player with one try and one offload matches for no
    reason. The observed rate is therefore divided by the rate the two
    columns' own distributions would produce if they were independent. A
    ratio near one is coincidence; a large one means one column has been
    written over the other.
    """
    # Rows where both columns are zero are dropped. Most appearances record
    # zero for most events, and counting all those agreements swamps the
    # comparison: metres carried then looks as duplicated as a column that
    # genuinely has been overwritten. Excluding them separates the two
    # cleanly, leaving ordinary related statistics at 1.6 or below and the
    # corrupted columns above 7.
    both = a.notna() & b.notna() & ((a > 0) | (b > 0))
    if both.sum() < 100:
        return float("nan")
    a, b = a[both], b[both]

    observed = float((a == b).mean())
    pa = a.value_counts(normalize=True)
    pb = b.value_counts(normalize=True)
    shared = pa.index.intersection(pb.index)
    expected = float((pa[shared] * pb[shared]).sum())

    return observed / expected if expected > 0 else float("nan")


def column_integrity(frame: pd.DataFrame) -> pd.DataFrame:
    """For each column, the worst duplication ratio against any other.

    This is the check that found the corruption in the first place, so it
    runs every time rather than being a one-off investigation.
    """
    numeric = {
        c: pd.to_numeric(frame[c], errors="coerce")
        for c in cfg.INTEGRITY_COLUMNS if c in frame.columns
    }
    rows = []
    for column, values in numeric.items():
        worst_ratio, worst_partner = 0.0, ""
        for other, other_values in numeric.items():
            if other == column:
                continue
            ratio = duplication_ratio(values, other_values)
            if ratio == ratio and ratio > worst_ratio:   # skips nan
                worst_ratio, worst_partner = ratio, other
        rows.append({
            "column": column,
            "ratio": worst_ratio,
            "duplicates": worst_partner,
            "suspect": worst_ratio > cfg.SUSPECT_RATIO_LIMIT,
        })
    return pd.DataFrame(rows).set_index("column").sort_values(
        "ratio", ascending=False
    )


def cap_implausible(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clip anything above the highest believable single performance.

    A second line of defence, not a patch for the two corruptions above. If
    these start binding, something the fixture filters do not catch has
    appeared in the source.
    """
    out = frame.copy()
    bound = {}
    for column, ceiling in cfg.PLAUSIBLE_MAX.items():
        if column not in out.columns:
            continue
        values = pd.to_numeric(out[column], errors="coerce")
        hits = int((values > ceiling).sum())
        if hits:
            bound[column] = hits
        out[column] = values.clip(upper=ceiling)
    return out, bound


# --- derived measures -----------------------------------------------------

def reconstruct_minutes(frame: pd.DataFrame) -> pd.Series:
    """Minutes played, falling back to carries over the carrying rate.

    The source records minutes for roughly half of all appearances but also
    carries a per-minute carrying rate, from which minutes can be recovered.
    Validated inside the season window at a mean absolute error of 2.3
    minutes. Carried over from RugbyBox, which established that figure.
    """
    direct = pd.to_numeric(frame.get("minutes_played"), errors="coerce")
    rate = pd.to_numeric(frame.get("carries_per_minute"), errors="coerce")
    carries = pd.to_numeric(frame.get("carries"), errors="coerce")

    derived = np.where((rate > 0) & carries.notna(), carries / rate, np.nan)
    minutes = direct.fillna(pd.Series(derived, index=frame.index))
    return minutes.clip(upper=cfg.FULL_MATCH_MINUTES)


def classify_positions(frame: pd.DataFrame) -> pd.Series:
    """Each player's position, taken as the one he most often started in.

    Bench labels say how a player came on rather than where he plays, so they
    cannot classify him.
    """
    specialist = frame[~frame.position.isin(cfg.BENCH_LABELS)]
    specialist = specialist.dropna(subset=["position"])
    modal = specialist.groupby("player_id")["position"].agg(
        lambda s: s.mode().iloc[0]
    )
    return modal.map(cfg.ROLE_MAP)


def main() -> None:
    os.makedirs(cfg.PROCESSED, exist_ok=True)

    raw = pd.read_parquet(f"{cfg.RAW}/player_appearances_raw.parquet")
    manifest = json.load(open(cfg.MANIFEST)) if os.path.exists(cfg.MANIFEST) else {}
    print(f"data as of: {manifest.get('data_as_of', 'unknown')}")

    dates = pd.to_datetime(raw.game_date, format="%Y%m%d")
    window = raw[
        (dates >= cfg.SEASON_START)
        & (dates <= cfg.SEASON_END)
        & (raw.competition == cfg.COMPETITION)
    ].copy()
    window["match_date"] = pd.to_datetime(window.game_date, format="%Y%m%d")

    fixtures_before = window.match_id.nunique()
    rows_before = len(window)
    print(f"appearances in {cfg.COMPETITION}: {rows_before:,} "
          f"across {fixtures_before} fixtures")
    print()

    # --- guard one: fixtures holding rates where counts belong ------------
    print("--- rejecting corrupted fixtures ---")
    rates = rate_contaminated_fixtures(window)
    lost = int(window.match_id.isin(rates).sum())
    print(f"  {'rates in count columns':<44} {len(rates):>3} fixtures, "
          f"{lost:>5} appearances")

    clean = window[~window.match_id.isin(rates)].copy()
    print(f"  {'kept':<44} {clean.match_id.nunique():>3} fixtures, "
          f"{len(clean):>5} appearances "
          f"({len(clean) / rows_before:.1%})")
    print()

    # --- guard two: columns written over one another ----------------------
    print("--- column integrity ---")
    print("  how much more often than chance does each column exactly match")
    print("  another? Above "
          f"{cfg.SUSPECT_RATIO_LIMIT:.1f} means one has been written over the other.")
    print()
    integrity = column_integrity(clean)
    for column, row in integrity.iterrows():
        scored = column in DEFAULT.points
        mark = "SUSPECT" if row.suspect else "ok"
        used = "scored" if scored else "not scored"
        print(f"    {column:<20} {row.ratio:>5.2f}  vs {row.duplicates:<18}"
              f" {mark:<8} {used}")

    scored_and_suspect = [
        c for c, r in integrity.iterrows() if r.suspect and c in DEFAULT.points
    ]
    if scored_and_suspect:
        raise SystemExit(
            f"\n  STOPPING. These columns are scored but look corrupted: "
            f"{scored_and_suspect}.\n"
            f"  Points would be awarded for data that records nothing. Either "
            f"drop them from\n  the rules or establish that the source has been "
            f"fixed."
        )

    expected = [c for c in cfg.KNOWN_CORRUPTED if c in integrity.index]
    still_bad = [c for c in expected if integrity.loc[c, "suspect"]]
    if len(still_bad) < len(expected):
        print(f"\n  NOTE: {sorted(set(expected) - set(still_bad))} no longer look "
              f"corrupted.\n  The source may have been fixed. Worth re-checking "
              f"whether they can be scored again.")
    print()

    clean, bound = cap_implausible(clean)
    if bound:
        print(f"  plausibility caps bound: {bound}")
        print("    each of these was above the highest believable single")
        print("    performance and has been clipped. Worth tracing: a cap")
        print("    that starts binding often means a new corruption.")
    else:
        print("  plausibility caps: none bound")
    print()

    # --- derive -----------------------------------------------------------
    clean["minutes"] = reconstruct_minutes(clean)
    roles = classify_positions(clean)
    clean["role"] = clean.player_id.map(roles)

    for event in EVENTS:
        clean[event] = pd.to_numeric(clean[event], errors="coerce").fillna(0.0)
    clean["fantasy_points"] = DEFAULT.score(clean)

    keep = [
        "player_id", "name", "team_id", "team", "match_id", "match_date",
        "role", "minutes", *EVENTS, "fantasy_points",
    ]
    appearances = clean[keep].sort_values(["match_date", "name"])
    appearances.to_parquet(f"{cfg.PROCESSED}/appearances.parquet", index=False)

    # --- one row per player -----------------------------------------------
    players = appearances.dropna(subset=["role"]).groupby("player_id").agg(
        name=("name", "first"),
        team_id=("team_id", "last"),
        team=("team", "last"),
        role=("role", "first"),
        appearances=("match_id", "nunique"),
        minutes=("minutes", "sum"),
        total_points=("fantasy_points", "sum"),
        mean_points=("fantasy_points", "mean"),
        sd_points=("fantasy_points", "std"),
    ).reset_index()
    players["selectable"] = players.appearances >= cfg.MIN_APPEARANCES
    players.to_parquet(f"{cfg.PROCESSED}/players.parquet", index=False)

    # --- checkpoint --------------------------------------------------------
    print("--- checkpoint ---")
    print(f"appearances kept:     {len(appearances):,}")
    print(f"  with a position:    {appearances.role.notna().sum():,}")
    print(f"  minutes missing:    {appearances.minutes.isna().sum()}")
    print(f"fixtures kept:        {appearances.match_id.nunique()}")
    print(f"players:              {len(players)}")
    print(f"  selectable ({cfg.MIN_APPEARANCES}+ apps): {players.selectable.sum()}")
    print()
    print("points per appearance by position:")
    print(DEFAULT.balance(appearances.dropna(subset=["role"])).round(2).to_string())
    print()
    print("highest scoring players this season:")
    cols = ["name", "role", "appearances", "minutes", "total_points", "mean_points"]
    print(players.nlargest(8, "total_points")[cols].round(1).to_string(index=False))
    print()
    print("best single appearances:")
    print(appearances.nlargest(5, "fantasy_points")[
        ["name", "role", "fantasy_points", "tries", "tackles_made", "metres_carried"]
    ].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
