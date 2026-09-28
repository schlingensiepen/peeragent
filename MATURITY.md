# Maturity

**Report date:** 2026-09-28 · **peeragent version:** 0.1.0

The command-line programs are not in this repository yet. `tools/` is
empty, and no part of the documented workflow can be run from this
repository today.
Everything below therefore separates two things: what the harnesses
were observed to do on a test host, and what peeragent is specified
to do about it.

The harness versions the statements in this document were checked
against, seen on a test host on 2026-09-23:

| Harness | Version string |
|---|---|
| `claude` | `2.1.278 (Claude Code)` |
| `codex` | `codex-cli 0.147.0` |
| `agy` | `1.2.8` |
| `opencode` | `1.18.25` |
| `copilot` | `GitHub Copilot CLI 1.0.88.` |

tmux on that host was 3.5a.
All five harnesses update themselves, some of them in the background
during a launch, so a version can change between two invocations.
Screen wordings, key sequences and session store layouts are
properties of those versions and not of peeragent: every statement
here ages, and the ones marked `tested` age with the date they carry.

## Overall state

peeragent 0.1.0 is a pre-release whose command set is specified and
whose harness behaviour is verified for `claude` end to end, verified
in part for `codex` and `copilot`, and verified no further than
detection and launch for `agy` and `opencode`.

## Evidence levels

Every statement in the tables below carries one of these levels.

| Level | Meaning |
|---|---|
| `tested` | Run on a test host and seen to behave this way; the date of the check is given |
| `documented` | Stated in the harness's own documentation, not run here |
| `observed` | Seen on a test host without a dedicated test, for example a session store inspected on disk |
| `unverified` | Assumption with no evidence behind it |

An `unverified` entry is not a defect and not a promise. It marks
the places where you should expect surprises and where a report from
you is worth most.

## Commands

| Command | Status | Evidence |
|---|---|---|
| `peeragent list harness` | specified for 0.1.0, not in this repository yet | `unverified` |
| `peeragent list models` | specified for 0.1.0, not in this repository yet | `unverified` |
| `peeragent start agent` | specified for 0.1.0, not in this repository yet | `unverified` |
| `peeragent send` | specified for 0.1.0, not in this repository yet | `unverified` |
| `peeragent duplicate` | specified for 0.1.0, not in this repository yet; supported for `claude` only | `unverified` |
| `peeragent version` | specified for 0.1.0, not in this repository yet | `unverified` |
| `peeragent list git-templates` | planned for a later version; does not exist in 0.1.0 and exits with code 2 | `unverified` |

The evidence column is `unverified` throughout because there is no
program to run. What has been tested is the harness behaviour these
commands are built on; that is the next table.

## Harnesses

| Harness | Detection | Launch | Prompt delivery | Resume | Duplicate |
|---|---|---|---|---|---|
| `claude` | `tested` 2026-09-23 | `tested` 2026-09-23 | `argv`, `tested` 2026-09-23 | `--continue`, `tested` 2026-09-23 | supported, `tested` 2026-09-16 |
| `codex` | `tested` 2026-09-23 | `tested` 2026-09-23 | `argv`, `tested` 2026-09-23 | `resume --last`, `documented` | refused; store `observed` |
| `agy` | `tested` 2026-09-23 | `tested` 2026-08-17 | `send_keys`, `unverified` | `--continue`, `documented` | refused; store `unverified` |
| `opencode` | `tested` 2026-09-23 | `tested` 2026-09-23 | `send_keys`, `unverified` | `--continue`, `documented` | refused; store `observed` |
| `copilot` | `tested` 2026-09-23 | `tested` 2026-09-23 | `send_keys`, `tested` 2026-09-23 | `--continue`, `documented` | refused; store `observed` |

"Detection" means that the binary was found and its version query
answered. "Launch" means that the harness came up in a tmux pane and
that the screen it showed there is known. "Prompt delivery" is the
way the launch prompt reaches the harness: as a command-line
argument (`argv`) or pasted into the running program (`send_keys`).

Per harness, in detail:

- `claude` blocks on the first launch in a new directory with a
  trust question whose preselected answer is refusal, so the answer
  is a key sequence and not a digit. The prompt passed as an argument
  survives that question. Resume replays the earlier conversation and
  then processes the new turn. Duplicating the working directory
  together with the session store was tested on 2026-09-16 and needs
  no rewriting of paths inside the copied session.
