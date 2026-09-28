# 0001. Standard library and system tools only

- Status: Accepted
- Date: 2026-09-16

## Context

peeragent is a small tool that a tester should be able to run by
copying a file. Anything that requires a package installation
first competes with the harness it is supposed to start. The Bash
implementation in particular has to run on whatever a plain Linux
host already has, because a shell script that needs its own
dependency list has no advantage over the Python one.

Two implementations also have to be reconcilable. Every capability
that only one of the two languages can reach becomes a difference
in behaviour, and differences in behaviour are what the
conformance test is built to prevent.

## Decision

The Python implementation uses the standard library only: no
third-party packages, no output-formatting library, no argument
parsing library beyond the standard one, no configuration file
parser.

The Bash implementation uses the shell and the command-line tools
of an ordinary Linux userland: coreutils for path resolution,
timeouts, dates and file metadata, findutils, and the process
tools. Beyond that the runtime needs tmux, and git only for the
optional repository setup. It does not use a JSON
processor, a SQLite client, a UUID generator or a character-set
converter. The tools named are those of a GNU userland rather than
a strictly minimal POSIX set, because path resolution, timeouts
and file metadata are needed in a form a bare POSIX environment
does not offer.

The Bash implementation never parses JSON. It only produces JSON.
Where it has to read a foreign file, it matches literal known
tokens or reads the file line by line; it does not interpret the
format.

Minimum versions are stated rather than guessed: Python 3.11,
Bash 4.4, tmux 3.2. A hosting-service command-line client is not a
dependency of this release.

## Consequences

- Installing means copying one file into a directory on the
  `PATH`. There is nothing to build and nothing to resolve.
- Model listings cannot be queried from the harnesses, because
  that would require reading their JSON output in Bash. They are
  static instead.
- Session indexes that a harness keeps in a SQLite database are
  out of reach for both implementations, because reaching them in
  only one of the two would break the equivalence. That limits
  which harnesses can have their session history copied.
- Configuration formats of other tools are read line by line for
  single, known keys, and never treated as a parsed document.
- The maintenance burden moves into the project: what a library
  would provide has to be written and tested here, which is why
  string escaping, identifier generation and redaction have their
  own unit tests.

## Alternatives considered

Allowing a JSON processor and a SQLite client for the Bash
implementation. Rejected: neither is present by default on a
minimal host, so the promise that the Bash version runs anywhere
would be void, and the Python version would gain capabilities the
Bash version lacks.

Shipping only the Python implementation and depending on a few
small packages. Rejected: it removes the reason for the second
implementation, which is the pressure it puts on the precision of
the specification.
