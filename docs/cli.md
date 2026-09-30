# Command reference

peeragent is a Linux command-line tool that starts a coding-agent
harness in a tmux session and reports the first screen back in
structured form.
It also delivers a launch prompt that was left behind, duplicates a
working directory together with a harness session history, and lists
installed harnesses and their model catalogs.

This file is the reference for every subcommand, every flag, the
preflight checks in their order, the message order and the exit
codes.
It describes what both programs do in version 0.1.0. How far each
statement is backed by a run, and how far only by the two programs
agreeing with each other, is recorded in
[../MATURITY.md](../MATURITY.md).

Message shapes, field tables per message type and the meaning of
each exit code are in [output-format.md](output-format.md).
Per-harness values such as prompt delivery, resume support, session
stores and the wording of trust prompts are in
[harnesses.md](harnesses.md).
Installation and `PATH` setup are in [install.md](install.md).

## Subcommands

| Subcommand | Purpose |
|---|---|
| `list harness` | Report which of the supported harnesses are installed |
| `list git-templates` | Reserved; not available in this version |
| `list models` | Report the static model catalog per harness |
| `start agent` | Start a harness in a tmux session and report the first screen |
| `send` | Deliver a prompt into a running session |
| `duplicate` | Copy a working directory and the harness session history |
| `version` | Report the peeragent version |

The supported harness keys are `claude`, `codex`, `agy`, `opencode`
and `copilot`.
Lists are emitted in a fixed order: claude, codex, agy, opencode,
copilot.

## Rules that apply to every subcommand

