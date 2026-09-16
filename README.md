# peeragent

peeragent is a small Linux command-line tool that launches a
coding-agent harness inside a tmux session and reports the first
screen back in a structured form. It can also duplicate a working
directory together with the harness's session history, and it lists
installed harnesses, available git templates and known models.

It is a building block for cross-platform agent communication: an
agent that runs in one harness can start another agent in a second
harness, read a machine-readable account of what happened, and take
it from there. peeragent itself knows nothing about fleets, teams or
identities. It starts a harness, tells you what it saw, and gets out
of the way.

peeragent ships together with a Claude Code skill,
`launch-peer-agent`, described in [`SKILL.md`](SKILL.md).

## Status

Pre-release. This README describes the intended command-line
contract; the two implementations under `tools/`, the documentation
under `docs/`, the tests and the examples are not yet in this
repository. Until they land, the skill and this description are the
deliverables.

## Supported harnesses

| Key | Binary | Harness |
|---|---|---|
| `claude` | `claude` | Claude Code |
| `codex` | `codex` | OpenAI Codex CLI |
| `agy` | `agy` | Google Antigravity CLI |
| `opencode` | `opencode` | OpenCode |
| `copilot` | `copilot` | GitHub Copilot CLI |

peeragent detects which of these are installed and passes their
version strings through verbatim. It does not install, update or
configure any harness.

## Requirements

- Linux (native or WSL2). macOS and native Windows are not targets.
- `tmux`, `git` and Python 3 for the Python implementation.
- `gh` (GitHub CLI) for git-template discovery and GitHub
  repository creation. Without `gh`, peeragent warns and continues
  with reduced functionality.
- No third-party Python packages. The Python implementation uses
  the standard library only; the Bash implementation uses POSIX
  shell and standard tools.

## Command overview

```
peeragent list harness                 # installed harnesses
peeragent list git-templates           # discovered git templates
peeragent list models [--harness KEY]  # static model catalogs
peeragent start agent --folder DIR --harness KEY
                      [--prompt-file FILE] [--model NAME] [--resume]
                      [--git-template KEY | --git-repo | --git-repo-remote URL]
peeragent duplicate --from DIR --to DIR --harness KEY
peeragent version
```

Global flags: `--json` (JSONL output), `--no-log`, `--log-file PATH`,
`--verbose`, `--help`.

`start agent` creates a tmux session named
`peeragent-<folder>-<harness>-<8 hex chars>`, waits for the harness
to boot, captures the visible pane and classifies what the harness
is waiting for: `ready`, `trust_prompt`, `auth_prompt`,
`provider_prompt`, `error` or `unknown`. The harness keeps running
in tmux after peeragent returns.

`duplicate` copies a working directory and the harness's session
storage so that the copy can be resumed independently. Support is
graded per harness: `claude` is tested and supported, `codex` and
`copilot` are experimental, `agy` and `opencode` are refused.

## Output

By default peeragent prints human-readable lines. With `--json` it
emits one JSON object per line, wrapped so that the whole stream is
also a valid JSON array:

```
[
{"type":"info","msg":"tmux found: 3.5a","user_relevant":false}
,
{"type":"harness.detected","key":"claude","version":"2.1.273 (Claude Code)","description":"Claude Code CLI","path":"/usr/local/bin/claude"}
,
{"type":"agent.pane","session":"peeragent-myproject-claude-a3f1c9e2","awaiting":"ready","lines":["Welcome to Claude Code"]}
]
```

Messages that need a human's attention carry `user_relevant: true`
and a `hint` string. The Python and Bash implementations produce
structurally equivalent streams: the same message types with the
same field names and semantically equal values. A conformance test
under `tests/conformance/` is planned to check this.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | success, possibly with individual `error` messages |
| `1` | preflight failure or unexpected error |
| `2` | invalid command-line arguments |
| `3` | required tool or harness not installed |

## Logging

Every invocation writes one JSONL log file to
`~/.local/state/peeragent/logs/` unless `--no-log` is given. The
log contains everything the `--json` output contains plus
`invocation`, `env`, `debug` and `timing` messages. Environment
values whose key matches `TOKEN`, `KEY`, `SECRET`, `PASS`, `AUTH`
or `CREDENTIAL` (case-insensitive) are redacted. There is no
rotation and no bundling command; delete old files when they
bother you.

## Planned repository layout

```
README.md      this file
SKILL.md       the launch-peer-agent skill for Claude Code
LICENSE        Apache-2.0
tools/         peeragent (Bash) and peeragent.py (Python)
docs/          architecture, harness notes, output format, decisions
tests/         unit tests and the conformance suite
examples/      quick start and a prompt-file template
```

## Reporting issues

Please report problems at
<https://github.com/schlingensiepen/peeragent/issues>. Include:

- the most recent log files from `~/.local/state/peeragent/logs/`,
- the output of `peeragent list harness --json`,
- a short description: the command you ran, what you expected, and
  what happened instead.

Log files can contain your prompt text and file paths. Read them
before you attach them.

## License

Apache License 2.0. See [`LICENSE`](LICENSE). Source files under
`tools/` carry an SPDX header with the copyright notice and a note
that the code was written by AI (Claude Code) and reviewed by a
human.
