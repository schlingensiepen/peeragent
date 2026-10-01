# Changelog

All notable changes to peeragent are recorded here.
The format follows Keep a Changelog, and the version numbers follow
Semantic Versioning.

## [0.2.0] - Unreleased

Two options a caller asked for, after a project tried to start eleven
agents at once and found what was missing. Nothing existing changed its
behaviour.

### Added

- `--harness-arg <arg>` on `start agent`, repeatable: the argument is
  appended to the harness's command line unchanged, after the arguments
  peeragent sets itself and before the prompt, so the prompt stays the
  last argument. The values are not read, not rewritten and not checked
  against the harness - peeragent does not know a harness's flags, and
  pretending to would be the part that goes stale.
- `--env <NAME=VALUE>` on `start agent`, repeatable: the variable is set
  in the new session through tmux, so the harness gets the caller's value
  rather than the tmux server's. Without it a harness started on a server
  that has been running since yesterday inherits yesterday's environment;
  that was measured, not assumed. The value is kept out of peeragent's
  own records, and a tmux that refuses the option is an error rather than
  a silent start without the variable.

### Not added, on purpose

- No option that answers a trust prompt. The key sequence peeragent
  knows describes someone else's interface on a particular day, and the
  cost of being wrong is a dialog whose preselected answer, for one
  harness, ends the session. Two routes that do not depend on peeragent
  being right are described in [docs/harnesses.md](docs/harnesses.md).
- No option that stops a session after a while. peeragent ends no
  session and no harness, under any circumstances; a caller that needs a
  deadline keeps it itself. [docs/cli.md](docs/cli.md) says how.

## [0.1.0] - 2026-10-01

First release, and a pre-release: both programs are in this
repository and run. What is verified and what is not is recorded in
[MATURITY.md](MATURITY.md); read it before relying on any statement
made here.

### Changed

- A start is one call now. The session is created with the harness
  already in it, and nothing is killed, replaced or configured on the
  pane afterwards beyond turning on mouse mode for whoever attaches.
  **peeragent ends no session under any circumstances.**
- A start that fails is still reported with its own message and exit
  code 4, but without an exit status and without pane content: a
  session exists exactly as long as the harness in it, so by the time
  the failure is noticed there is nothing left to read. The caller
  learns that the start failed and finds out why by running the same
  harness by hand. The earlier behaviour kept that evidence and paid
  for it with three extra calls and a killed shell in every start.

### Added

- Two call-compatible programs, one in Python using the standard
  library only and one in Bash, producing the same message types with
  the same fields in the same order. The wording of `msg` and `hint`
  is each program's own; the exceptions to the rest are named in
  [MATURITY.md](MATURITY.md).
- `peeragent start agent` launches one of the supported harnesses in
  its own tmux session, waits for it to come up, reports the visible
  screen and classifies it as ready, busy, or waiting for a trust,
  login or provider answer. A harness that died during startup is
  reported as such instead of being reported as running.
- Launch prompts are read from a file and handed to the harness
  either as a command-line argument or by pasting, depending on the
  harness. A prompt that could not be delivered because the harness
  was waiting for an answer is reported as deferred, with the
  command that delivers it afterwards.
- Launch prompts are limited to 120 effective characters, and paths
  that start with `/` and contain no spaces are not counted towards
  that. A longer prompt is
  refused with exit code 2 and a hint to write the assignment into a
  file in the working directory and pass a short prompt that points
  at it. The limit applies to a deferred delivery as well, so it
  cannot be bypassed.
- `peeragent send` hands a launch prompt to a session that is
  already running.
- `peeragent duplicate` copies a working directory together with the
  harness session history, so a second agent can continue an
  existing conversation in a copy of the workspace. Supported for
  `claude`; for the other harnesses the command refuses before it
  copies anything and names the harness's own way of resuming.
- `peeragent list harness` reports which of the supported harnesses
  are installed, with their version strings passed through
  unchanged, and `peeragent list models` reports the models known
  per harness. Any model string can be passed through even when it
  is not in the catalog.
- `--git-repo` initialises a local git repository in a working
  directory that does not have one.
- Every command prints plain text by default and single-line JSON
  objects with `--json`, with a fixed message order and exit codes
  that distinguish argument errors, missing tools, a harness that
  did not survive startup and runtime failures.
- Every invocation writes one log file under
  `~/.local/state/peeragent/logs/`, including the invocation, the
  environment with sensitive values masked, and every message.
  `--no-log` and `--log-file` control this.
- The Claude Code skill `launch-peer-agent` ships with the tool. It
  carries the obligations for the calling agent, the pointer prompt
  convention, how to handle a harness that waits for an answer, when
  to hand a prompt over afterwards, and the duty to give the user
  the name of the tmux session after every start.
- A documentation set covering installation, the command reference,
  the output format, the supported harnesses, troubleshooting, the
  architecture, a glossary and the design decisions, next to a
  maturity report that states the evidence behind every claim.
