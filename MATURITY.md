# Maturity

**Report date:** 2026-09-29 · **peeragent version:** 0.1.0

Both command-line programs are in this repository:
`tools/peeragent.py` (Python, standard library only) and
`tools/peeragent` (Bash). They accept the same arguments and were
written independently of each other.
What is known about them comes from three kinds of check, and this
document keeps them apart:

- **Equivalence.** `tests/conformance/run.sh` runs both programs over
  43 cases and compares them with each other. All 43 agree
  (2026-09-29). That shows the two behave alike. It does not show that
  either behaves correctly: a mistake both make in the same way
  passes. No case starts a harness in tmux, no case calls `send`, and
  the log files are not compared.
- **Runs against real harnesses.** On 2026-09-29 both programs were
  started against all five real harnesses on a test host, and one
  `agy` session was taken through the whole path with `send`. These
  runs are marked `tested` below, and only what they showed.
- **Harness behaviour checked directly.** The dates in the harness
  table before 2026-09-29 are checks made on the harness itself,
  before the programs existed. They say what the harness does, not
  that peeragent handles it.

The harness versions the statements in this document were checked
against, seen on a test host on 2026-09-23 and again by the programs
on 2026-09-29:

| Harness | 2026-09-23 | 2026-09-29 |
|---|---|---|
| `claude` | `2.1.278 (Claude Code)` | `2.1.284 (Claude Code)` |
| `codex` | `codex-cli 0.147.0` | `codex-cli 0.147.0` |
| `agy` | `1.2.8` | `1.2.12`, later the same day `1.2.13` |
| `opencode` | `1.18.25` | `1.18.32` |
| `copilot` | `GitHub Copilot CLI 1.0.88.` | `GitHub Copilot CLI 1.0.88.` |

tmux on that host was 3.5a.
All five harnesses update themselves, some of them in the background
during a launch, so a version can change between two invocations.
Screen wordings, key sequences and session store layouts are
properties of those versions and not of peeragent: every statement
here ages, and the ones marked `tested` age with the date they carry.

## Overall state

peeragent 0.1.0 is a pre-release. Its command set is implemented in
two programs that agree with each other on every conformance case.
Run against real harnesses, it has been taken as far as the first
screen for all five, and through a trust answer, a deferred delivery
with `send` and a reply for `agy`. Harness behaviour was checked
directly for `claude` end to end, in part for `codex` and `copilot`,
and no further than detection, launch and the first question for
`opencode`. Resume and duplicate have not been run through the
programs at all.

## Evidence levels

Every statement in the tables below carries one of these levels.

| Level | Meaning |
|---|---|
| `tested` | Run on a test host and seen to behave this way, and recorded; the date of the check is given |
| `documented` | Stated in the harness's own documentation, not run here |
| `observed` | Seen on a test host without a recorded test, for example a session store inspected on disk or a command run once by hand |
| `unverified` | Assumption with no evidence behind it |

Agreement in the conformance test is not one of these levels and does
not raise an entry to `tested`; it has its own column below.

An `unverified` entry is not a defect and not a promise. It marks
the places where you should expect surprises and where a report from
you is worth most.

## Commands

| Command | State | Both programs agree | Run on a host |
|---|---|---|---|
| `peeragent list harness` | implemented in both | yes: all installed, none installed, plain text, version query timing out, version query failing | `observed` 2026-09-29 against the five installed harnesses |
| `peeragent list models` | implemented in both | yes: all, one, not installed, unknown key, plain text | `observed` 2026-09-29 for one harness |
| `peeragent start agent` | implemented in both | only the refusals before anything starts: unknown harness, missing tool, missing or conflicting folder, missing, empty or too long prompt, bad flags. No case starts a harness | `tested` 2026-09-29: all five harnesses, both programs, up to the first classified screen. With `agy` the run continued through the trust answer and a prompt delivered afterwards |
| `peeragent send` | implemented in both | no case | `tested` 2026-09-29 with `agy` only |
| `peeragent duplicate` | implemented in both; `claude` only | yes: a copy with a fake `claude` history, a source without a history, the refusals for `codex` and `copilot`, and the path and destination checks | not run through the program against a real session history: `unverified`. The behaviour it relies on was tested by hand on 2026-09-16 |
| `peeragent version` | implemented in both | yes: plain text and JSON | `observed` 2026-09-29 |
| `peeragent list git-templates` | reserved for a later version; exits with code 2 in both | no case | `observed` 2026-09-29 |

