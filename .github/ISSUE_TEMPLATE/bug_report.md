---
name: Bug report
about: Report a failure, a wrong screen classification or a misleading message
labels: bug
---

# Bug report

Before you fill this in: log files contain the text of your launch
prompt, the captured pane content and absolute file paths. Read what
you attach and remove anything that should not become public. The
same applies to pane output you paste below.

## What happened

Describe what you did, in the order you did it.

**Expected behaviour:**

**Observed behaviour:**

## Command

The full command line you ran, with the flags:

```text

```

## Versions

Output of `peeragent version`:

```text

```

Output of `peeragent list harness --json`:

```text

```

## Harness

- Harness key: (`claude`, `codex`, `agy`, `opencode` or `copilot`)
- Harness version, as printed by `<binary> --version`:
- Did the harness work when you started it directly in the same
  directory, without peeragent?

## Environment

- Linux distribution and release, or WSL2 plus the Windows release:
- `tmux -V`:
- Which program you used: `tools/peeragent.py` or `tools/peeragent`

## Logs

Log files are written to `~/.local/state/peeragent/logs/`, one per
invocation, named by date, time, command and process id. Attach the
file belonging to the failing run.

- [ ] I attached the log file of the failing run
- [ ] I checked the log for prompt text, pane content and paths I do
      not want to publish, and removed or replaced them
- [ ] If the run was started with `--no-log`, I repeated it without
      that flag to get a log

## Anything else

Screens, key sequences or wordings you saw, especially when a harness
changed a dialog since its last release.
