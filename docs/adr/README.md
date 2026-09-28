# Architecture Decision Records

The decisions that shaped peeragent, one file each. Every record
states the context it was taken in, the decision itself, and the
consequences that follow from it. A record is not updated when the
design moves on; a later record supersedes it.

The architecture these decisions produced is described in
[../architecture.md](../architecture.md). What is implemented and
what is tested is recorded in [../../MATURITY.md](../../MATURITY.md).

| Number | Title | Status |
|---|---|---|
| [0001](0001-stdlib-only.md) | Standard library and system tools only | Accepted |
| [0002](0002-tmux-as-runtime.md) | tmux as the runtime | Accepted |
| [0003](0003-python-and-bash.md) | Two implementations, Python and Bash | Accepted |
| [0004](0004-json-pseudo-array.md) | JSONL in a pseudo-array frame | Accepted |
| [0005](0005-no-log-rotation.md) | No log rotation, no bundling | Accepted |
| [0006](0006-static-model-catalogs.md) | Static model catalogs | Accepted |
| [0007](0007-duplicate-scope-per-harness.md) | Duplicate scope per harness | Accepted |
| [0008](0008-launched-vs-peer-agent-terminology.md) | Launched harness versus peer agent | Accepted |
| [0009](0009-pointer-prompt.md) | Pointer prompt and task file | Superseded by 0016 |
| [0010](0010-generic-prompt-wrapper.md) | One generic prompt wrapper | Accepted |
| [0011](0011-race-free-tmux-start.md) | Race-free tmux start | Accepted |
| [0012](0012-send-subcommand.md) | A send subcommand instead of answering trust prompts | Accepted |
| [0013](0013-agent-exited-and-exit-code-4.md) | agent.exited and exit code 4 | Accepted |
| [0014](0014-trust-answers-and-marker-precedence.md) | Trust answers are key sequences, busy before ready | Accepted |
| [0015](0015-local-git-only.md) | Git setup limited to a local repository | Accepted |
| [0016](0016-enforce-pointer-prompt.md) | The tool enforces the pointer prompt | Accepted |
