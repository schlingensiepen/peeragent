# 0012. A send subcommand instead of answering trust prompts

- Status: Accepted
- Date: 2026-09-17

## Context

On a first start in a new directory, every supported harness stops
and asks something: whether it may work in this directory, that
nobody is logged in, or that a provider has to be chosen. This is
the normal case, not an edge case.

While the harness waits for that answer, the launch prompt is
undelivered. In the arrangement before this decision nothing
picked it up afterwards: the caller ended up with a running
session and a prompt file, and no supported way to bring the two
together. Restarting would mean answering the question again in a
new session.

The tempting fix is to answer the question automatically. But the
trust question is a permission decision about a directory, and
answering it on the user's behalf is exactly the kind of thing a
tool should not do quietly.

## Decision

peeragent gains a subcommand that delivers a prompt file into a
session that already exists, given the session name and the file.

When a prompt was not delivered, peeragent says so in its own
message, names which delivery path was in use, and gives the hint
that leads to the follow-up call. The caller therefore learns from
the output alone that there is unfinished business and how to
finish it.

peeragent does not answer the interactive questions. Where a
harness has a known key sequence for confirming trust, peeragent
quotes the full command line that would send it, so that the caller
or the user can send it deliberately. Automatic answering is
deferred to a later release.

## Consequences

- The decision to trust a directory stays with the caller and the
  user, and it is visible as an explicit step.
- The follow-up delivery pastes regardless of the state of the
  screen, because the caller has already judged the situation. The
  rule that follows is that it must only be called after peeragent
  reported an undelivered prompt; calling it otherwise risks
  delivering the same assignment twice.
- The start report names the prompt file, so the follow-up can be
  reconstructed from the recorded output without keeping state on
  the caller's side.
- The delivery path matters for the follow-up, which is why the
  deferred-prompt message names it and gives a different hint for
  each: one path needs an immediate delivery, the other needs a
  look at the screen first, because the harness may have taken the
  prompt already.

## Alternatives considered

A flag that sends the trust answer automatically. Deferred rather
than rejected: it is convenient, and it needs a deliberate opt-in
and a clear statement of what is being granted.

Waiting inside peeragent until the screen becomes ready. Rejected:
the question may require a human, and a command-line tool that
blocks for an unbounded time is less useful than one that reports
the situation and returns.
