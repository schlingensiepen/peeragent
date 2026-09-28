---
name: launch-peer-agent
description: Start a coding-agent harness (claude, codex, agy, opencode, copilot) in its own tmux session with peeragent, write an assignment it can act on, and handle the trust or login question it stops on. Use when a second agent should run beside you as an independent process rather than as a sub-agent.
---

# launch-peer-agent

This skill carries the judgement that the `peeragent` command line
cannot carry for you: how to write an assignment another agent can
act on, and what to do with the screen that comes back from the
first start.

You are the **starting agent**. The process you start is a
**launched harness** in its own tmux session. It keeps running
after `peeragent` returns, and it does not report back to you
unless your assignment tells it how.

## Read the maturity report before you promise anything

Read [`MATURITY.md`](../../MATURITY.md) first. It states, per
function and per harness, which paths are tested and which are
not, and whether the programs under `tools/` are present at all.
You need that before you tell the user what this will do, and
before you run any command shown here.

## Where the syntax lives, and why not here

Flags, message fields and exit codes are documented once, in
[`docs/cli.md`](../../docs/cli.md) for the command line and
[`docs/output-format.md`](../../docs/output-format.md) for the
plain-text and JSONL output. Look them up there when you need
them.

They are deliberately absent from this file. Two places holding
the same flag list drift apart, and this file is loaded into
context every time the task comes up, so it stays short. If you
ever extend it and the addition names a flag, a field or an exit
code, it belongs in the reference documents instead.

These links are relative to the repository. If you copied this
directory into your own skill store, they point back into your
checkout of the peeragent repository.

## Terms

- **Harness** — an executable that runs an AI coding agent:
  `claude`, `codex`, `agy`, `opencode` or `copilot`. peeragent
  launches harnesses. It does not install, update or configure
  them.
- **Peer agent** — what the tool is named after: an agent that
  works beside you in its own process and with its own context,
  not inside your session. Whether the harness you start becomes
  a peer in some larger agent system depends on infrastructure
  outside this tool. peeragent knows nothing about fleets, teams
  or identities.
- **Launched harness** — the process peeragent spawns in the tmux
  pane. This is the only term for it; do not call it a peer agent
  and do not call it a sub agent.
- **Sub agent** — an agent a harness starts from inside a prompt.
  peeragent starts none.
- **Starting agent** — you, the caller of `peeragent start agent`.
- **Launch prompt** — the text the launched harness receives at
  start, read from a file.
- **Pointer prompt** — a short launch prompt that points at a task
  file instead of containing the assignment. Required, see below.
- **Task file** — the file in the working directory that the
  pointer prompt names.
- **Git template** — a described way of creating a repository for
  the working directory. Version 0.1.0 covers the local kind
  only; see [`docs/cli.md`](../../docs/cli.md).

## Choose the implementation

Two files, `tools/peeragent.py` and `tools/peeragent`, are
call-compatible. Use `peeragent.py` where Python 3.11 or newer is
available, otherwise the bash version. Output and log are
structurally the same, so you may mix them within one project.

Call the installed program. This skill bundles no copy of it. If
`peeragent` is not on the `PATH`, use the path recorded when it
was installed;
[`docs/install.md`](../../docs/install.md) describes both
placements.

## Decide the working directory first

Before you write anything, decide which directory the peer agent
is to work in, and pass exactly that one. The launched harness
inherits nothing from you: not your own current directory, not the
directory you wrote the task file into. It starts where you point
it.

Point it at the project itself, not at the folder above it. A
parent directory is the mistake that costs the most, because
nothing fails: the harness starts, the prompt arrives, the pane
looks healthy. What goes wrong is quieter. The harness reads
relative paths against the wrong place, the trust question covers
more than you meant, and the session history is filed under that
path, so a later continuation of the intended directory finds
nothing to continue.

Two habits remove the problem:

- Name absolute paths in the prompt, for the task file and for
  anywhere the peer agent is to write.
- Tell the peer agent, in the assignment, which directory it is
  supposed to be in, and ask it to confirm the directory it
  actually finds itself in with its first report. That turns a
  silent misplacement into a sentence you can read.

If you are starting a peer agent for a project you are working in
yourself, do not assume your own working directory is the right
one. Establish it, then pass it.

## Write the assignment: the obligations

