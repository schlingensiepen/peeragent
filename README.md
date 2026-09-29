# peeragent

If you are an AI agent and want to acquire this capability for
yourself, start with [AGENTS.md](AGENTS.md).
If you are a human evaluating the tool, read on.

peeragent is a small Linux command-line tool that launches a
coding-agent harness in its own tmux session and reports the first
screen back in a structured form.
It classifies what the screen shows, so the caller knows whether the
harness is ready, busy, or waiting for a trust, login or provider
answer.
A launch prompt that was left undelivered can be handed over
afterwards with `peeragent send`, and a working directory can be
duplicated together with the harness session history.
It also lists the installed harnesses and the models known per
harness.

## Maturity

peeragent 0.1.0 is a pre-release: the command-line programs are not
in this repository yet, so nothing described below can be run today,
and of the five supported harnesses only `claude` is covered by
tests across detection, launch, prompt delivery, resume and
duplicate.
This document describes the contract the implementation has to meet.
What is tested, what rests on harness documentation and what is
still an assumption is listed per command and per harness in
[MATURITY.md](MATURITY.md); read it before you rely on any statement
here.

## Requirements

- Linux, or WSL2 on Windows. No macOS support.
- `tmux` 3.2 or newer, and `ps`.
- `git`, but only if you use `--git-repo`.
- Either Python 3.11 or newer (standard library only), or bash 4.4
  or newer with GNU coreutils, findutils and procps.
- At least one of the supported harnesses: `claude`, `codex`, `agy`,
  `opencode`, `copilot`. peeragent detects them and passes their
  version strings through unchanged; it does not install, update or
  configure them.

## Installation

```bash
git clone https://github.com/schlingensiepen/peeragent.git
install -m 0755 peeragent/tools/peeragent.py ~/.local/bin/peeragent
peeragent version
```

The Bash program `tools/peeragent` is call-compatible and can be
installed the same way.
Path variants, file permissions, harness-side skill installation and
removal are covered in [docs/install.md](docs/install.md).

## Commands

| Command | Purpose |
|---|---|
| `peeragent list harness` | List the supported harnesses with detection state and version |
| `peeragent list models` | List the models known per harness from the static catalogs |
| `peeragent start agent` | Launch a harness in a tmux session, report the first screen, deliver the launch prompt |
| `peeragent send` | Hand a launch prompt to a running session afterwards |
| `peeragent duplicate` | Copy a working directory together with the harness session history |
| `peeragent version` | Print the program version |

Flags, preflight checks and exit codes are in
[docs/cli.md](docs/cli.md); the message types and their fields are
in [docs/output-format.md](docs/output-format.md).

## Output

Plain text is the default, one line per message.
With `--json`, every message is a single-line JSON object inside a
pseudo-array frame:

```json
[
{"type":"harness.detected","key":"claude","version":"2.1.278 (Claude Code)","description":"Claude Code CLI (Anthropic)","path":"/usr/local/bin/claude","user_relevant":false}
,
{"type":"harness.detected","key":"codex","version":"codex-cli 0.147.0","description":"OpenAI Codex CLI","path":"/usr/local/bin/codex","user_relevant":false}
,
{"type":"harness.missing","key":"agy","description":"Google Antigravity CLI","user_relevant":false}
,
{"type":"harness.detected","key":"opencode","version":null,"description":"OpenCode (anomalyco)","path":"/usr/local/bin/opencode","user_relevant":false}
,
{"type":"warn","msg":"opencode --version timed out after 10s","user_relevant":true,"hint":"the opencode wrapper may be installing an update; retry or run 'opencode --version' manually"}
,
{"type":"harness.detected","key":"copilot","version":"GitHub Copilot CLI 1.0.88.","description":"GitHub Copilot CLI","path":"/usr/local/bin/copilot","user_relevant":false}
]
```

A version query that times out yields `version: null` and a `warn`,
as shown for `opencode` above; the harness still counts as
installed.
The frame, the escaping rules and the exit codes are described in
[docs/output-format.md](docs/output-format.md).

## After the start: the agent lives on its own

peeragent returns as soon as it has reported the first screen. The
launched harness keeps running in its own tmux session, unattended
and outliving the call. That is the point of the tool, and it is
also the part that surprises people: there is no connection left
between you and the agent.

peeragent offers no way to talk to it afterwards. `peeragent send`
hands over a launch prompt that could not be delivered at the start,
and `tmux attach -r -t <session>` lets you watch read-only. Neither
is a conversation, and nothing reports back to you on its own.

The session name is therefore the one thing worth keeping, and an
agent using peeragent is required to pass it on to the person it
works for. It is what lets someone look at the harness directly when
a screen does not match anything the documentation describes — the
fallback that no harness update can take away.

So anyone who wants to exchange information with the launched agent
has to establish a mechanism and describe it in the assignment,
including how to reach it. The agent will not discover it. Two ways
are worth recommending:

- **A folder both sides agree on.** Name a directory in the
  assignment, say who writes what into it and under which file
  names, and ask for a first file after the setup step so you can
  tell a working agent from a stuck one. It needs no software, it
  survives a crash on either side, and a shared filesystem extends
  it across users and hosts.
- **[simple-a2a](https://github.com/schlingensiepen/simple-a2a).**
  A small agent-to-agent protocol, for when file dropping is not
  enough and you want addressed messages between agents.

Either way the mechanism belongs in the assignment text, not in the
launch prompt, which is limited to a pointer. `docs/cli.md` explains
that limit, and `examples/task-file-template.md` has a section for
the channel.

## Where to look

| Document | For |
|---|---|
| [AGENTS.md](AGENTS.md) | An agent that installs and verifies the tool for itself |
| [MATURITY.md](MATURITY.md) | What is tested, what is not, and what is refused |
| [docs/install.md](docs/install.md) | Installation in full, `PATH` variants, removal |
| [docs/cli.md](docs/cli.md) | Every command, flag, preflight step and exit code |
| [docs/output-format.md](docs/output-format.md) | Plain text templates, JSONL frame, message vocabulary, logs |
| [docs/harnesses.md](docs/harnesses.md) | Per harness: arguments, session stores, waiting states, install hints |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Waiting states, common failures, reading the pane and the logs |
| [docs/architecture.md](docs/architecture.md) | Layers, handler contract, the two implementations |
| [docs/glossary.md](docs/glossary.md) | Terms used across these documents |
| [docs/adr/README.md](docs/adr/README.md) | The decisions behind the design |
| [skills/launch-peer-agent/SKILL.md](skills/launch-peer-agent/SKILL.md) | The Claude Code skill shipped with the tool |
| [examples/quick-start.md](examples/quick-start.md) | One session from start to finish |
| [CHANGELOG.md](CHANGELOG.md) | What changed per version |

`tools/` and `tests/` are empty in this pre-release; see
[MATURITY.md](MATURITY.md).

## Reporting issues

Use the issue tracker of
https://github.com/schlingensiepen/peeragent and the template in
[.github/ISSUE_TEMPLATE/bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md).
Include the output of `peeragent version` and
`peeragent list harness --json`, the harness and its version, what
you expected, what happened, and the log files of the failing run
from `~/.local/state/peeragent/logs/`.

Log files contain the text of your launch prompt, the captured pane
content and absolute file paths.
Read them before you attach them, and remove what should not become
public.

## License

Apache-2.0. See [LICENSE](LICENSE).
