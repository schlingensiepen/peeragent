# Template: the task file

The task file holds the full assignment. It lives in the working
directory you hand to `peeragent start agent`, and the prompt file
only points at it. Copy the block below into the working directory
as `TASK.md`, or under a name that says what it is, and fill in
the sections.

[`../MATURITY.md`](../MATURITY.md) says which of the calls around
this file are tested today.

The launched harness knows nothing about your project, your
session or you. Everything it needs has to be in this file,
because peeragent builds no channel back to you and nothing else
will tell it.

## The template

```markdown
# Assignment: <one line saying what is to be achieved>

## How to reach me
<Protocol, address and credentials of the back channel.>
<Whether to append or overwrite, and how often I read it.>
<For the folder variant: the absolute directory, the file name you
write, the file name I write, and the format of both.>

## Report back after setup
When you have finished the setup steps below, <send exactly this
signal over the channel above> before starting on the work.

## Setup for this project
- <command or step>
- <command or step>
- <the project's instruction files to read>
- <the test command, and what to do if it is not green>

## The work
<What to change or produce, precisely enough to be checkable.>

## Scope and stop
<What is in scope this time and what is explicitly not.>
<When to stop and what to report.>
```

## The obligations behind it

These are not style. Each one exists because a launched harness
went wrong without it.

### 1. Describe the communication mechanism and the access to it

Name the protocol, the address and the credentials of the back
channel. Do not rely on the launched harness discovering them: it
cannot see your session, and a harness that has no way to answer
will not answer at all.

peeragent is orthogonal to the mechanism and provides none of them.
Two are worth recommending.

A **folder both sides agree on** is the simplest that works. Name an
absolute directory, say who writes which file and in what format,
and ask for a first file after the setup step. It needs no software,
it leaves a readable trail, it survives a crash on either side, and
on a shared filesystem it spans users and hosts. The weakness is
that nobody is notified: both sides poll.

**[simple-a2a](https://github.com/schlingensiepen/simple-a2a)** is a
small agent-to-agent protocol for when file dropping is not enough
and you want addressed messages between agents.

A socket, a message queue or an issue tracker work too. Whatever you
pick, it belongs in this file with its address and its credentials,
not in the launch prompt, which holds only a pointer.

### 2. Ask for a report after initialization

Include an explicit sentence: after the first setup step, report
back over the channel described above. Without it you cannot tell
a harness that is working from a harness that is stuck on a
question you never saw, and both look identical from outside.

Make the signal specific enough to recognize, for example one line
containing a word you chose.

### 3. Include the project's usual initialization steps

Before you write the file, find out what a fresh session in that
project normally does: activate an environment, install
dependencies, read the project's instruction files, run the tests.
Then write those steps down here.

Say what to do when a setup step fails, in particular when the
test suite is not green before the change. Otherwise a harness may
spend its run repairing something unrelated.

### 4. State where you are

Once the channel is up, say which host you run on, under which
user and in which directory. File exchange in either direction
needs all three, and a harness that has to ask for them has
already lost a round trip.

## Practical notes

- **Absolute paths.** The launched harness starts in the working
  directory, but absolute paths cost nothing and remove the
  question.
- **One stopping condition.** More than one invites a harness to
  pick the loosest.
- **Version it.** The task file sits in the working directory, so
  it goes into the project's history with everything else. Change
  it and start again rather than describing amendments by hand.
- **Quoting is a non-issue here.** Quotes, braces, backticks and
  newlines are safe in this file precisely because it is a file.
  That is the point of keeping the prompt short.
- **Confidential content belongs here, not in the prompt file.**
  Three of the five harnesses receive the prompt as a command-line
  argument, readable by other users of the host in the process
  list. This file is read by the harness itself.

## Next

The short prompt that points at this file has its own template:
[`prompt-file-template.md`](prompt-file-template.md). A full
session using both is in [`quick-start.md`](quick-start.md). The
obligations above and what to do with the first screen are in
[`../skills/launch-peer-agent/SKILL.md`](../skills/launch-peer-agent/SKILL.md).
