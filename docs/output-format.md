# Output format

peeragent writes one message per event.
Without flags those messages are lines of plain text for a human
reader; with `--json` they are JSON objects in a frame that is both
a valid JSON array and readable line by line.
This file describes the plain-text templates, the JSON frame, the
complete message vocabulary with the fields of each type, the
`awaiting` values, the exit codes and the log files.

It describes the promised output contract, not the state of the
code: which parts already exist and how strongly each statement is
backed is recorded in [../MATURITY.md](../MATURITY.md).

Which subcommand emits which messages, and in which order, is in
[cli.md](cli.md).
The order of messages per subcommand is normative, and so are the
message types, their field names and the exit codes.
The wording of `msg` and `hint` is not, apart from the fixed
preflight success messages listed in [cli.md](cli.md); it may change
between releases.

## Plain text, the default

One line per message, with continuation lines indented by two
spaces.
ANSI colors are used only when stdout is a terminal, `NO_COLOR` is
empty and `--no-color` is absent: `warn` yellow, `error` and `fatal`
red, nothing else colored.

| Type | Line |
|---|---|
| `info` | `<msg>`; with a hint, a second line `  hint: <hint>` |
| `warn` | `warning: <msg>`; with a hint, `  hint: <hint>` |
| `error` | `error: <msg>` and `  hint: <hint>` |
| `fatal` | `fatal: <msg>` and `  hint: <hint>` |
| `debug` | `debug: <msg>` (only with `--verbose`) |
| `timing` | `timing: <step> <ms>ms` (only with `--verbose`) |
| `harness.detected` | `<key>  <version or "version unknown">  <path>  (<description>)` |
| `harness.missing` | `<key>  not installed  (<description>)` |
| `model.available` | `<harness>/<key>  <description>  [catalog <catalog_updated>]` |
| `agent.starting` | `starting <harness> in <folder>`, extended by ` (resume)`, ` model <model>` and ` prompt <prompt_file>` where those apply |
| `agent.pane` | `session <session> awaiting <awaiting>`, then the pane lines indented |
| `agent.prompt_sent` | `prompt sent to <session> (<bytes> bytes)` |
| `agent.prompt_deferred` | `prompt not delivered to <session> (<delivery>)` and `  hint: <hint>` |
| `agent.exited` | `harness exited in <session> with status <exit_status>`, then the pane lines indented, then `  hint: <hint>` |
| `agent.started` | `started <session> pane_pid <pane_pid>`, then one line `  <pid> <comm> <args>` per child process, then `  hint: <hint>` |
| `harness.duplicated` | `duplicated <key> session store: <files> files, <bytes> bytes` |
| `version` | `peeragent <version>` |

Plain text is for reading.
Anything that parses the output uses `--json`.

## JSONL with `--json`

With `--json`, stdout is a pseudo-array: an opening `[`, one message
object per line, a line holding a single `,` between two objects,
and a closing `]`.

```text
[
{"type":"info","msg":"tmux found: 3.5a","user_relevant":false}
,
{"type":"harness.detected","key":"claude","version":"2.1.278 (Claude Code)","description":"Claude Code CLI (Anthropic)","path":"/usr/local/bin/claude","user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-foo-claude-a3f1c9e2","awaiting":"ready","lines":["Welcome"],"user_relevant":false}
]
```

A consumer can read this line by line, skipping `[`, `]` and the
`,` lines and parsing each remaining line as one object, or read the
whole output at once as a JSON array.
That is where the name comes from.

### Frame rules

- Encoding is UTF-8, the line ending is LF.
- `[` is the first thing on stdout.
  It is written as soon as `--json` has been recognized, before
  argument parsing, so that even an argument error appears inside
  the array.
  The last line is `]`.
- Each object occupies exactly one line.
  Between two objects there is a line holding `,`.
  Empty output is `[` and `]` on two lines.
- An argument error is a `fatal` message inside the array with exit
  code 2.
  No usage text is printed on stdout.
- `--help` and `-h` are recognized before parsing as well and take
  precedence over `--json`: the usage text is printed and no array
  is opened.
