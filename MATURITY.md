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
| `agy` | `tested` 2026-09-23 | `tested` 2026-09-23 | `send_keys`, `unverified` | `--continue`, `documented` | refused; store `unverified` |
| `opencode` | `tested` 2026-09-23 | `tested` 2026-09-23 | `send_keys`, `unverified` | `--continue`, `documented` | refused; store `observed` |
| `copilot` | `tested` 2026-09-23 | `tested` 2026-09-23 | `argv`, `tested` 2026-09-28 | `--continue`, `documented` | refused; store `observed` |

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
- `copilot` blocks with a trust question before anything else, and
  the question covers the working directory rather than the
  repository it lies in (`tested` 2026-09-28). With no credentials in
  place it then shows `Please use /login to sign in to use Copilot`
  as a status line above the input, while the input line itself is
  present (`tested` 2026-09-28); peeragent reports that as an
  authentication question and not as ready. Pasting a three-line
  prompt works; a trailing newline in the prompt file does not submit
  it, so peeragent always sends the confirming key itself. A paste
  that arrives while the harness is busy is buffered and processed
  after the running turn.

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

- Expect the first launch to stop before any work, and note that
  there are two different reasons for it. `claude`, `codex` and
  `copilot` ask whether they may work in the directory, which follows
  from the directory being new to them. `agy` asks for a login
  method and `opencode` for a provider whenever none is configured,
  which follows from how the harness is set up on the machine and
  has nothing to do with the directory. On a machine where those two
  are configured, their first screen has not been observed here, so
  what they show then is `unverified`. Either way the caller has to
  handle a first screen that is not ready.
- There is no back channel. peeragent reports the first screen and
  returns; the launched harness keeps running in its tmux session.
  Anything the launched harness should report back has to be
  arranged in the assignment itself. The two recommended ways, a
  folder both sides agree on and simple-a2a, are in
  [README.md](README.md) and
  [examples/task-file-template.md](examples/task-file-template.md).
  Neither is part of peeragent and neither is tested by it.
- Answering one question does not mean the harness is ready. The
  causes are independent and can queue: a harness without
  credentials may ask to sign in first and about the directory
  afterwards, or the other way round (`tested` 2026-09-28 for two
  harnesses). Capture again after each answer.
- **A screen with no marker is the expected outcome.** peeragent
  carries markers for the questions that recur and reports anything
  else as `unknown` with the visible lines attached. It is not a
  model of each harness's interface and will not become one, because
  a marker for every dialog ages with the next release of that
  harness. One consequence is worth knowing: the Codex CLI can open
  with an offer to update itself whose preselected option installs a
  package globally (`tested` 2026-09-28). It has no marker, so it is
  reported as `unknown`, which is what keeps a key sequence out of
  it.
- **Two harnesses may accept a prompt on the command line without
  this being established.** The help output of `agy` and `opencode`
  names such a flag, but neither could be run here for want of a
  login and a provider, so both stay on pasting in the table above.
  For GitHub Copilot CLI the same question was settled by a run on
  2026-09-28 and the table reflects it.
- A launch prompt is limited to 120 effective characters, where
  absolute paths do not count. A longer prompt is refused before
  anything starts. The limit is specified and not yet exercised by a
  run, so it is `unverified` like the rest of the command surface.
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
- Whether the fork commands of three harnesses copy a history or
  only reference it, which would change how a workspace is
  duplicated. `unverified`; the documentation of one points at a
  reference rather than a copy, the others are silent.
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
