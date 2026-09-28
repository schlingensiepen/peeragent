# 0013. agent.exited and exit code 4

- Status: Accepted
- Date: 2026-09-17

## Context

A harness can die in the first seconds after being started: a
wrong flag, a missing dependency, a directory it will not accept.
Before this decision peeragent checked only whether the session
existed and then reported a successful start with a success exit
code. The caller had to notice from the stream that the screen
showed an error, and a caller that only looked at the exit code saw
nothing wrong at all.

That is the one failure a launcher must report well, because
everything the caller plans next depends on a process being alive.

## Decision

After the boot wait, peeragent asks whether the pane is dead. If it
is, peeragent emits a dedicated message carrying the exit status of
the process, the last lines of its output, and a hint for looking
at the session. It does not emit a start report. The session is
left standing, and the process ends with exit code 4, which is
reserved for this case and distinct from an argument error, a
missing tool, and a general runtime error.

## Consequences

- A failed start is visible from the exit code alone. A caller
  that only branches on the exit code behaves correctly.
- The output has to be read from the scroll history rather than
  from the visible screen, because the visible area of a dead pane
  shows only the multiplexer's own notice. The lines are truncated
  to the last non-empty ones, which is where the error is.
- Keeping the session is deliberate. It is the evidence, and the
  hint tells the caller how to look at it. Cleaning it up is the
  user's decision.
- The exit code space gains a case that has to stay distinct, so
  the code is not reused for anything else, and the reserved value
  in the screen classification for a dead harness is not used at
  all: the situation has its own message.

## Alternatives considered

Reporting it as a general runtime error. Rejected: it is
indistinguishable from a failure inside peeragent itself, and the
two need different reactions.

Killing the session and reporting the failure. Rejected: it
destroys the only copy of the harness output, which is the reason
the pane is kept alive in the first place.
