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

After the boot wait, peeragent asks whether the session is still
there. A session exists exactly as long as the harness in it, so an
absent session means the harness is gone. peeragent then emits a
dedicated message and ends with exit code 4, which is reserved for
this case and distinct from an argument error, a missing tool, and a
general runtime error. It does not emit a start report.

The message carries no exit status and no output. It cannot: both
went with the session. An earlier version kept them, by creating the
session empty, setting an option that holds a pane open after its
process exits, and only then replacing the placeholder shell with
the harness - three extra calls and the killing of a shell, in a
tool that does nothing but launch. That was given up deliberately.
The caller learns **that** the start failed; to learn **why**, run
the same harness by hand with the same arguments.

## Consequences

- A failed start is visible from the exit code alone. A caller
  that only branches on the exit code behaves correctly.
- The message is thin, and the hint says what to do instead of
  reading it. A caller that wanted the harness's own error has to
  reproduce the call; the fields stay in the message by name so that
  nothing has to change if a later version can fill them.
- peeragent ends no session, under any circumstances. There is no
  moment in which it holds one without a harness in it, so there is
  nothing it would have to clean up.
- The exit code space gains a case that has to stay distinct, so
  the code is not reused for anything else, and the reserved value
  in the screen classification for a dead harness is not used at
  all: the situation has its own message.

## Alternatives considered

Reporting it as a general runtime error. Rejected: it is
indistinguishable from a failure inside peeragent itself, and the
two need different reactions.

Keeping the pane alive after its process exits, so that the output
and the exit status survive. That is what this tool did until
2026-09-30. It works, and it was given up because the cost is
visible in every start: a session created empty, two options set, a
placeholder shell killed and replaced - all of it to preserve the
evidence of the one start in a hundred that fails. The judgement was
that a launcher should launch, and that a caller who needs the
harness's error can ask the harness.
