# 3. Which scoring system to target

- **Status:** accepted, this project's own scoring system
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

This project defines its own scoring system, in `src/rules.py` as a frozen
`Rules` object covering squad size, budget, position quotas, club cap,
transfer allowance, captain multiplier and the points awarded per event.

The point values were not invented. They were chosen against the real
distribution of events across 18 499 league appearances, with the explicit
aim that every position be worth picking. The tackle value is the lever that
balances forwards against backs: at one point per tackle the best position
outscores the worst by 2.5 times, at one and a half by 2.0. Raising try
assists and turnovers on top of that moved the ratio by 0.01, so the simpler
values were kept.

The squad is a real rugby fifteen: two props, a hooker, two locks, three
loose forwards, a scrum half, a fly half, two centres and a back three, with
a cap of three players from any one club.

Scoring is per appearance rather than per minute. A player who comes on for
twenty minutes accumulates fewer events and so scores less, with no minutes
adjustment needed. This also avoids the trap that caught RugbyBox, where a
per-minute measure rewarded players for barely playing.

## Consequences

No external dependency. The rules sit in version control where they can be
tested, prices can be modelled from statistics already held, and the whole
thing can be demonstrated at any time of year against historical seasons.

Nobody can use this to play a real game. It is a tool that demonstrates the
method, not a weekly companion to a running competition. That is the trade
accepted here.

Pointing the project at a real game later means writing a second `Rules`
instance and solving the price problem. Nothing else should need to change,
which is why no scoring rule may be hard-coded outside the rules object.

Props score least and the back three most, by about two to one. This is
realistic and self-correcting, because prices are modelled from projected
points, so a low-scoring prop is a cheap prop.
