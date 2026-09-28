# 0003. Two implementations, Python and Bash

- Status: Accepted
- Date: 2026-09-16

## Context

Not every host that runs a coding agent has a recent Python. A
tool whose job is to start such an agent should not fail on the
step before that.

There is a second reason, less obvious and at least as valuable.
A specification with one implementation is only as precise as that
implementation happens to be; every ambiguity is silently resolved
by the code. With two implementations in different languages, an
ambiguity shows up as a difference, and a difference can be
measured.

## Decision

peeragent exists twice: `tools/peeragent.py` in Python and
`tools/peeragent` in Bash. Both accept the same subcommands and
the same flags, and both produce equivalent output and an
equivalent log.

Equivalence is structural, not byte-exact. The two must produce
the same message types in the same order, with the same field
names and semantically equal values, and the same exit code. Field
order inside an object and whitespace are free.

A conformance test calls both with the same arguments in the same
sandbox and compares them against each other. The choice at call
time is simple: use the Python file when a suitable Python is
present, otherwise the Bash file. The two may be mixed within one
project.

## Consequences

- Every behaviour has to be expressible in both languages. A
  capability only one of them can reach is not a feature of
  peeragent; that constraint is what shaped the dependency rules
  and the static model catalogs.
- Both files are kept in the same internal section order, so that
  the two versions of one rule can be read side by side.
- Every change is made twice, and the conformance test is what
  makes the second time cheap: a forgotten port shows up as a
  failing comparison rather than as a surprise in the field.
- The version is a constant in both files, and the two are
  released together.
- Byte equality is explicitly not promised, because it is not
  reachable between a standard serializer and hand-built output
  without distorting one of them.

## Alternatives considered

One implementation in Python, with a vendored helper for anything
the standard library lacks. Rejected: it leaves hosts without a
suitable Python unserved, and it removes the pressure on the
specification.

One implementation in Bash only. Rejected: the parts that are
straightforward in Python, including JSON handling and the
comparison logic of the test, would have to be built by hand with
no benefit.
