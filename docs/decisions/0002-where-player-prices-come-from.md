# 2. Where player prices come from

- **Status:** accepted, modelled from projected points
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

Follows from decision 3. Since this project defines its own scoring system,
there is no external game whose prices could be scraped, so prices are
**modelled from projected points**.

Prices are still treated as an input with a documented CSV format, and the
modelled prices are simply the supplied default. Nothing downstream knows
where a price came from, so pointing this at a real game later means writing
that CSV from another source and changing nothing else.

A price has to rise faster than points, or the optimiser simply buys the
best players and the budget never binds. A convex mapping from projected
points to price is what makes the choice interesting, and the exact shape is
a parameter to be tuned so that the budget is a real constraint rather than
decoration. That tuning belongs with the pricing model, not here.

## Consequences

The optimiser's answers are not advice for any real competition, and nothing
in the interface may imply otherwise. A squad list looks equally
authoritative whether or not its prices are real, so this has to be stated
where the results are shown rather than buried in a caveat.

In exchange the project has no external dependency, no scraper to maintain,
no terms of service to work within, and can be demonstrated against any
historical season at any time of year.

Prices being derived from the same projections the optimiser maximises
creates a circularity worth watching: a projection error moves a player's
price and his attractiveness in the same direction, which could cancel out
and make the budget constraint toothless. Check that the chosen squad is
genuinely budget-constrained, rather than assuming it.
