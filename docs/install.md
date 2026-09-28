# Installing peeragent

This is the long form of the installation. `AGENTS.md` in the
repository root is the short, step-by-step version for an agent
that wants to acquire the capability; this document adds the
variants, the file permissions, the verification and the removal.

Read [`../MATURITY.md`](../MATURITY.md) before you start. It says
which parts of the tool exist, which are tested, and whether the
programs are present in the repository at all. The commands below
describe the installation as specified; the maturity report says
what you can expect of it today.

## Requirements

peeragent runs on Linux, natively or under WSL2. There is no
macOS and no native Windows support.

Check each requirement before installing. A missing entry in the
first group stops the installation.

| Requirement | Check | Expected |
|---|---|---|
| tmux 3.2 or newer | `tmux -V` | a version string, for example `tmux 3.5a` |
| git | `git --version` | a version string |
| A harness | `claude --version`, `codex --version`, `agy --version`, `opencode --version`, `copilot --version` | at least one of them answers |

The second group depends on which implementation you choose.

| Requirement | Check | Expected |
|---|---|---|
| Python 3.11 or newer | `python3 --version` | `Python 3.11` or higher |
| bash 4.4 or newer | `bash --version` | first line reports 4.4 or higher |
| GNU coreutils, findutils, procps | `realpath --version && timeout --version && stat --version && find --version && ps --version` | each answers |

The bash implementation uses `realpath`, `timeout`, `date`,
`stat`, `find` and `ps`. It needs no `jq`, no `sqlite3`, no
`uuidgen` and no `iconv`. The Python implementation uses the
standard library only.

`git` is a requirement of the tool as a whole even though a run
only needs it when you ask peeragent to initialize a repository
in the working directory.

peeragent does not install, update or configure the harnesses.
Install those from their own vendors:
Claude Code from Anthropic, Codex CLI from OpenAI, Antigravity
CLI from Google, OpenCode from anomalyco, GitHub Copilot CLI from
GitHub.

## Choose the implementation

`tools/peeragent.py` and `tools/peeragent` are call-compatible:
same subcommands, same flags, same message types in the same
order, same log format.

The rule: use `peeragent.py` where Python 3.11 or newer is
available, otherwise `peeragent`. You may mix them within one
project, because output and log are structurally the same.

## Install

Either placement works. Pick one.

### Copy into a PATH directory

Copy the file you chose under the name `peeragent`, without the
extension, so that the command is called the same way whichever
implementation is installed.

```bash
install -m 0755 tools/peeragent.py ~/.local/bin/peeragent
```

For the bash implementation:

```bash
install -m 0755 tools/peeragent ~/.local/bin/peeragent
```

`install -m 0755` creates the target directory entry with the
execute bit already set, so no separate `chmod` is needed. If the
target directory does not exist yet, create it with
`mkdir -p ~/.local/bin` first.

To install for all users of the host instead, copy to
`/usr/local/bin/peeragent` with the same mode. That needs write
access to `/usr/local/bin`.

### Run from the repository path

No copy. Make the file executable once and call it by path:

```bash
chmod 0755 tools/peeragent.py
/srv/src/peeragent/tools/peeragent.py version
```

This keeps one copy that updates with the repository. The cost is
that every caller has to know the path. If you are an agent,
record the absolute path in your own notes at this point; the
skill and the examples assume you can produce it when
`peeragent` is not on the `PATH`.

## PATH variants

`~/.local/bin` is on the `PATH` by default on many
distributions, but not on all. Check:

```bash
command -v peeragent
```

An empty answer means the shell cannot find it. Add the directory
in the startup file of your shell.

