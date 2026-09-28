# 0006. Static model catalogs

- Status: Accepted
- Date: 2026-09-16

## Context

A caller that is about to start a harness wants to know which
models it can ask for. Some harnesses can produce that list
themselves, others cannot. Where they can, the query needs a
login, network access, and a parser for the harness output, which
the Bash implementation does not have.

The list is a convenience rather than a correctness requirement,
because the model string is handed to the harness unchanged.
Whatever the harness accepts works, whether peeragent has heard of
it or not.

## Decision

peeragent ships a static catalog per harness. Each entry carries a
key, a description and the date the catalog was last updated.
There is no live query against a harness, and no field that claims
where an entry came from.

A model given on the command line is passed through opaquely. It
is not checked against the catalog.

## Consequences

- The listing works offline, without a login, and behaves
  identically in both implementations, which is what keeps it
  inside the equivalence contract.
- A model that was released after the catalog was written is
  missing from the listing, and a user who knows its name can use
  it anyway. A catalog entry that disappeared upstream stays in the
  listing until it is removed.
- The date on every entry makes staleness visible instead of
  letting a listing look authoritative. It is the honest part of
  the arrangement.
- Catalogs are maintenance work with every release, and the only
  cost of neglecting them is an incomplete listing, not a broken
  start.

## Alternatives considered

A hybrid: query the harness where it supports it, fall back to the
static list otherwise. Rejected: it needs a parser for the harness
output in Bash, and it makes the listing depend on login state, so
the two implementations and even two runs of the same
implementation could disagree.

No listing at all, on the grounds that the model string is opaque
anyway. Rejected: the caller would have to guess, and a stale
dated list is more useful than none.
