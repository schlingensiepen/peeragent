# Quick start: one session from beginning to end

This walks through a single use of peeragent: write the
assignment, start a harness, recognize the question it stops on,
answer it with the right key sequence, deliver the prompt that was
left behind, and look at the result.

Read [`../MATURITY.md`](../MATURITY.md) first. The commands below
are the specified behaviour; the maturity report says which of
these paths are tested and whether the programs are present in
the repository yet. The section "What is evidenced here" at the
end of this file says which screens on this page come from a test
run and which are the specified output.

The example uses `copilot`, because it shows the longest path: the
harness stops on a trust question, the prompt is not delivered,
and you deliver it afterwards. A shorter variant with `claude`
follows at the end.

Placeholders used throughout: `/srv/project` is the working
directory, `/srv/project/TASK.md` the assignment,
`/srv/project/.peeragent-prompt.txt` the prompt file.

## Step 1: write the task file

The full assignment goes into a file in the working directory, not
into the prompt. `task-file-template.md` in this directory is the
form to copy; it covers what the launched harness cannot find out
by itself.

```bash
cat > /srv/project/TASK.md <<'EOF'
# Assignment: add a health endpoint

## How to reach me
Write your replies to /srv/project/.reports/agent-out.md and append,
never overwrite. I poll that file every 30 seconds. I am running as
user dev on host build-01, in /srv/tooling.

## Report back after setup
When you have finished the setup steps below, append one line to the
reply file saying that you are up, before you start on the change.

## Setup for this project
- python3 -m venv .venv && . .venv/bin/activate
- pip install -r requirements-dev.txt
- read README.md and AGENTS.md in this directory
- pytest -q, and stop if it is not green before your change

## The change
Add a GET /healthz endpoint to src/app.py that returns
{"status": "ok"} with HTTP 200, and one test for it.

## Scope and stop
Only this endpoint and its test. Do not touch the deployment
configuration. When the tests pass, append your report and stop.
EOF
```

## Step 2: write the pointer prompt

The prompt file holds only a pointer to the assignment, with the
scope and the stopping condition. `prompt-file-template.md` in
this directory is the form to copy.

```bash
cat > /srv/project/.peeragent-prompt.txt <<'EOF'
Read /srv/project/TASK.md and do what it says. The setup steps
and the endpoint only, then stop and report as that file says.
EOF
```

Why not put the assignment in the prompt directly: the assignment
contains quotes, braces and newlines, and for two of the five
harnesses the prompt travels as a command-line argument, where it
would be visible to every user of the host in the process list.
peeragent also refuses it. A prompt above 120 effective characters
ends in exit code 2 before anything starts; absolute paths are not
counted, so the pointer above spends 104 of the 120.

## Step 3: start the harness

```bash
peeragent start agent \
  --folder /srv/project \
  --harness copilot \
  --prompt-file /srv/project/.peeragent-prompt.txt \
  --json
```

The output is one JSON object per line, wrapped in `[` and `]`
with `,` lines between objects, so the whole stream also parses as
a JSON array:

```json
[
{"type":"info","msg":"tmux found: 3.5a","user_relevant":false}
,
{"type":"info","msg":"harness copilot found: GitHub Copilot CLI 1.0.88.","user_relevant":false}
,
{"type":"agent.starting","harness":"copilot","folder":"/srv/project","model":null,"resume":false,"prompt_file":"/srv/project/.peeragent-prompt.txt","user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-project-copilot-b7e2d0f1","awaiting":"trust_prompt","lines":["╭ Confirm folder trust ─────────────────────────────╮","│ /srv/project                                      │","│ Do you trust the files in this folder?            │","│ ❯ 1. Yes                                          │","│   2. Yes, and remember this folder for future …   │","│   3. No (Esc)                                     │","╰───────────────────────────────────────────────────╯"],"user_relevant":false}
,
{"type":"warn","msg":"harness copilot is awaiting trust-prompt confirmation","user_relevant":true,"hint":"send '1' Enter to trust: tmux send-keys -t '=peeragent-project-copilot-b7e2d0f1:' 1 Enter"}
,
{"type":"agent.prompt_deferred","session":"peeragent-project-copilot-b7e2d0f1","prompt_file":"/srv/project/.peeragent-prompt.txt","awaiting":"trust_prompt","delivery":"send_keys","hint":"deliver with: peeragent send --session peeragent-project-copilot-b7e2d0f1 --prompt-file /srv/project/.peeragent-prompt.txt","user_relevant":true}
,
{"type":"agent.started","session":"peeragent-project-copilot-b7e2d0f1","pane_pid":18510,"child_processes":[{"pid":18511,"comm":"MainThread","args":"/usr/local/lib/copilot-linux-x64/copilot"}],"hint":"watch with: tmux attach -r -t '=peeragent-project-copilot-b7e2d0f1'","user_relevant":false}
]
```

