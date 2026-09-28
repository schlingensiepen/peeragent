# 0005. No log rotation, no bundling

- Status: Accepted
- Date: 2026-09-16

## Context

peeragent writes a log for exactly one purpose: someone who hits a
problem should be able to attach a file to a report. That purpose
is fully served by a file that exists and can be read.

Everything beyond it invites a second tool inside the tool. A
rotation policy needs sizes, ages and a locking story. A bundling
command needs to decide what belongs in a bundle and how to
redact it. A diagnostics command needs its own output format. A
configuration file needs a schema, a search path and a precedence
rule against the flags.

## Decision

One log file per invocation, under
`~/.local/state/peeragent/logs/`, in the same line-framed JSON
format as the machine-readable output. The file name carries the
date, the time, the subcommand and the process id, so that files
sort chronologically and can be named in a report.

What is deliberately not built: rotation, a bundling command, a
diagnostics command, and a configuration file. The only controls
are the flag that suppresses the log and the flag that redirects
it to a given path.

The log directory is created with owner-only permissions. Values
of environment variables whose names look like credentials are
replaced by a placeholder.

## Consequences

- The log directory grows monotonically. Cleaning it up is the
  user's decision, and the documentation says so rather than
  taking the decision away.
- The log is the complete record and the machine-readable output
  on stdout is a subset of it: the internal and timing messages,
  the invocation and the environment reach the file only.
- A log contains prompt text, captured pane content and absolute
  paths. That is what makes it useful and also what makes it
  sensitive, so the reporting instructions warn about it instead
  of pretending the file is anonymous.
- If the log file cannot be created, the run continues without one
  and says so as a warning rather than failing.
- If logging was suppressed, a fatal hint adds the advice to
  repeat the run with logging enabled, so the missing file does not
  cost a second round of questions.

## Alternatives considered

Rotation by size or age. Rejected: it adds policy and failure
modes to a feature whose whole value is that the file is there.

A bundling command that collects logs and system facts. Rejected
for this release: the same result is achieved by naming the
directory and the two commands whose output helps, and a bundle
would need its own redaction rules to be safe to send.
