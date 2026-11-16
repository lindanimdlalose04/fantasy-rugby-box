"""The scoring system and squad rules, in one place.

Nothing downstream may hard-code a point value or a squad limit. Everything
reads from a Rules object, so pointing this project at a different fantasy
game later is a matter of writing another Rules instance rather than hunting
through the projection and the optimiser. See
docs/decisions/0003-which-scoring-system-to-target.md.

The default ruleset is this project's own, not any published game's. Its
point values were chosen against the real distribution of events in the
league, so that every position is worth picking. See `balance` below and
docs/method.md.
"""

from dataclasses import dataclass, field
from typing import Mapping

import pandas as pd

# The eight positional groups, matching the role classification used when
# cleaning appearances.
POSITIONS = (
    "prop", "hooker", "lock", "loose_forward",
    "scrum_half", "fly_half", "centre", "back_three",
)

FORWARDS = frozenset({"prop", "hooker", "lock", "loose_forward"})

# Scoring events, and the column in the cleaned appearance table that counts
# each one. Every key here must exist as a column before scoring.
EVENTS = (
    "tries", "try_assists", "conversion_goals", "penalty_goals",
    "drop_goals_converted", "tackles_made", "turnovers_won", "line_breaks",
    "defenders_beaten", "metres_carried", "offloads", "penalties_conceded",
    "yellow_cards", "red_cards",
)


@dataclass(frozen=True)
class Rules:
    """One fantasy game's rules: how points are scored and what a legal squad is."""

    name: str

    # --- scoring ---
    points: Mapping[str, float]
    appearance_points: float = 0.0

    # --- the squad ---
    squad_size: int = 15
    quota: Mapping[str, int] = field(default_factory=dict)
    club_cap: int = 3
    budget: float = 100.0

    # --- playing the season ---
    transfers_per_gameweek: int = 2
    captain_multiplier: float = 2.0

    def __post_init__(self):
        unknown = set(self.points) - set(EVENTS)
        if unknown:
            raise ValueError(f"unknown scoring events: {sorted(unknown)}")

        bad_positions = set(self.quota) - set(POSITIONS)
        if bad_positions:
            raise ValueError(f"unknown positions: {sorted(bad_positions)}")

        if sum(self.quota.values()) != self.squad_size:
            raise ValueError(
                f"the quotas add to {sum(self.quota.values())}, "
                f"but the squad holds {self.squad_size}"
            )
        if any(n < 0 for n in self.quota.values()):
            raise ValueError("a position cannot have a negative quota")
        if self.club_cap < 1:
            raise ValueError("at least one player per club must be allowed")
        if self.budget <= 0:
            raise ValueError("the budget must be positive")
        if self.captain_multiplier < 1:
            raise ValueError("captaincy cannot cost points")

    def score(self, appearances: pd.DataFrame) -> pd.Series:
        """Fantasy points for each appearance.

        Takes a cleaned appearance table, one row per player per match, and
        returns the points that appearance was worth. Missing event columns
        are an error rather than a silent zero: a scoring rule that quietly
        stops applying is worse than one that fails.
        """
        missing = [e for e in self.points if e not in appearances.columns]
        if missing:
            raise KeyError(f"the appearance table has no column for {missing}")

        total = pd.Series(
            float(self.appearance_points), index=appearances.index, dtype=float
        )
        for event, value in self.points.items():
            counts = pd.to_numeric(appearances[event], errors="coerce").fillna(0.0)
            total = total + counts * value
        return total

    def balance(self, appearances: pd.DataFrame) -> pd.DataFrame:
        """Mean and spread of points per appearance, by position.

        A scoring system that leaves a position with nothing to offer makes
        that position's quota a tax rather than a decision. This is how the
        default values were chosen, and it is worth re-running after any
        change to them.
        """
        scored = appearances.assign(fantasy_points=self.score(appearances))
        out = scored.groupby("role").fantasy_points.agg(
            mean="mean", sd="std", appearances="size"
        )
        out["spread"] = out.sd / out["mean"]
        return out.sort_values("mean")


# The project's own scoring system.
#
# Two events a rugby fantasy game would normally reward are missing here:
# line breaks and turnovers won. Both columns are corrupted in the source.
# Across this competition, 84% of non-zero line break values are an exact
# copy of another column, usually carries, and turnovers won is almost as
# bad. Scoring either would have paid out for data that is not a record of
# anything. See docs/decisions/0004 and docs/data.md.
#
# Losing them costs the breakdown entirely, which is a real gap: a jackaling
# openside is invisible to this scoring system. Tackles are the only clean
# defensive statistic left, so they carry that weight instead.
#
# Point values were set against the real distribution of events across 3 821
# appearances in the competition. The tackle value is the lever that balances
# forwards against backs:
#
#     tackle worth 1.0   best:worst position ratio 2.46
#     tackle worth 1.5                             2.11
#     tackle worth 2.0                             1.91   <- chosen
#     tackle worth 2.5                             1.78
#
# Two and a half flattens the spread further but makes a fantasy rugby team
# a tackle-counting exercise, which is not the game. Two keeps every position
# worth picking while leaving tries the biggest prize.
#
# Props still score least and the back three and fly halves most. That is
# realistic and it corrects itself, because prices are modelled from
# projected points, so a low-scoring prop is a cheap prop. What matters is
# that the spread within each position stays wide, between 0.51 and 0.71 of
# the mean, since that is what makes one pick better than another.
#
# Scoring per appearance rather than per minute is deliberate. A player who
# comes on for twenty minutes accumulates fewer events and so scores less,
# with no need for a minutes adjustment. It also sidesteps the trap that
# caught RugbyBox, where a per-minute measure rewarded players for barely
# playing. See docs/lineage.md.
DEFAULT = Rules(
    name="Fantasy Rugby Box, own rules v1",
    points={
        # scoring
        "tries": 10.0,
        "try_assists": 5.0,
        "conversion_goals": 2.0,
        "penalty_goals": 3.0,
        "drop_goals_converted": 5.0,
        # carrying
        "metres_carried": 0.1,          # a point per ten metres
        "defenders_beaten": 1.0,
        "offloads": 2.0,
        # defending
        "tackles_made": 2.0,
        # indiscipline
        "penalties_conceded": -2.0,
        "yellow_cards": -5.0,
        "red_cards": -10.0,
    },
    appearance_points=2.0,
    squad_size=15,
    quota={
        "prop": 2, "hooker": 1, "lock": 2, "loose_forward": 3,
        "scrum_half": 1, "fly_half": 1, "centre": 2, "back_three": 3,
    },
    club_cap=3,
    budget=100.0,
    transfers_per_gameweek=2,
    captain_multiplier=2.0,
)
