# Troubleshooting

peeragent starts a coding-agent harness in a tmux pane and reports
the first screen. Most of what looks like a failure is not one: the
harness is up and waiting for an answer that only you or the
calling agent can give. This document explains how to tell those
cases apart, what to do about each one, and what to put in a bug
report when something is genuinely wrong.

The overall state of the tool — what is implemented, what is only
specified, and how well each claim is backed — is in
[`../MATURITY.md`](../MATURITY.md). Flags and subcommands are in
[`cli.md`](cli.md), message types and field names in
[`output-format.md`](output-format.md), and the harness-specific
wording and key sequences in [`harnesses.md`](harnesses.md).

## The waiting states

After the boot wait, peeragent captures the pane and classifies it.
The result is the `awaiting` field of the pane message.

| `awaiting` | Meaning | What to do |
|---|---|---|
| `ready` | The input prompt is visible and the harness is waiting for input. | Carry on. If the harness takes its prompt by paste and you gave a prompt file, peeragent has already delivered it. |
| `busy` | The harness is working: a spinner, a streaming answer or a tool call. | Wait. Watch the pane with `tmux capture-pane`. A prompt sent while the harness is busy is buffered by the interface and processed after the running turn (tested for the GitHub Copilot CLI on 2026-09-23). |
| `trust_prompt` | The harness is asking whether it may work in this directory. | Send the harness's key sequence with `tmux send-keys`, or ask the user first. Afterwards follow the hint of the deferred-prompt message if there was one. |
| `auth_prompt` | The harness is not logged in. | Tell the user. The login happens outside peeragent and usually needs a browser. |
| `provider_prompt` | The harness has no model provider configured. Only OpenCode reaches this state. | Tell the user. Configure a provider inside the pane with `/connect`. |
| `error` | Reserved; not assigned in this version. A harness that died produces its own exited message and exit code 4 instead. | Nothing. If you do see it, report it. |
| `unknown` | No pattern matched. | Show the captured lines to the user and ask. This is also what an unrecognised waiting state looks like, for example the usage-limit dialog of the Codex CLI. |

A harness that is no longer alive after the boot wait gets no
`awaiting` value at all. It produces an exited message with the
pane's exit status and the last lines from the scrollback, and
peeragent leaves the tmux session standing so you can attach to it.

### Precedence

Several markers can match one screen at once, so the order is
fixed:

```text
trust_prompt  >  auth_prompt / provider_prompt  >  busy  >  ready
```

Nothing matched means `unknown`. The classification never falls
back to `ready`.

`busy` beats `ready` for a concrete reason. In the GitHub Copilot
CLI the bare `❯` input line stays on screen while the harness
works, next to the `○ Working esc interrupt` status line, and in
Claude Code it stays on screen while an answer streams (tested
2026-09-23). A screen with the `❯` line is therefore not proof
that the harness is idle. The busy markers are deliberately narrow:
only text that appears exclusively while the harness works counts.

That leaves one gap. While Claude Code streams an answer, the
spinner line is gone and no marker matches at all. peeragent
closes the gap by capturing twice, two seconds apart: if the two
captures differ and no trust, auth or provider marker matched, the
state is `busy`. This is why a start can take a little longer than
the boot wait suggests.

Markers are matched case-sensitively against the visible pane text.
When a harness changes its wording in a new release, the result
becomes `unknown` — never a wrong `ready`.

## All five harnesses block on the first start in a new directory

This is the normal case, not an edge case. Plan for it.

On 2026-08-17, four of five harnesses were not able to answer
anything five seconds after starting in a fresh directory: the
Codex CLI and the GitHub Copilot CLI asked for directory trust,
the Antigravity CLI asked for a login method, and OpenCode had no
provider. On 2026-09-23, Claude Code 2.1.278 was found to have a
trust prompt of its own. All five block.

| Harness | First screen in a fresh directory | Key sequence |
|---|---|---|
| `claude` | `trust_prompt` — the preselected option is `No, exit` | `Down Enter` |
| `codex` | `trust_prompt` — trust applies to the Git repository root | `1 Enter` |
| `agy` | `auth_prompt` — login method selection | none; log in outside peeragent |
| `opencode` | `provider_prompt` — no provider configured | none; run `/connect` in the pane |
| `copilot` | `trust_prompt` — `1` once, `2` remembers the folder | `1 Enter` |

The key sequences are `tmux send-keys` arguments, not characters
to type into the pane:

```bash
tmux send-keys -t "=<session>:" 1 Enter
tmux send-keys -t "=<session>:" Down Enter
```

For Claude Code the arrow key matters: the preselected option is
`No, exit`, so sending only `Enter` would close the harness. The
exact wording of every prompt is in
[`harnesses.md`](harnesses.md).

There are consequences for the start prompt:

- With the harnesses that take the prompt on the command line
  (`claude`, `codex`) the prompt survives the trust prompt and
  becomes the first turn once the trust question is answered
  (tested 2026-09-23 for both). Capture the pane after answering;
  only if the input line is empty does the prompt need to be
  delivered again. Delivering it twice sends it twice.
