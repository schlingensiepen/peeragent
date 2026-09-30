# Contributing

peeragent is two programs that do the same job: `tools/peeragent.py`
(Python 3.11 or newer, standard library only) and `tools/peeragent`
(Bash 4.4 or newer, GNU coreutils, no `jq`, no `sqlite3`). They were
written independently, accept the same arguments and produce the same
messages in the same order. Most of what follows is about keeping
that true.

If you only use peeragent, you want [README.md](README.md) or, for an
agent, [AGENTS.md](AGENTS.md). Read
[docs/architecture.md](docs/architecture.md) before a larger change:
it has the layers, the handler contract and the equivalence rule, and
[docs/adr/README.md](docs/adr/README.md) lists the decisions that are
already settled.

## The rule: a behaviour change touches both programs

A change that alters what peeragent prints, accepts, refuses or does
is made in both files, in the same change, or it is not made. That
covers a new flag, a new message type or field, a different exit
code, a different order of messages, and a new or changed harness
marker, key sequence or catalog entry. A change that only alters the
wording of a `msg` or a `hint` is free to differ between the two, but
also has to be checked in both: the wording is not part of the
contract, the presence of a hint is.

In practice:

1. Make the change in one program.
2. Make the same change in the other, in the same section. Both
   files carry the same sections in the same order (see "File
   layout" in the architecture document), so the place for the second
   edit is where the first one was. Write it from the description of
   the behaviour, not by translating the first program line by line;
   the value of two implementations is that a misreading of the
   description shows up as a difference.
3. Add or change a conformance case (below) that would have caught a
   difference in this behaviour.
4. Run the conformance test. Everything has to agree.
5. Change the documents that state the behaviour. Flag lists, field
   names and exit codes live in exactly one place each:
   [docs/cli.md](docs/cli.md) and
   [docs/output-format.md](docs/output-format.md). Do not repeat them
   elsewhere.
6. Update [MATURITY.md](MATURITY.md) in the same change (see
   "Evidence" below).

Things the two programs must not do differently: the set of messages
and their order, the field names of each message, the exit codes, and
the semantic value of each field. What may differ: field order inside
an object, whitespace, the wording of `msg` and `hint`, and the
free-form pane lines.

Keep harness-specific knowledge inside a harness's handler section.
If a change would put a flag name, a banner text or a storage path
anywhere else, the handler contract is the wrong shape for it; raise
that in an issue first.

Do not change the version constant `PEERAGENT_VERSION` in a feature
change. It stays `0.1.0` until a release.

## Running the conformance test

```bash
tests/conformance/run.sh                 # every case
tests/conformance/run.sh version-json    # only the named cases
KEEP=1 tests/conformance/run.sh          # keep the sandbox to look at
```

It needs `bash`, `python3`, `tmux` and `git`; the runner checks for
all four before any case runs. Exit code 0 means every case agreed, 1
that at least one did not, and 3 that the run never got started - a
missing program or tmux, an unusable sandbox path, a case count that
no longer matches, a `bare` PATH that still finds a harness, or no
case to run.
A failing case prints what differed. With `KEEP=1`, a failing run
prints the sandbox path at the end; the raw output of each program is
in it.

The test compares the two programs with each other. It stores no
expected output and neither program is the reference. Read what that
means before you trust a green run: a mistake both programs make in
the same way passes. A green run is evidence of equivalence, never of
correctness. Correctness comes from reading the description and from
running a real harness. Also know what it does not reach today: no
case calls `send`, and no case uses a real harness. Seven do start a
fake one in tmux; `tests/conformance/README.md` has the current
figures, and the log files are compared for every case.

The programs run against fake harnesses from `tests/conformance/fixtures/bin/`
and never against a real one. The runner gives each program an empty
environment apart from `HOME`, `PATH`, `TMPDIR` and a UTF-8 locale.

## Adding a case

A case is a directory `tests/conformance/fixtures/<name>/`. The
name says what is covered. Files in it:

| File | Meaning |
|---|---|
| `args` | one line, the arguments, split on whitespace. `@SANDBOX@` and `@HOME@` are replaced at run time |
| `argv` | one argument per line, not split, instead of `args`. Needed for an argument that is empty or holds a space |
| `mode` | `json` (default), `plain`, or `help`: how the outputs are compared |
| `path` | `fakes` (default), `bare` to leave the fake harnesses out, or `notmux` to hide tmux as well |
| `env` | extra variables, one `KEY=VALUE` per line; `PEERAGENT_FAKE` selects the behaviour of the fake harnesses (`trust`, `exit`, `hang`, `noversion`, `padded`) |
| `home/` | a skeleton copied into the sandbox `HOME` before the run |
| `setup.sh` | run first with `SANDBOX` and `HOME` set, for anything whose name depends on the sandbox path, such as a session store |

The smallest useful case is a single `args` line:

```bash
mkdir tests/conformance/fixtures/list-models-one-plain
printf 'list models --harness codex\n' \
  > tests/conformance/fixtures/list-models-one-plain/args
printf 'plain\n' > tests/conformance/fixtures/list-models-one-plain/mode
tests/conformance/run.sh list-models-one-plain
```

Write the case first, run it against the unchanged programs to see
that it is not vacuous, then make the change. If a case passes
before and after a change to one program only, it is not covering
that change.

Before comparing, values that cannot match (timestamps, process ids,
the random suffix of a session name, counts, pane lines, harness
version strings, free text) are replaced by a placeholder. The
presence of a key is still compared. The list is in
[tests/conformance/README.md](tests/conformance/README.md).

## Trying a change against a real harness

Do this before you claim anything about a real harness's behaviour,
and use a scratch directory, not a project you care about.

peeragent uses your tmux server. To keep an experiment away from your
own sessions, point it at a separate server through the `TMUX`
variable, which tmux reads to find its socket when no socket option is
given (observed with tmux 3.5a):

```bash
TMUX=/tmp/tmux-$(id -u)/pa-try,0,0 tools/peeragent.py start agent \
  --folder /tmp/pa-try-dir --harness agy --json
tmux -S /tmp/tmux-$(id -u)/pa-try ls
```

Check with `tmux ls` on your own server that nothing appeared there.
End each session you created by its exact name:

```bash
tmux -S /tmp/tmux-$(id -u)/pa-try kill-session -t "=<session>"
```

Never `kill-server`. Not on your default socket, and not on one you
created either - the habit is what causes the damage, and a socket
directory under a scratch path disappears with the path anyway. Never
a loop over a pattern or a prefix, which is one typo away from a
session that was not yours.

The reason is not hypothetical. Taking down a shared tmux server ends
every client attached to it, which can end the login session those
clients belong to, and on an account without lingering systemd then
removes everything else that account was running.

Harnesses also keep trust decisions and session histories for the
directories you start them in, so a real run leaves entries behind in
the harness's own configuration.

## Evidence

[MATURITY.md](MATURITY.md) separates four levels: `tested` (run on a
host, with a date), `documented` (in the harness's own documentation),
`observed` (seen but not recorded) and `unverified` (an assumption). A
change that moves a statement up needs a run; a change that makes a
statement stale moves it back down. Do not write `tested` for
something that only passed the conformance test.

Documents are written as descriptions of what the programs do, in
English, without dates of intent and without promises. Where a
document and the code disagree, that is a bug in one of them: report
it as an issue rather than bending one to fit the other.

## Reporting a bug

Use the issue tracker and the template in
[.github/ISSUE_TEMPLATE/bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md).

When only one harness is affected, these make the report actionable:

- The harness key and the literal output of `<binary> --version`, and
  the date. Harnesses update themselves, sometimes between two runs.
- Whether the harness worked when you started it by hand in the same
  directory.
- The output of `peeragent list harness --json`.
- The pane, taken with `tmux capture-pane -t "=<session>:" -p -S -`
  while the session still exists. This is the most useful attachment:
  a wrong screen classification is a statement about someone else's
  interface on a particular day.
- The log file of the run, read first for anything you do not want to
  publish. It holds your prompt text, the pane content and absolute
  paths.
- Whether the other program gives the same result for the same call.
  If only one program misbehaves, it is a difference between the two
  and the conformance test is missing a case. If both do the same,
  either the behaviour is wrong in both or the harness changed.
- For an unrecognised screen: the lines from the `agent.pane` message.
  A screen reported as `unknown` is not by itself a bug; say why you
  expected a marker.

A key sequence that worked yesterday and closed or misled a dialog
today is exactly the report that matters most. Send the pane capture
and the harness version.
