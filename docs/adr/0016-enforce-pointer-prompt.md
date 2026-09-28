# 0016. The tool enforces the pointer prompt

- Status: Accepted
- Date: 2026-09-28
- Supersedes: [0009](0009-pointer-prompt.md) in the part that left
  enforcement to the caller

## Context

Record 0009 separated the assignment from the prompt and made the
pointer prompt an obligation of the caller, enforced by nothing.
The tool's only limits were a warning above 100 KiB and a refusal
above 120 KiB where the prompt travels as a command-line argument,
which exist for the argument length limit and amount to no limit on
the shape of a prompt: roughly a hundred thousand characters pass.

Practice showed the obligation does not hold by itself. A caller in
a hurry passes the assignment, and nothing objects. The costs then
land elsewhere: the substance sits in the process list where one of
the two delivery paths puts it, the terminal history and the log
carry a wall of text, and the launched agent cannot read its own
assignment again once the pane has scrolled on. A task file can be
re-read on request; a command-line argument cannot.

## Decision

The tool refuses a launch prompt above 120 effective characters
with exit code 2, before it starts anything, and names the remedy
in the hint. The same check runs when a deferred prompt is
delivered later, so the limit cannot be circumvented by starting
without a prompt.

Effective length counts the words, not the paths. The content is
decoded as UTF-8, whitespace at both ends is removed, the rest is
split on whitespace, every token beginning with a slash is
dropped, the remaining tokens are joined with one space each, and
the Unicode code points of that string are counted. A pointer can
therefore name the task file and the place to write the report
without spending its budget, and a deep directory tree does not eat
into the text.

There is no flag that lifts the limit. A prompt file that does not
decode as UTF-8 is refused as well, since the count needs the
decoded text.

## Consequences

- The convention holds without depending on the caller's
  discipline, which is what 0009 could not achieve.
- The limit is measured in what a pointer actually needs: a path,
  a scope and a stopping condition fit, an assignment does not.
- The size limits in bytes fall away as unreachable, and the limit
  no longer depends on how the harness receives the prompt. One
  rule replaces two.
- A caller whose prompt does not fit is told what to do instead,
  and doing it costs two lines: write the file, point at it.
- The counting rule is part of the contract and has to be
  identical in both implementations, so the conformance suite
  carries a case for the refusal and a boundary case with two long
  paths.

## Alternatives considered

A warning instead of a refusal. Rejected: a warning leaves the
convention optional, which is the state this record replaces.

A flag that permits a long prompt. Rejected: an agent that meets a
refusal with an available override learns to append the flag rather
than to write the file, and the exception would become the habit.

A larger limit, so that no existing example needs shortening.
Rejected the other way round: the examples were measured against
the rule and the two that missed it were too wordy, not too
constrained. The shorter forms say the same thing.
