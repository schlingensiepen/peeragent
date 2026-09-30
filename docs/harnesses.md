# Harnesses

A harness is a coding-agent command-line program that peeragent
starts in a tmux pane. peeragent supports these and nothing else:
`claude`, `codex`, `agy`, `opencode`, `copilot`.

peeragent does not install, update, configure or log in to a
harness. It detects whether the binary is on `PATH`, asks it for
its version, starts it, and reports the first screen. Everything
else is the harness's own business.

This document collects the harness-facing facts: the binary, the
version query, the start arguments, the model flag, resume
support, where the harness keeps its session, how the start prompt
reaches it, whether a working directory can be duplicated, the
waiting states with their real wording and key sequence, and how
to install the harness when peeragent reports it missing.

The overall state of the tool is in [`../MATURITY.md`](../MATURITY.md).
peeragent's own flags are in [`cli.md`](cli.md), its message
fields in [`output-format.md`](output-format.md). This document
does not repeat them.

## How to read the evidence markers

Every statement below carries one of these markers. They are part
of the statement, not decoration.

| Marker | Meaning |
|---|---|
| `tested` | Seen on a test host during a recorded run. The date is given. |
| `documented` | From the harness's own `--help` or its official documentation. |
| `observed on a test host` | From a single host inspection, without a test run behind it. In prose this marker is often written out as a leading phrase, `On a test machine, ...`, so that the scope of the sentence stands before the claim and not after it. |
| `unverified` | An assumption. Nothing in the sources backs it. |

Harnesses update themselves. A version string can change between
two peeragent runs, and a harness can change its screen wording
in any release. When wording changes, the detection falls back to
`awaiting: "unknown"`, never to `ready`.

## The model catalogs are static

peeragent ships a fixed model list per harness and does not ask
the harness what it can actually serve. A model string is passed
through opaquely; the harness decides whether it accepts it, and
it usually decides that on the first request, not at startup.
None of the catalog entries is validated by peeragent, and an
entry can be unavailable on your plan or withdrawn by the
provider.

All five catalogs carry the same date: **2026-08-16**. They are
reproduced per harness below and are what `peeragent list models`
prints.

## Overview

| Key | Product | Binary | Prompt delivery | Resume | Duplicate | Trust answer | Version string seen 2026-09-23 |
|---|---|---|---|---|---|---|---|
| `claude` | Claude Code CLI (Anthropic) | `claude` | `argv` | `ok` | `ok`, tested | `Down Enter` | `2.1.278 (Claude Code)` |
| `codex` | OpenAI Codex CLI | `codex` | `argv` | `experimental` | `unsupported` | `1` | `codex-cli 0.147.0` |
| `agy` | Google Antigravity CLI | `agy` | `send_keys` | `experimental` | `unsupported` | `Enter` | `1.2.8` |
| `opencode` | OpenCode (anomalyco) | `opencode` | `send_keys` | `experimental` | `unsupported` | none | `1.18.25` |
| `copilot` | GitHub Copilot CLI | `copilot` | `argv` | `experimental` | `unsupported` | `1` | `GitHub Copilot CLI 1.0.88.` |

The version strings were `tested` on 2026-09-23, as the literal
first line of `<binary> --version` with whitespace stripped from
both ends. peeragent never compares or parses them.

`argv` means the prompt is the last element of the command line
that starts the harness. `send_keys` means peeragent pastes the
prompt into the running pane, and only when the pane is `ready`.
A `trust answer` is a `tmux send-keys` key sequence, not a
character to type: see [`troubleshooting.md`](troubleshooting.md).

## claude

### Binary and version query

The binary is `claude`. On a test machine, the native installer
had placed a symlink at `~/.local/bin/claude` pointing into
`~/.local/share/claude/versions/<version>`; a second installation
may well look different. Package installs put `claude` on `PATH`
directly (`documented`).

```bash
claude --version
```

