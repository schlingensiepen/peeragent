#!/usr/bin/env bash
set -eu
mkdir -p "$SANDBOX/w"
cat > "$SANDBOX/w/p.txt" <<'EOF'
Read the task file and do what it says, then stop and report back to the agent that started youxxxxxxxxxxxxxxxxxxxxxxxxx /srv/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/TASK.md /srv/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/REPORT.md
EOF