- `codex` blocks with a trust question that applies to the git
  repository root, not only to the directory you point it at. The
  prompt passed as an argument survives it and becomes the first
  turn. A usage limit of the account can interrupt the run right
  after that with a dialog of its own, which peeragent reports as an
  unclassified waiting state. Pasting a prompt into a running
  `codex` has not been tried, and the position of the model argument
  after a resume is unverified.
- `agy` blocks with a login selection when no account is configured,
  which is what a test host without a login sees. Nothing beyond
  that is verified: there is no known marker for its input prompt,
  the prompt hand-over by pasting has never been run, and its
  session store layout is unknown.
- `opencode` comes up but refuses to work until a provider is
  configured. Its wrapper may run a package install during startup,
  which is why a version query can time out. The prompt hand-over by
  pasting has never been run.
- `copilot` blocks with a trust question before anything else and,
  on a host where credentials come from the environment, shows no
  login dialog at all. Pasting a three-line prompt works; a trailing
  newline in the prompt file does not submit it, so peeragent always
  sends the confirming key itself. A paste that arrives while the
  harness is busy is buffered and processed after the running turn.

Input-prompt markers are established for `claude` and `copilot`
only. For `codex`, `agy` and `opencode` there is no reliable marker
yet, so their screens are reported as an unclassified waiting state
more often, and the launch prompt is deferred rather than delivered.

## What is refused, and why

peeragent refuses rather than guess. In each case the harness has a
means of its own.

| Case | Reason | What to do instead |
|---|---|---|
| `duplicate` for `codex` | The session history is indexed in a SQLite thread index next to the transcript files; copying the files alone leaves the index inconsistent, and writing that index is out of scope | `codex fork`, or `codex resume --all <id>` in the original directory |
| `duplicate` for `copilot` | The session directories are indexed in a SQLite session store which `--continue` reads | `copilot --resume <id>` in the original directory |
| `duplicate` for `agy` | The session store layout is unknown; only a summary database has been seen, and credentials live in the system keyring | Keep working in the original directory and continue there with `agy --continue` (`documented`) |
| `duplicate` for `opencode` | Its database carries no schema marker and mixes authentication tables into the same file | Keep working in the original directory and continue there with `opencode --continue` (`documented`) |
| Answering a trust, login or provider question | A tool that answers a trust question on your behalf decides about file access for you | peeragent reports the waiting state and the key sequence that answers it; send it yourself, then hand the prompt over with `peeragent send` |
| Git templates and remote repositories | Only a local repository is in scope for 0.1.0 | `--git-repo` creates a local repository in an empty working directory |

A refusal is a preflight failure with exit code 2 and a hint naming
the alternative. It happens before anything is copied.

## Known limits

- All five harnesses block on the first launch in a new directory:
  `claude`, `codex` and `copilot` with a trust question, `agy` with a
  login selection, `opencode` with a missing provider. That is the
  normal case, not the exception, and the caller has to handle it.
- There is no back channel. peeragent reports the first screen and
  returns; the launched harness keeps running in its tmux session.
  Anything the launched harness should report back has to be
  arranged in the launch prompt itself.
- Model strings are passed through opaquely. peeragent does not
  validate them, and a wrong string surfaces as a harness error in
  the pane, not as a peeragent error.
- Model lists come from static catalogs compiled on 2026-08-16, not
  from the harness. A model missing from a catalog can still be
  used: pass it with `--model`.
- Linux and WSL2 only. There is no macOS and no native Windows
  support, and none is planned for 0.1.0.
- Logs are written once per invocation and never rotated, bundled or
  trimmed. They contain the text of your launch prompt, the captured
  pane content and absolute paths.
- A screen is a snapshot. While a harness streams its answer, the
  state cannot always be told from one capture, which is why
  peeragent captures twice before it calls a screen unclassified.

## Planned

- The two programs, the conformance test between them, and the
  unit tests.
- Input-prompt markers for `codex`, `agy` and `opencode`, which need
  a host with a login and a configured provider.
- `duplicate` for `codex` and `copilot`, each of which depends on
  whether their index can be extended without writing SQLite.
- Git templates, repository discovery and remote creation.
- An option for peeragent to answer trust questions under an
  explicit policy, and a command that captures a pane without
  pasting anything.

No dates. Each item moves out of this section when it has evidence,
not when it has code.

## How this document is maintained

This document is updated with every test run and every release, in
the same change as the behaviour it describes.
The evidence level is part of the statement, not decoration: an entry
may only lose `unverified` when someone has run the case, and an
entry marked `tested` carries the date of that run so that readers
can judge how far it has aged behind the harness.
When a harness changes a wording, a key sequence or a session store,
the affected rows drop back to the level the new evidence supports.
