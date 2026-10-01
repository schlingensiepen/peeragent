#!/usr/bin/env bash
# Run both implementations over the same cases and compare them.
#
# Neither implementation is the reference. There are no stored expected
# outputs: a case passes when the two agree after normalisation, which
# means the test measures the specification rather than one program's
# habits. A case both get wrong in the same way is invisible here and
# has to be caught by reading.
#
#   ./run.sh              run every case
#   ./run.sh <name> ...   run only these cases
#   KEEP=1 ./run.sh       keep the sandbox for inspection
set -uo pipefail

here=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(cd -- "$here/../.." && pwd)
py="$root/tools/peeragent.py"
sh="$root/tools/peeragent"
fixtures="$here/fixtures"
# The host's own PATH is the base, so tmux and the standard tools are
# found wherever this machine keeps them. Hard-coding /usr/bin:/bin made
# the suite pass on a machine where tmux lives elsewhere, because both
# programs then failed the same way.
base_path_global="${PATH:-/usr/bin:/bin}"

missing=0
for impl in "$py" "$sh"; do
  [ -f "$impl" ] || { printf 'not found: %s\n' "$impl" >&2; missing=1; }
done
[ "$missing" -eq 0 ] || exit 3

sandbox=$(mktemp -d "${TMPDIR:-/tmp}/peeragent-conformance-XXXXXX")
cleanup() { [ -n "${KEEP:-}" ] || rm -rf "$sandbox"; }
trap cleanup EXIT

# --- Preflight -------------------------------------------------------
#
# Every case compares the two programs with each other, so an
# environment that breaks both of them the same way reads as agreement.
# That is the one way this suite can lie, and these checks are what
# stops it: they fail loudly instead of passing quietly.

case "$sandbox" in
  *[[:space:]]*)
    printf 'the sandbox path contains a space: %s\n' "$sandbox" >&2
    printf 'set TMPDIR to a path without spaces and run again\n' >&2
    exit 3 ;;
esac

# A tmux socket path is limited by the length of a unix domain socket
# address, about 100 characters. Past that, every case that starts a
# harness fails in both programs alike.
if [ ${#sandbox} -gt 80 ]; then
  printf 'the sandbox path is %s characters, which leaves no room for a\n' \
    "${#sandbox}" >&2
  printf 'tmux socket beneath it: set TMPDIR to something shorter\n' >&2
  exit 3
fi

if ! command -v tmux >/dev/null 2>&1; then
  printf 'tmux is not on PATH; the cases that start a harness need it\n' >&2
  exit 3
fi

# Same reasoning as for tmux, one size smaller: without git the two cases
# about --git-repo make both programs answer fatal (3) for the same wrong
# reason, and the suite counts them as agreement.
if ! command -v git >/dev/null 2>&1; then
  printf 'git is not on PATH; the cases for --git-repo need it, and\n' >&2
  printf 'without it they agree for the wrong reason\n' >&2
  exit 3
fi

# The canary: if this does not work, nothing below means anything.
for impl in "$py" "$sh"; do
  case "$impl" in
    *.py) out=$(python3 "$impl" version --json 2>/dev/null) ;;
    *)    out=$(bash "$impl" version --json 2>/dev/null) ;;
  esac
  case "$out" in
    \[*'"type":"version"'*\]*) : ;;
    *) printf 'canary failed: %s did not answer "version --json"\n' "$impl" >&2
       printf 'got: %s\n' "${out:-<nothing>}" >&2
       exit 3 ;;
  esac
done

# --- The "bare" PATH ------------------------------------------------
#
# The cases that produce a missing harness need a PATH that has the
# standard tools and none of the five harnesses. Leaving the host PATH
# in place is not enough: a host that has claude installed then gets a
# real claude started by a case called start-harness-missing, and both
# programs agree about it, so the suite stays green while three cases
# measure the opposite of their names. That happened.
#
# So every directory holding one of the harnesses is dropped, and the
# result is checked below instead of trusted.
bare_path=""
for d in $(printf '%s\n' "$base_path_global" | tr ':' '\n'); do
  [ -n "$d" ] || continue
  keep=1
  for h in claude codex agy opencode copilot; do
    [ -x "$d/$h" ] && keep=0
  done
  [ "$keep" -eq 1 ] && bare_path="${bare_path:+$bare_path:}$d"
