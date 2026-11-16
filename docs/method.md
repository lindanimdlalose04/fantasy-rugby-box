# Method

Three problems, solved in order. Each is written up here as it is built.

## 1. Projecting points

**Status: not started.**

How many fantasy points is each player expected to score in the next
gameweek? Historical appearances are converted into fantasy points by
applying the scoring rules, which gives points per player per match. The
projection is then a forecast of the next one.

The hazard here is known, and comes from RugbyBox. A per-match or per-minute
rate computed from one or two appearances is mostly noise, and ranking on it
puts fringe players at the top. In RugbyBox the raw efficiency measure
correlated -0.61 with minutes played before this was corrected. Any
projection must be shrunk toward a baseline in proportion to the evidence
behind it, with the shrinkage point estimated from the data rather than
asserted. See `src/04_dea.py` in that repository for the split-half
reliability approach.

Fixture difficulty belongs here too: the same player is worth more against a
weak defence. That needs a team rating, which is its own small model.

## 2. Picking the squad

**Status: not started.**

A binary integer programme. One variable per player, one if selected.

Maximise total projected points, subject to:

- exactly the squad size the rules specify
- total price at or below the budget
- each position's quota satisfied
- no more than the permitted number of players from any one club
- a captain chosen, scoring a multiple of his projection

This is a knapsack with side constraints. It is small, a few hundred binary
variables, and solves in well under a second with CBC through PuLP.

The captain choice interacts with selection, so it is solved jointly rather
than picked afterwards: the best captain among an optimal squad is not
necessarily the best squad-and-captain pair.

## 3. Planning transfers

**Status: not started.**

This is the part that distinguishes the project from a weekly knapsack.

Transfers are a limited resource over a season. Spending one now to chase a
favourable fixture costs the flexibility to react to an injury later. Picking
the best squad each week independently is therefore not the same as playing
well across a season, and will usually be worse.

Treated as a multi-period problem over a rolling horizon of several
gameweeks: state is the current squad and the transfers banked, and the
decision each week is which transfers to spend. Solved as a dynamic
programme, or as one integer programme spanning the horizon.

## 4. Risk

**Status: not started.**

The highest expected score is not always the right target. A team built from
players with volatile returns can have a high mean and a poor floor, which
loses head-to-head leagues.

Two ways to express the alternative, both standard: a chance constraint, so
the squad must exceed some score in a stated proportion of simulated
outcomes, or a mean-variance objective trading expected points against their
variance. Which is preferable depends on whether the user is playing a
league or chasing an overall rank, so it is exposed as a setting rather than
chosen for them.

Any simulation used here must be validated against data the optimiser has not
already fitted to. Simulating the output of an optimiser and reporting how
often it breaches a constraint it was pushed against produces a number that
looks like a finding and is close to circular. RugbyBox made exactly that
mistake; see `docs/lineage.md`.

## What the rules object has to supply

The maths above is the same for any rugby fantasy game. These are the
parameters that differ, and they live in one place so none of them leaks into
the code:

    squad size, budget, position quotas, club cap,
    transfer allowance, captain multiplier,
    points per scoring event