The first line has the form `MAJOR.MINOR.PATCH (Claude Code)`
(`documented`); on 2026-09-23 it was `2.1.278 (Claude Code)`
(`tested`). Claude Code updates itself in the background and
reports `Update installed · Restart to update` in its status line
(`tested` 2026-09-23), so the version can differ between two
peeragent runs.

### Start arguments

peeragent starts `claude` with no extra arguments. With resume it
adds `--continue`.

### Model flag

`--model <model>` (`documented`). Aliases and full identifiers are
both accepted, and the value is validated on the first request,
not at startup (`documented`).

| Model key | Description |
|---|---|
| `default` | Account default (Opus 5 on Max/Team/Enterprise/API, Sonnet 5 on Pro) |
| `best` | Fable 5 where available, otherwise newest Opus |
| `fable` | Claude Fable 5 (opt-in) |
| `opus` | Newest Opus |
| `sonnet` | Newest Sonnet |
| `haiku` | Newest Haiku |
| `opus[1m]` | Opus with 1M token context |
| `sonnet[1m]` | Sonnet with 1M token context |
| `opusplan` | Opus for plan mode, Sonnet for execution |
| `claude-opus-5` | Claude Opus 5 |
| `claude-sonnet-5` | Claude Sonnet 5 |
| `claude-fable-5` | Claude Fable 5 |
| `claude-opus-4-8` | Claude Opus 4.8 |
| `claude-opus-4-7` | Claude Opus 4.7 |
| `claude-sonnet-4-5` | Claude Sonnet 4.5 |
| `claude-haiku-4-5` | Claude Haiku 4.5 |

### Resume

Supported (`ok`). `--continue` continues the most recent
conversation of the current directory. On 2026-09-23
`claude --continue "<prompt>"` produced the replay of the stored
conversation plus a new turn, and the trust decision for the
directory was remembered (`tested`). In an earlier run the replay
took about eight seconds (`tested` 2026-09-16), so a longer boot
wait is useful with resume.

### Session store

`<config>/projects/<sanitized-path>/`, where `<config>` is
`CLAUDE_CONFIG_DIR` if set and `~/.claude` otherwise. The
sanitizer replaces every character outside `[a-zA-Z0-9]` with `-`,
so `/srv/foo` becomes `-srv-foo`. A simple session is a single
`<uuid>.jsonl` file; a companion directory `<uuid>/` appears for
larger sessions (`tested` 2026-09-16). That `CLAUDE_CONFIG_DIR`
actually moves this directory is `unverified`.

### Prompt delivery

`argv`: the prompt text is the last argument of the command line.
On 2026-09-23 a three-line prompt file arrived unchanged, and it
survived the trust prompt — after the trust answer the harness
took it up as the first turn (`tested`). No paste is needed.

Because the prompt is an argument, it is visible in the process
list. For confidential material, put a pointer in the prompt file
and the content in a file the agent reads, or deliver the prompt
with `peeragent send` after the harness is ready.

### Duplicate

Supported (`ok`) and tested on 2026-09-16. Copying the working
directory and copying the project directory of the session store
is enough: no identifier is renamed and no path is rewritten. The
`cwd` field inside the copied session file stays at the old path
and the harness ignores it (`tested` 2026-09-16). A test in the copy answered
from the session context and did not re-read a deliberately
changed file, which is what makes the copy useful.

### Waiting states

**Trust prompt.** The first start in a new directory shows
(`tested` 2026-09-23, Claude Code 2.1.278):

```text
Accessing workspace: <folder>
Quick safety check: Is this a project you created or one you trust?
❯ No, exit
  Yes, I trust this folder
Enter to confirm · Esc to cancel
```

The markers are `Quick safety check` and
`Yes, I trust this folder`. The preselected option is `No, exit`,
so the answer is an arrow key followed by Enter:

```bash
tmux send-keys -t "=<session>:" Down Enter
```

The decision is remembered per directory; a second start in the
same directory does not ask (`tested` 2026-09-23).

**Auth prompt.** With an empty configuration directory the
onboarding dialog comes first — `Let's get started` and
`Choose the text style` — and `Select login method` follows after
Enter (`tested` 2026-09-23). Both texts are markers. There is no
key sequence for this: the login happens outside peeragent.