- Global flags (see [Global flags](#global-flags)) are accepted
  before or after the subcommand.
- Every path argument is made absolute before first use: symlinks
  resolved, trailing slash removed.
  A path that does not exist is accepted at this point; existence is
  a preflight matter.
- An unknown `--harness` key is `fatal` with exit code 2 in every
  subcommand.
  A known but not installed harness is `fatal` with exit code 3.
- A missing or unknown second token after `list` or `start` is
  `fatal` with exit code 2.
- `--boot-wait` belongs to `start agent` and `--wait` belongs to
  `send`.
  Passing either to another subcommand is `fatal` with exit code 2.
- The order of messages per subcommand is normative.
  A consumer may rely on it.
- Each successful tool check emits exactly one `info` with fixed
  wording: `tmux found: <version>` or `git found: <version>`.
  Each successful harness check in `start agent`, `send` (when a
  handler was determined) and `duplicate` emits exactly one `info`
  `harness <key> found: <version>`, or `harness <key> found, version
  unknown` when the version could not be read, followed by a `warn`.
  `list harness` emits `harness.detected` and `harness.missing`
  instead; `list models` emits the `info` per installed harness.
  Path and argument checks emit nothing on success.
  These messages are part of the normative order.
- Errors about a missing tool are deliberately verbose: what is
  missing, what it is used for, and how to install it.
  They carry `user_relevant: true` and a `hint`.
- The wording of `msg` and `hint` beyond the fixed success messages
  is not part of the contract and may change between releases.
  Message types, field names and exit codes are the contract.
- No environment variable configures peeragent.
  Every switch is a flag.

## `peeragent list harness`

Reports detection and version for each supported harness.

**Synopsis**

```text
peeragent list harness [global flags]
```

**Flags:** none besides the global flags.

**Preflight:** detection of every harness.
Neither tmux nor git is required.

**Flow**

Each harness is probed in the fixed order with `command -v` and, if
the binary is present, with `<binary> --version` under a timeout of
10 seconds.
The version string is the literal first line of that output with
whitespace trimmed at both ends.
peeragent does not interpret it.
A timeout or an exec failure with a present binary yields
`installed: true` and `version: null`.

**Output**

`harness.detected` per installed harness with `key`, `version`,
`description` and `path`; `harness.missing` per absent harness with
`key` and `description`.
When `version` is `null`, a `warn` follows the object it belongs to.

**Exit codes:** 0, including the case that no harness is installed.

## `peeragent list git-templates`

This subcommand does not exist in this version.
The token is reserved for a later version that will list git
templates for repository setup.

**Synopsis**

```text
peeragent list git-templates
```

**Flow:** the call is rejected as an unknown second token after
`list`.

**Output:** a single `fatal`.

**Exit codes:** 2.

Local repository setup is available through `--git-repo` on
`start agent`.

## `peeragent list models`

Reports the model catalog per harness.
The catalogs are static and shipped with peeragent; peeragent does
not query the harness for its models.

**Synopsis**

```text
peeragent list models [--harness <key>] [global flags]
```

**Flags**

| Flag | Required | Meaning |
|---|---|---|
| `--harness <key>` | optional | Restrict the output to this harness. An unknown key is `fatal` (2), a key that is known but not installed is `fatal` (3). |

Without `--harness`, every installed harness is reported in the
fixed order.
Harnesses that are not installed stay invisible; no
`harness.missing` is emitted.

**Preflight:** detection of every harness, or of the one named by
`--harness`.

**Output**

The preflight `info` per installed harness, then `model.available` per
model with `harness`, `key`, `description` and `catalog_updated`, in
catalog order.

**Exit codes:** 0; 2 for an unknown `--harness` key; 3 for a harness
that is not installed.

If a model is missing from a catalog, it arrives with the next
release.
Any model string can be passed through opaquely with `--model` on
`start agent` in the meantime; peeragent does not validate it.

## `peeragent start agent`

Starts a harness in a tmux session, waits for it to boot, classifies
the first screen and reports what the caller has to do next.

**Synopsis**

```text
peeragent start agent --folder <path> --harness <key>
                      [--prompt-file <path>] [--model <string>]
                      [--resume] [--git-repo]
                      [--boot-wait <seconds>] [global flags]
```

**Flags**

| Flag | Required | Meaning |
|---|---|---|
| `--folder <path>` | required | Working directory for the harness. Must exist and be a directory. It is made absolute and becomes the harness process's own working directory. See below for what it decides. |
| `--harness <key>` | required | Which harness to start. Must be installed. |
| `--prompt-file <path>` | optional | File holding the launch prompt, UTF-8. Without it the harness starts with no prompt and waits in its own interface. |
| `--model <string>` | optional | Model string, passed through to the harness opaquely. peeragent does not validate it; the per-harness flag it is mapped to is in [harnesses.md](harnesses.md). |
| `--resume` | optional | Continue the harness session for this directory. What that means per harness, and which harnesses only support it experimentally, is in [harnesses.md](harnesses.md). |
| `--git-repo` | optional | Run `git init -b main` in `<folder>` when it is not a git repository yet. No commit, no remote. |
| `--boot-wait <seconds>` | optional | How long to wait after the start before the first capture. Whole number from 1 to 120, default 5. A replay under `--resume` can take longer than the default, so a higher value is useful there. |

**What the working directory decides**

`--folder` is not a convenience. The launched harness inherits
nothing from the caller: not the shell's current directory, not the
directory the prompt file sits in. Its working directory is the path
given here, and four things follow from it.

- **What the harness can see.** It starts in that directory and
  reads relative paths against it. A task file placed elsewhere is
  out of reach unless the prompt names an absolute path.
- **What the harness asks to trust.** The trust question of the
  first start covers this directory, and for some harnesses the
  whole repository it lies in, which can be much larger than
  intended. [harnesses.md](harnesses.md) has it per harness.
- **Where the session history goes, and what `--resume` finds.**
  Harnesses key their session store by the working directory, so
  `--resume` continues the session belonging to this path. Starting
  one directory above the project therefore continues nothing, and
  the earlier history stays where it was.
- **The name of the tmux session**, which embeds the directory's
  base name.

peeragent sets it twice where it can: as the working directory of
the process, and through the harness's own directory option where
one exists. The two are not the same thing — for one harness the
trust question follows the repository containing the directory it
was given, and ignores where the process was started.

Pass the directory the work happens in, not its parent and not the
place peeragent is called from. If a caller passes the parent, every
command still succeeds: the harness starts, the prompt arrives, and
the session is anchored one level too high. Nothing reports an
error, which is why the choice is worth a deliberate moment.
[troubleshooting.md](troubleshooting.md) lists the symptoms.

**Preflight, in this order**

1. tmux installed, otherwise `fatal` (3).
2. Harness key known, otherwise `fatal` (2); harness installed,
   otherwise `fatal` (3).
3. `<folder>` exists and is a directory, otherwise `fatal` (2).
4. `<folder>` contains `.git` while `--git-repo` is set, which is
   `fatal` (2) with the hint that the folder is already a git repo.
5. With `--git-repo`: git installed, otherwise `fatal` (3).
6. With `--resume` on a harness whose resume support is
   `unsupported`: `fatal` (2).
   No harness carries that value in this version; the step is
   provision for later handlers.
7. With `--prompt-file`: the file exists, is regular, is readable
   and is not empty, otherwise `fatal` (2). Its effective length is
   at most 120 characters, otherwise `fatal` (2) with the hint to
   write the assignment into a file and point at it. The rule is the
   same for `send`; see below for how the length is counted.
   peeragent does not check the encoding of the file and never
   refuses one because of it.

**How the prompt length is counted, and why it is limited**

A launch prompt is a pointer, not the assignment. peeragent
enforces that: above 120 effective characters the call is refused
with exit code 2 before anything is started.

Effective length is counted like this, identically in both
implementations:

1. The file content is read as UTF-8.
2. Whitespace at both ends is removed. Whitespace is exactly four
   code points: space, tab, carriage return and line feed. No
   others, so that both implementations split the same text the
   same way.
3. The rest is split on those same four code points.
4. Every token that begins with `/` is dropped.
5. The remaining tokens are joined with one space each.
6. The Unicode code points of that string are counted.

Paths therefore cost nothing, as long as they start with `/` and
contain no spaces. A pointer may name the task file and the place
to write the report without spending budget, and a deep directory
tree does not eat into the text. There is no flag that lifts the
limit.

The rule is deliberately coarse. It does not recognise paths, it
drops tokens that look like one: a path containing a space counts
in part, a path in quotes or inside a Markdown link counts in full,
a relative path and a URL count in full, and in a script without
word boundaries the whole text is one token that fits far more
assignment into 120 code points than English does. None of that is
worth a second rule set to maintain in two languages. The limit
exists so that the assignment ends up in a file, not so that it
measures fairly. If a pointer is refused although it is one, write
the path without quotes and without spaces. A prompt that does not fit belongs in a file:
write it into the working directory and point at it, as
[../examples/prompt-file-template.md](../examples/prompt-file-template.md)
shows.

The reasons are practical. Three of the five harnesses receive the
prompt as a command-line argument, where it is visible to every
user of the host in the process list. A long prompt is also out of
sight as soon as the pane has scrolled on, while a task file can be
read again at any time, including on request. And a file can be
versioned, re-read and referred to; a command line cannot.

**Flow after a passed preflight**

1. With `--git-repo` and no `.git` in `<folder>`:
   `git init -b main`.
   A failure is `fatal` (1) and no harness is started.
   If `<folder>` lies inside an enclosing repository, the
   initialization still happens and a `warn` about the nested
   repository follows.
2. The argv is assembled from the harness launch arguments, the
   resume arguments if any, the model arguments if `--model` was
   given, and the prompt text if the harness receives the prompt as
   a command-line argument.
3. `agent.starting` reports `harness`, `folder`, `model`, `resume`
   and `prompt_file`.
4. With `--resume` on a harness whose resume support is
   `experimental`: a `warn` with `user_relevant: true` and a
   harness-specific `hint`.
5. The tmux session is created, named
   `peeragent-<sanitized-folder-basename>-<harness>-<8 hex>`, and
   the harness is started in its pane.
6. peeragent waits `--boot-wait` seconds, measured from the start of
   the harness process.
7. Diagnosis.
   If the session is gone, the harness did not survive the boot
   wait: `agent.exited` says so and the run ends with exit code 4.
   There is no exit status and no pane content to report, because
   the session went with the harness. No `agent.started` follows.
   Otherwise `agent.pane` reports the session name, the classified
   `awaiting` value and the visible pane lines.
   For `trust_prompt`, `auth_prompt`, `provider_prompt` and
   `unknown` a `warn` with `user_relevant: true` and a `hint`
   follows; for `trust_prompt` the `hint` contains the complete
   `tmux send-keys` line that confirms the prompt.
8. If the screen is `ready`, the harness receives its prompt through
   the terminal, and a prompt file was given: the prompt is pasted,
   `agent.prompt_sent` reports the delivered byte count, peeragent
   waits 2 seconds and emits a second `agent.pane`.
9. If a prompt file was given and the prompt was not delivered:
   `agent.prompt_deferred` with `session`, `prompt_file`,
   `awaiting`, `delivery` and a delivery-specific `hint`.
   This happens for terminal delivery whenever `awaiting` is not
   `ready`, and for command-line delivery when `awaiting` is
   `trust_prompt`, `auth_prompt`, `provider_prompt` or `unknown`.
   On `busy` and `ready`, a prompt passed on the command line counts
   as delivered.
10. `agent.started` reports the session name, the pane PID, the
    child processes and a `hint` with the read-only attach line
    `tmux attach -r -t '=<session>'`.

The harness keeps running in tmux after peeragent returns, on its
 own and with no connection back to the caller. Talking to it later
 needs a mechanism arranged in the assignment; the recommended ways
 are in [../README.md](../README.md).
peeragent never ends a session, under any circumstances. It holds no
session without a harness in it, so there is nothing for it to clean
up.

**Output**

The preflight `info` messages, then the messages of the flow above
in that order.
The `awaiting` values and what to do about each of them are in
[output-format.md](output-format.md) and
[troubleshooting.md](troubleshooting.md).

**Exit codes:** 0 on a successful start, including a start that ends
in a trust prompt or a deferred prompt; 1 for a failed `git init` or
a failed session creation; 2 for argument and path problems; 3 for a
missing tool or harness; 4 when the harness is no longer alive after
the boot wait; 130 on SIGINT during the boot wait, which leaves the
session standing.

**Prompt files**

peeragent reads the prompt file to count its effective length and
to remove trailing newlines before a paste.
There is no templating and no preprocessing.
A prompt that is passed on the command line is visible in the
process list of the host, so a prompt with confidential content
belongs into a session delivered with `send`, or into a task file
that a short pointer prompt refers to.
The pointer-prompt convention and ready-made templates are in
[../skills/launch-peer-agent/SKILL.md](../skills/launch-peer-agent/SKILL.md)
and [../examples/prompt-file-template.md](../examples/prompt-file-template.md).

## `peeragent send`

Delivers a prompt into a running session, typically after the caller
has answered a trust prompt and has seen `agent.prompt_deferred`
with `delivery: "send_keys"`.

**Synopsis**

```text
peeragent send --session <name> --prompt-file <path>
               [--wait <seconds>] [global flags]
```

**Flags**

| Flag | Required | Meaning |
|---|---|---|
| `--session <name>` | required | The tmux session, exactly as reported by `agent.started`. |
| `--prompt-file <path>` | required | File holding the prompt, UTF-8. |
| `--wait <seconds>` | optional | How long to wait after the paste before the second capture. Whole number from 0 to 120, default 2. |

**Preflight, in this order**

1. tmux installed, otherwise `fatal` (3).
2. The session exists, otherwise `fatal` (2).
3. The handler is determined from the session name.
   If one was determined, the harness is detected and the success
   `info` is emitted; a harness that is not installed yields a
   `warn` and not a `fatal`, because `send` does not need the
   binary.
4. The prompt file is checked as in `start agent` step 7,
   otherwise `fatal` (2). The length limit applies here too:
   without it, `send` would be the way around the pointer rule.
5. The session is still there, otherwise `fatal` (2): no session
   means no harness to paste into.

**Handler determination**

The session name is matched right-anchored against
`^peeragent-(.+)-(claude|codex|agy|opencode|copilot)-([0-9a-f]{8})$`,
and the second group is the harness key.
A name that does not match is reported with `awaiting: "unknown"`
and no handler is used.

**Flow**

A capture yields the first `agent.pane`.
The prompt is then pasted regardless of the `awaiting` value,
because the caller has already decided, and `agent.prompt_sent`
reports the byte count.
After `--wait` seconds a second capture yields the second
`agent.pane`.

A paste that arrives while the harness is working is buffered by the
harness interface and processed after the current turn; that was
tested with copilot on 2026-09-23.

**Output**

The preflight `info` messages, `agent.pane`, `agent.prompt_sent`,
`agent.pane`.

**Exit codes:** 0; 1 when the paste itself fails, because the paste
is the whole operation of this subcommand; 2 for a missing session,
a session whose harness has exited, or a prompt-file problem; 3 for
a missing tmux.

Call `send` only after an `agent.prompt_deferred`.
Calling it without that message risks delivering the same prompt
twice.
With `delivery: "argv"` the prompt may have been picked up already;
capture the pane first and send only if the input line is empty.

## `peeragent duplicate`

Copies a working directory and, for a harness that supports it, the
session history that belongs to the source directory, so that the
copy can continue the conversation.

**Synopsis**

```text
peeragent duplicate --from <src> --to <dst> --harness <key>
                    [global flags]
```

**Flags**

| Flag | Required | Meaning |
|---|---|---|
| `--from <src>` | required | Source working directory. Must exist and be a directory. |
| `--to <dst>` | required | Destination path. The parent directory must exist. |
| `--harness <key>` | required | Whose session store is copied along with the directory. |

**Preflight, in this order**

1. Harness key known, otherwise `fatal` (2).
2. The harness supports duplication, otherwise `fatal` (2) before
   any copying, with a harness-specific `hint` naming the harness
   command that can continue the session instead.
3. `<src>` exists and is a directory, otherwise `fatal` (2).
4. The parent directory of `<dst>` exists, otherwise `fatal` (2).
5. `<dst>` does not lie inside `<src>` and `<src>` does not lie
   inside `<dst>`, otherwise `fatal` (2).
6. The harness is installed, otherwise `fatal` (3).
7. No session store for `<dst>` exists yet, otherwise `fatal` (1)
   with the message that the session store for the destination
   already exists.
8. Either `<dst>` does not exist, or it passes a cheap check: the
   number and the names of the top-level entries of `<src>` and
   `<dst>` are equal, hidden entries included.
   Otherwise `fatal` (1) with the message that the destination
   exists and differs from the source.

Step 8 makes a second call for another harness on the same
destination possible without copying the tree twice.

**Support per harness**

In this version `claude` is the only harness whose session store is
duplicated.
For `codex`, `copilot`, `agy` and `opencode` the call is refused in
preflight step 2, and the `hint` names the harness-native way to
continue a session in the copy.
The reason per harness and the state of that assessment are in
[harnesses.md](harnesses.md) and
[../MATURITY.md](../MATURITY.md).

**Flow**

1. If `<dst>` does not exist, the whole tree is copied with
   attributes and symlinks preserved, and `info` `copied workspace`
   reports `files` and `bytes`.
   If `<dst>` exists and passed the cheap check, the copy is skipped
   and `info` reports `workspace already present, skipped copy`.
2. The session store is copied, and `harness.duplicated` reports
   `key`, `status`, `files`, `bytes` and the session directory.
   If no session store was found for `<src>`, a `warn` with
   `user_relevant: true` precedes it and the message carries
   `files: 0`, `bytes: 0` and `session_dir: null`.
   That is not an error.
3. `info` `duplicate complete` closes the run, with a `hint` that
   the copied working tree shares origin and branch with the source
   and that the first start in the copy may show a trust prompt.

`files` counts the regular files in the copied tree and `bytes` is
the sum of their sizes.

**Output**

The preflight `info`, the workspace `info`, `harness.duplicated`,
the closing `info`.

**Exit codes:** 0; 1 when the destination session store exists or
the cheap check fails; 2 for an unsupported harness, an unknown key
or a path problem; 3 for a harness that is not installed.

A copy made this way contains `.git` if the source had one, so a
later `start agent --git-repo` on the copy is `fatal` (2).

## `peeragent version`

Reports the version of the running implementation.

**Synopsis**

```text
peeragent version [global flags]
```

**Flags:** none besides the global flags.

**Output**

In plain text a single line `peeragent <version>`.
With `--json` a single `version` message carrying `version` and
`impl`, where `impl` names the implementation that ran.

**Exit codes:** 0.

## Global flags

| Flag | Meaning |
|---|---|
| `--json` | JSONL output instead of plain text, see [output-format.md](output-format.md). Recognized before argument parsing: an argv element that is exactly `--json`. |
| `--no-log` | Write no log file. |
| `--log-file <path>` | Write the log to this path instead of the default location. Together with `--no-log` it is `fatal` (2). |
| `--verbose` | Also print `debug` and `timing` messages on stdout. They always go into the log. |
| `--no-color` | No ANSI colors, in addition to the effect of `NO_COLOR`. |
| `--boot-wait <seconds>` | Only for `start agent`. On another subcommand it is `fatal` (2). |
| `--wait <seconds>` | Only for `send`. On another subcommand it is `fatal` (2). |
| `--help`, `-h` | Recognized before argument parsing, like `--json`, and takes precedence over it: a usage text on stdout, exit code 0, no log file and no JSON array. |

An argument error under `--json` appears as a `fatal` message inside
the array with exit code 2; no usage text is printed on stdout.

### Environment

Nothing is configured through the environment.
The variables peeragent reads are `HOME`, `NO_COLOR`, `TMUX` (only
to note in the log that peeragent itself runs inside tmux), `TMPDIR`
with `/tmp` as the fallback, and the harness configuration
directories `CLAUDE_CONFIG_DIR`, `CODEX_HOME` and `COPILOT_HOME`
where they are set.

Every external call runs with stdin closed, with stdout and stderr
captured, and under a timeout: 10 seconds for harness detection and
tmux calls, 30 seconds for `git init`.
Nothing a subprocess prints is passed through to stdout.

## Where to go next

- [output-format.md](output-format.md) for the message types, their
  fields, the `awaiting` values, the exit codes and the log files.
- [harnesses.md](harnesses.md) for per-harness behaviour, session
  stores, prompt wordings and key sequences.
- [troubleshooting.md](troubleshooting.md) for what to do when a
  start does not end in a working harness.
- [../examples/quick-start.md](../examples/quick-start.md) for one
  complete session from the first call to the finished task.
- [glossary.md](glossary.md) for the terms used here.