done

# The check that makes the profile honest: with this PATH both programs
# have to report all five harnesses as missing. If they do not, the
# cases that rely on it are meaningless and the suite says so instead of
# passing.
for impl in "$py" "$sh"; do
  case "$impl" in
    *.py) out=$(env -i PATH="$bare_path" HOME="$sandbox" LC_ALL=C.UTF-8 \
                python3 "$impl" list harness --json 2>&1) ;;
    *)    out=$(env -i PATH="$bare_path" HOME="$sandbox" LC_ALL=C.UTF-8 \
                bash "$impl" list harness --json 2>&1) ;;
  esac
  found=$(printf '%s' "$out" | grep -c '"type":"harness.detected"' || true)
  missing=$(printf '%s' "$out" | grep -c '"type":"harness.missing"' || true)
  if [ "$found" -ne 0 ] || [ "$missing" -ne 5 ]; then
    printf 'the bare PATH still finds a harness, or the run failed:\n' >&2
    printf '  %s: %s detected, %s missing (5 missing expected)\n' \
      "$impl" "$found" "$missing" >&2
    printf '  PATH was: %s\n' "$bare_path" >&2
    printf 'the cases list-harness-none, list-models-not-installed and\n' >&2
    printf 'start-harness-missing cannot work like this\n' >&2
    exit 3
  fi
done

