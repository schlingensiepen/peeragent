# 0002. tmux as the runtime

- Status: Accepted
- Date: 2026-09-16

## Context

The harnesses peeragent starts are interactive terminal programs.
They expect a terminal, they draw a full-screen interface, and
they keep running until someone ends them. peeragent, by contrast,
is a command that starts something, reports what happened, and
returns.

The mismatch creates requirements of its own. The launched harness
has to survive the return of peeragent, and the human has to be
able to look at it and take it over, because the interactive
questions a harness asks on a first start may need a person to
answer them.

A plain background process with pipes satisfies neither: without a
terminal the interface does not work, and there is no way to hand
a pipe to a human.

## Decision

Every start creates a detached tmux session. The session name is
built from the working directory, the harness key and a random
suffix, so that a caller can tell sessions apart and derive the
harness from the name later.

peeragent reads back what it needs through tmux: the first screen
by capturing the pane, and the process picture by asking for the
pane process and its children. Then it reports and exits, leaving
the session running.

tmux runs as the user's standard server rather than on a private
socket, so that the sessions appear where the user already looks
for sessions.

## Consequences

- tmux is a hard dependency of the subcommands that touch a
  session; its absence is a fatal preflight error with an install
  hint. The listing subcommands and `version` do not need it.
- The captured pane is the only feedback channel from a running
  harness, which makes the classification of that screen a
  first-class concept of the tool rather than an afterthought.
- The user can attach to a session, answer a question, and keep
  working in it. peeragent names the attach command in its
  output.
- Once a harness is running, peeragent never ends a session. The
  session belongs to the user from that moment on.
- The tool inherits tmux behaviour, including the target syntax
  for addressing sessions, windows and panes, and the fact that
  pane output scrolls out of the visible area.

## Alternatives considered

A background process with captured pipes. Rejected: a full-screen
interface needs a terminal, and the user could not take over.

A private tmux server on a dedicated socket. Deferred: it would
isolate peeragent sessions from mistakes in the user's own tmux
configuration, but it would also hide them from the user's session
list, which is the more important property for now.
