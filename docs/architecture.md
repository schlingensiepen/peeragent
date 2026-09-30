# Architecture

This document describes how peeragent is built: the layers of the
tool, the handler contract that keeps all harness knowledge in one
place, the two implementations and the equivalence they owe each
other, the conformance test that enforces that equivalence, and
the tmux runtime.

It describes the design that is specified. What is implemented,
what is tested and what is still missing is recorded in
[MATURITY.md](../MATURITY.md); read it first. Flags, fields and
exit codes are not repeated here: the command surface is in
[cli.md](cli.md), the message vocabulary, the output frame and the
log format in [output-format.md](output-format.md). The terms used
below are defined in [glossary.md](glossary.md), the reasoning
behind the design in [adr/README.md](adr/README.md).

## Layers

Listed from the outside in. Each layer uses only the layers below
it.

| Layer | Responsibility |
|---|---|
| CLI | recognize `--help` and then `--json` before parsing, parse arguments, select the subcommand, set the exit code |
| Commands | one flow per subcommand: `list harness`, `list models`, `start agent`, `send`, `duplicate`, `version` |
| Preflight | tool and argument checks per subcommand in a normative order, `fatal` with a `hint`, exactly one `info` per successful tool and harness check |
| Runtime | create the tmux session without a race, read the pane, deliver the prompt, detect processes |
| Git setup | local `git init` for `--git-repo` |
| Handler registry | map a harness key to its handler, iterate in a fixed order, call the contract functions |
| Handlers | one section per harness: metadata, detection, catalog, argv, prompt delivery, pane classification, session store checks, session copy |
| Catalogs | the static model lists per harness, each entry with its `catalog_updated` date |
| Subprocess | one call path for every external program: stdin from `/dev/null`, a timeout, output captured |
| Emitter | plain-text and JSON output from fixed templates, `user_relevant` and `hint`, the log sink, the verbose filter, a clean close |
| Log | one file per invocation, JSONL, with environment redaction |

Commands call preflight, the runtime, git setup and the handlers.
Everything that leaves the process goes through the emitter.
Handlers never write to stdout and never emit messages; they
return data, and the core decides what becomes a message.

The registry order is fixed: `claude`, `codex`, `agy`,
`opencode`, `copilot`. Every listing and every iteration follows
it, because the order of messages is part of the output contract.

`list git-templates` is reserved. It parses, and then ends with a
`fatal` and exit code 2 until the remaining git template kinds
are built.

## File layout

Each implementation is a single executable file: `tools/peeragent.py`
in Python and `tools/peeragent` in Bash. Neither is a package, so
installing the tool means copying one file; there are no import
paths to fix. The cost is two long files. A package layout becomes
worthwhile only once handlers come from outside the project.
Whether the files are present in this repository yet is stated in
[MATURITY.md](../MATURITY.md).

Both files carry the same sections in the same order, so that a
reviewer and the conformance test can put the two versions of one
rule side by side:

```text
1   header: license, PEERAGENT_VERSION, constants, minimum versions
2   emitter and log
3   helpers: paths, sanitizing, redaction, subprocess, UUIDv7
4   catalogs (data)
5   handler contract and the handler sections
6   runtime (tmux)
7   git setup
8   preflight
9   commands
10  CLI and main
```

A handler section is the block of code for one harness inside that
one file. The version is the constant `PEERAGENT_VERSION` in both
files; there is no version file, and
[CHANGELOG.md](../CHANGELOG.md) carries the version in readable
form.

## The emitter

The emitter is the only writer to stdout. It exists once per run:
a class in Python, a set of functions over global state in Bash.
Its contract:

- `--help` is recognized before anything else. It prints usage to
  stdout, exits 0, writes no log and opens no array.
- `--json` is recognized before argument parsing, by looking for
  an argv element that is exactly `--json`. In JSON mode `[` is
  the first thing on stdout, so even an argument error appears as
  a `fatal` inside the array.