**Busy.** The marker is `· thinking)`, as in the spinner line
`✢ Pouncing… (1s · thinking)` (`tested` 2026-09-23). The second
marker `esc to interrupt` is `unverified`: it did not appear in the
test, and no source establishes it.

**Ready.** A line that is exactly `❯` once whitespace is stripped
(`tested`; Claude Code writes `❯ ` with a trailing space). The
same line stays visible while an answer streams, so `busy` wins
over `ready`. That is also why the second capture is taken for a
`ready` screen and not only for an unrecognised one: without it a
harness that is working would be reported as waiting for input.
After a finished turn the pane looks like this (`tested`
2026-09-23, model `haiku`):

```text
 ▐▛███▛█   Claude Code v2.1.278
▝▜██████▀  Haiku 4.5 · Claude Max
❯ Line one of the prompt: please answer with the single word ZEBRA.
  Line two: do not read any files.
  Line three: then stop.
● ZEBRA
✻ Cogitated for 1s · done
❯ 
```

The `✻` line marks the end of a turn, not work in progress, so it
is not a busy marker.

### Installing Claude Code

When peeragent reports `claude` as missing, install it from
Anthropic (`documented`):

```bash
# native installer, Linux, WSL2 and macOS
curl -fsSL https://claude.ai/install.sh | bash

# or Homebrew
brew install --cask claude-code

# or npm, needs Node.js 22 or newer
npm install -g @anthropic-ai/claude-code
```

The native installer writes to `~/.local/bin`; make sure that
directory is on your `PATH`.

## codex

### Binary and version query

The binary is `codex`. In the pane it runs directly, with no
wrapper process in front of it (`tested` 2026-08-17).

```bash
codex --version
```

The output carries a prefix: `codex-cli 0.147.0` (`tested`
2026-08-17 and 2026-09-23 — the same string on both dates).

### Start arguments

peeragent starts `codex` with `-C <folder>`, the working directory
you named. It is set twice on purpose: the pane gets the directory
too, but this flag is what the harness itself treats as its root,
and the trust question follows the Git repository root of **this**
path. With resume it
starts `codex resume --last`. No sandbox or approval flags are
set.

### Model flag

`-m <model>` (`documented` for a fresh start). Whether `-m` may
follow `resume --last`, and in which position, is `unverified`.
Codex takes literal model identifiers and has no alias system;
reasoning effort is a separate setting of the harness.

| Model key | Description |
|---|---|
| `gpt-5.6-sol` | Flagship, deepest reasoning, complex coding |
| `gpt-5.6-terra` | Balanced everyday model |
| `gpt-5.6-luna` | Fast and cheap |
| `gpt-5.3-codex-spark` | Research preview, near-instant iteration (ChatGPT Pro) |
| `gpt-5.5` | Prior flagship (ChatGPT plans only) |
| `gpt-5.4` | Legacy, retires 2026-08-31 |
| `gpt-5.4-mini` | Legacy fast and cheap |
| `gpt-5.3-codex` | Prior codex-specialist model |
| `gpt-5-codex` | Canonical example ID in the official docs |

Some of these need a ChatGPT login rather than an API key
(`documented`).

### Resume

`experimental`: `documented`, not tested. `codex resume --last`
jumps to the most recent session, filtered to the current
directory by default. There is no short form for `--last`.
peeragent emits a warning when you resume an `experimental`
harness.

### Session store

Rollout files under
`<home>/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`
with an index `<home>/session_index.jsonl`; `<home>` is
`CODEX_HOME` if set and `~/.codex` otherwise (`documented`). The
store is global, not namespaced per directory. On a test machine
running codex-cli 0.147.0, there was a thread index
`<home>/state_5.sqlite` with a `threads` table holding `id`,
`rollout_path`, `cwd` and `recency_at`. Another version may name
or shape it differently. peeragent
decides whether a store exists for a path by looking for the
token `"cwd":"<path>"` in a rollout file.

### Prompt delivery

