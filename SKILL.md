---
name: launch-peer-agent
description: Start a coding-agent harness (claude, codex, agy, opencode, copilot) in a tmux session with peeragent, hand it a launch prompt, and interpret the structured JSONL result. Use when you need to start another agent as an independent peer rather than as a sub-agent.
---

# launch-peer-agent

This skill teaches you to start another coding agent with
`peeragent` and to read what peeragent reports back. You are the
**starting agent**. The process you start is a **launched harness**
running in its own tmux session.

## Terms

- **Harness** — an executable that runs an AI coding agent:
  `claude`, `codex`, `agy`, `opencode` or `copilot`. peeragent
  launches harnesses; it does not install or configure them.
- **Peer agent** — the name of the tool refers to an agent that
  works as an equal alongside you, in its own process and with its
  own context, rather than as a sub-agent inside your own session.
  What peeragent actually starts is a harness in a tmux pane.
  Whether that harness becomes a peer in a larger agent system
  depends on infrastructure outside this tool.
- **Starting agent** — you: the agent that calls
  `peeragent start agent`.
- **Launch prompt** — the text the launched harness receives at
  start, passed with `--prompt-file`.
- **Git template** — a described way to create a repository:
  local only, GitHub via `gh`, push-to-create, or an existing
  remote.

## Prerequisites

peeragent runs on Linux (native or WSL2) and needs `tmux` and
`git`. `gh` is optional but required for GitHub-related git
templates. Check what is available first:

```bash
peeragent list harness --json
```

Each installed harness appears as a `harness.detected` message with
`key`, `version`, `description` and `path`; missing harnesses appear
as `harness.missing`. Use the `key` in later calls.

## Writing the launch prompt

peeragent passes the prompt file through unchanged. It does not
template, preprocess or inspect it. Before you start a harness,
make sure the prompt covers the following:

1. **Communication channel and access.** Describe how the launched
   harness should talk back to you: which protocol, which address,
   which credentials. Do not rely on it discovering this by itself.
2. **A request to report back after initialization.** Include an
   explicit sentence such as: "After your first setup step, report
   back over the channel described above; otherwise we will assume
   you are lost." Without it, the launched harness may work
   silently and you cannot tell whether it is alive or stuck.
3. **The project's usual initialization steps.** Check what a
   fresh session in that project normally does (activate a virtual
   environment, install dependencies, read the project's
   instruction files, run the tests) and put those steps into the
   prompt. The launched harness does not know the project.
4. **Your own location.** Once the channel is up, tell the launched
   harness which host you run on, under which user and in which
   directory. This makes later file exchange easier.

**Keep the prompt file short.** For any substantial assignment,
write the full task description as a separate file inside the target
working directory (for example `TASK.md` or a file with a meaningful
name) and let the prompt file contain only a short pointer:

```
Read /path/to/project/TASK.md and carry out the assignment described
there. Complete step 1 only, then stop and report back.
```

A short pointer avoids shell-quoting problems, keeps the tmux and
log history readable, and makes the call repeatable because the
task file is versioned with the project.

## Starting a harness

```bash
peeragent start agent \
  --folder /path/to/project \
  --harness claude \
  --prompt-file /path/to/prompt.txt \
  --json
```

Optional flags:

- `--model NAME` — passed to the harness unchanged.
- `--resume` — continue the harness's previous session in that
  folder. Support depends on the harness; peeragent refuses the
  flag for harnesses that cannot resume interactively.
- Exactly one of `--git-template KEY`, `--git-repo` or
  `--git-repo-remote URL` — initialize a repository in the folder
  if it has none. peeragent refuses these flags when the folder is
  already a git repository.

peeragent checks that tmux, the harness and the folder exist,
optionally sets up git, creates the tmux session, waits about five
seconds for the harness to boot, captures the visible pane and
reports. The harness keeps running after peeragent returns.

## Reading the result

The `--json` output is a stream of one-line JSON objects, wrapped in
`[` and `]` with `,` lines between objects, so the whole output is
also a valid JSON array. The messages you will see for
`start agent`, in order:

```
{"type":"agent.starting","harness":"claude","folder":"/path/to/project","model":null,"resume":false}
{"type":"agent.pane","session":"peeragent-project-claude-a3f1c9e2","awaiting":"ready","lines":["..."]}
{"type":"agent.started","session":"peeragent-project-claude-a3f1c9e2","pane_pid":18320,"child_processes":[{"pid":18321,"comm":"claude","args":"claude"}]}
```

For `codex`, `opencode` and `copilot`, which receive the prompt
after boot, an additional message appears between `agent.pane` and
`agent.started`:

```
{"type":"agent.prompt_sent","session":"peeragent-project-codex-b7e2d0f1","bytes":312}
```

`claude` and `agy` receive the prompt as a command-line argument at
launch, so this message does not appear for them.

Basic message types that can appear anywhere:

| Type | Meaning |
|---|---|
| `info` | progress information |
| `warn` | something notable; the operation continues |
| `error` | a sub-operation failed; the operation continues |
| `fatal` | the operation was aborted |

Messages that need a human's attention carry `user_relevant: true`
and a `hint` string. Read the `hint` and decide whether to act on
it yourself or to inform the user.

## Handling the `awaiting` state

The `agent.pane` message tells you what the launched harness is
waiting for. Three of the five harnesses block on an interactive
question when started in a new directory, so treat this as the
normal case, not the exception.

| `awaiting` | What it means | What you do |
|---|---|---|
| `ready` | The harness shows its input prompt and is ready for work. | Continue with your task. |
| `trust_prompt` | The harness asks whether to trust the directory. | Answer with `tmux send-keys -t <session> "1" Enter`, or ask the user, depending on your policy. |
| `auth_prompt` | The harness is not logged in. | Inform the user that an external login is required. peeragent does not automate logins. |
| `provider_prompt` | The harness needs a model provider configured (typical for `opencode`). | Inform the user that the harness needs configuration. |
| `error` | The harness process exited; `lines` holds the last screen. | Inform the user and check the peeragent log file. |
| `unknown` | The screen matched no known pattern. | Show the user the captured `lines` and ask how to proceed. |

The tmux session name is in the `session` field. You can inspect
the pane at any time with `tmux capture-pane -t <session> -p` and
send input with `tmux send-keys -t <session> ...`.

## Duplicating a working directory

```bash
peeragent duplicate --from /path/to/project --to /path/to/project-copy --harness claude --json
```

This copies the working directory and the harness's session storage
so that the copy resumes with the original conversation history.
The result is a `harness.duplicated` message with
`status: "ok" | "experimental" | "unsupported"` and `tested: true |
false`. For `claude` the operation is tested and supported. For
`codex` and `copilot` it is experimental and produces a warning.
For `agy` and `opencode` peeragent refuses with a `fatal` message
because their session storage is a database that cannot be copied
safely.

## Logs

Every call writes a JSONL log to `~/.local/state/peeragent/logs/`
(one file per invocation, named by date, time, action and process
id). When something goes wrong, the log file is the first thing to
look at and the right thing to attach to a bug report. Logs may
contain the prompt text and file paths.

## When not to use peeragent

You can always start a harness directly, for example
`tmux new-session -d -s work -c /path/to/project claude`. Use
peeragent when you want the uniform, machine-readable account of
what happened, the `awaiting` classification and the per-invocation
log. If you do not need those, the direct call is fine.
