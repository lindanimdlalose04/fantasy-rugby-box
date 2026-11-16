# Data

## Where it comes from

Match records come from the parquet store that backs the
[rugbypy](https://github.com/seanyboi/rugbypy) package, Apache-2.0. Files are
read directly from the store rather than through the package, so the fetch is
explicit and every request is visible.

    https://raw.githubusercontent.com/seanyboi/rugbydata/main/data/v3/

Five kinds of file are available: `team`, `player`, `match`, `competition`
and `venue`. Each takes either an entity id or a registry name such as
`team_registry`.

## What the store holds

Figures below were counted from the store, not quoted from its
documentation.

| Store | Size | Useful contents |
|---|---|---|
| `match_registry` | 8 066 matches | ids, teams, dates |
| `team_registry` | 366 teams | across 33 competitions |
| `venue_registry` | 413 venues | |
| one `match` file | 22 columns | scores, venue, city, attendance, kickoff, referee, pre-match form |
| one `team` file | 67 columns | per fixture: score, possession, territory, 22m entries, ruck speed, scrums, lineouts |
| one `player` file | 58 columns | per appearance, listed below |

## The player columns that matter here

A fantasy scoring system awards points for events. These are the columns that
correspond to scoring events in most rugby fantasy games, and all are present
in the store:

    tries, try_assists, conversion_goals, penalty_goals,
    drop_goals_converted, points, tackles_made, tackles_missed,
    turnovers_won, turnovers_lost, line_breaks, clean_breaks,
    defenders_beaten, metres_carried, carries, offloads, passes, kicks,
    lineouts_won, penalties_conceded, yellow_cards, red_cards

Also useful: `minutes_played`, `position`, `team_id`, `team_vs_id`,
`competition`, `game_date`, and `height_cm` and `weight_kg` where recorded.

What the store does **not** hold: fantasy prices, fantasy points, ownership
percentages, or an injury list. See
`docs/decisions/0002-where-player-prices-come-from.md`.

## Two problems to expect

**Minutes are missing for roughly half of all appearances.** The store also
records `carries_per_minute`, from which minutes can be recovered by dividing
carries by that rate. Checked against the appearances where both are present,
inside a single season window, the mean absolute error of that reconstruction
is 2.3 minutes. Across every season held in the store it is 3.0 minutes. The
approach is carried over from RugbyBox, which validated it.

**Coverage varies by column and by season.** Several columns are populated
for only part of the data: `kick_percent_success`, `clean_breaks` and
`weight_kg` each appear on under half of player rows. Check coverage before
building any scoring rule on a column, rather than discovering the gap in the
output.

## Snapshot date

The store is updated by its maintainers, so the same code gives different
answers on different days. Every run records the date its data was fetched,
and that date is reported wherever results are shown. A result without its
data date cannot be reproduced.

## Refreshing

The per-player fetch is cached locally and is not committed. A re-run only
fetches what is missing. The host throttles sustained sequential access, so
requests are retried with exponential backoff and a full league fetch takes
roughly fifteen minutes from cold.