Exit code 0. This is a successful run: the harness is up, and it
is waiting for an answer. What to read out of it:

- `agent.pane.awaiting` is `trust_prompt`. This is the normal
  outcome of a first start in a directory, not a failure. Every
  harness stops on something the first time: on the trust question
  if the directory is new to it, or on a login or provider question
  if none is configured on the machine.
- `agent.prompt_deferred` says the assignment has **not** reached
  the harness, and `delivery` is `send_keys`. You will deliver it
  in step 5.
- `agent.started.session` is the name you need for every
  follow-up command. Keep it.

Without `--json` the same run prints one line per message, with
the pane content indented underneath. Use `--json` when an agent
reads the output; see [`../docs/output-format.md`](../docs/output-format.md).

## Step 4: answer the trust question

peeragent does not answer for you in version 0.1.0. The hint of
the warning contains the whole command. For `copilot` the answer
is option 1:

```bash
tmux send-keys -t "=peeragent-project-copilot-b7e2d0f1:" 1 Enter
```

Note the `:` at the end of the target. Pane commands need it;
without it tmux reads the name as a window name and fails.

Per harness, the first start in a new directory and its answer:

| Harness | Stops on | Key sequence |
|---|---|---|
| `claude` | trust question | `Down Enter` |
| `codex` | trust question | `1 Enter` |
| `copilot` | trust question | `1 Enter` |
| `agy` | login selection | none; the user has to log in |
| `opencode` | provider selection | none; the user has to run `/connect` |

The key sequences were tested on 2026-09-23. `claude` needs
`Down Enter` because its dialog preselects "No, exit". For
`codex`, answering also trusts the whole git root, not just the
folder you pointed at, so tell the user before you answer.

For `agy` and `opencode` there is nothing to send. Inform the user
and stop; the login and the provider setup are interactive and
external.

## Step 5: deliver the prompt

Now, and only now, deliver the assignment. The rule is strict:
call `send` only after you have seen `agent.prompt_deferred` for
that session, because otherwise the harness may already have the
prompt and would carry out the assignment twice.

```bash
peeragent send \
  --session peeragent-project-copilot-b7e2d0f1 \
  --prompt-file /srv/project/.peeragent-prompt.txt \
  --json
```

```json
[
{"type":"info","msg":"tmux found: 3.5a","user_relevant":false}
,
{"type":"info","msg":"harness copilot found: GitHub Copilot CLI 1.0.88.","user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-project-copilot-b7e2d0f1","awaiting":"ready","lines":["  █ ▘▝ █  Check for mistakes.","","❯"],"user_relevant":false}
,
{"type":"agent.prompt_sent","session":"peeragent-project-copilot-b7e2d0f1","bytes":118,"user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-project-copilot-b7e2d0f1","awaiting":"busy","lines":["❯ Read /srv/project/TASK.md and carry out the assignment described there.","❯","○ Working esc interrupt"],"user_relevant":false}
]
```

The first `agent.pane` is the screen before the paste, the second
the screen after it. `awaiting: busy` in the second one is what
you want to see: the harness took the prompt and started working.

If it had come back `ready` again, the paste did not land. Look at
the pane before sending a second time.

## Step 6: look at the result

While the harness works, capture the pane as often as you like.
This is read-only and does not disturb it:

```bash
tmux capture-pane -t "=peeragent-project-copilot-b7e2d0f1:" -p
```

A `copilot` pane in the middle of a turn looks like this. Captured
on 2026-09-23 during a test with a three-line prompt, so the text
is that test's, not this example's:

```text
 ❯ Line one of the prompt: please answer with the single word ZEBRA.
   Line two: do not read any files.
   Line three: then stop.
 ❯
  ○ Working esc interrupt                       Auto → mai-code-1.1-flash
```

