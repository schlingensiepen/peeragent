# Glossary

The terms peeragent uses in its output, its documentation and its
code, in alphabetical order. Each entry gives the short meaning;
the longer explanations live in [cli.md](cli.md),
[output-format.md](output-format.md),
[architecture.md](architecture.md) and
[harnesses.md](harnesses.md). What is implemented and what is
tested is recorded in [MATURITY.md](../MATURITY.md).

- **agent.exited** — the message peeragent emits when the launched
  harness is no longer alive after the boot wait. It carries the
  exit status, the last lines of pane output and a hint; the tmux
  session is left standing so the output can be inspected.
- **agent.prompt_deferred** — the message peeragent emits when a
  launch prompt exists but was not delivered. It names the
  delivery kind and gives the hint that leads to the follow-up
  delivery with `send`.
- **awaiting** — the classification of the pane in a pane report:
  `ready`, `busy`, `trust_prompt`, `auth_prompt`,
  `provider_prompt` or `unknown`. The value `error` is reserved
  and is not assigned.
- **busy** — the awaiting value meaning that the harness is
  working. It takes precedence over `ready`, because the empty
  input line of some harnesses stays on screen during work. With
  argv delivery a busy pane means the prompt has been taken.
- **double capture** — the second pane capture taken a short time
  after the first during the post-boot diagnosis. If the two
  differ and no trust, auth or provider marker matched, the state
  is `busy`.
- **duplicate** — the subcommand that copies a working directory
  together with the harness session history, so that a second
  agent can continue from the same state.
- **evidence level** — the labelling of a statement about a
  harness as tested, documented, observed on a test host, or
  unverified.
- **exit code** — the process exit status: 0 success, 1 runtime
  error, 2 argument validation, 3 a required tool or harness is
  missing, 4 the harness was not alive after the boot wait, 130
  interrupted. Where several apply, the first fatal condition in
  preflight order decides.
- **git template** — a described way of creating a repository for
  the working directory. This release implements the local kind
  only.
- **handler contract** — the constants and functions every handler
  section exports, so that the core can work with a harness
  without knowing anything about it.
- **handler section** — the block of code inside an implementation
  file that holds everything specific to one harness. Handler
  sections never emit messages and never write to stdout; they
  return data.
- **harness** — an executable tool that runs an AI coding agent.
  peeragent knows `claude`, `codex`, `agy`, `opencode` and
  `copilot`.
- **harness session store** — the place where a harness keeps its
  own conversation history for a working directory. It is what
  `duplicate` has to copy in addition to the files, and what
  resuming a session reads.
- **JSONL pseudo-array frame** — the output format under `--json`:
  an opening bracket on the first line, one single-line object per
  message, a line holding a comma between objects, a closing
  bracket on the last line. The contract is structural, not
  byte-exact.
- **launch prompt** — the text in the file given with
  `--prompt-file`, written by the starting agent and passed to the
  launched harness unchanged.
- **launch template** — a named, fixed way of starting a harness.
  peeragent has no external configuration for this; the argument
  vector comes from the handler section.
- **launched harness** — the process peeragent spawned in the tmux
  pane.
- **log file** — the JSONL file peeragent writes per invocation
  under `~/.local/state/peeragent/logs/`, containing the
  invocation, the environment, timings and every message, with
  sensitive environment values redacted.
- **maturity level** — the honest classification of resuming and
  duplicating per harness as `ok`, `experimental` or
  `unsupported`, together with whether the duplicate has been
  exercised on a test host.
- **message type** — the kind of a message: the base types `info`,
  `warn`, `error`, `fatal` and `debug`, and the domain types such
  as the pane report, the started report, the duplicate result and
  the version report.
- **model catalog** — the static list of models peeragent knows
  for a harness, each entry with the date the catalog was last
  updated. There is no live query against the harness.
- **peer agent** — an agent that holds an identity in a team of
  agents. peeragent uses the term only to explain its own name and
  the name of the skill it ships; it assigns no identity and knows
  nothing of teams.
- **peeragent** — the command-line tool itself: it starts
  harnesses in tmux, reports the first screen, delivers a prompt
  afterwards, duplicates working directories, and lists harnesses
  and models.
- **pointer prompt** — a short launch prompt that only points at a
  task file in the working directory instead of carrying the
  assignment itself.
- **prompt delivery** — how the launch prompt reaches the
  harness: `argv`, as the last element of the command line at
  start, or `send_keys`, pasted into the pane after boot.
- **selection object** — any item in a listing. Each carries a
  short `key` for the next call and a `description` for a human or
  an agent to read.
- **send** — the subcommand that delivers a launch prompt into a
  session that is already running. It is meant to be called after
  peeragent has reported an undelivered prompt.
- **session** — the running process in a tmux session. The term
  also appears as the harness session store and should be read in
  context.
- **session_store_exists** — the contract function that answers
  whether a harness already keeps a session store for a given
  path. It guards the destination of `duplicate`.
- **skill launch-peer-agent** — the agent-facing document shipped
  with peeragent. It states the obligations of the starting agent,
  makes the pointer prompt mandatory, and points at the reference
  documents instead of repeating them.
- **starting agent** — the agent that calls `peeragent start
  agent`, writes the launch prompt and reads the output.
- **sub agent** — an agent that a harness starts from within a
  prompt. peeragent starts none.
- **subcommand** — one of `list harness`, `list models`,
  `start agent`, `send`, `duplicate` and `version`.
  `list git-templates` is reserved for a later release.
- **task file** — the file in the working directory that holds the
  full assignment and that the pointer prompt names.
- **tmux runtime** — the part of peeragent that owns the tmux
  session: naming, race-free creation, the target forms for
  session and pane commands, prompt delivery by paste buffer, pane
  capture and the post-boot diagnosis.
- **trust, auth and provider prompts** — the interactive questions
  a harness asks before it becomes productive: whether it may work
  in this directory, that it is not logged in, or that it needs a
  provider configured. All five harnesses block on one of these on
  a first start in a new directory.
- **trust_answer** — the handler constant holding the key sequence
  that answers a trust question with yes. peeragent names it in a
  hint and does not send it itself.
- **two implementations** — `tools/peeragent.py` in Python and
  `tools/peeragent` in Bash, call-compatible and structurally
  equivalent in output and log, each a single file, compared
  against each other by the conformance test.
- **user** — the human who runs the system, informed by the
  starting agent.
- **user_relevant** — the field every message carries. Together
  with a hint it tells the starting agent whether the human needs
  to be told.
