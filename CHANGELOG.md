# Changelog

Notable changes, newest first. Versions follow [semantic
versioning](https://semver.org). The project stays on `0.x` until it is
something a stranger could rely on.

Because results depend on data that is updated outside this project, each
release also records the date of the data snapshot it was built against.

## Unreleased

### Added

- Repository scaffold, documentation and decision records
- `src/rb.py`, the parquet store reader, carried over unchanged from RugbyBox
- `src/rules.py`, the scoring system and squad rules as a validated object,
  with point values tuned against 18 499 real appearances so that every
  position is worth picking

### Decided

- This project uses its own scoring system rather than a published game's
  (`docs/decisions/0003`)
- Prices are modelled from projected points, with a CSV input kept as the
  interface so another source can be swapped in (`docs/decisions/0002`)
- Corrupted source fixtures are rejected at fixture level on two signatures,
  costing about 7% of appearances (`docs/decisions/0004`)

- `src/01_fetch.py` and `src/02_clean.py`, the pipeline, producing 4 077
  appearances across 93 fixtures with a recorded data snapshot date
- A column integrity check that stops the pipeline if any column being
  scored looks like a copy of another

### Found

- **`line_breaks` and `turnovers_won` are unusable.** 84% of non-zero
  `line_breaks` values are an exact copy of another column, usually
  `carries`, and only 1 fixture in 93 is free of it. Both are dropped from
  the scoring system. The breakdown is consequently invisible to the model.
- Per-minute rates in count columns on 7 fixtures elsewhere in the store,
  none inside the current window.
- One appearance recording two red cards, which cannot happen.
- **This affects RugbyBox**, whose efficiency analysis uses both corrupted
  columns as two of its four outputs, over the same competition and season.

### Changed

- Tackles raised from 1.5 to 2.0 points, rebalancing the positions after the
  loss of turnovers. Best-to-worst position ratio is 1.91.
- The first guard, which rejected whole fixtures on a duplicated pair, is
  replaced. It discarded 28% of appearances and still missed the problem.

## Planned

- `v0.1.0` optimiser picks a squad from a budget and a rules object
- `v0.2.0` an interface
- `v1.0.0` usable by someone who did not write it