- With the harnesses that take the prompt by paste (`agy`,
  `opencode`, `copilot`) nothing was delivered, and peeragent says
  so with a deferred-prompt message. Answer the prompt first, then
  deliver with `peeragent send`.

Trust decisions are remembered per directory by Claude Code
(tested 2026-09-23), and the GitHub Copilot CLI offers a remember
option as its second choice. The second start in the same
directory is usually quiet.

## Common failure pictures

The exit code is the quickest classifier; the full list is in
[`cli.md`](cli.md).

| What you see | Exit | Cause | Remedy |
|---|---|---|---|
| `tmux` reported as missing | 3 | Starting a harness and sending a prompt both need tmux. | Install tmux with your distribution's package manager and run again. |
| A harness reported as missing | 3 | The binary is not on `PATH`. | Install it as described in [`harnesses.md`](harnesses.md). If it is installed under `~/.local/bin`, put that directory on `PATH`. |
| `git` reported as missing | 3 | Only requested because you asked peeragent to initialise a repository. | Install git, or drop the repository option. |
| Harness found, version unknown, plus a warning | 0 | The version query timed out or failed although the binary exists. | Run `<binary> --version` by hand. A self-updating launcher may be busy installing; OpenCode installs a package at startup. |
| The exited message with an exit status | 4 | The harness was no longer alive after the boot wait. | Read the reported lines: they come from the scrollback and usually carry the harness's own error. The session was kept, so attach and look. |
| Folder is already a git repository | 2 | You asked for a repository to be initialised in a folder that already has one. | Drop the repository option. |
| Prompt file missing, unreadable or empty | 2 | The path is wrong, or the file has no content. | Check the path. A prompt file must be non-empty UTF-8. |
| Prompt too long | 2 | The prompt holds more than 120 effective characters, so it is an assignment and not a pointer. | Write the assignment into a file in the working directory and pass a short prompt that points at it. Absolute paths do not count towards the length; the counting rule is in [`cli.md`](cli.md). |
| Prompt file not valid UTF-8 | 2 | The file is in another encoding, or it is not text at all. | Convert it to UTF-8. The length count needs the decoded text. |
| Duplicate refused before anything was copied | 2 | Only Claude Code sessions can be duplicated. The other four keep their sessions in a database or in an unknown layout. | Use the harness-native way named in the hint. |
| Session store for destination already exists | 1 | A previous duplicate already created the destination's session store. | Choose a different destination, or remove the stale store yourself. |
| Destination exists and differs from source | 1 | The destination directory is not a copy of the source. peeragent refuses rather than merge. | Choose an empty destination, or remove the existing one. |
| Session name collision | 1 | Five attempts at a random session suffix all collided. | Run again. If it repeats, list your tmux sessions; something is generating the same names. |
| Paste failed while starting | 0 | The clipboard handover to tmux failed, but the harness is running. | Deliver the prompt with `peeragent send`. |
| Paste failed while sending | 1 | The paste is the whole operation, so it fails the run. | Check that the session still exists and the pane is alive. |
| Child processes empty, plus a warning | 0 | `ps` is not available, so the process tree could not be read. | Cosmetic. Install the package that provides `ps` if you want the process list. |
| No log file, plus a warning | 0 | The log directory is not writable, or a given log path points into a directory that does not exist. | Create the directory, or pass a writable log path. |
| Interrupted run | 130 | You pressed Ctrl-C during the boot wait or a paste wait. | The tmux session is left standing. Attach to it or end it yourself. |
| Prompt is in the pane but nothing happened | 0 | The harness buffered the paste while it was busy, or it is waiting for a trust or login answer. | Capture the pane again a few seconds later. |

Harness-specific pictures worth knowing:

- **OpenCode, slow first start.** The launcher installs a package
  update before the interface appears (tested 2026-08-17), so the
  first start after an update can outlast the default boot wait.
  Raise the boot wait.
- **Codex CLI, usage limit.** A dialog beginning
  `You've hit your usage limit` with a model-switch menu is a
  waiting state peeragent has no marker for; it reports `unknown`
  (tested 2026-09-23). Answer it in the pane, or start again with
  a model your plan still serves.
- **Codex CLI, sandbox warning.** `Codex could not find bubblewrap
  on PATH` is harness output and startup continues (tested
  2026-09-23). It is not a peeragent warning.
- **Codex CLI, trust scope.** The trust question resolves the Git
  repository root and applies to all of it, not only to the folder
  you started in (tested 2026-08-17). Say so before you answer it
  on someone's behalf.
- **Claude Code, environment override.** An API key in the
  environment silently takes precedence over a working
  subscription (documented). peeragent logs the presence of such
  variables with the value masked.
- **GitHub Copilot CLI, resume fallback.** Without a session in the
  current directory, continuing falls back to the globally most
  recent session (documented), which may belong to another
  directory. peeragent warns about this when you resume copilot.
