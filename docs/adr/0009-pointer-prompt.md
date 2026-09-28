# 0009. Pointer prompt and task file

- Status: Accepted
- Date: 2026-09-17

## Context

A substantial assignment passed as a launch prompt is awkward in
several ways at once. Long text on a command line is fragile to
quote and, with one of the two delivery paths, visible in the
process list. Long text in a log and in a terminal history makes
both unreadable. And a prompt that exists only as an argument
cannot be reviewed, corrected or repeated: the next run has to
reconstruct it.

The assignment itself is a document. Documents belong in files.

## Decision

The recommended shape separates the two. The starting agent writes
the full assignment into a file in the working directory, the task
file. The prompt file then contains only a short instruction to
read that file and carry it out, together with the scope and the
condition on which to stop, and that short text is what
`--prompt-file` receives.

peeragent enforces nothing. The prompt file remains just a file
holding the launch prompt, with no templating and no
preprocessing. The obligation lives in the shipped skill, which
makes the convention mandatory for the starting agent and carries
a template for both files.

## Consequences

- Command lines, terminal histories and logs stay short and
  readable, and a run can be repeated by pointing at the same task
  file again.
- The assignment is a file inside the project, so it can be
  reviewed by a human, corrected, versioned and referred to in a
  later run.
- With the delivery path that puts the prompt on the command line,
  a pointer prompt keeps the substance out of the process list.
- A caller that ignores the convention is not blocked. The rule is
  a documented obligation of the caller, not a check in the tool,
  which keeps the tool's contract unchanged.
- Two template files ship with the tool, so the convention is
  something to copy rather than something to reconstruct from a
  description.

## Alternatives considered

Building a template mechanism into the tool, with variables filled
from the command line. Rejected: composing the assignment is the
caller's work, and a templating language would be a second
interface to specify, document and keep equivalent across both
implementations.

Enforcing the convention by rejecting prompts above a certain
length. Rejected: the tool does limit prompt size for technical
reasons, but the shape of a prompt is a matter of judgement and
belongs in the skill.