- Plain mode prints one line per message from a fixed template
  per message type, continuation lines indented by two spaces.
  Colors only on a TTY, without `NO_COLOR` and without
  `--no-color`.
- The array and the log are closed by an exit handler, and by
  handlers for SIGINT, SIGTERM and SIGHUP. Only SIGKILL leaves an
  unterminated array. In Bash the exit trap runs in the main
  process only, guarded by a process-id comparison.
- `debug` and `timing` messages reach the log always and stdout
  only with `--verbose`. `invocation` and `env` reach the log
  only, never stdout.
- `user_relevant` is present on every message. `hint` is
  mandatory on `error` and `fatal`. Every `warn` goes through the
  emitter; nothing is written to stderr except interpreter
  warnings and emitter emergencies.
- The order of messages, including the preflight success
  messages, is normative. It is what the conformance test
  compares.

Output from subprocesses is captured into variables and never
passed through, so that stdout stays the emitter's alone.

The Bash implementation only has to produce JSON, never read it.
A small set of functions is enough: one that escapes a string, one
that builds a single-line object from typed key-value pairs, and
one that builds an array of strings. Everything that comes from a
subprocess, a pane or a path goes through the escaping function.
Pane captures are taken without escape sequences, so no terminal
control bytes reach the output.

## The handler contract

The core knows nothing about harnesses. It knows the vocabulary of
the contract, not flag names, banner texts or storage paths. What
a harness cannot do, its handler declares, and the core reports it
instead of simulating it.

### Constants

| Constant | Type | Meaning |
|---|---|---|
| `key` | string | the harness key used on the command line and in every message, for example `claude` |
| `description` | string | the fixed human-readable name of the harness, used in listings |
| `binary` | string | the program name looked up in `PATH` |
| `prompt_delivery` | `"argv"` or `"send_keys"` | how the launch prompt reaches the process: as the last argv element at start, or pasted into the pane after boot |
| `resume_support` | `"ok"`, `"experimental"` or `"unsupported"` | maturity of resuming an earlier session. `unsupported` makes `start agent --resume` a `fatal` in preflight; `experimental` produces a `warn` |
| `duplicate_support` | `"ok"`, `"experimental"` or `"unsupported"` | maturity of copying the session store. `unsupported` makes `duplicate` a `fatal` before anything is copied; `experimental` produces a `warn` |
| `duplicate_tested` | boolean | whether the copy has been exercised on a test host. It feeds [harnesses.md](harnesses.md) and does not appear in any message |
| `trust_answer` | string or null | the key sequence that answers the trust question with yes, for example `1` or `Down Enter`. It is named in the `hint` of a warning; the tool does not send it itself. It records what a dialog looked like on a given day and may be broken by a harness update |
| `resume_hint` | string or null | what to do when a resume is attempted on a harness whose resume support is `experimental`. The core has no harness names, so texts that differ per harness live here |
| `duplicate_refusal_hint` | string or null | what to do instead when the harness does not support duplicating. It must not refer to the copy: the refusal happens before anything is copied |
| `resume_failure_hint` | string or null | what to do when a resume finds no session in the copy |

### Functions

Signatures are written in the Python form. The Bash form is the
same contract under a naming convention, described below.

