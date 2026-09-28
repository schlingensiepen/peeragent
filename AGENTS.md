# AGENTS.md

**State:** the command-line programs are not in this repository yet.
`tools/` is empty, so the steps below cannot be completed today.
Read step 1 and stop there: tell the user that peeragent is a
pre-release without an executable program, and do not promise a
launch.

This file is the instruction sheet for an AI agent that wants to
acquire the peeragent capability for itself: install the program,
anchor it in its own harness, verify it, and know where the limits
are.

## 1. Read the maturity report first

Read [MATURITY.md](MATURITY.md) before anything else.

The core state, repeated here so that you know it without following
the link: peeragent 0.1.0 is a pre-release, the programs are not in
this repository yet, and of the five supported harnesses only
`claude` is covered by tests across detection, launch, prompt
delivery, resume and duplicate.
For `codex` the launch and the prompt hand-over are tested, resume
rests on harness documentation; for `agy` and `opencode` the prompt
hand-over has never been run; `duplicate` is refused for everything
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

The rule that matters most: write the full assignment into a file in
the target working directory, and pass only a short prompt that
points at that file, with a scope and a stop condition.

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
[docs/architecture.md](docs/architecture.md) for the layers, the
handler contract and the equivalence rule between the two
implementations, and [docs/adr/README.md](docs/adr/README.md) for the
decisions that are already settled and the reasons behind them.
Keep flag lists, field names and exit codes in
[docs/cli.md](docs/cli.md) and
[docs/output-format.md](docs/output-format.md); they exist in exactly
one place on purpose.