- Numbers are unquoted, booleans are `true` and `false`, and an
  absent optional value is `null`.
- Field order inside an object and whitespace are free.

### Escaping

Both implementations escape the same way: `\` becomes `\\`, `"`
becomes `\"`, LF becomes `\n`, CR becomes `\r`, TAB becomes `\t`,
and any other character below 0x20 becomes `\u00XX`.
A NUL byte is removed.
Invalid UTF-8 is either replaced by U+FFFD or removed; which of the
two happens is left to the implementation, because captured pane
content is not compared byte for byte.
Everything else stays raw, including non-ASCII characters and the
box-drawing and prompt characters that harnesses print.

### A structural contract, not a byte contract

peeragent ships as two implementations of the same behaviour.
Both outputs are accepted by a JSON parser and yield the same
message types in the same order with the same field names and
semantically equal values.
Byte-level equality is explicitly not promised: field order and
whitespace may differ.
The test that checks this equivalence is described in
[architecture.md](architecture.md).

### Termination and signals

The emitter closes the array even when the run fails.
It registers an exit handler and handlers for SIGINT, SIGTERM and
SIGHUP; each of them writes `]`, closes the log and exits with 128
plus the signal number, so SIGINT ends the run with exit code 130.
A broken pipe ends the run silently.
Only SIGKILL prevents the closing `]`, so a line-by-line parser
should tolerate a missing one.

### What reaches stdout

Every message goes through the emitter, including every `warn`.
Output of subprocesses such as `git init`, `<harness> --version`,
`tmux` and `ps` is captured and never passed through.
Only interpreter warnings and emergencies of the emitter itself
reach stderr.

`debug` and `timing` always go into the log and reach stdout only
with `--verbose`, and then inside the array.
`invocation` and `env` go into the log only and never reach stdout.

## Message vocabulary

Every message is a JSON object with `type` and `user_relevant`
(boolean, always present).
The base types also carry `msg`.
All other fields depend on the type.

### Base types

| Type | Meaning | Fields |
|---|---|---|
| `info` | Unremarkable progress information | `msg`; optional `hint`, `bytes`, `files` |
| `warn` | Remarkable, the operation continues | `msg`; optional `hint` |
| `error` | A sub-operation failed, the overall operation continues | `msg`, `hint` (required) |
| `fatal` | The overall operation was aborted | `msg`, `hint` (required) |
| `debug` | Internal detail; log, and stdout only with `--verbose` | `msg` |

A `fatal` ends the operation, and the emitter still closes the
array.

### Domain-specific types

| Type | Where it appears | Fields |
|---|---|---|
| `harness.detected` | `list harness` only | `key`, `version` (string or `null`), `description`, `path` |
| `harness.missing` | `list harness` only | `key`, `description` |
| `model.available` | `list models` | `harness`, `key`, `description`, `catalog_updated` |
| `agent.starting` | `start agent`, before the harness is spawned | `harness`, `folder`, `model` (string or `null`), `resume` (bool), `prompt_file` (absolute path or `null`) |
| `agent.pane` | after the boot wait, after a paste, and twice in `send` | `session`, `awaiting`, `lines[]` |
| `agent.prompt_sent` | after a successful paste | `session`, `bytes` (size of the prompt file) |
| `agent.prompt_deferred` | `start agent`, when the prompt was not delivered | `session`, `prompt_file`, `awaiting`, `delivery` (`argv` or `send_keys`), `hint` |
| `agent.exited` | `start agent`, when the harness is no longer alive after the boot wait | `session`, `exit_status` (number or `null`), `lines[]`, `hint` |
| `agent.started` | `start agent`, as the last message | `session`, `pane_pid`, `child_processes[]` of `{pid, comm, args}`, `hint` |
| `harness.duplicated` | `duplicate` | `key`, `status` (`ok` or `experimental`), `files`, `bytes`, `session_dir` (path or `null`) |
| `version` | `version --json` | `version`, `impl` |

Notes on the fields:

- `session` is the tmux session name, in the form
  `peeragent-<sanitized-folder-basename>-<harness>-<8 hex>`.
  It is what `send --session` expects.