`argv`. On 2026-09-23 `codex "<prompt>"` in a fresh directory
showed the trust prompt first; after the trust answer the prompt
appeared as the first turn (`tested`):

```text
│ >_ OpenAI Codex (v0.147.0)                             │
│ model:     gpt-5.6-terra   /model to change            │
› Print the word ZEBRA and nothing else, then stop.
```

The run then stopped at a usage limit of the account it was run
with, which is a property of that account and not a delivery
problem. `codex resume --last "<prompt>"` is
`documented`. Delivering a prompt to codex by paste is
`unverified`.

### Duplicate

Refused (`unsupported`). Codex keeps a SQLite thread index next
to the rollout files, and copying files does not reach it. The
refusal names the way round it instead: copy the folder yourself
with `cp -a` and continue there with `codex resume --all <id>`. It
cannot point into a copy, because it happens before anything is
copied.

### Waiting states

**Trust prompt.** The first start in a new directory shows
(`tested` 2026-08-17):

```text
> You are in <folder>
  Note: You're in a subdirectory of a Git project. Trusting will
  apply to the repository root: <repository root>
  Do you trust the contents of this directory? …

› 1. Yes, continue
  2. No, quit
```

The marker is `Do you trust the contents of this directory`. The
answer is the digit alone, with no Enter after it: the digit both
selects and confirms (`tested` 2026-09-28). An Enter sent after it
goes into the session that is by then already running, and what it
does there has not been checked.

```bash
tmux send-keys -t "=<session>:" 1
```

Note what you are agreeing to: codex resolves the Git repository
root and trusts that, not only the folder you started in.

**Auth prompt.** With an empty configuration directory the pane
shows `Welcome to Codex` and `Sign in with ChatGPT` (`tested`
2026-09-23). The marker is `Sign in with ChatGPT`.

**Ready.** No marker is backed by any source. The input line
begins with `›`, but so do menu entries, so peeragent does not use
it. A codex pane that is neither at the trust prompt nor at the
login prompt is reported as `unknown`.

**Usage limit.** A further waiting state without a marker
(`tested` 2026-09-23):

```text
■ You've hit your usage limit. …
› 1. Switch to gpt-5.6-luna
```

peeragent reports this as `unknown`. Answer it in the pane
yourself, or start again with a model your plan still serves.

**Startup warning.** Without `bubblewrap` on `PATH`, codex prints
`Codex could not find bubblewrap on PATH` and continues to start
(`tested` 2026-09-23). This is harness output in the pane, not a
peeragent warning.

### Installing the Codex CLI

When peeragent reports `codex` as missing, install it from OpenAI
(`documented`):

```bash
# installer script, Linux and macOS
curl -fsSL https://chatgpt.com/codex/install.sh | sh

# or npm, Node.js 22 recommended
npm install -g @openai/codex

# or Homebrew, macOS
brew install --cask codex
```

## agy

### Binary and version query

The binary is `agy`, not `antigravity`. The default path is
`~/.local/bin/agy` (`documented`). The installer can be told to
skip the `PATH` edit, in which case the binary exists but
peeragent will not find it.

```bash
agy --version
```

The output is a bare version number with no prefix; the format is
`observed on a test host`. The string seen on 2026-09-23 was `1.2.8`,
and on 2026-09-29 `1.2.12` (`tested` both times). Antigravity releases often and updates itself
in the background, which is visible in the pane's process line as
`--bg-updater`.

### Start arguments

peeragent starts `agy` with no extra arguments. With resume it
adds `--continue`. peeragent never passes a login flag; you must
be logged in beforehand.

### Model flag

`--model <model>` (`documented`, version 1.0.5 and newer). The
keys are human-readable strings with spaces and parentheses, so
they have to be quoted on a command line. Availability depends on
the Google plan.

