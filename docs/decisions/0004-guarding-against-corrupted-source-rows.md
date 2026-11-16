# 4. Guarding against corrupted source rows

- **Status:** accepted
- **Date:** 2026-11-16

## Context

While setting the scoring values, two distinct corruptions were found in the
source data. Neither is announced anywhere, and both inflate exactly the
statistics a fantasy scoring system pays most for.

**Per-minute rates sitting in count columns.** 57 appearances across 7
fixtures hold a rate where a count belongs. The tell is that `tackles_made`
is not a whole number, for example 0.08 tackles. On those same fixtures the
try counts are nonsense: one player is credited with 36 tries and another
with 27, each alongside about one metre carried.

**One column copied over another.** On 153 fixtures, more than a quarter of
the players have `line_breaks` exactly equal to `turnovers_won` at a non-zero
value. Across all appearances, 22.5% of non-zero pairs are identical, which
is far above anything independence would produce. The copied values also run
implausibly high: 24 line breaks and 24 turnovers in a single appearance,
where the 99th percentile of each is 10.

The second is the more dangerous of the two. It is not obviously wrong on
inspection, it affects 1 718 appearances, and because the default rules award
4 points for a line break and 4 for a turnover, a single corrupted value is
paid for twice.

Without a guard, the top scoring appearance in the entire dataset is a player
credited with 24 line breaks and 24 turnovers, worth 192 points of the 253 he
would be awarded. Any projection built on that would rate him among the best
players in the league.

## Decision

Reject at the fixture level, not the row level, because both corruptions
affect whole fixtures.

A fixture is rejected if either:

- any of its appearances has a non-integer value in a count column, or
- more than a quarter of its appearances have `line_breaks` equal to
  `turnovers_won` at a non-zero value

This removes roughly 7% of appearances. The cleaning stage reports how many
fixtures each rule rejected, so a change in the source data shows up as a
change in that count rather than as a silent change in the answers.

A plausibility cap is kept as a second line of defence, applied after the
fixture filter and logged whenever it binds. It exists to catch a corruption
of a kind not yet seen, not to patch these two.

## Consequences

About 7% of appearances are discarded. That is a real cost and it is worth
it: the discarded rows are concentrated in exactly the statistics the scoring
system rewards most.

The scoring values were checked against both the contaminated and the cleaned
data. The ratio between the best and worst scoring position moved from 2.09
to 2.04 and the order of positions did not change, so the choice of point
values does not rest on this cleaning being right. The within-position spread
tightened from 0.72 to 0.85 down to 0.54 to 0.71, which is consistent with
the rejected rows being noise rather than signal.

These rules are heuristics fitted to two corruptions that happen to be
visible. There may be others that are not. Any statistic that looks
remarkable should be traced back to its appearance before it is believed.