`○ Working esc interrupt` is the marker peeragent reads as `busy`.
When the turn finishes, that line is gone and the bare `❯` line
remains; that is `ready`.

To let the user watch, pass on the attach line from
`agent.started`:

```bash
tmux attach -r -t "=peeragent-project-copilot-b7e2d0f1"
```

`-r` is read-only. The user can watch and scroll without typing
into the harness by accident. Detaching is the usual tmux key,
`Ctrl-b d` in a default configuration.

The harness's own reply arrives wherever your assignment told it
to write. In this example that is
`/srv/project/.reports/agent-out.md`, so the finished run is
visible there and in the project's git status, not in peeragent's
output. peeragent builds no channel back to you; that is why the
task file has to describe one.

Every peeragent call also wrote a log file:

```bash
ls -1t ~/.local/state/peeragent/logs/ | head -5
```

One file per invocation, named by date, time, action and process
id. The log is JSONL even when the run printed plain text, and it
contains the prompt text, the captured pane content and absolute
paths. It is the right thing to attach to a bug report and the
wrong thing to paste into a public channel unread.

## When peeragent is finished, the session is not

peeragent returns as soon as it has reported the first screen. The
harness keeps running in tmux, and peeragent never ends a session
it started. Cleaning up is yours:

```bash
tmux kill-session -t "=peeragent-project-copilot-b7e2d0f1"
```

Do that only once the harness has finished and you have its
reply.

## The shorter path: claude

`claude` receives the prompt as a command-line argument, so the
prompt survives the trust question and usually needs no `send`.
The start command is the same with `--harness claude`.

Its trust dialog, captured on 2026-09-23 with claude 2.1.278 in a
new directory:

```text
Accessing workspace: /srv/project
Quick safety check: Is this a project you created or one you trust?
❯ No, exit
  Yes, I trust this folder
Enter to confirm · Esc to cancel
```

The preselected option is the refusing one. Answering therefore
takes two keys:

```bash
tmux send-keys -t "=peeragent-project-claude-a3f1c9e2:" Down Enter
```

After that, `claude` picks up the argument prompt as its first
turn. Tested on 2026-09-23: no `send` was needed. Because
`delivery` is `argv` rather than `send_keys`, the rule differs
from step 5 above: capture the pane first, and deliver with `send`
only if the input line is empty, meaning the harness did not take
the prompt.

A finished turn in `claude` looks like this, captured on
2026-09-23 with the same three-line test prompt:

```text
 ▐▛███▛█   Claude Code v2.1.278
▝▜██████▀  Haiku 4.5 · Claude Max
❯ Line one of the prompt: please answer with the single word ZEBRA.
  Line two: do not read any files.
  Line three: then stop.
● ZEBRA
✻ Cogitated for 1s · done 17:52
❯
```

The bare `❯` line at the end is `ready`. Note that it is also
present while `claude` streams an answer, which is why peeragent
captures twice before deciding.

## What is evidenced here

- Tested on 2026-09-23: the trust dialog wording of `claude` and
  its `Down Enter` answer; the `1 Enter` answer for `codex` and
  `copilot`; the `copilot` busy marker `○ Working esc interrupt`
  and its bare `❯` ready line; `claude` picking up an argument
  prompt after the trust answer; `codex` doing the same after
  `1 Enter`; a paste arriving during a `copilot` turn being
  buffered rather than lost. The two pane captures reproduced
  above are from that run, with a short test prompt in place of
  this example's.
- Not recorded end to end: this page is not a transcript of one
  session. The JSON blocks are the specified output for these
  calls, assembled from the specification rather than copied from
  a log, and the pane content inside them is illustrative.
- Not confirmed: the ready markers of `agy`, `opencode` and
  `codex`. A healthy first screen from those three may come back
  as `awaiting: unknown`. Show it to the user rather than
  treating it as a failure. `agy` was not tested past its login
  selection and `opencode` not past its provider selection, both
  for want of an account on the test host.

For the flags used above, see [`../docs/cli.md`](../docs/cli.md);
for the message types and fields,
[`../docs/output-format.md`](../docs/output-format.md); for the
rules behind the task file and the pointer prompt,
[`../skills/launch-peer-agent/SKILL.md`](../skills/launch-peer-agent/SKILL.md).
