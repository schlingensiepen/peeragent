# 0007. Duplicate scope per harness

- Status: Accepted
- Date: 2026-09-17

## Context

Copying a working directory so that a second agent can continue
from the same state is only useful if the harness can also
continue its own conversation history there. The files are the easy
half; the history lives outside the directory, in a store the
harness keeps for itself.

Each harness does that differently. One keeps a directory per
working directory, which can be copied. Others additionally index
their sessions in a database keyed by directory path, and a copy
that does not update the index leaves the harness unable to find
the history it now has on disk. Reaching such an index would need a
database client that neither implementation is allowed to depend
on.

Of the five copy paths, one has been exercised on a test host. The
others are, at best, plausible.

## Decision

The harness is a required argument of the duplicate subcommand;
there is no implicit copy of everything that happens to be
installed.

Each handler declares its own duplicate maturity. In this release
one harness is supported, and the other four refuse. A refusal
happens in preflight, before any file is copied, and its hint names
the harness-native alternative for continuing a session instead.
There is no override that forces a copy.

The core copies the working tree; the handler copies only the
session store. Before either happens, the preflight also checks
that the destination does not already have a session store for
that harness.

## Consequences

- A refusal is cheap and leaves nothing half-copied.
- Raising a harness from refusing to experimental requires
  evidence that its index can be carried over, not an argument
  that it probably can. Until then, the documentation states the
  refusal and the alternative.
- A source without a session store is not an error: the working
  tree is copied, the result reports that nothing was copied from
  the store, and a warning says so. Copying the files alone is
  still useful.
- The maturity per harness is a documented fact with an evidence
  level, not a hidden default.
- Anyone who needs more can change the handler, which is one
  clearly delimited block of code.

## Alternatives considered

Copy everything and warn. Rejected: a session index that points at
the wrong directory is worse than no history at all, because the
harness then reports confusing state rather than a clean start.

An environment variable or flag that overrides the refusal.
Rejected: such a switch ends up being set by default, and the
failure it enables is hard to attribute afterwards.
