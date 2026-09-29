#!/usr/bin/env python3
"""Compare two runs of peeragent after normalising what cannot match.

The two implementations are call-compatible, not byte-identical. What
has to agree is the sequence of message types, the set of field names
and the meaning of the values; what cannot agree is a timestamp, a
process id, a random session suffix or a free-text sentence. So each
value of that kind is replaced by a fixed placeholder before the
comparison, while the presence of the key stays part of it: a field
that one side omits is still a difference.

Read from two JSON-lines files plus the two exit codes, write a verdict
to stdout and exit non-zero on any difference.
"""

import json
import re
import sys

# Values replaced wholesale. The key must still be present on both
# sides; only what is inside it is ignored.
OPAQUE = {
    "timestamp",
    "pid",
    "pane_pid",
    "child_processes",
    "bytes",
    "files",
    "lines",
    "impl",
    "impl_version",
    "msg",
    "hint",
}

# Message types exempt from the equivalence claim altogether.
EXEMPT_TYPES = {"env"}

SESSION = re.compile(r"^(peeragent-.*-)[0-9a-f]{8}$")

NON_ALNUM = re.compile(r"[^a-zA-Z0-9]")


def sanitized(path):
    """The form a harness uses when it names a store after a directory."""
    return NON_ALNUM.sub("-", path)


def normalise(value, key=None, sandbox=None, home=None):
    if key in OPAQUE:
        return f"<{key}>"
    if isinstance(value, dict):
        return {k: normalise(v, k, sandbox, home) for k, v in value.items()}
    if isinstance(value, list):
        return [normalise(v, key, sandbox, home) for v in value]
    if isinstance(value, str):
        # The harness version strings vary with what is installed; the
        # peeragent version in the version message does not and is
        # compared. That is why this runs on the key, not the value.
        if key == "version":
            return "<version>"
        if key == "session":
            m = SESSION.match(value)
            if m:
                return m.group(1) + "<hex>"
        if key == "argv":
            return value
        out = value
        # Longest first: home sits inside sandbox, so replacing the
        # shorter one first would leave a mangled remainder. Each path
        # is also replaced in the form a harness stores it under, with
        # every non-alphanumeric character turned into a dash - that is
        # how a session store is named after its working directory.
        for raw, label in ((home, "<HOME>"), (sandbox, "<SANDBOX>")):
            if not raw:
                continue
            out = out.replace(raw, label)
            out = out.replace(sanitized(raw), label)
        return out
    return value


def normalise_message(obj, sandbox, home):
    out = {}
    for k, v in obj.items():
        if k == "argv" and isinstance(v, list) and v:
            # argv[0] is the path the implementation was called by and
            # differs by definition; the rest is the caller's input.
            rest = [normalise(x, "argv", sandbox, home) for x in v[1:]]
            out[k] = ["peeragent"] + rest
            continue
        out[k] = normalise(v, k, sandbox, home)
    return out


def load(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    if not text.strip():
        return [], text
    # The output is a pseudo-array: an opening bracket, one object per
    # line, comma lines between them, a closing bracket. Parsing it as
    # one document is the strictest check that the frame is intact.
    try:
        return json.loads(text), text
    except json.JSONDecodeError as exc:
        raise SystemExit(f"not parsable as JSON: {path}: {exc}")


def compare_json(a_path, b_path, boxes):
    """boxes: ((sandbox_a, home_a), (sandbox_b, home_b)).

    Each side runs in its own sandbox, so each is normalised with its
    own paths before the two are held against each other.
    """
    (sa, ha), (sb, hb) = boxes
    a, _ = load(a_path)
    b, _ = load(b_path)
    problems = []
    if len(a) != len(b):
        problems.append(f"message count: python {len(a)}, bash {len(b)}")
    for i, (x, y) in enumerate(zip(a, b)):
        tx, ty = x.get("type"), y.get("type")
        if tx != ty:
            problems.append(f"message {i}: type {tx!r} vs {ty!r}")
            continue
        if tx in EXEMPT_TYPES:
            continue
        nx = normalise_message(x, sa, ha)
        ny = normalise_message(y, sb, hb)
        if nx != ny:
            keys = set(nx) ^ set(ny)
            if keys:
                problems.append(
                    f"message {i} ({tx}): fields only on one side: "
                    f"{sorted(keys)}"
                )
            for k in sorted(set(nx) & set(ny)):
                if nx[k] != ny[k]:
                    problems.append(
                        f"message {i} ({tx}): {k} = {nx[k]!r} vs {ny[k]!r}"
                    )
    return problems


def compare_plain(a_path, b_path):
    """Plain text is compared by shape, not wording."""
    a = [l for l in open(a_path, encoding="utf-8", errors="replace")]
    b = [l for l in open(b_path, encoding="utf-8", errors="replace")]
    problems = []
    if len(a) != len(b):
        problems.append(f"line count: python {len(a)}, bash {len(b)}")
    for i, (x, y) in enumerate(zip(a, b)):
        fx = x.split()[0] if x.split() else ""
        fy = y.split()[0] if y.split() else ""
        if fx != fy:
            problems.append(f"line {i}: first word {fx!r} vs {fy!r}")
    return problems


def main():
    if len(sys.argv) < 6:
        raise SystemExit(
            "usage: compare.py <mode> <a> <b> <exit_a> <exit_b> "
            "[sandbox_a home_a sandbox_b home_b]"
        )
    mode, a_path, b_path, code_a, code_b = sys.argv[1:6]
    rest = sys.argv[6:]
    if len(rest) == 4:
        boxes = ((rest[0], rest[1]), (rest[2], rest[3]))
    elif len(rest) == 2:
        boxes = ((rest[0], rest[1]), (rest[0], rest[1]))
    else:
        boxes = ((None, None), (None, None))

    problems = []
    if code_a != code_b:
        problems.append(f"exit code: python {code_a}, bash {code_b}")

    if mode == "json":
        problems += compare_json(a_path, b_path, boxes)
    elif mode == "plain":
        problems += compare_plain(a_path, b_path)
    elif mode == "help":
        # The usage text is deliberately not specified, so only its
        # shape is checked: non-empty, and not a JSON array.
        for label, path in (("python", a_path), ("bash", b_path)):
            text = open(path, encoding="utf-8", errors="replace").read()
            if not text.strip():
                problems.append(f"{label}: help output is empty")
            elif text.lstrip().startswith("["):
                problems.append(f"{label}: help output starts an array")
    else:
        raise SystemExit(f"unknown mode: {mode}")

    for p in problems:
        print(f"  {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
