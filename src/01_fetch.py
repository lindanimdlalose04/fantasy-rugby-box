"""Stage A: fetch every player who featured in the competition.

The store lists no clubs per competition, so they are discovered from one
club's own fixture list: everyone it met in the competition inside the
season window, plus itself. Each club's team file names the players on every
team sheet, and the union of those is who to fetch.

Individual player files are cached, so a re-run only fetches what is missing.
A full run from cold takes roughly fifteen minutes, because the host
throttles sustained sequential access.

The date of the fetch is written to a manifest. Results depend on data that
is updated outside this project, so a figure without its data date cannot be
reproduced.

Run from the project root:  python src\\01_fetch.py
"""

import json
import os
import sys
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from rb import get  # noqa: E402


def cached_player(player_id: str) -> pd.DataFrame:
    """One player's match records, read from the local cache if present."""
    path = f"{cfg.PLAYER_CACHE}/{player_id}.parquet"
    if os.path.exists(path):
        return pd.read_parquet(path)
    frame = get("player", player_id)
    frame.to_parquet(path)
    return frame


def in_window(frame: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(frame.game_date, format="%Y%m%d")
    return frame[(dates >= cfg.SEASON_START) & (dates <= cfg.SEASON_END)]


def discover_clubs() -> list[str]:
    """The clubs in the competition, from the seed club's fixture list."""
    seed = get("team", cfg.SEED_CLUB_ID)
    fixtures = in_window(seed)
    print(f"  seed club fixtures in window: {len(fixtures)}")

    # Which of those fixtures were in the competition. The team file does not
    # record the competition, so it is read off the seed club's own player
    # rows, which do.
    pool = pd.concat(
        [cached_player(p) for p in sorted({p for s in fixtures["players"] for p in s})],
        ignore_index=True,
    )
    league_matches = set(
        pool[
            (pool.competition == cfg.COMPETITION)
            & (pool.match_id.isin(set(fixtures.match_id)))
        ].match_id
    )
    print(f"  of which {cfg.COMPETITION}: {len(league_matches)}")

    opponents = fixtures[
        fixtures.match_id.isin(league_matches)
    ].team_vs_id.dropna().unique()
    return sorted({cfg.SEED_CLUB_ID, *opponents})


def main() -> None:
    os.makedirs(cfg.PLAYER_CACHE, exist_ok=True)

    print(f"discovering the clubs in {cfg.COMPETITION}...")
    clubs = discover_clubs()
    print(f"  clubs found: {len(clubs)}")

    print("collecting team sheets...")
    everyone = set()
    for club_id in clubs:
        try:
            sheets = in_window(get("team", club_id))
        except Exception as exc:
            print(f"  WARN could not read club {club_id}: {type(exc).__name__}")
            continue
        before = len(everyone)
        for sheet in sheets["players"]:
            everyone.update(list(sheet))
        print(f"  {club_id}: {len(sheets):>2} fixtures, "
              f"+{len(everyone) - before} new players")

    everyone = sorted(everyone)
    cached = sum(
        os.path.exists(f"{cfg.PLAYER_CACHE}/{p}.parquet") for p in everyone
    )
    print(f"players to fetch: {len(everyone)}  ({cached} already cached)")

    frames, failed = [], []
    for n, player_id in enumerate(everyone, 1):
        try:
            frames.append(cached_player(player_id))
        except Exception as exc:
            failed.append((player_id, type(exc).__name__))
        if n % 50 == 0:
            print(f"  {n}/{len(everyone)}")

    appearances = pd.concat(frames, ignore_index=True)
    os.makedirs(cfg.RAW, exist_ok=True)
    appearances.to_parquet(f"{cfg.RAW}/player_appearances_raw.parquet")

    manifest = {
        "data_as_of": date.today().isoformat(),
        "competition": cfg.COMPETITION,
        "season_start": cfg.SEASON_START,
        "season_end": cfg.SEASON_END,
        "clubs": clubs,
        "players_fetched": len(frames),
        "players_failed": [p for p, _ in failed],
        "rows": int(len(appearances)),
    }
    json.dump(manifest, open(cfg.MANIFEST, "w"), indent=2)

    print()
    print("--- checkpoint ---")
    print(f"players fetched:  {len(frames)}, failed {len(failed)}")
    if failed:
        print(f"  failures: {failed[:10]}")

    window = in_window(appearances)
    league = window[window.competition == cfg.COMPETITION]
    print(f"rows fetched:     {len(appearances):,}")
    print(f"  in window:      {len(window):,}")
    print(f"  in competition: {len(league):,}")
    print(f"distinct players: {league.player_id.nunique()}")
    print(f"distinct clubs:   {league.team_id.nunique()}")
    print(f"distinct fixtures:{league.match_id.nunique()}")
    print(f"data as of:       {manifest['data_as_of']}")


if __name__ == "__main__":
    main()