For bash, append to `~/.bashrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

For zsh, the same line in `~/.zshrc`. Open a new shell, or source
the file, and check `command -v peeragent` again.

A login shell reads `~/.bash_profile` rather than `~/.bashrc` on
some distributions. If `command -v peeragent` works in your
terminal but not in a session started by something else, that is
usually the reason.

peeragent reads no configuration from the environment. The only
variables it looks at are `HOME`, `NO_COLOR`, `TMUX`, `TMPDIR`,
and the harnesses' own configuration directory variables
`CLAUDE_CONFIG_DIR`, `CODEX_HOME` and `COPILOT_HOME` where those
are set. There is nothing to configure for peeragent itself and
no configuration file.

## File permissions

- The program file needs mode `0755`, or at least the execute bit
  for the user who runs it. Without it the shell reports
  permission denied.
- The log directory `~/.local/state/peeragent/logs/` is created
  with mode `0700` on first use. Logs contain the prompt text,
  captured pane content and absolute paths, so the restrictive
  mode is intentional. Do not loosen it.
- A working directory you hand to peeragent has to be readable
  and writable by the user who runs the harness, since the
  harness works in it.

## Anchor the capability in your harness

Installing the program gives you the command. The judgement that
goes with it is in
[`../skills/launch-peer-agent/SKILL.md`](../skills/launch-peer-agent/SKILL.md):
how to write an assignment, the pointer prompt rule, the trust
prompt key sequences, and when to deliver a prompt that was left
behind.

### Claude Code

Claude Code reads skills from `~/.claude/skills/`. Copy the whole
directory:

```bash
cp -a skills/launch-peer-agent ~/.claude/skills/
```

The skill becomes available in a new session. It bundles no code;
it calls the `peeragent` you installed above.

### The other harnesses

`codex`, `agy`, `opencode` and `copilot` have no skill format, so
there is nothing to copy the directory into. This is a gap in the
harnesses, not something peeragent works around.

What to do instead: read
[`../skills/launch-peer-agent/SKILL.md`](../skills/launch-peer-agent/SKILL.md)
and keep it as a reference
you can open when the task comes up, or transfer its content into
whatever mechanism your harness does offer — a rules file, a
project instruction, a note in the working directory. The form is
your choice. The obligations it describes hold either way.

## Verify

```bash
peeragent list harness --json
```

Expected output: a JSON array, one line per object, with a
`harness.detected` message for each installed harness and a
`harness.missing` message for each one that is absent. Exit code
0.

An array with only `harness.missing` messages is a successful run
that found no harness. peeragent is installed correctly; there is
nothing for it to start yet. Install a harness and repeat.

A `warn` message with `version: null` on a detected harness means
the binary is there but did not answer `--version` within the
timeout. That is not fatal; peeragent does not interpret version
strings.

For the plain-text form, drop `--json`:

```bash
peeragent list harness
```

To check which implementation answers:

```bash
peeragent version --json
```

The `impl` field is `python` or `bash`.

Both forms write a log file to
`~/.local/state/peeragent/logs/`. If the directory cannot be
created, the run continues without a log and says so in a
warning.

For what the messages and fields mean, see
[`output-format.md`](output-format.md); for the subcommands and
their flags, [`cli.md`](cli.md).

## First use

The short version of the rule: the assignment goes into a file in
the working directory, and the prompt file holds only a short
pointer to it.
[`../examples/quick-start.md`](../examples/quick-start.md) walks
through one complete session, and
[`../examples/task-file-template.md`](../examples/task-file-template.md)
and
[`../examples/prompt-file-template.md`](../examples/prompt-file-template.md)
are copy-ready forms.

## Uninstall

Remove the program and the skill:

```bash
rm -f ~/.local/bin/peeragent
rm -rf ~/.claude/skills/launch-peer-agent
```

If you installed for all users, the first path is
`/usr/local/bin/peeragent`. If you ran from the repository path,
there is nothing to remove there.

What is left behind on purpose:

- The logs in `~/.local/state/peeragent/logs/`. Delete them with
  `rm -rf ~/.local/state/peeragent` when you no longer need them.
  peeragent never rotates or deletes logs by itself.
- The tmux sessions of harnesses that are still running. peeragent
  never ends a session it started. List them with `tmux ls` and
  end the ones you recognize by name; the names begin with
  `peeragent-`.

Nothing else is touched. peeragent writes no configuration file
and changes no harness settings, so the harnesses keep whatever
sessions, trust decisions and logins they had.
