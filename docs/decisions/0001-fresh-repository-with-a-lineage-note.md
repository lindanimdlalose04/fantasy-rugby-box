# 1. Fresh repository with a lineage note

- **Status:** accepted
- **Date:** 2026-11-16

## Context

This project reuses the data layer and the integer programming approach from
RugbyBox, an assessed university project that is now finished. RugbyBox had
to stay citable: the commit that was submitted must remain identifiable, and
nothing done here should alter it.

Four options were considered.

A long-lived **branch** in the RugbyBox repository would have mixed product
work into the assessed artefact's history, and would never have merged back.

A **fork or clone**, keeping the history, was the first instinct. On
inspection RugbyBox had three commits, and most of what a fantasy optimiser
needs is not in them. The first commit here would have been largely
deletions: the Excel workbook, the efficiency analysis, the goal programme.

A **monorepo** with a shared core package and several apps is the right shape
once two or more applications share a library. There is one application.
That buys workspace tooling and build configuration for a benefit that does
not yet exist.

Extracting a **shared package** has the same problem: versioning and
releasing a library with exactly one consumer.

## Decision

A fresh repository. The reusable parts are copied in deliberately. The
connection to RugbyBox is recorded in `docs/lineage.md` and in a note at the
top of RugbyBox's README, and RugbyBox is frozen behind a tag marking the
assessed state.

Some duplication is accepted, mainly the parquet reader and the fetching and
cleaning stages. Those are expected to diverge quickly, because this project
needs prices, gameweeks and a scoring system that RugbyBox has no notion of.

## Consequences

A fix to the shared data layer has to be applied in two places. Given that
RugbyBox is frozen, in practice this means fixes flow one way only, into
this repository, and that is acceptable.

This repository's history starts with the product rather than with the
removal of something else.

Revisit if a second application appears that needs the same data layer, for
example the match simulator sketched during the RugbyBox review. That is the
point at which a monorepo or an extracted package starts to pay for itself.
