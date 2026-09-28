# Template: the prompt file

The prompt file is what `peeragent start agent --prompt-file`
reads. For any substantial assignment it holds a **pointer** to a
task file in the working directory, not the assignment itself.
Copy the block below, replace the paths and the two sentences, and
save it as a plain text file.

[`../MATURITY.md`](../MATURITY.md) says which of the calls shown
here are tested today.

## The template

```text
Read /ABSOLUTE/PATH/TO/TASK.md and do what it says.
<SCOPE: which part.> <STOP: when to stop, and where to report.>
```

## Filled in

```text
Read /srv/project/TASK.md and do what it says. Step 1 only,
then stop and append your report to /srv/project/.reports/agent-out.md.
```

That is 74 effective characters, well inside the limit described
below.

Save it next to the task file and pass it by absolute path:

```bash
peeragent start agent \
  --folder /srv/project \
  --harness claude \
  --prompt-file /srv/project/.peeragent-prompt.txt
```

## What the parts do

- **The path.** Absolute, not relative. The launched harness
  starts in the working directory, but an absolute path removes
  the question entirely and reads correctly in the tmux and log
  history.
- **The scope.** Without it, a harness may take on the whole task
  file when you wanted one step, or one step when you wanted the
  whole file. Name which part is in scope this time.
- **The stop condition.** Say when to stop and where to put the
  result. A harness that has finished and does not know it should
  stop keeps going.

## Rules

- **Keep it short, and it is not a matter of taste.** peeragent
  refuses a prompt above 120 effective characters with exit code 2.
  Absolute paths do not count towards that, so the two paths above
  are free; only the words between them are. The counting rule is in
  [`../docs/cli.md`](../docs/cli.md). If your text does not fit, it
  is not a pointer any more and belongs in the task file.
- No confidential content. Two of the five harnesses receive the
  prompt as a command-line argument, where it is visible to other
  users of the host in the process list. The task file is not.
- Plain text, UTF-8, and not empty. peeragent rejects an empty or
  unreadable file before starting anything, and it rejects one whose
  content does not decode as UTF-8, because the length count needs
  the decoded text.
- A trailing newline is harmless. peeragent strips trailing
  newlines before pasting into a harness that takes the prompt by
  keystrokes, so the paste does not submit early.
- No templating. peeragent does not substitute anything in this
  file; it reads it to count the length and passes the content
  through unchanged.

## When the prompt file may hold the whole thing

A one-line instruction with nothing to quote can stay in the
prompt file directly. The pointer convention exists for
assignments long enough that shell quoting, log readability or
repeatability become a problem.

## Next

The task file this points at has its own template:
[`task-file-template.md`](task-file-template.md). A full session
using both is in [`quick-start.md`](quick-start.md). The flags used
above are documented in [`../docs/cli.md`](../docs/cli.md).