| Function | Meaning |
|---|---|
| `detect() -> HarnessInfo{installed: bool, path: str \| None, version: str \| None}` | look the binary up in `PATH`, then run `<binary> --version` under a timeout. `version` is the first line **of stdout** with whitespace trimmed from both ends, kept opaque: no regular expression, no format claim. stderr is discarded, because one of the harnesses writes a warning line there. A timeout or an exec failure while the binary exists yields `installed: true, version: null`, and the core emits a `warn` |
| `list_models() -> list[Model{key, description, catalog_updated}]` | the static catalog for this harness, in catalog order |
| `launch_argv(folder, resume) -> list[str]` | the binary plus resume arguments. Without the model, without the prompt |
| `model_argv(model) -> list[str]` | the model arguments, with the model string passed through opaquely. Called only when `--model` was given |
| `prompt_prefix_argv() -> list[str]` | arguments that must sit immediately before the prompt text. Only meaningful for `argv` delivery, and usually empty |
| `detect_prompt_type(pane_text) -> Awaiting` | classify the pane. The text is the captured lines joined with newlines; the patterns are substring or whole-line matches, case-sensitive, over the whole text, and they live in the handler |
| `session_store_exists(path) -> bool` | whether this harness already keeps a session store for `path`. Used by the preflight of `duplicate` against the destination |
| `duplicate_session(src, dst) -> DuplicateResult{status, files, bytes, session_dir \| None}` | copy the session store only; the core copies the working tree. Called only when `duplicate_support` is not `unsupported`. If there is no store for `src`, the result is `files: 0`, `bytes: 0`, `session_dir: null`, and the core emits a `warn` instead of failing |

`HarnessInfo`, `Model` and `DuplicateResult` are plain records.
The registry maps each key to its handler and preserves the fixed
order.

`Awaiting` is the classification of the first screen. Its values
are `ready`, `busy`, `trust_prompt`, `auth_prompt`,
`provider_prompt` and `unknown`; the value `error` is reserved and
is not assigned, because a harness that has died is reported as
its own message. The default is `unknown`. A handler returns
`ready` or `busy` only on a marker it has evidence for. When
several markers match, the precedence is `trust_prompt` over
`auth_prompt` and `provider_prompt`, over `busy`, over `ready`:
the empty input line of some harnesses stays on screen while they
work, so `busy` markers are deliberately narrow and cover only
text that appears exclusively during work. The case where no
marker matches at all is not the handler's problem; the core
catches it with the double capture described under the runtime.

### Where the core calls them

- Preflight of `start agent`: `detect` decides whether the
  harness is installed; `resume_support` decides `--resume`;
  `prompt_delivery` sets the size limit for the prompt file,
  because an argv prompt has to fit on a command line.
- Building the argv: `launch_argv`, then `model_argv` when
  `--model` was given, then, for `argv` delivery,
  `prompt_prefix_argv` and the prompt text.
- Post-boot diagnosis: `detect_prompt_type` produces the
  `awaiting` value. On `trust_prompt` the emitted `hint` contains
  the full key-sending command line built from `trust_answer`.
- Prompt delivery: only for `send_keys` delivery and only when
  the pane is `ready` does the core paste the prompt. Otherwise it
  reports the prompt as not delivered.
- Preflight of `duplicate`: `duplicate_support` before any copy,
  then `session_store_exists` against the destination. The core
  copies the working tree and then calls `duplicate_session`.

### The Bash form

Bash has no objects, so the contract is a naming convention.
Functions are named `h_<key>_<name>`, results go to stdout, and
the core dispatches by building the function name from the key:

| Function | Result on stdout |
|---|---|
| `h_<key>_meta` | the constants, pipe-separated: `description`, `binary`, `prompt_delivery`, `resume_support`, `duplicate_support`, `duplicate_tested`, `trust_answer` |
| `h_<key>_hints` | the three hint texts, pipe-separated: `resume_hint`, `duplicate_refusal_hint`, `resume_failure_hint`; an empty field stands for null |
| `h_<key>_detect` | `installed\|path\|version`, with `installed` as 0 or 1 and an empty `version` standing for null |
| `h_<key>_list_models` | one record per line, `key\|description\|catalog_updated` |
| `h_<key>_launch_argv <folder> <resume>` | the argv, NUL-separated |
| `h_<key>_model_argv <model>` | the argv, NUL-separated |
| `h_<key>_prompt_prefix_argv` | the argv, NUL-separated |
| `h_<key>_detect_prompt_type` | the pane text arrives on stdin, the awaiting token is printed |
| `h_<key>_session_store_exists <path>` | nothing; the exit status answers, 0 meaning the store exists |
| `h_<key>_duplicate_session <src> <dst>` | `status\|files\|bytes\|session_dir` |

