# Quick start: one session from beginning to end

This walks through a single use of peeragent: write the
assignment, start a harness, recognise the question it stops on,
answer it with the right key sequence, deliver the prompt that was
left behind, and look at the result.

Read [`../MATURITY.md`](../MATURITY.md) first. The section "What is
evidenced here" at the end of this file says which screens on this
page come from a recorded run and which come from earlier checks.

The example uses `agy`, because it shows the longest path: the
harness stops on a trust question, the prompt is not delivered, and
you deliver it afterwards. The output in steps 3 to 6 is from a run
on 2026-09-29 with the Python program and Antigravity CLI 1.2.13.
It is edited in four ways, and only these: paths are replaced by
neutral ones, the logo and the account line of the start banner are
left out, long runs of padding are shortened, and the byte count is
the one of the neutral prompt file. A shorter variant with `claude`
follows at the end.

Placeholders used throughout: `/srv/project` is the working
directory, `/srv/project/TASK.md` the assignment,
`/srv/project/.peeragent-prompt.txt` the prompt file.

## Step 1: write the task file

The full assignment goes into a file in the working directory, not
into the prompt. The assignment in this example is deliberately
tiny, so that the run costs nothing and touches nothing. A real
assignment follows `task-file-template.md` in this directory, which
covers what the launched harness cannot find out by itself, among
other things how it reaches you.

```bash
cat > /srv/project/TASK.md <<'EOF'
# Assignment: say ZEBRA

Answer with the single word ZEBRA and nothing else.
Do not read or change any other file. Then stop.
EOF
```

## Step 2: write the pointer prompt

The prompt file holds only a pointer to the assignment, with the
scope and the stopping condition. `prompt-file-template.md` in
this directory is the form to copy.

```bash
cat > /srv/project/.peeragent-prompt.txt <<'EOF'
Read /srv/project/TASK.md and do what it says. Then stop.
EOF
```

Why not put the assignment in the prompt directly: the assignment
contains quotes, braces and newlines, and for three of the five
harnesses the prompt travels as a command-line argument, where it
would be visible to every user of the host in the process list.
peeragent also refuses it. A prompt above 120 effective characters
ends in exit code 2 before anything starts; absolute paths are not
counted, so the pointer above spends 36 of the 120.

## Step 3: start the harness

```bash
peeragent start agent \
  --folder /srv/project \
  --harness agy \
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
{"type":"info","msg":"harness agy found: 1.2.13","user_relevant":false}
,
{"type":"agent.starting","harness":"agy","folder":"/srv/project","model":null,"resume":false,"prompt_file":"/srv/project/.peeragent-prompt.txt","user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-project-agy-27f1d588","awaiting":"trust_prompt","lines":["Accessing workspace:","","/srv/project","","Do you trust the contents of this project?","","Antigravity CLI requires permission to read, edit, and execute files here.","","> Yes, I trust this folder","  No, exit","","  ↑/↓ Navigate · enter Confirm","                        Gemini 3.8 Flash · high"],"user_relevant":false}
,
{"type":"warn","msg":"harness agy is awaiting trust-prompt confirmation","user_relevant":true,"hint":"send 'Enter' to trust: tmux send-keys -t '=peeragent-project-agy-27f1d588:' Enter"}
,
{"type":"agent.prompt_deferred","session":"peeragent-project-agy-27f1d588","prompt_file":"/srv/project/.peeragent-prompt.txt","awaiting":"trust_prompt","delivery":"send_keys","hint":"deliver with: peeragent send --session peeragent-project-agy-27f1d588 --prompt-file /srv/project/.peeragent-prompt.txt","user_relevant":true}
,
{"type":"agent.started","session":"peeragent-project-agy-27f1d588","pane_pid":67615,"child_processes":[],"hint":"watch with: tmux attach -r -t '=peeragent-project-agy-27f1d588'","user_relevant":false}
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
  the harness, and `delivery` is `send_keys`: this harness takes its
  prompt by paste, and peeragent pastes only into a screen that is
  ready. Step 5 delivers it.
- `agent.started.session` is the name you need for every
  follow-up command. Keep it, and tell the user, together with
  the read-only attach line from the hint. That is how they can
  look at the harness themselves when a screen does not match
  anything described here.

Without `--json` the same run prints one line per message, with
the pane content indented underneath. Use `--json` when an agent
reads the output; see [`../docs/output-format.md`](../docs/output-format.md).

## Step 4: answer the trust question

peeragent does not answer for you in version 0.2.0. The hint of
the warning contains the whole command. For `agy` the answer is
a bare `Enter`, because its dialog preselects "Yes, I trust this
folder":

```bash
tmux send-keys -t "=peeragent-project-agy-27f1d588:" Enter
```

Note the `:` at the end of the target. Pane commands need it;
without it tmux reads the name as a window name and fails.

Four seconds later the pane looked like this (banner logo and
account line left out):

```text
                  Antigravity CLI 1.2.13
                  Gemini 3.8 Flash (High)
                  /srv/project
