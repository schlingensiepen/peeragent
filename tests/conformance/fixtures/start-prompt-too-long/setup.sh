#!/usr/bin/env bash
set -eu
mkdir -p "$SANDBOX/w"
printf '%s\n' "Read the task file and carry out everything described in it, then write a report about what you did and stop there without starting anything else at all." > "$SANDBOX/w/p.txt"
