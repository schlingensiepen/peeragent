# Conformance test

Two programs in this repository do the same job: `tools/peeragent.py`
in Python and `tools/peeragent` in Bash. They accept the same
arguments and are meant to produce the same messages in the same
order. This test is how that claim is checked.

## What it compares, and against what

Nothing. There are no expected outputs stored here, and neither
program is the reference. Each case runs both of them with the same
arguments in the same sandbox and compares the two results against
each other.

That choice has a consequence worth stating plainly: a mistake both
programs make in the same way passes. What this test finds is
divergence, which is the failure mode that matters when a contract has
two implementations. What finds the rest is reading the reference
documents under `docs/` against the two programs, and running a real
harness.

Before comparing, values that cannot match are replaced by a
placeholder: timestamps, process ids, the random suffix of a session
name, byte and file counts, harness version strings, and every
free-text `msg` and `hint`. Captured pane lines are replaced by their
number, so what a stand-in printed stays out of the comparison while
how much of it each program reported stays in. The **presence** of a
key stays part of the comparison, so a field one side omits is still a
difference. The `env` message is exempt entirely, because it describes
the interpreter rather than the behaviour.

## Running it

```bash
tests/conformance/run.sh              # every case
tests/conformance/run.sh version-json # only these
KEEP=1 tests/conformance/run.sh       # keep the sandbox to look at
```

Exit code 0 means every case agreed, 1 that at least one did not, and
3 that one of the two programs is missing.

Each case runs with an empty environment apart from `HOME`, `PATH`,
`TMPDIR`, a UTF-8 locale and whatever the case adds, and `HOME` points
into a throwaway directory. Nothing outside the sandbox is written,
and no real harness is ever called.

## The fake harnesses

`fixtures/bin/` holds five names that are all symlinks to one script.
It reports a version, prints a banner and then blocks, so a pane stays
alive and the first screen is predictable. `PEERAGENT_FAKE` selects
other behaviour: `trust` prints a trust dialog, `exit` fails
immediately, `hang` makes the version query outlast any timeout,
`noversion` makes it fail while the binary still exists, `padded` pads
the ready marker with U+00A0, the way Claude Code does, `vanish`
prints an unrecognisable screen and exits between the two captures, and
`needenv` refuses to start unless `--sandbox` was passed through and
`PROBE=expected` arrived in the environment - which turns a failed
pass-through into a session that is gone, something the comparison can
see even though the captured screen is compared only by line count.

## Adding a case

A case is a directory under `fixtures/` containing:

| File | Meaning |
|---|---|
| `args` | one line, the arguments, split on whitespace. `@SANDBOX@` and `@HOME@` are replaced at run time |
| `argv` | one argument per line, not split, instead of `args`. The only way to pass an argument that is empty or holds a space |
| `mode` | `json` (default), `plain`, or `help` — how the outputs are compared |
| `path` | `fakes` (default), `bare` to leave the fake harnesses out, or `notmux` to hide tmux as well |
| `env` | extra variables, one `KEY=VALUE` per line |
| `home/` | a skeleton copied into the sandbox `HOME` before the run |
| `setup.sh` | run with `SANDBOX` and `HOME` set, for anything whose name depends on the sandbox path |

`setup.sh` earns its place: a session store is named after the working
directory it belongs to, so it cannot be a static fixture.

## What is not covered yet

No case calls `send`, and none uses a real harness: the five names
under `fixtures/bin/` are all one stand-in script.

Nine of the 61 cases do start a fake harness in tmux, so **the suite
needs tmux**, and it checks for it before running anything. `run.sh`
also refuses to run when the number of cases no longer matches the
number written into it, because that number and the one in
`MATURITY.md` are what the documents quote. Each case gets
its own tmux server through `TMUX_TMPDIR`, and takes its sessions
down by name afterwards, so a run never touches a server it did not
create.
