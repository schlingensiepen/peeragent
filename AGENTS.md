# AGENTS.md

**State:** peeragent 0.1.0 is a pre-release. Both programs are in
this repository, `tools/peeragent.py` and `tools/peeragent`, and they
run. What has been checked, and how, is in
[MATURITY.md](MATURITY.md). Read step 1 before you go on, and promise
the user only what it covers.

This file is the instruction sheet for an AI agent that wants to
acquire the peeragent capability for itself: install the program,
anchor it in its own harness, verify it, and know where the limits
are.

## 1. Read the maturity report first

Read [MATURITY.md](MATURITY.md) before anything else.

The core state, repeated here so that you know it without following
the link: peeragent 0.1.0 is a pre-release. Both programs are in this
repository and run.
On 2026-09-29 both were started against all five real harnesses on a
test host and reported a first screen; a complete path with a trust
answer and a prompt handed over afterwards with `send` was run through
to an answer for `agy` only.
The two programs agree with each other on 43 conformance cases. That
shows they behave alike, not that either is correct, and none of those
cases starts a harness.
`--resume` and `duplicate` have not been run through the programs
against a real harness.

Of the five supported harnesses only `claude` has detection, launch,
prompt delivery, resume and duplicate checked on the harness itself.
For `codex` launch and prompt hand-over are tested and resume rests on
harness documentation; for `agy` the trust answer and the hand-over by
pasting were tested on 2026-09-29; for `opencode` the prompt hand-over
by pasting has never been run; `duplicate` is refused for everything
except `claude`.

You need this before you act, not after: what you promise the user
has to be covered by evidence, and the evidence level is part of
every statement in that document.

## 2. Check the prerequisites

Run each command and compare against the expected result.

| Command | Expected |
|---|---|
| `uname -s` | `Linux`. On Windows this has to be a WSL2 shell; native Windows and macOS are not supported |
| `tmux -V` | `tmux 3.2` or newer |
| `git --version` | any version |
| `python3 --version` | `Python 3.11` or newer, if you intend to use the Python program |
| `bash --version` | `4.4` or newer, if you intend to use the Bash program |

The Bash program additionally needs GNU coreutils (`realpath`,
`timeout`, `date`, `stat`), findutils (`find`) and procps (`ps`).
It needs neither `jq` nor `sqlite3`.

Stop if `uname -s` is not `Linux`, if `tmux` is missing, or if
neither interpreter reaches its minimum version.
Report which check failed and what it is needed for; do not try to
install anything on the user's machine without being asked.

## 3. Choose the implementation

Both programs accept the same arguments and produce the same
messages in the same order, so the choice is free and may differ
between projects.

That equivalence is checked, and it has two named exceptions. The
message describing the environment reports the interpreter, so it
differs by construction. And on a screen that matches no marker and
carries something moving, such as a spinner, one program may call it
busy and the other unrecognised, because the rule compares two
captures two seconds apart and the outcome depends on which two
seconds. Both values tell a caller the same thing - look for
yourself - and neither permits a key sequence.
[MATURITY.md](MATURITY.md) keeps the current list.

- Python 3.11 or newer available: use `tools/peeragent.py`.
- Otherwise: use `tools/peeragent` (Bash).

## 4. Install the program

Either copy it into a directory on your `PATH`:

```bash
install -m 0755 tools/peeragent.py ~/.local/bin/peeragent
```

Or call it from the repository without copying:

```bash
chmod +x tools/peeragent.py && ./tools/peeragent.py version
```

If you take the second way, write down the absolute path you used;
you will need it whenever you call the tool, and the skill refers to
it as well.
The long form, including `PATH` variants and file permissions, is in
[docs/install.md](docs/install.md).

## 5. Anchor the capability in your own harness

If you are Claude Code, copy the skill directory into your skill
store:

```bash
cp -r skills/launch-peer-agent ~/.claude/skills/
```

The other four harnesses have no skill format.
Read [skills/launch-peer-agent/SKILL.md](skills/launch-peer-agent/SKILL.md)
and carry its content over into whatever your harness offers: a rule
file, a project instruction, a note you keep in context.
The form is your choice; the obligations in that document are not
optional.

## 6. Verify

```bash
peeragent list harness --json
```

Expected: a line `[`, then one object per supported harness in the
order `claude`, `codex`, `agy`, `opencode`, `copilot`, separated by
lines containing a single `,`, then a line `]`.
Each object is of type `harness.detected` with `key`, `version`,
`description` and `path`, or of type `harness.missing` with `key` and
`description`.
A `harness.detected` object with `version: null` is followed by a
`warn`: the binary is there, but the version query timed out or
failed.
The exit code is 0 even when every harness is missing.

If every object is `harness.missing`, none of the supported
harnesses is on your `PATH`; that is a valid result and not an error.
If the array contains nothing at all, the run ended before the first
message: look at the newest log file in
`~/.local/state/peeragent/logs/`.

## 7. First use

Read [skills/launch-peer-agent/SKILL.md](skills/launch-peer-agent/SKILL.md)
and take the task file template from
[examples/task-file-template.md](examples/task-file-template.md).

Three rules matter most.

The working directory is the one you name with `--folder`, and the
launched harness inherits nothing else: not your own current
directory, not the place the prompt file sits in. Name the project
directory itself, never the folder above it. A parent directory does
not fail, it only puts the trust question, the relative paths and the
session history one level too high.

Write the full assignment into a file in that directory, and pass
only a short prompt that points at that file, with a scope and a stop
condition. This is enforced, not advised: a prompt longer than 120
effective characters is refused with exit code 2. Paths that start
with `/` and contain no spaces are not counted, so the path to the
task file is free.

Tell the user the name of the tmux session after every start, along
with the read-only attach line the tool reports. Do this whether or
not anything went wrong. Everything peeragent knows about the
harnesses' screens describes someone else's interface on a
particular day, and an update can invalidate any of it; when that
happens, the user attaching to the session and looking is the only
diagnosis left, and it only works if they were given the name.

Remember what happens after the call: the agent you launched keeps
running in its tmux session on its own, and nothing connects you to
it any more. If you want to hear from it, establish a channel and
describe it in the assignment. [README.md](README.md) names the two
recommended ways.

A complete session, including the trust question and the
hand-over of a deferred prompt, is played through in
[examples/quick-start.md](examples/quick-start.md).

## 8. Uninstall

```bash
rm -f ~/.local/bin/peeragent
rm -rf ~/.claude/skills/launch-peer-agent
```

Log files stay behind in `~/.local/state/peeragent/logs/`; remove
that directory as well if you do not need them.

## 9. If you want to contribute

This file is the entry point for an agent that *uses* peeragent, not
a rule sheet for agents changing this repository.
If you are here to change the code or the documents, read
[CONTRIBUTING.md](CONTRIBUTING.md) first, then
[docs/architecture.md](docs/architecture.md) for the layers, the
handler contract and the equivalence rule between the two
implementations, and [docs/adr/README.md](docs/adr/README.md) for the
decisions that are already settled and the reasons behind them.
Keep flag lists, field names and exit codes in
[docs/cli.md](docs/cli.md) and
[docs/output-format.md](docs/output-format.md); they exist in exactly
one place on purpose.