| Model key | Description |
|---|---|
| `Gemini 3.1 Pro` | Gemini 3.1 Pro |
| `Gemini 3.1 Pro (High)` | Gemini 3.1 Pro, high effort |
| `Gemini 3.7 Flash` | Gemini 3.7 Flash |
| `Gemini 3.6 Flash` | Gemini 3.6 Flash |
| `Gemini 3.5 Flash` | Gemini 3.5 Flash |
| `Claude Opus 4.6 (Thinking)` | Claude Opus 4.6 with thinking (paid plans) |
| `Claude Sonnet 4.6 (Thinking)` | Claude Sonnet 4.6 with thinking (paid plans) |
| `GPT-OSS-120b` | Open-weight GPT-OSS 120b |

An unknown key falls back to another model with a warning in the
interactive interface, and fails hard only in the headless mode
(`documented`).

### Resume

`experimental`: `documented`, not tested. `--continue` continues
the most recently active conversation of the current workspace,
and the working directory is the only key for that lookup.
peeragent therefore always starts the harness in the target
folder. A deleted conversation yields a fresh session without an
error (`documented`).

### Session store

Unknown. peeragent reports that no store exists for any path and
refuses to duplicate. On a test host that had never been logged
in, only `conversation_summaries.db` and a cached project
identifier were found under `~/.gemini/`
(`observed on a test host`); the documented cache files were
absent. Credentials live in the system keyring, not in a file
(`documented`). No environment variable for relocating the
configuration directory is documented.

### Prompt delivery

`send_keys`. A flag for an interactive start with an initial prompt
does exist — `--prompt-interactive`, short `-i` — but what it does
has never been run here, and the print flag is the headless one,
which would end the pane. peeragent therefore pastes the prompt
into the running pane, and only when the pane is `ready`.

The paste path is `tested` 2026-09-29: with an account configured
and the trust question answered, a prompt delivered with
`peeragent send` reached the harness and was answered. Delivery by
`start agent` itself, without the trust question in the way, has
not been run.

### Duplicate

Refused (`unsupported`), because the layout of the conversation
store is unknown. Without knowing it, a copy would be guesswork.

### Waiting states

**Auth prompt.** Both test runs ended here (`tested` 2026-08-17,
again 2026-09-23 with agy 1.2.8):

```text
     ▄▀▀▄
    ▀▀▀▀▀▀
   ▀▀▀▀▀▀▀▀
  ▄▀▀    ▀▀▄

 Welcome to the Antigravity CLI. You are currently not signed in.
 Select login method:
 > 1. Google OAuth
   2. Use a Google Cloud project
```

The markers are `Select login method` and `not signed in`. There
is no key sequence for this one: peeragent does not automate a
login. Log in outside peeragent, then start again.

That screen belongs to a machine without an account. It is not a
property of the harness, and describing it as one was a mistake
that two test hosts without a login made easy to believe.

**Trust prompt** (`tested` 2026-09-29, agy 1.2.12). With an account
configured, a start in a directory the harness does not know yet
asks about the directory instead:

```text
 Accessing workspace:
 /srv/project

 Do you trust the contents of this project?
 Antigravity CLI requires permission to read, edit, and execute files here.

 > Yes, I trust this folder
   No, exit

   Up/Down Navigate - enter Confirm
```

The markers are `Do you trust the contents of this project` and
`I trust this folder`. **The preselected option is the accepting
one**, so the answer is a bare `Enter`:

```bash
tmux send-keys -t "=<session>:" Enter
```

That differs from Claude Code, which preselects the refusing option
and needs an arrow key first. Sending `Enter` alone there would
close the harness, so do not carry one answer over to the other.

**Ready** (`tested` 2026-09-29). After the trust answer the pane
shows a line that is exactly `>`, with a status line reading
`? for shortcuts`. That is the marker, so a prompt is delivered by
paste once the pane reaches it.

**Process picture.** The pane process re-executes itself with
internal flags, seen as
`agy --bg-updater --app_data_dir=antigravity-cli --gemini_dir=.gemini`
(`tested` 2026-08-17). The command line stays recognisable even
though the short process name does not.

### Installing the Antigravity CLI

When peeragent reports `agy` as missing, install it from Google
(`documented`). No package-manager route is documented.

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