- `lines[]` is the visible pane content with trailing blank lines
  and trailing whitespace per line removed, and otherwise unchanged.
  In `agent.exited` the lines come from the scrollback and are cut
  to the last 50 non-empty lines, because the output of a harness
  that died is no longer in the visible area.
- `exit_status` is `null` when the harness died without reporting a
  status.
- `child_processes[]` lists the descendants of the pane process down
  to two levels.
  `comm` is truncated by the kernel to 15 characters and does not
  identify the harness reliably; `args` is the dependable column.
  When no process listing is available the list is empty and a
  `warn` follows.
- `agent.started.hint` carries the read-only attach line
  `watch with: tmux attach -r -t '=<session>'`.
- `status` in `harness.duplicated` is `ok` or `experimental`.
  A harness that does not support duplication never reaches this
  message, because the preflight refuses the call first.
  When no session store was found for the source, `files` and
  `bytes` are `0`, `session_dir` is `null`, and a `warn` precedes
  the message.
- `model.available` and `harness.detected` follow the selection-object
  pattern: `key` is the value for the next call, `description` is
  the explanation for the reader.

### Types that appear in the log only

| Type | Where it appears | Fields |
|---|---|---|
| `invocation` | first message of every log | `argv` (with `argv[0]` set to `peeragent`), `timestamp` (UTC, ISO 8601 with `Z`), `pid`, `cwd` |
| `env` | second message of every log | `impl`, `impl_version` (interpreter version), `peeragent_version`, `tmux`, `git`, `gh` (first line of the version output, or `null`), `vars` (object, redacted) |
| `timing` | log, once per step; stdout with `--verbose` | `step`, `ms` |

`timing.step` is one of `preflight`, `git-init`, `tmux-create`,
`boot-wait`, `diagnose`, `paste`, `paste-wait`, `process-tree`,
`workspace-copy`, `session-copy`.
Not every step occurs in every subcommand.

## `user_relevant` and `hint`

`user_relevant` is present in every message.
It is `true` on every `error`, on every `fatal`, and on those `warn`
messages that a human has to know about: a harness waiting for a
trust confirmation, a resume on a harness where resume is only
experimental, a prompt file above 100 KiB, a missing session store
in `duplicate`, a log file that could not be created, a missing
process listing.

A caller that drives peeragent programmatically uses the marker to
decide whether to interrupt the human: `user_relevant: false` is
progress it can absorb itself, `user_relevant: true` is something
the human should see.

`hint` is a single string that says what to do next.
It is required on `error` and `fatal` and accompanies every
`user_relevant` warning.
Hints are written to be actionable: they contain the complete
command to run, for example the `tmux send-keys` line that confirms
a trust prompt, or the `peeragent send` line that delivers a
deferred prompt.

With `--no-log` in effect, a `fatal` hint carries the addition to
re-run without `--no-log` to capture a log file.

### The hints of `agent.prompt_deferred`

With `delivery: "send_keys"` the harness receives prompts through
its terminal, and the hint is the delivery command:

```text
deliver with: peeragent send --session <session> --prompt-file <file>
```

With `delivery: "argv"` the prompt was already on the command line
of the harness process, so it may have been consumed once the
blocking dialog is answered.
The hint says so:

```text
the prompt was passed as a command-line argument; after answering
the prompt, capture the pane - if the harness did not pick it up
(input line empty), deliver with: peeragent send --session
<session> --prompt-file <file>
```

`send` is called after an `agent.prompt_deferred` and not otherwise;
see [cli.md](cli.md).

## The `awaiting` values

`agent.pane.awaiting` classifies the screen that peeragent captured.

