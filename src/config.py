"""Paths, the competition window, and the data quality guards.

Anything shared between stages or worth tuning lives here. The scoring
system does not: that is in rules.py, and nothing here may duplicate it.

Nothing in this module reads or writes data. Import it, do not run it.
"""

# --- paths ---------------------------------------------------------------

RAW = "data/raw"
PROCESSED = "data/processed"
PLAYER_CACHE = f"{RAW}/players"
MANIFEST = f"{RAW}/manifest.json"

# --- what to fetch --------------------------------------------------------

COMPETITION = "Gallagher Premiership"
SEASON_START = "2025-09-01"
SEASON_END = "2026-06-30"

# The clubs in a competition are not listed anywhere in the store, so they
# are discovered from one club's own fixture list: everyone it played in the
# competition during the window, plus itself.
SEED_CLUB_ID = "821a6e9b"          # Bath Rugby

# --- positions ------------------------------------------------------------
# Raw position labels to the eight groups the squad rules are written over.

ROLE_MAP = {
    "hooker": "hooker",
    "prop": "prop",
    "loosehead_prop": "prop",
    "tighthead_prop": "prop",
    "lock": "lock",
    "flanker": "loose_forward",
    "openside_flanker": "loose_forward",
    "blindside_flanker": "loose_forward",
    "number_eight": "loose_forward",
    "scrum_half": "scrum_half",
    "fly_half": "fly_half",
    "centre": "centre",
    "inside_centre": "centre",
    "outside_centre": "centre",
    "wing": "back_three",
    "left_wing": "back_three",
    "right_wing": "back_three",
    "fullback": "back_three",
}

# Labels that say a player came off the bench rather than where he plays, so
# they cannot be used to classify him.
BENCH_LABELS = {"front_row_sub", "back_sub", "forward_sub", "default", ""}

# --- data quality guards --------------------------------------------------
# Two corruptions are present in the source and neither is announced. Both
# are rejected at fixture level, because both affect whole fixtures. See
# docs/decisions/0004-guarding-against-corrupted-source-rows.md.

# Columns that count events, and so can never hold a fraction. A single
# non-integer value condemns the fixture: it means rates have been written
# where counts belong, and the other columns on that fixture are wrong too.
COUNT_COLUMNS = [
    "tries", "try_assists", "tackles_made", "tackles_missed",
    "turnovers_won", "line_breaks", "defenders_beaten", "carries",
    "offloads", "penalties_conceded", "yellow_cards", "red_cards",
]

# Some columns in the store have been overwritten by their neighbours. The
# tell is two columns holding exactly the same value far more often than
# their separate distributions would produce by chance.
#
# Comparing raw equality rates is not enough, because small count columns
# coincide constantly: tries of 1 equals offloads of 1 for no reason at all.
# So the observed rate is divided by the rate independence alone would give,
# ignoring rows where both columns are zero, and only a large ratio counts.
# On this competition that leaves ordinary related statistics between 1.1 and
# 1.6, and the corrupted columns above 7, so the limit sits in the gap.
SUSPECT_RATIO_LIMIT = 3.0

# Columns compared against one another when looking for that duplication.
INTEGRITY_COLUMNS = [
    "tries", "try_assists", "tackles_made", "turnovers_won", "line_breaks",
    "defenders_beaten", "carries", "offloads", "penalties_conceded",
    "metres_carried", "passes", "kicks",
]

# Columns already known to be corrupted in this source, checked at every run
# so that a change upstream shows up rather than being assumed. Nothing in
# the default scoring system may depend on them.
KNOWN_CORRUPTED = ("line_breaks", "turnovers_won")

# Second line of defence, applied after the fixture filters. These are set
# well above the highest believable single performance, so they should
# almost never bind. Every time one does, it is reported: a cap that starts
# binding means a corruption the fixture filters do not catch.
PLAUSIBLE_MAX = {
    "tries": 6,
    "try_assists": 5,
    "conversion_goals": 12,
    "penalty_goals": 8,
    "drop_goals_converted": 3,
    "tackles_made": 32,
    # A back having an exceptional afternoon beats a lot of defenders. The
    # four highest in this competition, 13 to 16, were all genuine: real
    # carry counts, real metres, real tries behind them.
    "defenders_beaten": 18,
    "metres_carried": 320,
    "offloads": 8,
    "penalties_conceded": 6,
    "yellow_cards": 2,
    # A player can only be sent off once. One appearance in this competition
    # records two, alongside a yellow, which cannot be what happened.
    "red_cards": 1,
}

# --- derived measures -----------------------------------------------------

# Minutes are missing for roughly half of all appearances and are rebuilt
# from carries divided by the recorded carrying rate. Validated inside the
# season window at a mean absolute error of 2.3 minutes.
FULL_MATCH_MINUTES = 80

# Appearances a player needs before his record is worth projecting from.
# Below this he is carried in the data but not offered for selection.
MIN_APPEARANCES = 2
