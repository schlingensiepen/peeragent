#!/usr/bin/env bash
set -eu
mkdir -p "$SANDBOX/w"
printf %s "Read /srv/x/TASK.md and stop." > "$SANDBOX/w/p.txt"