The installer accepts `--skip-aliases` and `--skip-path`. With
`--skip-path` the binary lands in `~/.local/bin/agy` without
being added to your `PATH`, and peeragent will report it as
missing.

## opencode

### Binary and version query

The binary is `opencode`. On a test machine, the installer script
had put it in `~/.local/bin/opencode`. There are no companion
binaries.

```bash
opencode --version
```

The output is a bare version number with no prefix (`tested`); on
2026-09-23 it was `1.18.25`.

### Start arguments

peeragent starts `opencode` with no extra arguments. With resume
it adds `--continue`.

### Model flag

`-m <provider>/<model>` (`documented`). opencode is the only one
of the five that uses this two-part notation, and the provider
part has to be configured in the harness before the model works.

| Model key | Description |
|---|---|
| `anthropic/claude-opus-5` | Anthropic Claude Opus 5 |
| `anthropic/claude-sonnet-5` | Anthropic Claude Sonnet 5 |
| `anthropic/claude-sonnet-4-5` | Anthropic Claude Sonnet 4.5 |
| `anthropic/claude-haiku-4-5` | Anthropic Claude Haiku 4.5 |
| `openai/gpt-5.6-sol` | OpenAI GPT-5.6 Sol |
| `openai/gpt-5.3-codex` | OpenAI GPT-5.3 Codex |
| `openai/gpt-5-codex` | OpenAI GPT-5 Codex |
| `google/gemini-3-pro` | Google Gemini 3 Pro |
| `opencode/big-pickle` | OpenCode Zen Big Pickle (free tier, no login) |

### Resume

`experimental`: `documented`, not tested. `--continue` starts the
interface with the last session of the current project, and the
project is derived from the Git root with the working directory
only as a fallback. Two directories inside one repository
therefore reach the same session. opencode has no `--resume`
flag; peeragent translates its own resume option into
`--continue`.

### Session store

A SQLite database at `~/.local/share/opencode/opencode.db` is the
primary store, with snapshots under a project-derived directory
alongside it (`documented`). There is no per-directory store, so
peeragent reports that no store exists for any path.

### Prompt delivery

`send_keys`; no initial prompt for the interactive start is
documented. peeragent pastes into the running pane, and only when
the pane is `ready`. Because no provider was configured in either
test run, the paste path for opencode is `unverified`.

### Duplicate

Refused (`unsupported`). The database carries no schema marker —
`PRAGMA user_version` was `0` (`observed on a test host`) — and it
holds credential tables next to the session tables. Cloning rows
would be reverse engineering inside a credential store. The
harness-native route is its own export and import commands
(`documented`).

### Waiting states

**Provider prompt.** Both test runs ended here (`tested`
2026-08-17, again 2026-09-23 with empty configuration
directories):

```text
    █▀▀█ █▀▀█ █▀▀█ █▀▀▄ █▀▀▀ █▀▀█ █▀▀█ █▀▀█
    █  █ █  █ █▀▀▀ █  █ █    █  █ █  █ █▀▀▀
    ▀▀▀▀ █▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀

 ┃  Ask anything... "Fix a TODO in the codebase"
 ┃  Build · Big Pickle OpenCode Zen
 tab agents  ctrl+p commands

 ● Tip Run /connect to add an AI provider and start coding
```

The marker is `Run /connect`. There is no key sequence: the
interface is up but has no provider, so configure one with
`/connect` inside the pane. The trust answer for opencode is
empty.

**Ready.** `Ask anything` without the tip text. This is only
partly backed: the placeholder `Ask anything...` is `tested`, but
in both runs it appeared together with the tip line, and whether
it disappears while opencode works is `unverified`.

**Startup.** The launcher runs a package install before the
interface appears, seen as `npm install opencode-ai@1.18.18`
(`tested` 2026-08-17). The pane process is that launcher, not
opencode itself, which is why peeragent walks the process tree
instead of trusting the pane process. The first start after an
update can take longer than the default boot wait.

### Installing OpenCode

When peeragent reports `opencode` as missing (`documented`):

