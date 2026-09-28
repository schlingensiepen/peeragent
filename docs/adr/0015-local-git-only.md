# 0015. Git setup limited to a local repository

- Status: Accepted
- Date: 2026-09-17

## Context

A working directory handed to a fresh agent is often better off
being a repository from the start, so that the agent's changes are
reviewable. Creating one locally is a single command.

Everything beyond the local case is not. Creating a repository on a
hosting service means resolving a name, deciding whether the remote
already exists, possibly committing the directory content because
some creation paths require a commit, authenticating without ever
prompting, and choosing what to do when a step half succeeds.
Written out as one flow, those steps turned out not to be
executable in the order they had been specified: the existence of
the remote was to be discovered from the failure of an operation
that should not have been attempted yet.

## Decision

This release implements one kind of git setup. A flag initializes a
repository in the target folder with a fixed default branch name.
No commit, no remote, no attributes file.

A failure of that call is fatal and the harness is not started,
because the caller asked for a repository and would otherwise get a
started agent in a directory that is not one. If the folder lies
inside an enclosing repository, it is still initialized and a
warning says so, since nesting is sometimes intended and sometimes
a mistake. git is required only when the flag is given.

Templates, discovery of remotes that already exist, remote
creation, and the listing subcommand that would enumerate the
available kinds are deferred. The questions that have to be
answered before they can be specified are written down rather than
left to the implementation: the grammar of the keys and their
mapping to kinds, which directory the calls run in, an explicit
existence probe before any write instead of inferring existence
from a failure, whether peeragent may commit the user's content,
and how a half-completed setup is reported.

## Consequences

- The git surface of this release is one flag, one call and one
  timeout, with no network access and no credentials involved.
- A directory produced by the duplicate subcommand already contains
  a repository, so the flag refuses there. That is a consequence
  worth stating, because it is the one case where the flag is not
  idempotent in the way a caller might expect.
- The listing subcommand for template kinds exists in the command
  surface and ends with an argument error until the remaining kinds
  are built, rather than silently not existing.
- Callers that need a remote create it themselves, which is one
  command in the agent session and needs no support from peeragent.

## Alternatives considered

Shipping the full template flow as specified. Rejected: the open
questions would have been answered by whichever implementation was
written first, and the second one would have had to copy those
answers rather than the intended behaviour.

Shipping no git support at all. Rejected: the local case is a
single call with a clear failure mode, and having it at start time
saves the caller a round trip before the first change is made.
