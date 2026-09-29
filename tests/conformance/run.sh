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

missing=0
for impl in "$py" "$sh"; do
  [ -f "$impl" ] || { printf 'not found: %s\n' "$impl" >&2; missing=1; }
done
[ "$missing" -eq 0 ] || exit 3

sandbox=$(mktemp -d "${TMPDIR:-/tmp}/peeragent-conformance-XXXXXX")
cleanup() { [ -n "${KEEP:-}" ] || rm -rf "$sandbox"; }
trap cleanup EXIT

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

  work="$sandbox/$name"
  home="$work/home"
  mkdir -p "$home"
  [ -d "$dir/home" ] && cp -a "$dir/home/." "$home/"

  # mode: json (default), plain, or help - how the outputs are compared.
  mode=json
  [ -f "$dir/mode" ] && mode=$(tr -d '[:space:]' < "$dir/mode")

  # path: which directories go on PATH. "fakes" (default) puts the fake
  # harnesses first; "bare" leaves them out, which is how a missing
  # harness is produced; "notmux" additionally hides tmux.
  profile=fakes
  [ -f "$dir/path" ] && profile=$(tr -d '[:space:]' < "$dir/path")

  case "$profile" in
    fakes)  path="$fixtures/bin:/usr/bin:/bin" ;;
    bare)   path="/usr/bin:/bin" ;;
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

  [ -f "$dir/setup.sh" ] && SANDBOX="$work" HOME="$home" \
    bash "$dir/setup.sh" >"$work/setup.log" 2>&1

  args=$(sed -e "s|@SANDBOX@|$work|g" -e "s|@HOME@|$home|g" "$dir/args")
  # shellcheck disable=SC2206  # deliberate word splitting of the case args
  argv=($args)

  for impl in py sh; do
    case "$impl" in
      py) cmd=("python3" "$py") ;;
      sh) cmd=("bash" "$sh") ;;
    esac
    env -i HOME="$home" PATH="$path" TMPDIR="$work" \
        LC_ALL=C.UTF-8 TERM=dumb "${extra[@]}" \
        "${cmd[@]}" "${argv[@]}" \
        >"$work/$impl.out" 2>"$work/$impl.err"
    printf '%s' "$?" > "$work/$impl.code"
  done

  out=$(python3 "$here/compare.py" "$mode" \
        "$work/py.out" "$work/sh.out" \
        "$(cat "$work/py.code")" "$(cat "$work/sh.code")" \
        "$work" "$home")
  if [ -z "$out" ]; then
    printf 'ok   %s\n' "$name"
    pass=$((pass + 1))
  else
    printf 'FAIL %s\n%s\n' "$name" "$out"
    fail=$((fail + 1)); failed+=("$name")
  fi
done

printf '\n%s passed, %s failed\n' "$pass" "$fail"
if [ "$fail" -gt 0 ]; then
  printf 'failed: %s\n' "${failed[*]}"
  [ -n "${KEEP:-}" ] && printf 'sandbox kept at %s\n' "$sandbox"
  exit 1
fi
