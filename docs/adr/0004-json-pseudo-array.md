# 0004. JSONL in a pseudo-array frame

- Status: Accepted
- Date: 2026-09-16

## Context

The caller of peeragent is usually another agent, and it wants the
output in two ways at once. While a start is in progress it wants
to read messages as they arrive, line by line. Afterwards it wants
to hand the whole output to a parser and get a list.

Neither common format gives both. Line-delimited JSON streams
well, but the whole file is not a valid document. A single
indented JSON document parses as a whole, but nothing can be read
from it until it is complete.

There is a third requirement. An argument error must also appear in
the machine-readable output, rather than as a usage text on stdout
that no parser expects.

## Decision

Under `--json` the output is framed as an array without ever being
buffered as one:

- The first line is an opening bracket.
- Each message is one object on one line.
- Between two objects there is a line holding only a comma.
- The last line is a closing bracket.

The opening bracket is written as soon as the flag is recognized,
which happens before argument parsing. An argument error is
therefore emitted as a fatal message inside the array, with the
argument-error exit code, and no usage text reaches stdout. The
exception is a help request, which prints usage and opens no
array.

The closing bracket is written by an exit handler and by handlers
for the interrupt, terminate and hangup signals. Empty output is
the two bracket lines.

## Consequences

- A caller can read the stream incrementally, and can also load
  the completed output with a normal JSON parser.
- Only a signal that cannot be caught leaves an unterminated
  array. Everything else, including a fatal error and an
  interrupt, closes it.
- stdout under `--json` belongs to the emitter alone. Subprocess
  output is captured into variables, and every warning goes
  through the emitter rather than to stderr.
- The contract is structural: the set of message types, their
  order and their fields are promised, while field order inside an
  object and whitespace are not.
- The log uses the same frame, so a log file and a captured stdout
  can be read with the same code.

## Alternatives considered

Plain line-delimited JSON with no frame. Rejected: the caller
would have to reassemble a list itself, and the most common
mistake, loading the whole output at once, would fail.

One indented document written at the end. Rejected: nothing could
be read while a start is in progress, which is exactly when the
caller needs to know that a harness is asking a question.
