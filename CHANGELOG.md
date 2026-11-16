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

### Open decisions

- Where player prices come from (`docs/decisions/0002`)
- Which scoring system to target (`docs/decisions/0003`)

## Planned

- `v0.1.0` optimiser picks a squad from a budget and a rules object
- `v0.2.0` an interface
- `v1.0.0` usable by someone who did not write it
