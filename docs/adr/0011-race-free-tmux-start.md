# 0011. Race-free tmux start

- Status: Accepted
- Date: 2026-09-17

## Context

The obvious way to start a harness in a terminal multiplexer is to
create the session with the harness as its command. It works
whenever the harness lives, and it fails in exactly the case that
matters most.

The option that keeps a pane after its process has exited can only
be set on a session that already exists, which is one call too
late. If the harness exits within the first moments, because a
flag was wrong or a dependency was missing, the pane closes, the
session closes with it, and the error message is gone before
anything can read it. The tool then reports that it created a
session it can no longer find.

## Decision

The session is prepared empty and the harness is put into it
afterwards:

1. Create the session detached, running the default shell, in the
   target folder, with a fixed pane size so that captures are
   deterministic.
2. Turn on mouse mode for the session.
3. Set the window option that keeps a pane after its process
   exits.
4. Replace the shell with the harness by respawning the pane with
   the argument vector.

The user's standard multiplexer server is used. If a step after a
successful create fails, peeragent may remove the session, because
no harness is running in it yet; it then reports a fatal error.
After a successful respawn, peeragent never ends a session.

## Consequences

- A harness that dies immediately leaves a pane holding its output
  and its exit status. That is what makes a truthful report of a
  failed start possible at all.
- The pane size is fixed, so a captured screen has the same shape
  on every host.
- Two extra calls per start, and the harness starts a fraction
  later. Both are acceptable against losing the diagnosis.
- Session commands and pane commands have to address different
  targets, and the pane form must name the window explicitly.
  Getting that wrong fails silently in the form of a command that
  addresses nothing, so the target forms are part of the runtime
  rules rather than a detail of each call site.
- The sessions appear in the user's own session list, which is
  where the user will attach.

## Alternatives considered

Creating the session with the command and accepting the loss.
Rejected: it makes the most important failure invisible, and it
was the behaviour the change was made to fix.

Reading the harness output through a pipe in parallel as a safety
net. Rejected: it duplicates the capture path and does not help,
because a full-screen interface does not write anything useful to a
pipe.

**Wrapping the harness in a shell that outlives it**, so that the
pane stays open because the shell is still there:

```bash
tmux new-session -d -s <name> "bash -c \"cd <folder> && <harness>; read\""
```

This works, it needs no option set after the fact, and it needs no
kill of any kind - one call instead of four. It is what a sibling
tool does, and for its purpose it is the better choice.

Rejected here, for one reason: the pane is then never dead. The
shell is its process, and the shell is alive and waiting. The
multiplexer reports no exit status, because from its point of view
nothing exited. The harness's exit code would have to be printed by
the wrapper and read back out of a captured screen - turning a
number that the multiplexer hands over into a string to be found
among the harness's own output, and putting a line of our own into
the screen this tool reports to its caller.

The choice follows from who is reading. A tool that opens a session
for a person to attach to is right to keep the pane warm with a
shell and a "press enter to close". A tool whose output is consumed
by a program is better off with a field that holds a number. Both
are defensible; they are not the same job.