- **The peer agent works in the wrong directory.** This one
  reports no error at all, which is what makes it expensive. The
  symptoms: the harness says it cannot find the task file although
  the file is there; it lists unrelated projects when asked what it
  sees; the trust question named a path wider than expected; a
  later start with a continuation finds no session although one was
  created earlier; the tmux session name carries a base name you
  did not intend. The cause is almost always a working directory
  one level too high, usually the parent of the project or the
  directory peeragent was called from. Check it in the
  `agent.starting` message, which reports the absolute folder, and
  start again with the right one. Killing the misplaced session
  costs nothing; the harness keeps the history it wrote under the
  wrong path, so there is nothing to clean up beyond the session
  itself.
- **Trailing newline in a prompt file.** peeragent strips trailing
  newlines before pasting and always sends `Enter` separately,
  because a trailing newline inside the paste does not submit
  (tested for the GitHub Copilot CLI on 2026-09-23).

## Looking at the pane yourself

The harness keeps running in tmux after peeragent returns.
peeragent never ends a session once the harness has started, so
the pane is yours to inspect.

Watch without being able to type:

```bash
tmux attach -r -t "=<session>"
```

Print the visible pane, or the scrollback as well:

```bash
tmux capture-pane -t "=<session>:" -p
tmux capture-pane -t "=<session>:" -p -S -
```

Ask whether the pane is still alive:

```bash
tmux list-panes -t "=<session>" -F '#{pane_dead},#{pane_dead_status},#{pane_pid}'
```

While the pane lives, the middle field is empty. A dead pane
reports its exit status there, and the visible area then shows only
a `Pane is dead` line — the harness's own output has scrolled into
the scrollback, which is why the scrollback form above matters
(tested 2026-09-23 on tmux 3.5a).

Answer a trust prompt:

```bash
tmux send-keys -t "=<session>:" 1 Enter
```

Note the target form. Session-level commands take `=<session>`;
window and pane commands — capture, send-keys, paste-buffer,
respawn-pane — take `=<session>:` with the trailing colon. Without
the colon, tmux reads the name as a window name and the command
fails (tested on tmux 3.5a). The leading `=` forces an exact name
match.

The session name is in the started message, and it has the form
`peeragent-<folder>-<harness>-<8 hex digits>`. If you lost it:

```bash
tmux list-sessions | grep '^peeragent-'
```

End a session when you are done with it:

```bash
tmux kill-session -t "=<session>"
```

## Where the logs are and what they contain

peeragent writes one log file per run:

```text
~/.local/state/peeragent/logs/<yyyy-mm-dd>_<hhmmss>_<action>_<pid>.jsonl
```

The directory is created with mode 0700. The timestamp is UTC. The
action token is one of `list-harness`, `list-models`,
`start-agent`, `send`, `duplicate`, `version`, or `invalid` for an
argument error.

The log is JSONL even when the terminal output is plain text, and
it uses the same framing as the machine-readable output. It
contains every message of the run, including the diagnostic and
timing messages that the terminal hides unless you ask for them.
The first message records the invocation, the second the
environment.

The environment message carries a fixed set of variables: `PATH`,
`SHELL`, `TERM`, `LANG`, `LC_ALL`, `TMUX`, `HOME`, and every
variable whose name starts with one of the harness or provider
prefixes peeragent knows. A value is replaced by a redaction
marker when the variable name looks like a secret — names
containing `TOKEN`, `KEY`, `SECRET`, `PASS`, `AUTH` or
`CREDENTIAL`, matched without regard to case.

**Pane content is not redacted.** The captured lines go into the
log exactly as the harness printed them, and a harness can print
file paths, repository names, branch names or a token into its own
screen. Read a log before you send it to anyone.

You can move the log with a log-path option or switch it off
entirely; both are described in [`cli.md`](cli.md). With logging
off, a fatal message says so, because the log is the thing a bug
report needs most. There is no rotation and no bundling command:
the files accumulate until you delete them.

## What belongs in an issue

Use [`../.github/ISSUE_TEMPLATE/bug_report.md`](../.github/ISSUE_TEMPLATE/bug_report.md).
It asks for what is listed here, and filling it in saves a round
trip.

- The exact command you ran, with the flags, and the exit code.
- The peeragent version and which implementation you used.
- Your tmux version, from `tmux -V`, and whether you were inside
  tmux at the time.
- The harness key and the literal output of `<binary> --version`.
- The output of `peeragent list harness --json`. It names every
  harness peeragent found, with path and version string, which
  settles most detection questions in one paste.
- The log file of the failing run, reviewed first for anything you
  do not want to publish. If you ran with logging off, run again
  with it on.
- What you expected instead. A waiting state is usually not a bug,
  so say why you think this one is.

If the harness itself misbehaved rather than peeragent, include
your own pane capture. The scrollback form above is the one that
shows a dead harness's last words.

Redact before posting: absolute paths under your home directory,
repository and branch names, anything from the pane that names an
account, and the content of your prompt file. The prompt file is
the single most likely place for confidential material, and
peeragent has no way to know that.
