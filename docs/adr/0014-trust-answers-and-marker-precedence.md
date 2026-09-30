# 0014. Trust answers are key sequences, busy before ready

- Status: Accepted; one sentence in it was overtaken by
  [0017](0017-simplest-start.md)
- Date: 2026-09-23

## Context

Reading the first screen of a harness is how peeragent decides what
to do next, so the classification has to be right about the things
that tests on a test host turned out to contradict the earlier
assumptions about.

The interactive questions are not answered by typing a word. They
are menus. One harness even preselects the option that declines,
so a plain confirmation keystroke would refuse to work in the
directory rather than accept it.

The empty input line that looks like an invitation to type stays on
screen in some harnesses while they are working. Treating it as a
ready marker reports a busy harness as ready, and a prompt pasted
into a harness that is not listening can be lost silently.

And some harnesses show no textual sign of work at all: no spinner
text, no status word, nothing a pattern could match.

## Decision

The key sequence that confirms a trust question is a handler
constant, per harness, expressed as a sequence of keys rather than
a word. peeragent quotes it inside a hint as a complete command
line and does not send it itself.

When several markers match the same screen, the interactive
questions win, then the working state, then the ready state.
Markers for the working state are deliberately narrow: only text
that appears exclusively while the harness works.

Where no marker matches at all, the core captures the screen a
second time after a short pause. If the two captures differ, the
harness is working, and the state is reported as busy even though
no text said so.

The output of a dead pane is read from the scroll history, not from
the visible area. **This no longer holds.** Record 0017 gave up
keeping the pane alive after its process exits, so there is no dead
pane and no scroll-history branch; a start whose session is gone
reports no output at all. The rest of this record is unchanged.

## Consequences

- The ready state becomes trustworthy enough to paste into, which
  is what the paste-based delivery path depends on.
- A harness with no working-state marker is still recognised as
  working, at the cost of one extra capture and a short additional
  delay on every start.
- Adding a harness means supplying its markers and, if it has one,
  its key sequence. It does not mean writing a general pattern for
  the idea of a prompt.
- The classification remains a heuristic over screen text, and
  `unknown` stays a legitimate answer. In that case peeragent hands
  the captured lines to the caller to show to a human instead of
  guessing.
- Because the precedence puts the working state above the ready
  state, a screen that shows both an idle-looking input line and a
  working marker is reported as working, which is the safe
  direction: waiting costs time, pasting into the wrong moment
  costs the assignment.

## Alternatives considered

Sending the trust answer automatically now that the exact key
sequence is known. Rejected here for the reason given in the
decision about the follow-up delivery: the answer grants a
permission and needs a deliberate opt-in.

Treating the idle-looking input line as ready and relying on the
harness to buffer a paste it was not ready for. Rejected: the
behaviour differs between harnesses, and silent loss of the
assignment is the worst available outcome.