─────────────────────────────────────────────
>
─────────────────────────────────────────────
? for shortcuts                Gemini 3.8 Flash · high
```

Per harness, the first start in a new directory and its answer:

| Harness | Stops on | Key sequence |
|---|---|---|
| `claude` | trust question | `Down Enter` |
| `codex` | trust question | `1` |
| `copilot` | trust question | `1` |
| `agy` | trust question, or a login selection with no account | `Enter` |
| `opencode` | provider selection | none; the user has to run `/connect` |

The sequences for `claude`, `codex` and `copilot` were tested on
2026-09-23 and corrected on 2026-09-28; the one for `agy` on
2026-09-29. `claude` needs `Down Enter` because its dialog
preselects "No, exit". For `codex` and `copilot` the digit alone
both selects and confirms, so nothing follows it. For `codex`,
answering also trusts the whole git root, not just the folder you
pointed at, so tell the user before you answer.

A harness update may change any of these dialogs. If the screen
does not match the description, send nothing and attach to the
session instead. The same goes for a screen reported as `unknown`:
a `codex` that opens with an offer to update itself is one, and
the digit that trusts a folder in another harness would start an
installation there.

For `opencode`, and for `agy` on a machine with no account, there
is nothing to send. Inform the user and stop; the login and the
provider setup are interactive and external.

## Step 5: deliver the prompt

Now, and only now, deliver the assignment. The rule is strict:
call `send` only after you have seen `agent.prompt_deferred` for
that session, because otherwise the harness may already have the
prompt and would carry out the assignment twice.

```bash
peeragent send \
  --session peeragent-project-agy-27f1d588 \
  --prompt-file /srv/project/.peeragent-prompt.txt \
  --json