`tested` in the last column means a recorded run of that command; the
run of 2026-09-29 covers the first screen of each harness and the
one `agy` path, nothing more.

Not exercised by either kind of check against a real harness:
`--resume`, `--model`, `--git-repo` on a directory that has no
repository yet, `--log-file`, and the exit code 4 path with a harness
that dies. The last one, and exit code 130 after Ctrl-C during the
boot wait, were seen once with a stand-in program that exits at once
or blocks (`observed` 2026-09-29, both programs).

The harness behaviour these commands are built on is in the next
table.

## Harnesses

| Harness | Detection | Launch | Prompt delivery | Resume | Duplicate |
|---|---|---|---|---|---|
| `claude` | `tested` 2026-09-29 | `tested` 2026-09-29 | `argv`, `tested` 2026-09-23 | `--continue`, `tested` 2026-09-23 | supported, `tested` 2026-09-16 |
| `codex` | `tested` 2026-09-29 | `tested` 2026-09-29 | `argv`, `tested` 2026-09-23 | `resume --last`, `documented` | refused; store `observed` |
| `agy` | `tested` 2026-09-29 | `tested` 2026-09-29 | `send_keys`, `tested` 2026-09-29 | `--continue`, `documented` | refused; store `unverified` |
| `opencode` | `tested` 2026-09-29 | `tested` 2026-09-29 | `send_keys`, `unverified` | `--continue`, `documented` | refused; store `observed` |
| `copilot` | `tested` 2026-09-29 | `tested` 2026-09-29 | `argv`, `tested` 2026-09-28 | `--continue`, `documented` | refused; store `observed` |

"Detection" means that the binary was found and its version query
answered. "Launch" means that the harness came up in a tmux pane and
that the screen it showed there is known; from 2026-09-29 on that is
seen through the programs, for both. The other columns are harness
behaviour checked on the harness itself, with the dates given, except
where a later paragraph says a program was involved. "Prompt delivery" is the
way the launch prompt reaches the harness: as a command-line
argument (`argv`) or pasted into the running program (`send_keys`).

Per harness, in detail:

- `claude` blocks on the first launch in a new directory with a
  trust question whose preselected answer is refusal, so the answer
  is a key sequence and not a digit. The prompt passed as an argument
  survives that question. Resume replays the earlier conversation and
  then processes the new turn. Duplicating the working directory
  together with the session store was tested on 2026-09-16 and needs
  no rewriting of paths inside the copied session. On 2026-09-29 both
  programs met the trust question again and reported it as such.
- `codex` blocks with a trust question that applies to the git
  repository root, not only to the directory you point it at. The
  prompt passed as an argument survives it and becomes the first
  turn. A usage limit of the account can interrupt the run right
  after that with a dialog of its own, which peeragent reports as an
  unclassified waiting state. The first screen can also be an offer
  to update itself whose preselected option runs a global package
  install; on 2026-09-29 both programs met it and reported it as
  unclassified, which is what keeps a key sequence out of it. Pasting
  a prompt into a running `codex` has not been tried, and the position of the model argument
  after a resume is unverified.
- `agy` blocks with a login selection when no account is
  configured, which is what a test host without a login sees. With
  an account configured it asks about the directory instead and then
  comes up ready; both screens, the trust answer and the prompt
  hand-over by pasting are `tested` 2026-09-29, through both programs.
  The input line is a bare `>` and it stays on screen while `agy`
  generates its answer. peeragent has no busy marker for `agy`, so
  the pane captured right after a `send` was reported as `ready`
  while the answer was still being generated (`observed` 2026-09-29,
  both programs). Delivery of a launch prompt by `start agent` itself
  once `agy` is ready has not been run; the tested path used `send`.
  Its session store layout remains unknown, so duplicating is still
  refused.
- `opencode` comes up but refuses to work until a provider is
  configured. Its wrapper may run a package install during startup,
  which is why a version query can time out; on 2026-09-29 the
  process list of a start showed a package install under way. The
  prompt hand-over by pasting has never been run.
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

