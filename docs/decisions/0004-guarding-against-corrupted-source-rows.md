# 4. Guarding against corrupted source columns

- **Status:** accepted
- **Date:** 2026-11-16
- **Supersedes:** the fixture-level duplicate guard first proposed here

## Context

While setting the scoring values, two problems were found in the source.
Neither is documented anywhere.

**Per-minute rates sitting in count columns.** Across the whole store, 57
appearances in 7 fixtures hold a rate where a count belongs. The tell is a
non-integer count, such as `tackles_made` of 0.08. On those fixtures the try
counts are nonsense too: one player credited with 36 tries alongside one
metre carried. None of those fixtures fall inside this project's competition
and season window, but the guard is kept because the window will move.

**Columns written over one another.** This is the serious one, and the first
diagnosis of it was wrong.

It first looked like a handful of bad fixtures: `line_breaks` exactly equal
to `turnovers_won` for most of a team. The guard written for that rejected
whole fixtures, and on this competition it threw away 28% of appearances
while still letting implausible values through. Chasing those leftovers found
the real pattern. `line_breaks` was also equal to `carries`, in rows the
fixture filter had kept.

Measured properly, across this competition's 4 077 appearances, **84% of
non-zero `line_breaks` values are an exact copy of another column**, usually
`carries`. `turnovers_won` is almost as bad. Only 1 fixture in 93 is free of
it. This is not a few corrupt fixtures. These columns do not hold what they
claim to hold.

### Measuring it honestly

A first attempt compared raw equality rates and flagged nine of twelve
columns, which said more about the test than the data. Small count columns
agree constantly: a player with one try and one offload matches for no reason
at all.

The test that works divides the observed equality rate by the rate the two
columns' own distributions would produce if they were independent, ignoring
rows where both are zero. Those all-zero rows are most of the data and
counting them swamps the comparison, which is what made a clean column look
as bad as a corrupted one.

On that measure the separation is unambiguous:

| Column pair | Ratio to chance |
|---|---|
| `carries` and `line_breaks` | 7.14 |
| `turnovers_won` and `carries` | 7.03 |
| `metres_carried` and `carries` | 1.55 |
| `tackles_made` and `carries` | 1.24 |
| everything else | below 1.2 |

## Decision

**`line_breaks` and `turnovers_won` are not scored.** They are named in
`config.KNOWN_CORRUPTED` and a test asserts the scoring system does not use
them.

**The cleaning stage runs the duplication check every time** and stops the
pipeline if any column it is about to score looks corrupted. This is the
check that found the problem, so it runs rather than sitting in a notebook.
It also reports when a known-corrupted column stops looking corrupted, in
case the source is fixed.

**Fixtures are still rejected for holding rates in count columns.** That
corruption really is per-fixture.

**Plausibility caps stay as a backstop**, applied last and reported whenever
they bind. They caught one appearance recording two red cards, which cannot
happen. They also caught four players beating 13 to 16 defenders, which was
genuine, so the cap was raised rather than the data discarded.

## Consequences

The breakdown is invisible to the scoring system. A jackaling openside earns
nothing for it, because turnovers are the statistic that would have measured
that and it cannot be trusted. Tackles are the only clean defensive measure
left and now carry that weight at 2 points each. This is a real gap in the
model, not a rounding error, and it should be stated wherever the scoring
system is explained.

Nothing is thrown away. The earlier fixture-level guard discarded 28% of
appearances and still missed the problem; dropping the two columns keeps all
93 fixtures and 4 077 appearances.

**This affects RugbyBox.** Its efficiency analysis uses four outputs:
`metres_carried`, `line_breaks`, `tackles_made` and `turnovers_won`. Two of
those four are the corrupted columns, over the same competition and season.
Its AHP weights are defined over the same four measures. That project is
frozen and assessed, so nothing here changes it, but anyone citing its
efficiency figures should know.

The check is a heuristic. It finds columns duplicated from other columns in
the same row. A column corrupted some other way, scaled wrongly, or stale,
would pass it. Any statistic that looks remarkable should still be traced
back to its appearance before it is believed.