```

```json
[
{"type":"info","msg":"tmux found: 3.5a","user_relevant":false}
,
{"type":"info","msg":"harness agy found: 1.2.13","user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-project-agy-27f1d588","awaiting":"ready","lines":["","","      ▄▀▀▄        Antigravity CLI 1.2.13","","    ▀▀▀▀▀▀▀▀      Gemini 3.8 Flash (High)","   ▄▀▀    ▀▀▄     /srv/project","","────────────────────────────────────────────────────────────",">","────────────────────────────────────────────────────────────","? for shortcuts                        Gemini 3.8 Flash · high"],"user_relevant":false}
,
{"type":"agent.prompt_sent","session":"peeragent-project-agy-27f1d588","bytes":58,"user_relevant":false}
,
{"type":"agent.pane","session":"peeragent-project-agy-27f1d588","awaiting":"ready","lines":["","","      ▄▀▀▄        Antigravity CLI 1.2.13","","    ▀▀▀▀▀▀▀▀      Gemini 3.8 Flash (High)","   ▄▀▀    ▀▀▄     /srv/project","","────────────────────────────────────────────────────────────","> Read /srv/project/TASK.md and do what it says. Then stop.","⡿  Generating...","────────────────────────────────────────────────────────────",">","────────────────────────────────────────────────────────────","esc to cancel                          Gemini 3.8 Flash · high"],"user_relevant":false}
]
```

The first `agent.pane` is the screen before the paste, the second
the screen after it. Read the second one carefully. The prompt is
in the input area and a `Generating...` line shows that the harness
took it and is working, yet `awaiting` is `ready`. peeragent has no
busy marker for `agy`, and the bare `>` input line stays on screen
while it works (`observed`, see MATURITY.md). For this harness the
evidence that the prompt landed is the pane, not the `awaiting`
value. Look at the pane before sending a second time.

## Step 6: look at the result

While the harness works, capture the pane as often as you like.
This is read-only and does not disturb it:

```bash
tmux capture-pane -t "=peeragent-project-agy-27f1d588:" -p
```

Eight seconds after the paste it showed:

```text
> Read /srv/project/TASK.md and do what it says. Then stop.
● Read(/srv/project/TASK.md) (ctrl+o to expand)
  ZEBRA
─────────────────────────────────────────────
>
─────────────────────────────────────────────
? for shortcuts                Gemini 3.8 Flash · high
```

The `● Read(...)` line is the harness reading the task file that the
pointer prompt named, and `ZEBRA` is what the task file asked for.

To let the user watch, pass on the attach line from
`agent.started`:

```bash
tmux attach -r -t "=peeragent-project-agy-27f1d588"
```

`-r` is read-only. The user can watch and scroll without typing
into the harness by accident. Detaching is the usual tmux key,
`Ctrl-b d` in a default configuration.

In a real assignment the harness's reply arrives wherever the task
file told it to write, and it is visible there and in the project's
git status, not in peeragent's output. peeragent builds no channel
back to you; that is why the task file has to describe one.

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
it started. Cleaning up is yours, one session at a time, by its
exact name:

```bash
tmux kill-session -t "=peeragent-project-agy-27f1d588"
```

Do that only once the harness has finished and you have its
reply. Do not use `tmux kill-server`: the sessions run on your own
tmux server, together with everything else you have there.

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

- Recorded run, 2026-09-29, Antigravity CLI 1.2.13 and tmux 3.5a,
  Python program: the output of steps 3 and 5 and the pane text of
  steps 4 and 6, with the edits named at the top. The Bash program
  was taken through the same path in a second directory; it gave the
  same `awaiting` value at every step, including `ready` in the
  pane that was still generating (`observed`, not recorded line by
  line).
- Tested on 2026-09-23: the trust dialog wording of `claude` and
  its `Down Enter` answer; the trust answer for `codex` and
  `copilot`; the two `claude` pane captures in the variant below;
  `claude` picking up an argument prompt after the trust answer;
  `codex` doing the same.
- Tested on 2026-09-28, correcting the above: `codex` and
  `copilot` confirm their dialogs on the digit alone, so the trust
  answer for both is `1` and not `1` followed by `Enter`. An
  `Enter` sent after it lands in the session that is by then
  already running.
- Not run through peeragent: the `claude` variant below. Its screens
  and its `Down Enter` answer come from checks on the harness
  itself; the start command for it is the same as above with a
  different `--harness`.
- Not confirmed: the ready markers of `codex` and `opencode`. A
  healthy first screen from those two may come back as
  `awaiting: unknown`. Show it to the user rather than treating it
  as a failure. `opencode` was not run past its provider selection
  for want of a provider on the test host.

For the flags used above, see [`../docs/cli.md`](../docs/cli.md);
for the message types and fields,
[`../docs/output-format.md`](../docs/output-format.md); for the
rules behind the task file and the pointer prompt,
[`../skills/launch-peer-agent/SKILL.md`](../skills/launch-peer-agent/SKILL.md).
