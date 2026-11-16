# Fantasy Rugby Box

Pick a fantasy rugby squad that scores the most points your budget allows,
and plan your transfers more than one week ahead.

> **Early development.** The data layer works. The optimiser and the
> interface are being built. Nothing here is usable yet.

## The problem

Every week thousands of people solve the same constrained selection problem
by eye: pick fifteen players inside a budget, respecting position quotas and
a cap on players from any one club, to score as many points as possible.
Doing it by feel is hard, and doing it well over a whole season is harder,
because transfers are a limited resource. Spending one now to chase a good
fixture costs you the flexibility to react to an injury next month.

That is a knapsack problem followed by a planning problem, and both have
known solutions.

## What it will do

- Pick the optimal squad for a budget and a scoring system
- Choose a captain
- Plan transfers across several gameweeks rather than one at a time
- Offer a risk setting, so you can ask for the highest floor instead of the
  highest expected score

## Status

| Part | State |
|---|---|
| Match data from `rugbydata` | working, carried over from RugbyBox |
| Fetch and clean pipeline | working, 4 077 appearances across 93 fixtures |
| Data quality guards | working, and they found two unusable columns |
| Scoring rules | settled, tuned against 3 821 real appearances |
| Player prices | settled in principle, modelled from projected points |
| Points projection | not started |
| Optimiser | not started |
| Interface | not started |

This project uses **its own scoring system**, not any published game's. It is
a tool for demonstrating the method, not a companion to a real competition,
and the squads it picks are not advice for one.

## Running it

Requires Python 3.11+.

    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt

Then, from the project root:

    python src/01_fetch.py     # every player in the competition (~15 min cold)
    python src/02_clean.py     # the appearance table, with the quality guards

Player files are cached, so a re-run only fetches what is missing.

    .venv\Scripts\pytest       # add --network to also read the live store

## Documentation

| Document | What it covers |
|---|---|
| `docs/method.md` | the maths: objective, constraints, why a MIP |
| `docs/data.md` | where the data comes from and how to refresh it |
| `docs/lineage.md` | where this project came from |
| `docs/decisions/` | why things were built the way they were |
| `CHANGELOG.md` | what changed in each release |

## Where this came from

This grew out of [RugbyBox](https://github.com/lindanimdlalose04/RugbyBox), a
multi-criteria squad selection system built for a university decision support
systems module. That project is finished and frozen. The data layer and the
integer programming approach carry over; the DEA, AHP and goal programming
stages do not. See `docs/lineage.md`.

## Data

Match data comes from the parquet store behind
[rugbypy](https://github.com/seanyboi/rugbypy), Apache-2.0.