Scalars are pipe-separated because they are short and known;
argument vectors are NUL-separated because they may contain
anything, including spaces and newlines.

### Adding a harness

A contributor who wants a sixth harness needs no change to the
core. The work is:

- Add a handler section to both implementation files, in the same
  place in the section order, exporting the constants and the
  functions above.
- Add the harness key to the registry in both files, keeping one
  shared order.
- Supply a static model catalog with a `catalog_updated` date.
- Supply the pane markers for the states the harness actually
  shows, and leave everything else at `unknown`. Declare
  `resume_support` and `duplicate_support` honestly; `unsupported`
  with a `hint` naming the harness-native alternative is a
  complete answer.
- Add a fake binary and fixtures to the conformance test, and
  record the evidence level of each claim in
  [MATURITY.md](../MATURITY.md) and
  [harnesses.md](harnesses.md).

Nothing else in the tool may learn the name of the new harness.
If a change would put a flag name, a banner text or a storage path
outside a handler section, the contract is the wrong shape and has
to be extended instead.

## The two implementations

`tools/peeragent.py` requires Python 3.11 or newer and uses the
standard library only: no third-party packages. `tools/peeragent`
requires Bash 4.4 or newer with GNU coreutils and findutils. Both
implementations need tmux 3.2 or newer and `ps` from procps for the
runtime, and git only when `--git-repo` is used. It uses no `jq`,
no `sqlite3`,
no `uuidgen` and no `iconv`, and it sets a UTF-8 C locale. The
absence of `iconv` is why the tool does not validate the encoding
of a prompt file: a check that only one of the two implementations
could perform would not be one check but two.

The Bash implementation never parses JSON. It may match literal,
known tokens in foreign files with `grep` or `sed`, and it reads
line-oriented formats line by line, but it does not interpret
them. That single constraint explains several design choices:
model catalogs are static rather than queried from the harness,
and session indexes kept in SQLite are not touched, which is why
the corresponding duplicate paths refuse instead of guessing.

### The equivalence contract

Both files accept the same subcommands and the same flags. Their
outputs are equivalent in structure, not in bytes. Concretely,
for the same arguments in the same environment:

- Both outputs are accepted by a JSON parser.
- Both produce the same message types in the same order.
- Corresponding messages carry the same field names, and values
  that are semantically equal.
- The exit codes are equal.
- Both logs parse, and carry the same sequence of message types
  once `debug` and `timing` are removed.

What is explicitly free: the order of fields inside an object,
and whitespace. Python writes compact JSON without escaping
non-ASCII characters; Bash builds the same objects with
formatted output and a shared escaping rule. Byte equality was
tried and abandoned: a standard JSON serializer and hand-built
output cannot be reconciled byte for byte without contorting one
of them, and the contract that matters to a caller is the
structure.

One message is exempt from equivalence: the environment message
in the log, which states which implementation is running, the
interpreter version, and the peeragent version. It is expected to
differ.

### Choosing an implementation

Use `peeragent.py` when Python 3.11 or newer is present, and
`peeragent` otherwise. The two may be mixed within one project,
because output and log are structurally the same.

## The conformance test

The conformance test is a Bash runner under `tests/conformance/`
that calls both implementations with the same arguments and
compares them. It uses Python only to parse and compare. It has no
golden files and no `expected/` directory: the comparison is one
implementation against the other, so neither can drift towards a
recorded snapshot of itself.

The sandbox per case gives each run its own home directory and its
own `PATH`. The harnesses on that `PATH` are fake binaries in
`fixtures/bin/`: shell scripts that answer `--version` with a
fixed string, print a banner in interactive mode, and then block.
A variable selects the variant a case needs: normal, a trust
question on the first screen, an immediate exit with an error
line, a `--version` call that hangs, and a `--version` call that
fails. The absence of tmux is arranged by leaving it off the
`PATH`.