| Value | Meaning | What the caller does |
|---|---|---|
| `ready` | The input prompt is visible and the harness is waiting | Continue; with terminal delivery peeragent has already pasted the prompt |
| `busy` | The harness is working | Wait and watch the pane with `tmux capture-pane -t "=<session>:" -p`; a paste that arrives now is buffered and processed after the current turn |
| `trust_prompt` | The harness asks whether it may work in this directory | Send the key sequence from the `hint`, or ask the human; then follow the hint of `agent.prompt_deferred` |
| `auth_prompt` | The harness is not logged in | Tell the human; the login happens outside peeragent |
| `provider_prompt` | The harness needs a provider configuration | Tell the human |
| `error` | Reserved and not assigned in this version; a harness that died yields `agent.exited` instead | Not applicable |
| `unknown` | No pattern matched | Show `lines[]` to the human and ask |

The precedence between several matching patterns is
`trust_prompt` before `auth_prompt` and `provider_prompt`, those
before `busy`, and `busy` before `ready`.
`busy` outranks `ready` because at least one harness keeps its empty
input line on screen while it works, so a `ready` match alone is not
evidence that the harness is idle.
For the same reason the patterns for `busy` are narrow: only text
that appears exclusively while the harness works counts.

A screen that matches none of the waiting patterns is captured a
second time after two seconds.
If the two captures differ, `awaiting` is `busy`, because the
harness is evidently producing output even though no text marker
matched.
The reported `lines[]` is the second capture.

The per-harness patterns, the wording of the dialogs and the key
sequence that confirms each trust prompt are in
[harnesses.md](harnesses.md).
What to do with each state in practice is in
[troubleshooting.md](troubleshooting.md).

## Exit codes

| Code | Meaning | Examples |
|---|---|---|
| `0` | Success, also with warnings or single errors | A recognized trust prompt, a deferred prompt, `list harness` without a single installed harness |
| `1` | Runtime failure | `git init` failed, session creation failed, a session-name collision that persisted over five attempts, the destination session store already exists, the cheap check on the destination failed, the paste in `send` failed |
| `2` | Argument validation | Unknown flag or subcommand, unknown harness key, missing folder, `.git` conflict with `--git-repo`, prompt file missing, empty or too large, duplication not supported for this harness, `--no-log` together with `--log-file`, missing session in `send`, `--boot-wait` or `--wait` on the wrong subcommand |
| `3` | A tool or harness is not installed | tmux missing, a known harness missing, git missing with `--git-repo` |
| `4` | The harness was no longer alive after the boot wait | `agent.exited` |
| `130` | SIGINT | Interruption during the boot wait or a wait; the tmux session is left standing |

When several codes would apply, the code of the first `fatal` in
preflight order wins.
A missing tmux is therefore code 3 even when the folder is also
missing, because the tmux check comes first.

The exit code is deliberately coarse.
The detail is in the messages, and under `--json` the output is
complete even on a non-zero exit, because the emitter closes the
array.

## Log files

Every invocation writes one log file.
Its purpose is a single one: a tester who runs into a problem can
attach files to a report.

**Location and name.**
The default directory is `~/.local/state/peeragent/logs/`, created
with mode 0700.
The file name is
`<yyyy-mm-dd>_<hhmmss>_<action>_<pid>.jsonl`, with the time in UTC
and the action token taken from `list-harness`, `list-models`,
`start-agent`, `send`, `duplicate`, `version` or `invalid` for an
argument error.
The directory grows without bound; nothing rotates it.

**Content.**
The log is JSONL in the same `[`, `,`, `]` frame as `--json`
output, and it is JSONL even when stdout is plain text.
It is opened after argument parsing, and the emitter buffers
messages until then.
The first message is `invocation`, the second is `env`, and after
those come all messages of the run including `debug` and `timing`.
The same handler that closes the array on stdout closes the log.
`--help` produces no log.

**Switches.**
`--no-log` suppresses the log file.
`--log-file <path>` writes it elsewhere; combined with `--no-log`
that is `fatal` (2).
If the log file cannot be created, for example because the directory
is not writable or `--log-file` points into a directory that does
not exist, a `warn` with `user_relevant: true` is emitted and the
run continues without a log.