Input-prompt markers are established for `claude`, `copilot` and
`agy`. For `codex` and `opencode` there is no reliable marker yet, so
their screens are reported as an unclassified waiting state more
often, and a launch prompt that has to be pasted is deferred rather
than delivered. The `agy` marker is the bare `>` line, which is also
on screen while `agy` works, so `ready` for `agy` does not mean idle.

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
  has nothing to do with the directory. On a machine where `agy` has
  an account, its first screen is the directory question and then
  ready (`tested` 2026-09-29). On a machine where `opencode` has a
  provider, its first screen has not been observed here, so what it
  shows then is `unverified`. Either way the caller has to handle a
  first screen that is not ready.
- **A harness inherits the environment of the tmux server, not of
  the caller.** peeragent uses the standard tmux server, and a server
  that is already running was started by something else with whatever
  environment that had. A variable you set for the peeragent call -
  a relocated harness configuration directory, for instance - does
  not reach a harness launched into an existing server. On a machine
  where the server started fresh with the call it does. There is no
  way to tell from the output which of the two happened, so treat any
  environment-dependent setting as unreliable across a start.
- **The launched harness outlives peeragent, but not everything.**
  It keeps running in its tmux session, as intended. It does not
  survive the tmux server going down, and on a machine where the
  account has no lingering enabled, logging out takes the server with
  it. If an unattended agent has to survive a disconnect, the server
  has to be allowed to.
- **Key sequences describe dialogs on a date, and there are three
  different ones.** The answer to a trust question is whatever the
  harness showed when it was checked. Claude Code preselects the
  refusing option, so an arrow key comes first. The two that ask
  with a numbered menu act on the digit alone, without the Enter
  their own hint text suggests (`tested` 2026-09-28). The
  Antigravity CLI preselects the accepting option, so a bare Enter
  confirms (`tested` 2026-09-29). Three harnesses, three patterns
  for one question - which is why the sequence belongs to the
  harness description and not to a general rule. A harness
  update may renumber the options or replace the dialog, and then
  the sequence is wrong. This is why every start ends with the
  session name being passed to the user: attaching to the session
  and looking is the one diagnosis that no update can break.
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
  names such a flag. For `opencode` there is no provider on the test
  host to try it with, and for `agy` it has not been tried, so both
  stay on pasting in the table above. For GitHub Copilot CLI the same
  question was settled by a run on 2026-09-28 and the table reflects
  it.
- A launch prompt is limited to 120 effective characters, where
  absolute paths do not count. A longer prompt is refused before
  anything starts. Both programs refuse an over-long prompt with exit
  code 2 in one conformance case, which shows they agree on that
  case. Run once by hand with a stand-in harness on 2026-09-29, both
  programs accepted a prompt of exactly 120 effective characters next
  to a path and refused one of 121 (`observed`). The counting rule has
  no test of its own beyond that, so its other edge cases (a path with
  a space, a quoted path, text without word boundaries) are
  `unverified`, and the limit has not been met in a run against a
  real harness.
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
- **`busy` and `unknown` can differ between the two programs.**
  Whenever the first capture did not match a trust, authentication or
  provider question - so for a ready, busy or unrecognised screen
  alike - the rule is to capture again after two seconds and report
  `busy` if the two differ. When the
  screen carries something that changes, such as a spinner, the
  outcome depends on where the second capture falls, and on
  2026-09-29 one program reported `unknown` and the other `busy` for
  the same `agy` screen. Both applied the rule as written. The
  difference is not a divergence in logic, and for the caller both
  values mean the same thing: look at the pane yourself. But the
  claim that both programs report the same value holds only for
  screens that do not change.

## Planned

- Conformance cases that start a harness in tmux and call `send`,
  compare the log files, and cover the counting rule for the prompt
  limit; unit tests for the classification of screens.
- Input-prompt markers for `codex` and `opencode`, which need a host
  with a login and a configured provider, and a busy marker for
  `agy`.
- A run of `--resume`, `--model` and `duplicate` through the programs
  against real harnesses.
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
A new conformance case is recorded in the column for it and does not
change an evidence level.
