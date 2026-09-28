# 0010. One generic prompt wrapper

- Status: Accepted
- Date: 2026-09-17

## Context

Some harnesses accept the initial prompt as the last argument of
their command line. That is the better path where it works,
because the harness starts working immediately and no state of the
screen has to be guessed. It brings one hard requirement: the
prompt text must reach that argument without passing through a
shell quoting level, since a prompt can contain quotes, newlines,
dollar signs and backticks in any combination.

An earlier arrangement had a wrapper command written out per
harness, plus a separate contract function that built the
prompt-carrying arguments. The two overlapped, disagreed about
which part contributed which arguments, and dropped flags that one
of them had added.

## Decision

The prompt text is always the last element of the argument vector,
and the core builds exactly one wrapper for every harness that
takes the prompt this way. The wrapper receives the absolute path
of the prompt file as its first argument, shifts that argument
away, and replaces itself with the remaining argument vector,
appending the content of the file as the final argument.

A handler contributes only its own arguments: the launch arguments,
the model arguments, and, if it needs anything immediately before
the prompt, the arguments from one dedicated function. Without a
prompt file there is no wrapper at all; the argument vector is
passed straight through.

The argument vector always reaches the terminal multiplexer as
separate arguments, never as a single string to be re-split.

## Consequences

- The prompt content never passes through a shell level belonging
  to peeragent, so there is no escaping rule for it to get wrong.
- Adding a harness that takes its prompt as an argument needs no
  new wrapper and no change to the core.
- Flags cannot be lost between two places that both build
  arguments, because only one place assembles the vector.
- The prompt text does appear in the command line of the harness
  process and is therefore readable through the process list by
  other users of the host. That is stated where it matters, and the
  answers are a pointer prompt or delivery after the start.

## Alternatives considered

A wrapper string per harness. Rejected: that was the arrangement
whose duplication caused the dropped flags.

Always writing the prompt into the pane after boot, for every
harness. Rejected: for harnesses that accept an argument prompt it
would trade a reliable path for one that depends on recognizing
the right moment on screen.
