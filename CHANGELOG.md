# Changelog

All notable changes to peeragent are recorded here.
The format follows Keep a Changelog, and the version numbers follow
Semantic Versioning.

## [0.1.0] - Unreleased

Not released. The command-line programs are not in this repository
yet; what is verified and what is not is recorded in
[MATURITY.md](MATURITY.md).

### Added

- Two call-compatible programs, one in Python using the standard
  library only and one in Bash, producing the same messages in the
  same order.
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
