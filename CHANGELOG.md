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

### Found

- Two undocumented corruptions in the `rugbydata` store: per-minute rates in
  count columns on 7 fixtures, and `line_breaks` duplicated from
  `turnovers_won` on 153 fixtures. See `docs/data.md`.

## Planned

- `v0.1.0` optimiser picks a squad from a budget and a rules object
- `v0.2.0` an interface
- `v1.0.0` usable by someone who did not write it