A case is a directory `fixtures/<name>/` holding the argument line
for the run, optionally a skeleton of the home directory, and
optionally a setup script that the runner executes first with the
sandbox and home paths in the environment, for cases that need a
session store whose name depends on the sandbox. The argument line
may use placeholders for the sandbox and home paths, which the
runner substitutes at run time.

Before comparing, the runner normalizes the values that cannot be
stable: timestamps, process ids, the pane process id, the child
process list, the random suffix of a session name, byte and file
counts, captured pane lines, harness version strings, the
implementation name, and the human-readable message and hint
texts; sandbox paths and the program name in the recorded argument
vector are replaced as well. The peeragent version in the version
message is not normalized. Normalizing means replacing a value
with a fixed placeholder: whether the key is present at all
remains part of the comparison. Messages and hints are normalized
because they are prose. The two programs word them independently and
nothing requires them to agree, which is easy to confirm: ask either
for a subcommand that does not exist and read the two answers. A
document that quotes one particular wording as a promise is wrong
for that reason.

The comparison then checks that both message lists have the same
length and that each position is equal as a parsed object, that
the exit codes match, and that the logs parse with the same type
sequence. For each subcommand there is additionally a plain-text
case, compared by line count and by the first word of each line
after the same normalization. A difference is reported as a diff.

There are no unit tests. The parts that would be easier to check
directly than through the command line - the escaping, path
sanitizing, environment redaction, identifier generation, and the
screen classification patterns against recorded panes - are covered
only as far as a conformance case happens to exercise them. That is
a gap, and [MATURITY.md](../MATURITY.md) lists it as planned rather
than pretending otherwise.

## The tmux runtime

peeragent uses the standard tmux server of the user rather than a
private socket, so that a started harness appears in the sessions
the user already sees. Every call is made with the UTF-8 flag, and
every new session gets mouse mode on.

Target forms matter and are easy to get wrong. Session commands
address the session as `=<sess>`; window and pane commands address
the first window as `=<sess>:`. The leading `=` demands an exact
session name; without the trailing colon a pane command reads the
name as a window name and fails.

### Session naming

A session is named `peeragent-<basename>-<harness>-<8 hex>`. The
folder path is made absolute first and its trailing slash
removed; an empty basename becomes a fixed placeholder. In the
basename every character outside letters and digits becomes a
hyphen, and the result is truncated to 32 characters. The suffix
is eight random hex characters. A name collision is recognized
from the error text of the create call and answered with a new
suffix, up to a small number of attempts before the run fails.

The name carries the harness key in a position that can be read
back, which is how `send` finds the right handler for a session it
did not create.

### Creating the session without a race

One call creates the session with the harness already in it,
detached, in the target folder, at a fixed pane size of 200 by 50.
Mouse mode is set afterwards, for the person who attaches; if that
does not take, nothing is lost, because the harness is running,
which is what was asked for. Argv is always passed as separate
arguments, never as one string.

A session exists exactly as long as the harness in it. If the
harness dies, the session goes with it, and asking whether the
session is there is how peeragent knows. What it does **not** get
that way is the reason: no exit status, no last lines of output.
That is a deliberate trade, and it replaced an earlier sequence
that created the session empty, set an option keeping the pane
after its process exits, and then replaced the placeholder shell
with the harness. The earlier way preserved the evidence of a
failed start and cost three more calls and the killing of a shell
in a tool that does nothing but launch.

**peeragent ends no session, under any circumstances.** There is
no longer a moment in which it holds a session without a harness
in it, so there is nothing it would have to clean up.

### Delivering the launch prompt

For `argv` delivery the prompt text is always the last element of
the argv, and the core builds exactly one generic wrapper around
the harness call:

```text
bash -c 'pf=$1; shift; exec "$@" "$(cat "$pf")"' _ <prompt-file> <launch_argv> <model_argv> <prompt_prefix_argv>
```

The first argument is the absolute prompt file; after the shift
the remaining arguments are the full harness argv. The prompt
content is read from the file by the wrapper and never passes
through a shell level of the caller, so no quoting of the prompt
is needed anywhere. Without a prompt file the argv is passed
directly, with no wrapper.

One consequence has to be stated plainly: with `argv` delivery the
prompt text stands in the command line of the harness process and
is therefore readable by other users of the host through the
process list. Where that matters, deliver the prompt afterwards,
or keep the prompt short and put the substance in a task file.

For `send_keys` delivery the argv is passed directly as well, and
the prompt follows after boot: peeragent copies the prompt file
without its trailing newlines, loads the copy into a tmux buffer,
pastes it into the pane in bracketed-paste mode, and sends a
final newline. Bracketed paste is what keeps a multi-line prompt
from being submitted line by line. The buffer is deleted again,
including on the error path.

### Post-boot diagnosis

After the configured boot wait, measured from the moment the
session was created, the runtime asks tmux for the process id of
the pane.

No answer means no session, and therefore no harness: it did not
survive the boot wait. peeragent reports that, with no exit status
and no lines, because there is nothing left to read, and ends with
the exit code reserved for this case. The caller learns that the
start failed and not why; the way to find out is to run the same
harness by hand.

Otherwise the pane is captured and handed to the handler for
classification. If the result is not one of the three waiting
states, a second capture follows after a short pause: if the two
captures differ, the harness is working, and the state is `busy`
even though no text marker matched. This double capture is the
generic answer to harnesses that show no spinner. The reported
pane content is the second capture.

For the waiting states and for `unknown`, a warning with a hint
accompanies the pane report, so the caller knows that a human
decision or a key sequence is needed. Only when the pane is
`ready` and delivery is by paste is the prompt sent. In every
other case where a prompt exists but was not delivered, peeragent
says so explicitly, names the delivery kind, and gives the hint
that leads to the follow-up delivery.

### Process detection

The pane process id comes from tmux. Its children are read from
the process table, recursively to a depth of two. The short
command name is not usable for recognizing a harness, because the
kernel truncates it and several harnesses run under a wrapper; the
full argument line is the reliable column. If the process tool is
missing, the child list stays empty and a warning says so.

Each step of a run is timed into the log under a fixed step name,
which makes a slow start attributable without any extra
instrumentation.

## Command flows

The layers above compose into a small number of flows. The full
preflight order, all flags and the exact messages per step are in
[cli.md](cli.md) and [output-format.md](output-format.md).

`start agent` parses, opens the log, runs preflight, optionally
initializes a local git repository, announces the start, creates
the session with the harness in it, waits out the boot wait,
diagnoses the pane, delivers or defers the prompt, and finally
reports the session with its process tree. A harness that died
during boot ends the flow early with its own message and exit
code.

`send` delivers a prompt into a session that already exists. Its
preflight checks tmux, the session, the prompt file and that the
pane is alive, and it derives the handler from the session name;
if the name does not match the scheme, no handler is used and the
pane state is reported as unknown. The paste happens regardless of
the pane state, because the caller has already decided; that is
why the rule is to call it only after peeragent has reported an
undelivered prompt.

`duplicate` copies a working directory together with the harness
session history. Everything that can refuse, refuses before
anything is copied: the harness key, the duplicate maturity, the
paths and their containment, the presence of the harness, and
whether the destination already has a session store. Then the core
copies the working tree, and the handler copies the session store.
A missing source store is reported as a copy of nothing plus a
warning, not as a failure, because the working tree copy is still
useful.

`list harness`, `list models` and `version` need neither tmux nor
git. They exist so that a caller can discover what is available
before it commits to a start.