**Environment redaction.**
`env.vars` is not a dump of the environment.
It holds `PATH`, `SHELL`, `TERM`, `LANG`, `LC_ALL`, `TMUX`, `HOME`
and the variables whose name starts with `PEERAGENT_`, `CLAUDE_`,
`CODEX_`, `GEMINI_`, `OPENCODE_`, `COPILOT_`, `ANTHROPIC_`,
`OPENAI_`, `GH_` or `GITHUB_`.
A value is replaced by `<redacted>` when its name matches
`TOKEN`, `KEY`, `SECRET`, `PASS`, `AUTH` or `CREDENTIAL`,
case-insensitively.
That is a deliberately simple rule, not a thorough scrubber.

**What a log reveals.**
Pane content is not redacted, and neither are paths.
A log file therefore contains the text of the launch prompt, the
absolute paths of the working directory and the prompt file, and
whatever the harness printed on its first screen, which can include
parts of the task.
Read a log before attaching it to a report.

Log rotation, a bundling subcommand, a diagnostics subcommand and a
configuration file do not exist.
The only switches are `--no-log` and `--log-file`.

## Example outputs

The examples below are shortened and use placeholder paths.
`/srv/foo` stands for a working directory.

`list harness --json` on a host where one harness is absent and one
did not answer the version query in time:

```text
[
{"type":"harness.detected","key":"claude","version":"2.1.278 (Claude Code)","description":"Claude Code CLI (Anthropic)","path":"/usr/local/bin/claude","user_relevant":false}
,
{"type":"harness.detected","key":"codex","version":"codex-cli 0.147.0","description":"OpenAI Codex CLI","path":"/usr/local/bin/codex","user_relevant":false}
,
{"type":"harness.missing","key":"agy","description":"Google Antigravity CLI","user_relevant":false}
,
{"type":"harness.detected","key":"opencode","version":null,"description":"OpenCode (anomalyco)","path":"/usr/local/bin/opencode","user_relevant":false}
,
{"type":"warn","msg":"opencode --version timed out after 10s","user_relevant":true,"hint":"the wrapper may be installing an update; retry or run 'opencode --version' manually"}
,
{"type":"harness.detected","key":"copilot","version":"GitHub Copilot CLI 1.0.88.","description":"GitHub Copilot CLI","path":"/usr/local/bin/copilot","user_relevant":false}
]
```

`start agent --harness claude --json` with a prompt that the harness
received on its command line and picked up immediately:

```text
[
{"type":"info","msg":"tmux found: 3.5a","user_relevant":false}
,
{"type":"info","msg":"harness claude found: 2.1.278 (Claude Code)","user_relevant":false}
,
{"type":"agent.starting","harness":"claude","folder":"/srv/foo","model":null,"resume":false,"prompt_file":"/srv/foo/prompt.txt","user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-foo-claude-a3f1c9e2","awaiting":"busy","lines":["Claude Code v2.1.278","","❯ Read /srv/foo/TASK.md and carry out the assignment described there.","✢ Reading TASK.md… (2s · thinking)","❯ "],"user_relevant":false}
,
{"type":"agent.started","session":"peeragent-foo-claude-a3f1c9e2","pane_pid":18320,"child_processes":[{"pid":18321,"comm":"npm","args":"npm exec @playwright/mcp"}],"hint":"watch with: tmux attach -r -t '=peeragent-foo-claude-a3f1c9e2'","user_relevant":false}
]
```

`start agent --harness copilot --json` where the harness asks for
directory trust first, so the prompt is deferred:

