# 3. Which scoring system to target

- **Status:** open, shapes the projection and the constraints
- **Date:** 2026-11-16

## Context

A fantasy optimiser is only as meaningful as the rules it optimises against.
The scoring system decides which statistics matter, the squad rules decide
what a legal team looks like, and both differ between games.

The choice also decides decision 2, because the price source follows from the
game.

**A real, running game** (for example a league or tournament fantasy game)
makes the output immediately useful: a real team, in a real competition, with
real prices. The costs are that the rules and prices live outside this
project and can change without notice, automated access to prices has to be
checked against the operator's terms, and the project is tied to one
competition's calendar.

**A scoring system of this project's own** removes every external dependency.
The rules sit in version control, prices can be modelled from the statistics
already held, and the whole thing can be demonstrated at any time of year
against historical seasons. The cost is that nobody can use it to play, so it
is a portfolio piece rather than a tool.

## What does not depend on this

Worth separating, because it is most of the work. Whatever the game:

- the squad is a fixed number of players chosen inside a budget
- positions carry quotas
- there is usually a cap on players from any one club
- one player is captained for a multiplier
- transfers are limited, which makes planning ahead a dynamic programme
- points come from events the data already records: tries, try assists,
  conversions, penalties, drop goals, tackles, turnovers, line breaks,
  defenders beaten, metres, offloads, penalties conceded and cards

So the optimiser, the projection machinery and the interface can all be built
against a rules object without knowing which game fills it in.

## Decision

Not yet made.

The rules will live in one place as a configuration object, covering squad
size, budget, position quotas, club cap, transfer allowance, captain
multiplier and the points awarded per event. A default ruleset ships so the
project runs, and it is clearly marked as a placeholder rather than any
particular game's rules.

## Consequences

Nothing is blocked while this is open, as long as no scoring rule is
hard-coded anywhere outside the rules object.

When the choice is made, confirming the default ruleset against the real
rules is a small, well-defined job. Discovering a hard-coded rule somewhere
in the projection code at that point would not be.
