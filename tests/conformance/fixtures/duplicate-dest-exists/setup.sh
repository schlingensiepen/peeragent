#!/usr/bin/env bash
# Claude Code keeps its history per working directory, under a name
# derived from the path, so the store can only be created once the
# sandbox path is known.
set -eu
mkdir -p "$SANDBOX/a"
sanitized=$(printf '%s' "$SANDBOX/a" | sed 's|[^a-zA-Z0-9]|-|g')
mkdir -p "$HOME/.claude/projects/$sanitized"
printf '%s\n' '{"type":"user","cwd":"'"$SANDBOX/a"'"}' \
  > "$HOME/.claude/projects/$sanitized/session.jsonl"
mkdir -p "$SANDBOX/b"
printf x > "$SANDBOX/b/other"