```bash
# installer script
curl -fsSL https://opencode.ai/install | bash

# or npm, the package name carries a suffix
npm install -g opencode-ai

# or Homebrew
brew install anomalyco/tap/opencode

# or Arch Linux
sudo pacman -S opencode
```

## copilot

### Binary and version query

The binary is `copilot`. This is the standalone terminal CLI, not
the retired extension of the GitHub CLI (`documented`). The
installation channel cannot be told from the binary.

```bash
copilot --version
```

The first line has the form `GitHub Copilot CLI 1.0.88.` — the
trailing period is part of the output and peeragent keeps it. The
format is `observed on a test host`; the string was `tested` on
2026-09-23. A second line offering an update is dropped, because
peeragent reads the first line only.

### Start arguments

peeragent starts `copilot` with `-C <folder>`, the working directory
you named, for the same reason as the Codex CLI: the pane directory
and the harness's own idea of its root are two different things.
With resume it
adds `--continue`.

### Model flag

`--model <model>` (`documented`). The keys are lower-case
long forms with hyphens. The list a plan actually offers is
filtered on the server side, and the model picker inside the
harness is the authority on what is currently available.

**Three of the keys below were refused on a test host**
(`tested` 2026-09-30): `claude-opus-5`, `claude-sonnet-4.5` and
`gpt-5-mini` each produced

```text
✗ Model "<key>" from --model flag is not available. Using "auto" instead.
```

and the harness continued with its automatic choice. Whether the
keys are wrong or that account simply has no entitlement to those
models, the message does not say - "not available" covers both, so
this is `unverified` rather than a correction to the list.

What matters for a caller is the shape of the failure: **a refused
model does not stop anything.** The harness runs, with a different
model than the one asked for, and the only sign is one line in the
pane. peeragent cannot see it: the line is not a marker, and the
screen classifies as ready or as a trust question like any other. If
the model matters, read the pane.

| Model key | Description |
|---|---|
| `claude-opus-5` | Claude Opus 5 via Copilot |
| `claude-opus-4.6` | Claude Opus 4.6 via Copilot |
| `claude-sonnet-4.6` | Claude Sonnet 4.6 via Copilot |
| `claude-sonnet-4.5` | Claude Sonnet 4.5 via Copilot |
| `claude-haiku-4.5` | Claude Haiku 4.5 via Copilot |
| `gpt-5.3-codex` | GPT-5.3 Codex via Copilot |
| `gpt-5-mini` | GPT-5 mini via Copilot |
| `gpt-4.1` | GPT-4.1 via Copilot |
| `gemini-3-pro` | Gemini 3 Pro via Copilot |
| `kimi-k3` | Kimi K3 via Copilot |

### Resume

`experimental`: `documented`, not tested. `--continue` prefers the
most recent session of the current directory, but without one it
falls back to the globally most recent session — so a resume in a
fresh directory can continue somebody else's work in another
directory. peeragent names exactly this in the warning it emits
when you resume copilot.

### Session store

One directory per session at `<home>/session-state/<uuid>/`
containing a `workspace.yaml`; `<home>` is `COPILOT_HOME` if set
and `~/.copilot` otherwise (`documented`). On a test machine, that
file held the fields `id`, `cwd`, `git_root`, `repository` and
`branch`, and there was an index
`<home>/session-store.db`, a SQLite database with a `sessions`
table and an index on `cwd`. Neither layout is documented, so
neither is promised. peeragent decides whether a store
exists for a path by reading the `cwd:` line of those YAML files.

### Prompt delivery

`argv`, through `-i <prompt>`. On 2026-09-28 a prompt passed that
way survived the trust question and became the first turn after it
was answered, and the session stayed interactive (`tested`).

Pasting also works and stays the path for delivering a prompt into
a running session. On 2026-09-23 a bracketed paste put all three
lines of a prompt file into the input, one `Enter` sent them, and a
trailing newline in the file did not send by itself (`tested`). A
paste that arrives while copilot is working is buffered by the
interface and processed after the running turn
(`tested` 2026-09-23).

### Duplicate