# The number of cases, in one place. A case added or removed without
# this number and the documents that quote it drifting apart is what
# put three different figures into five documents.
expected_cases=61
actual_cases=$(find "$fixtures" -mindepth 1 -maxdepth 1 -type d ! -name bin | wc -l)
if [ "$actual_cases" -ne "$expected_cases" ] && [ $# -eq 0 ]; then
  printf 'fixtures/ holds %s cases, this script expects %s\n' \
    "$actual_cases" "$expected_cases" >&2
  printf 'update expected_cases here, and the count in\n' >&2
  printf 'tests/conformance/README.md and MATURITY.md with it\n' >&2
  exit 3
fi

pass=0; fail=0; failed=()

cases=("$@")
if [ ${#cases[@]} -eq 0 ]; then
  while IFS= read -r d; do cases+=("$(basename "$d")"); done < <(
    find "$fixtures" -mindepth 1 -maxdepth 1 -type d ! -name bin | sort
  )
fi

for name in "${cases[@]}"; do
  dir="$fixtures/$name"
  if [ ! -d "$dir" ]; then
    printf 'FAIL %s\n  no such fixture\n' "$name"
    fail=$((fail + 1)); failed+=("$name"); continue
  fi

  # Each implementation gets its own sandbox. They must: a case that
  # writes - duplicate creates a session store - would otherwise let
  # whichever ran first decide what the second one finds.
  work="$sandbox/$name"
  mkdir -p "$work"

  # mode: json (default), plain, or help - how the outputs are compared.
  mode=json
  [ -f "$dir/mode" ] && mode=$(tr -d '[:space:]' < "$dir/mode")

  # path: which directories go on PATH. "fakes" (default) puts the fake
  # harnesses first; "bare" leaves them out, which is how a missing
  # harness is produced; "notmux" additionally hides tmux.
  profile=fakes
  [ -f "$dir/path" ] && profile=$(tr -d '[:space:]' < "$dir/path")

  base_path="$base_path_global"
  case "$profile" in
    fakes)  path="$fixtures/bin:$base_path" ;;
    bare)   path="$bare_path" ;;
    notmux) path="$fixtures/bin:$work/nothing" ;;
    *)      printf 'FAIL %s\n  unknown path profile: %s\n' "$name" "$profile"
            fail=$((fail + 1)); failed+=("$name"); continue ;;
  esac

  # env: extra variables, one KEY=VALUE per line. PEERAGENT_FAKE picks
  # the behaviour of the fake harnesses.
  extra=()
  if [ -f "$dir/env" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] && extra+=("$line")
    done < "$dir/env"
  fi

  for impl in py sh; do
    box="$work/$impl"
    home="$box/home"
    mkdir -p "$home"
    [ -d "$dir/home" ] && cp -a "$dir/home/." "$home/"
    [ -f "$dir/setup.sh" ] && SANDBOX="$box" HOME="$home" \
      bash "$dir/setup.sh" >"$box/setup.log" 2>&1

    # Two ways to give the arguments. "args" is one line, split on
    # whitespace, which is short to read and enough for most cases.
    # "argv" is one argument per line and is not split: it is the only
    # way to pass an argument that is empty or contains a space, and an
    # empty line is an empty argument. A case that needs one and uses
    # "args" instead tests something other than what its name says.
    argv=()
    if [ -f "$dir/argv" ]; then
      while IFS= read -r line; do
        argv+=("$line")
      done < <(sed -e "s|@SANDBOX@|$box|g" -e "s|@HOME@|$home|g" "$dir/argv")
    else
      args=$(sed -e "s|@SANDBOX@|$box|g" -e "s|@HOME@|$home|g" "$dir/args")
      set -f  # no globbing while the case arguments are split
      # shellcheck disable=SC2206  # deliberate word splitting of the case args
      argv=($args)
      set +f
    fi

    case "$impl" in
      py) cmd=("python3" "$py") ;;
      sh) cmd=("bash" "$sh") ;;
    esac
    # A tmux server of this case's own. Without it a case that starts a
    # harness would land on whatever server the person running the suite
    # happens to have, and leave sessions behind in it. TMUX is not
    # inherited here because the environment is built from nothing.
    mkdir -p "$box/tmux"
    env -i HOME="$home" PATH="$path" TMPDIR="$box" \
        TMUX_TMPDIR="$box/tmux" \
        LC_ALL=C.UTF-8 TERM=dumb "${extra[@]}" \
        "${cmd[@]}" "${argv[@]}" \
        >"$work/$impl.out" 2>"$work/$impl.err"
    printf '%s' "$?" > "$work/$impl.code"
  done

  # Whatever a case started is taken down by name, one session at a
  # time. Killing a whole server is never done here, not even on a
  # socket this script created: the habit is what causes the damage,
  # and a socket directory under the sandbox is removed with it anyway.
  for impl in py sh; do
    sock="$work/$impl/tmux"
    [ -d "$sock" ] || continue
    while IFS= read -r sess; do
      [ -n "$sess" ] || continue
      TMUX= TMUX_TMPDIR="$sock" tmux kill-session -t "=$sess" \
        >/dev/null 2>&1 || true
    done < <(TMUX= TMUX_TMPDIR="$sock" tmux list-sessions \
             -F '#{session_name}' 2>/dev/null)
  done

  # Both streams, and the exit status: a comparison that dies with a
  # message on stderr must not read as agreement.
  out=$(python3 "$here/compare.py" "$mode" \
        "$work/py.out" "$work/sh.out" \
        "$(cat "$work/py.code")" "$(cat "$work/sh.code")" \
        "$work/py" "$work/py/home" "$work/sh" "$work/sh/home" 2>&1)
  verdict=$?
  if [ "$verdict" -eq 0 ] && [ -z "$out" ]; then
    printf 'ok   %s\n' "$name"
    pass=$((pass + 1))
  else
    printf 'FAIL %s\n%s\n' "$name" "$out"
    fail=$((fail + 1)); failed+=("$name")
  fi
done

if [ "$pass" -eq 0 ] && [ "$fail" -eq 0 ]; then
  printf 'no cases ran; fixtures/ is empty or the names given do not exist\n' >&2
  exit 3
fi

printf '\n%s passed, %s failed\n' "$pass" "$fail"
if [ "$fail" -gt 0 ]; then
  printf 'failed: %s\n' "${failed[*]}"
  [ -n "${KEEP:-}" ] && printf 'sandbox kept at %s\n' "$sandbox"
  exit 1
fi