peeragent starts a process and then lets go of it. The launched
harness lives on in its tmux session, unattended, after peeragent
has returned, and nothing connects the two of you. `send` delivers
a prompt that was left over from the start, and a read-only attach
lets you watch; neither is a conversation. Everything the launched
harness needs to know has to be in the assignment, because nothing
else will tell it. Cover all of these:

1. **The communication mechanism and how to reach it.** Protocol,
   address and credentials of the back channel belong in the
   assignment. Do not rely on the launched harness discovering
   them. peeragent is orthogonal to the mechanism and provides
   none, so pick one and describe it. Two are worth recommending:
   - **A folder both sides agree on.** Name the directory, say who
     writes what under which file names, and ask for a first file
     after the setup step. No software, no daemon, survives a crash
     on either side, and a shared filesystem carries it across
     users and hosts.
   - **[simple-a2a](https://github.com/schlingensiepen/simple-a2a),**
     a small agent-to-agent protocol, when file dropping is not
     enough and you want addressed messages.

   A socket, a message queue or an issue tracker work as well. What
   does not work is leaving it out and hoping.
2. **An explicit request to report back after initialization.**
   A sentence such as "after your first setup step, report back
   over the channel described above" is what separates a harness
   that is working from a harness that is stuck. Without it you
   cannot tell the two apart.
3. **The project's usual initialization steps.** Find out what a
   fresh session in that project normally does — activate an
   environment, install dependencies, read the project's
   instruction files, run the tests — and write those steps into
   the assignment. The launched harness does not know the
   project.
4. **Where you are.** Once the channel is up, state the host, the
   user and the directory you are running in. File exchange in
   either direction needs it.

[`examples/task-file-template.md`](../../examples/task-file-template.md)
is a copy-ready form of these obligations.

## Use a pointer prompt, not the assignment itself

This is not a style preference, and it is not left to you:
peeragent refuses a prompt above 120 effective characters with exit
code 2, before anything is started. Absolute paths do not count
towards that length, so naming the task file and the place to report
costs you nothing; the words between them are the budget. The same
check applies when you deliver a deferred prompt later, so there is
no way around it. The counting rule is in
[`docs/cli.md`](../../docs/cli.md).

What to do with it:

1. Write the full assignment into a file in the target working
   directory — `TASK.md`, or a name that says what it is. Version
   it there if it changes.
2. Write a short prompt that tells the launched harness to read
   that file and carry out what it says, with the scope and the
   stopping condition. Pass only this short prompt as the prompt
   file.

```text
Read /srv/project/TASK.md and carry out the assignment described
there. Complete step 1 only, then stop and report back.
```

[`examples/prompt-file-template.md`](../../examples/prompt-file-template.md)
is a copy-ready form.

The reasons: no shell quoting of long text, so quotes, backticks
and newlines in the assignment are harmless; a short and readable
tmux and log history; a repeatable call, because the assignment
is a file you can point at again; and, where the harness receives
the prompt as a command-line argument, the assignment text does
not end up in the process list where other users of the host can
read it.

peeragent enforces none of this. The prompt file is just a file
with the launch prompt. Keeping the convention is your job. A
one-line instruction may of course stay in the prompt file
itself.

## Read the first screen: the `awaiting` states

Expect the first start in a directory to stop short of doing
work. All five harnesses block there: `claude`, `codex` and
`copilot` ask whether they may trust the directory, `agy` is not
logged in, `opencode` has no provider configured. This is the
normal case, not the exception.

After the boot wait, peeragent captures the visible pane and
classifies it in the `awaiting` field of the `agent.pane`
message.

| `awaiting` | What it means | What you do |
|---|---|---|
| `ready` | The input prompt is visible and the harness is waiting. | Carry on. Where the prompt is delivered by keystrokes, peeragent has already pasted it. |
| `busy` | The harness is working. | Wait. Watch the pane with `tmux capture-pane -t "=<session>:" -p`. Do not deliver the prompt again. |
| `trust_prompt` | The harness asks whether to trust the directory. | Answer with the key sequence below, or ask the user first if your policy says so. Then follow the deferred-prompt rule. |
| `auth_prompt` | The harness is not logged in. | Tell the user. The login is external and interactive; peeragent does not automate it. |
| `provider_prompt` | The harness needs a model provider configured. | Tell the user. For `opencode` this is `/connect` inside the harness. |
| `unknown` | No known pattern matched. | Show the user the captured lines and ask how to proceed. |
| `error` | Reserved, not used in version 0.1.0. | A harness that died reports `agent.exited` instead; tell the user and read the log. |

### Answering a trust prompt

peeragent does not answer trust prompts itself in version 0.1.0.
It reports the key sequence in the hint of its warning, and you
send it:

```bash
tmux send-keys -t "=<session>:" Down Enter
```

| Harness | First start in a new directory | Key sequence |
|---|---|---|
| `claude` | trust prompt | `Down Enter` |
| `codex` | trust prompt | `1 Enter` |
| `copilot` | trust prompt | `1 Enter` |
| `agy` | login selection, no trust prompt | none; the user has to log in |
| `opencode` | provider selection, no trust prompt | none; the user has to configure a provider |

The key sequences were tested on 2026-09-23. `claude` needs
`Down Enter` rather than a confirming key because its dialog
preselects the refusing option, "No, exit". For `codex` and
`copilot`, option 1 is the plain yes; `copilot` also offers a
"remember this folder" variant, which peeragent does not choose
for the user.

Before you answer for `codex`, note that its trust question
covers the whole git root, not just the folder you pointed at. If
the folder sits inside a larger repository, you are trusting the
repository. Say so to the user rather than answering silently.

A trust answer is remembered per directory for `claude`, `codex`
and `copilot`, so the second start in the same directory usually
goes straight to work.

For `agy` and `opencode` no confirmed ready marker exists yet, so
a healthy first screen from them may still be reported as
`unknown`. Show it to the user instead of assuming failure.

## Deliver a deferred prompt with `send`, and only then

If peeragent could not get the prompt into the harness, it emits
`agent.prompt_deferred` with a `delivery` field and a hint.

- Never call `peeragent send` without having seen
  `agent.prompt_deferred` for that session. The prompt may
  already be in the harness, and a second delivery means the
  assignment is carried out twice.
- `delivery: "send_keys"` — the harness takes the prompt by
  keystrokes. Answer whatever the pane was waiting for, then
  deliver right away:

```bash
peeragent send --session <session> --prompt-file <prompt-file>
```

- `delivery: "argv"` — the prompt was passed as a command-line
  argument and may have survived the interruption. Capture the
  pane first and send only if the harness did not pick it up,
  that is, if the input line is empty. Tested on 2026-09-23:
  `codex` took the argument prompt as its first turn after
  `1 Enter`, and `claude` after `Down Enter`. In both cases no
  `send` was needed.
- A paste that arrives while the harness is `busy` is buffered by
  the harness and processed after the current turn (tested with
  `copilot`). So a mistaken `send` will not corrupt the session,
  but it will still deliver the assignment twice.

## After a duplicate

A duplicated working directory carries its own trust state.
The first start in the copy shows a trust prompt again for
`claude`, `codex` and `copilot`, because trust is remembered per
directory. The copy also already contains `.git`, so asking
peeragent to initialize a repository there fails; see
[`docs/cli.md`](../../docs/cli.md).

## When a resume start fails

If a start with resume ends in `agent.exited`, or in
`awaiting: unknown` with a message about no session being found,
start again without resume. The hint on the message says what
applies to that harness. Resume support is tested for `claude`
only; for the other four it is documented but untested, and
`copilot` in particular falls back to the most recent session
anywhere on the host when the working directory has none.
Check [`MATURITY.md`](../../MATURITY.md) before you rely on it.

## Let the user watch

The `agent.started` message carries a hint with a read-only
attach line:

```bash
tmux attach -r -t "=<session>"
```

Pass that line on when you tell the user what you started.
Read-only means they can watch and scroll without typing into the
harness by accident.

## The harness can also be started directly

A harness in a tmux session is something you can create yourself:

```bash
tmux new-session -d -s work -c /srv/project claude
```

peeragent is worth using when you want the uniform
machine-readable account of what happened, the `awaiting`
classification and the per-invocation log. When you do not need
those, call the harness directly.

The obligations above are not part of peeragent either. They hold
whichever way you start the harness.

## If your harness has no skill format

This file is a Claude Code skill, and Claude Code is the only one
of the five harnesses with a skill directory. If you are running
`codex`, `agy`, `opencode` or `copilot`, there is no format to
install it into. Read this file and keep it as a reference, or
translate it into whatever your harness does offer — a rules
file, a project instruction, a note. The form is your choice. The
obligations, the pointer prompt rule and the `send` rule are not.