Refused (`unsupported`). Sessions are indexed in a SQLite database
by working directory, and copying the YAML directories does not
reach that index. The refusal points at `copilot --resume <id>`
instead. Copilot also synchronises sessions to the GitHub account
by default, and what a hand-made local copy would do on the next
synchronisation is unknown (`unverified`).

### Waiting states

**Trust prompt.** The first start in a new folder shows (`tested`
2026-08-17; the recorded lines are abridged where the source cut
them):

```text
╭ Confirm folder trust ─────────────────────────────╮
│ <folder>                                          │
│ Do you trust the files in this folder?            │
│ ❯ 1. Yes                                          │
│   2. Yes, and remember this folder for future …   │
│   3. No (Esc)                                     │
╰───────────────────────────────────────────────────╯
```

The marker is `Confirm folder trust`. The answer is the digit
alone, with no Enter after it — the digit both selects and
confirms, although the box says "enter to select" (`tested`
2026-09-28):

```bash
tmux send-keys -t "=<session>:" 1
```

`1` trusts this once, `2` trusts and remembers the folder, `3`
cancels. peeragent's hint names `1`, so the answer is not
remembered and the question returns on the next start in that
folder. The box names the working directory, not the repository it
lies in (`tested` 2026-09-28), which differs from the Codex CLI.

**Auth notice.** With no credentials in place, the line
`Please use /login to sign in to use Copilot` appears (`tested`
2026-09-28). Two things about it matter. It is a **status line above
the input, not a dialog**, so looking for a box misses it. And it
stands **at the same time as the `❯` line**, so a screen that looks
ready belongs to a harness that cannot do anything until someone
logs in:

```text
● MCP Servers reloaded: 0 servers connected
Please use /login to sign in to use Copilot
 <folder> [⎇ main]
───────────────────────────────────────────
❯
```

peeragent therefore reports `auth_prompt` here, not `ready`: the
waiting states have a precedence, and an authentication question
outranks a ready line.

**Two gates in sequence.** The trust box came first and the auth
notice after it (`tested` 2026-09-28). An answered question does not
mean the harness is ready, so capture again rather than assume.

**Busy.** The marker is `esc interrupt`, from the status line
(`tested` 2026-09-23):

```text
 ❯ Line one of the prompt: please answer with the single word ZEBRA.
   Line two: do not read any files.
   Line three: then stop.
 ❯
  ○ Working esc interrupt                       Auto → mai-code-1.1-flash
```

**Ready.** A line that is exactly `❯` once whitespace is stripped
(`tested` 2026-09-23). As the capture above shows, that line is
present while copilot works too, which is why `busy` wins over
`ready`. When the turn ends, the `Working` line disappears and the
bare `❯` line remains.

**No login prompt.** With an empty configuration directory the
trust box still came first, and the ready screen followed with
`Session: 0 AIC used` — authentication came from the environment
(`tested` 2026-09-23). peeragent therefore has no auth marker for
copilot. If the account is not entitled, the harness says so in
the pane and peeragent reports `unknown`.

**Process picture.** The short process name is `MainThread`; the
command line is the binary path under a platform-specific
directory (`tested` 2026-09-23). The short name is not a reliable way to
recognise the harness.

### Installing the GitHub Copilot CLI

When peeragent reports `copilot` as missing, install it from
GitHub (`documented`):

```bash
# npm, needs Node.js 22 or newer
npm install -g @github/copilot

# or Homebrew
brew install --cask copilot-cli

# or installer script, Linux and macOS
curl -fsSL https://gh.io/copilot-install | bash
```

An active GitHub Copilot subscription is required, and on business
or enterprise plans an administrator has to allow CLI access
(`documented`).

## What to read next

- The waiting states, their precedence and what to do about each
  one: [`troubleshooting.md`](troubleshooting.md).
- The flags that select a harness, a model or a resume:
  [`cli.md`](cli.md).
- The message and field names quoted above:
  [`output-format.md`](output-format.md).
- What is implemented, what is only specified, and how well each
  claim is backed: [`../MATURITY.md`](../MATURITY.md).
