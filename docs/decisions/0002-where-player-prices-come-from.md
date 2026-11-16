# 2. Where player prices come from

- **Status:** open, blocking the optimiser
- **Date:** 2026-11-16

## Context

The optimiser maximises projected points subject to a budget. Without a price
per player there is no budget constraint, and without a budget constraint the
answer is simply the fifteen highest-projected players, which nobody needs a
model for. Prices are therefore not a detail; they are half the problem.

**Prices are not in the data this project already has.** The parquet store
behind `rugbypy` carries match and player statistics across 33 competitions
and 8 066 matches. It carries no fantasy prices, because it is not a fantasy
data source.

Three ways to get them.

**Scrape the live game.** Gives real prices that move during the season, which
is what makes transfer planning interesting. Costs: the prices change weekly
so the scraper has to keep running, the markup can change under you without
warning, and whether automated collection is permitted depends on the
operator's terms. That last point has to be checked before any code is
written, not after.

**Enter them by hand.** A CSV the user updates each week. No legal or
technical risk, works immediately, and the format is the same whatever the
source. It is tedious across a few hundred players, but it is tedious for the
person who chose to do it, which is a different kind of cost.

**Model them.** Fit a price from the statistics already held, the way
RugbyBox modelled salary from position averages scaled by playing time. The
model then runs out of the box with no external dependency. The prices are
not real, so the answers are not actionable in a real game, but every other
part of the system can be built and tested against them.

## Decision

Not yet made. It depends on which fantasy game this targets, which is
decision 3.

The shape that keeps the options open: treat prices as an **input with a
documented CSV format**, with a modelled fallback so the project runs
without them. Whichever source is chosen later writes that CSV, and nothing
downstream needs to know where the numbers came from.

## Consequences

Until this is settled, any figure the optimiser produces is a demonstration
rather than advice. That must be stated plainly wherever results are shown,
not buried in a caveat, because a squad list looks equally authoritative
whether or not its prices are real.