```text
[
{"type":"info","msg":"tmux found: 3.5a","user_relevant":false}
,
{"type":"info","msg":"harness copilot found: GitHub Copilot CLI 1.0.88.","user_relevant":false}
,
{"type":"agent.starting","harness":"copilot","folder":"/srv/foo","model":null,"resume":false,"prompt_file":"/srv/foo/prompt.txt","user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-foo-copilot-b7e2d0f1","awaiting":"trust_prompt","lines":["╭ Confirm folder trust ─────────────────────────────╮","│ /srv/foo                                          │","│ Do you trust the files in this folder?            │","│ ❯ 1. Yes                                          │","│   2. Yes, and remember this folder for future …   │","│   3. No (Esc)                                     │","╰───────────────────────────────────────────────────╯"],"user_relevant":false}
,
{"type":"warn","msg":"harness copilot is awaiting trust-prompt confirmation","user_relevant":true,"hint":"send '1' Enter to trust: tmux send-keys -t '=peeragent-foo-copilot-b7e2d0f1:' 1 Enter"}
,
{"type":"agent.prompt_deferred","session":"peeragent-foo-copilot-b7e2d0f1","prompt_file":"/srv/foo/prompt.txt","awaiting":"trust_prompt","delivery":"send_keys","hint":"deliver with: peeragent send --session peeragent-foo-copilot-b7e2d0f1 --prompt-file /srv/foo/prompt.txt","user_relevant":true}
,
{"type":"agent.started","session":"peeragent-foo-copilot-b7e2d0f1","pane_pid":18510,"child_processes":[{"pid":18511,"comm":"MainThread","args":"/usr/local/lib/copilot-linux-x64/copilot"}],"hint":"watch with: tmux attach -r -t '=peeragent-foo-copilot-b7e2d0f1'","user_relevant":false}
]
```

`send --json` into that session after the trust question was
answered:

```text
[
{"type":"info","msg":"tmux found: 3.5a","user_relevant":false}
,
{"type":"info","msg":"harness copilot found: GitHub Copilot CLI 1.0.88.","user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-foo-copilot-b7e2d0f1","awaiting":"ready","lines":["  █ ▘▝ █  Check for mistakes.","","❯"],"user_relevant":false}
,
{"type":"agent.prompt_sent","session":"peeragent-foo-copilot-b7e2d0f1","bytes":118,"user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-foo-copilot-b7e2d0f1","awaiting":"busy","lines":["❯ Read /srv/foo/TASK.md and carry out the assignment described there.","❯","○ Working esc interrupt"],"user_relevant":false}
]
```

`start agent` where the harness died during startup, which ends the
run with exit code 4.
The failure cause in this example is invented; the shape of the
message is not:

```text
[
{"type":"info","msg":"tmux found: 3.5a","user_relevant":false}
,
{"type":"info","msg":"harness agy found: 1.2.8","user_relevant":false}
,
{"type":"agent.starting","harness":"agy","folder":"/srv/foo","model":null,"resume":false,"prompt_file":null,"user_relevant":false}
,
{"type":"agent.exited","session":"peeragent-foo-agy-c1d2e3f4","exit_status":2,"lines":["error: unknown option '--no-such-flag'"],"hint":"the harness exited during startup; the tmux session was kept: tmux attach -t '=peeragent-foo-agy-c1d2e3f4'","user_relevant":true}
]
```

`duplicate --harness claude --json` on success:

```text
[
{"type":"info","msg":"harness claude found: 2.1.278 (Claude Code)","user_relevant":false}
,
{"type":"info","msg":"copied workspace","files":42,"bytes":52340,"user_relevant":false}
,
{"type":"harness.duplicated","key":"claude","status":"ok","files":1,"bytes":223173,"session_dir":"/home/user/.claude/projects/-srv-foo-branch","user_relevant":false}
,
{"type":"info","msg":"duplicate complete","user_relevant":false,"hint":"working tree shares origin and branch with source; the first start in the copy may show a trust prompt"}
]
```

`duplicate --harness codex --json`, which is refused in the
preflight before anything is copied:

```text
[
{"type":"fatal","msg":"duplicate for codex is not supported","user_relevant":true,"hint":"codex indexes sessions in a database that peeragent does not modify; use 'codex fork' or 'codex resume --all <id>' in the copied folder instead"}
]
```

`version --json`:

```text
[
{"type":"version","version":"0.1.0","impl":"python","user_relevant":false}
]
```

## Where to go next

- [cli.md](cli.md) for the subcommands, their flags and the order in
  which they emit these messages.
- [troubleshooting.md](troubleshooting.md) for the `awaiting` states
  and the common failure pictures.
- [harnesses.md](harnesses.md) for what each harness prints and
  expects.
- [architecture.md](architecture.md) for the equivalence contract
  between the two implementations.
- [../examples/quick-start.md](../examples/quick-start.md) for a
  complete session with its output.
