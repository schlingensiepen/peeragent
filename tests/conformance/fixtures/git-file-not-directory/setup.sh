#!/usr/bin/env bash
set -eu
mkdir -p "$SANDBOX/w"
# A worktree or submodule has .git as a file, not a directory.
printf %s "gitdir: /elsewhere/.git/modules/x" > "$SANDBOX/w/.git"
