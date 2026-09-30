# 0017. The simplest start: one call, no kill

- Status: Accepted
- Date: 2026-09-30
- Supersedes [0011](0011-race-free-tmux-start.md)

## Context

Record 0011 built the session in four steps so that a harness dying
in its first seconds would leave a readable pane: create the session
empty with a placeholder shell, turn on mouse mode, set the window
option that keeps a pane after its process exits, then replace the
shell with the harness. The last step kills the shell.

That bought the **reason** for a failed start - the exit status and
the last lines of output. Three things were measured before giving
it up.

Detecting the failure never needed any of it. A session exists
exactly as long as the harness in it, so asking whether the session
is there answers whether the harness survived.

The obvious shortcut does not work: creating the session with the
harness and setting the option immediately afterwards loses the
race every time. Tried three times against a command that exits at
once, and three times the session was already gone when the second
call arrived.

And the cost is not only four calls. It is a kill in a tool whose
entire job is to launch something, which is the kind of thing a
reader has to stop and check.

## Decision

One call creates the session with the harness in it, detached, in
the working directory, at a fixed pane size. Mouse mode follows,
for the person who attaches; a failure there is not worth stopping
for, because the harness is running, which is what was asked.

Nothing is killed and nothing is replaced. One option is set, mouse
mode on the new session, and it is set through the pane target form
because that is what the session option needs; a failure there is
ignored. **peeragent ends no session and no harness, under any
circumstances.**

One qualification, so the claim is exact: the deadlines on peeragent's
own short-lived probes - a version query, a multiplexer call, reading
the process list - do end those probes when they hang, which is what a
deadline is for. The launched harness is not among them. It is a child
of the multiplexer's own server, not of peeragent, and peeragent has
no handle on it.

A start that fails is reported by its absence: no session, so
`agent.exited` with no status and no lines, and exit code 4. The
caller learns that the start failed and not why, and finds out by
running the same harness by hand.

## Consequences

- The tool never ends a session or a harness. That is worth stating
  because it is the first question a careful reader asks of something
  that starts processes for a living - and the answer used to have an
  exception.
- A failed start is thinner to diagnose. The exit code still
  separates it from every other failure, so a caller that branches
  on the exit code is unaffected; a caller that wanted the harness's
  own words has to reproduce the call.
- The fields for the status and the lines stay in the message, empty.
  A caller reads them by name, and a later version may be able to
  fill them.
- Roughly seventy lines of runtime, one helper, one constant and one
  cleanup path are gone, and with them the only branch that handled a
  pane whose process had ended.
- The pane is never in a state the capture has to treat specially, so
  the capture has one form instead of two.

## Alternatives considered

Wrapping the harness in a shell that outlives it, as other launchers
do. Measured on 2026-09-30: the pane then stays alive
with the wrapper waiting in it, no status is recorded, and **a
harness that died is indistinguishable from one waiting for input**.
Telling them apart would mean matching the wrapper's own prompt text
- a line this tool would have written into the screen it reports to
its caller. Rejected for that reason, not for the extra shell.

Keeping record 0011 as it was. Rejected on the judgement that
preserving the evidence of the rare failed start does not justify a
kill and three extra calls in every successful one.
