#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jörn Schlingensiepen
# This code was written by AI (Claude Code) and reviewed by a human.
"""peeragent - start a coding-agent harness in a tmux session, report the
first screen as JSONL, deliver a queued prompt later, duplicate a working
directory together with its harness session history, and list installed
harnesses and their models.

Single-file implementation, standard library only. Internal layout, in
order: header, emitter/log, helpers, model catalogs, handler contract and
handlers, tmux runtime, git setup, preflight, commands, CLI/main.
"""

import atexit
import glob
import json
import os
import platform
import re
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

PEERAGENT_VERSION = "0.1.0"
IMPL_NAME = "python"

HARNESS_ORDER = ["claude", "codex", "agy", "opencode", "copilot"]

TMUX_DETECT_TIMEOUT = 10
GIT_INIT_TIMEOUT = 30

SESSION_NAME_RE = re.compile(
    r"^peeragent-(.+)-(claude|codex|agy|opencode|copilot)-([0-9a-f]{8})$"
)

EFFECTIVE_LENGTH_LIMIT = 120
# Exactly these four codepoints count as whitespace for the prompt length
# rule: space, tab, CR, LF. Python's str.strip() and a naive split() treat
# more characters as whitespace than this, and would disagree with a shell
# implementation at the boundary of the limit.
WHITESPACE_CODEPOINTS = chr(0x20) + chr(0x09) + chr(0x0D) + chr(0x0A)
WHITESPACE_SPLIT_RE = re.compile("[" + WHITESPACE_CODEPOINTS + "]+")

REDACT_EXACT_VARS = {"PATH", "SHELL", "TERM", "LANG", "LC_ALL", "TMUX", "HOME"}
REDACT_PREFIXES = (
    "PEERAGENT_", "CLAUDE_", "CODEX_", "GEMINI_", "OPENCODE_",
    "COPILOT_", "ANTHROPIC_", "OPENAI_", "GH_", "GITHUB_",
)
REDACT_NAME_RE = re.compile(r"(TOKEN|KEY|SECRET|PASS|AUTH|CREDENTIAL)", re.I)


# ---------------------------------------------------------------------------
# Emitter and log
# ---------------------------------------------------------------------------

class Emitter:
    """Owns every byte written to stdout and to the log file.

    Messages are buffered for the log until the log path is known (it
    depends on the parsed subcommand); stdout is written as soon as a
    message is accepted, subject to the json/plain mode and the verbose
    filter. Both streams share one JSON pseudo-array framing so that a
    truncated run (any signal but SIGKILL) still closes cleanly.
    """

    def __init__(self, json_mode: bool, verbose: bool = False, no_color: bool = False):
        self.json_mode = json_mode
        self.verbose = verbose
        self.color = (
            not no_color
            and os.environ.get("NO_COLOR", "") == ""
            and sys.stdout.isatty()
        )
        self._stdout_first = True
        self._log_first = True
        self._log_file = None
        self._default_log_path = True
        self._log_buffer = []
        self._closed = False
        self.exit_code = 0
        if self.json_mode:
            print("[")
            sys.stdout.flush()

    # -- serialization --------------------------------------------------

    @staticmethod
    def _clean(obj):
        if isinstance(obj, str):
            return obj.replace("\x00", "")
        if isinstance(obj, dict):
            return {k: Emitter._clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [Emitter._clean(v) for v in obj]
        return obj

    @staticmethod
    def _to_json_line(obj) -> str:
        return json.dumps(Emitter._clean(obj), separators=(",", ":"), ensure_ascii=False)

    # -- plain-text rendering --------------------------------------------

    def _color_wrap(self, text: str, kind: str) -> str:
        if not self.color:
            return text
        if kind == "warn":
            return f"\x1b[33m{text}\x1b[0m"
        if kind in ("error", "fatal"):
            return f"\x1b[31m{text}\x1b[0m"
        return text

    def _render_plain(self, obj) -> list[str]:
        t = obj["type"]
        lines: list[str] = []
        if t == "info":
            head = obj["msg"]
            if "files" in obj and "bytes" in obj:
                head += f" ({obj['files']} files, {obj['bytes']} bytes)"
            lines.append(head)
            if obj.get("hint"):
                lines.append("  hint: " + obj["hint"])
        elif t == "warn":
            lines.append(self._color_wrap("warning: " + obj["msg"], "warn"))
            if obj.get("hint"):
                lines.append("  hint: " + obj["hint"])
        elif t in ("error", "fatal"):
            lines.append(self._color_wrap(f"{t}: {obj['msg']}", t))
            lines.append("  hint: " + obj.get("hint", ""))
        elif t == "debug":
            lines.append("debug: " + obj["msg"])
        elif t == "timing":
            lines.append(f"timing: {obj['step']} {obj['ms']}ms")
        elif t == "harness.detected":
            version = obj["version"] if obj["version"] is not None else "version unknown"
            lines.append(f"{obj['key']}  {version}  {obj['path']}  ({obj['description']})")
        elif t == "harness.missing":
            lines.append(f"{obj['key']}  not installed  ({obj['description']})")
        elif t == "model.available":
            lines.append(
                f"{obj['harness']}/{obj['key']}  {obj['description']}  "
                f"[catalog {obj['catalog_updated']}]"
            )
        elif t == "agent.starting":
            head = f"starting {obj['harness']} in {obj['folder']}"
            if obj.get("resume"):
                head += " (resume)"
            if obj.get("model") is not None:
                head += f" model {obj['model']}"
            if obj.get("prompt_file") is not None:
                head += f" prompt {obj['prompt_file']}"
            lines.append(head)
        elif t == "agent.pane":
            lines.append(f"session {obj['session']} awaiting {obj['awaiting']}")
            for line in obj.get("lines", []):
                lines.append("  " + line)
        elif t == "agent.prompt_sent":
            lines.append(f"prompt sent to {obj['session']} ({obj['bytes']} bytes)")
        elif t == "agent.prompt_deferred":
            lines.append(f"prompt not delivered to {obj['session']} ({obj['delivery']})")
            lines.append("  hint: " + obj.get("hint", ""))
        elif t == "agent.exited":
            status = obj["exit_status"] if obj["exit_status"] is not None else "unknown"
            lines.append(f"harness exited in {obj['session']} with status {status}")
            for line in obj.get("lines", []):
                lines.append("  " + line)
            lines.append("  hint: " + obj.get("hint", ""))
        elif t == "agent.started":
            lines.append(f"started {obj['session']} pane_pid {obj['pane_pid']}")
            for child in obj.get("child_processes", []):
                lines.append(f"  {child['pid']} {child['comm']} {child['args']}")
            lines.append("  hint: " + obj.get("hint", ""))
        elif t == "harness.duplicated":
            lines.append(
                f"duplicated {obj['key']} session store: {obj['files']} files, "
                f"{obj['bytes']} bytes"
            )
        elif t == "version":
            lines.append(f"peeragent {obj['version']}")
        else:
            lines.append(obj.get("msg", ""))
        return lines

    # -- public interface -------------------------------------------------

    def emit(self, obj: dict) -> None:
        if self._closed:
            return
        obj.setdefault("user_relevant", False)
        t = obj["type"]
        # stdout side
        if t not in ("invocation", "env"):
            if t not in ("debug", "timing") or self.verbose:
                if self.json_mode:
                    if not self._stdout_first:
                        print(",")
                    print(self._to_json_line(obj))
                    self._stdout_first = False
                else:
                    for line in self._render_plain(obj):
                        print(line)
        # log side
        if self._log_file is not None:
            self._write_log(obj)
        else:
            self._log_buffer.append(obj)

    def _write_log(self, obj: dict) -> None:
        if not self._log_first:
            self._log_file.write(",\n")
        self._log_file.write(self._to_json_line(obj) + "\n")
        self._log_first = False

    def open_log(self, path: Optional[str], is_default: bool = True) -> Optional[str]:
        """Try to open the log file; returns a warning message on failure."""
        self._default_log_path = is_default
        if path is None:
            self._log_buffer = []
            return None
        try:
            # Only the default location is created on demand. A path the
            # caller chose is taken as given: silently creating a
            # directory somewhere in their filesystem is a surprise, and
            # a mistyped path should be reported rather than realised.
            if self._default_log_path:
                os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
            self._log_file = open(path, "w", encoding="utf-8")
            self._log_file.write("[\n")
            for buffered in self._log_buffer:
                self._write_log(buffered)
            self._log_buffer = []
            return None
        except OSError as exc:
            self._log_file = None
            self._log_buffer = []
            return f"could not open log file {path}: {exc}"

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.json_mode:
            print("]")
        else:
            pass
        sys.stdout.flush()
        if self._log_file is not None:
            try:
                self._log_file.write("]\n")
                self._log_file.close()
            except OSError:
                pass

    def fatal(self, msg: str, hint: str, code: int) -> None:
        # A fatal during argument parsing happens before the log is open.
        # Opening it here is what keeps the failing run in the log at all,
        # and it is the run most worth reading afterwards.
        if "--no-log" in sys.argv:
            # Nothing was written, so the hint says how to get a log next
            # time rather than pointing at a file that does not exist.
            hint = f"{hint}; re-run without --no-log to capture a log file"
        elif self._log_file is None:
            self.open_log(default_log_path("invalid"))
        self.emit({"type": "fatal", "msg": msg, "hint": hint, "user_relevant": True})
        self.exit_code = code
        self.close()
        sys.exit(code)

    def error(self, msg: str, hint: str) -> None:
        self.emit({"type": "error", "msg": msg, "hint": hint, "user_relevant": True})

    def warn(self, msg: str, hint: Optional[str] = None, user_relevant: bool = True) -> None:
        obj = {"type": "warn", "msg": msg, "user_relevant": user_relevant}
        if hint is not None:
            obj["hint"] = hint
        self.emit(obj)

    def info(self, msg: str, hint: Optional[str] = None, files: Optional[int] = None,
              bytes_: Optional[int] = None) -> None:
        obj = {"type": "info", "msg": msg, "user_relevant": False}
        if files is not None and bytes_ is not None:
            obj["files"] = files
            obj["bytes"] = bytes_
        if hint is not None:
            obj["hint"] = hint
        self.emit(obj)

    def debug(self, msg: str) -> None:
        self.emit({"type": "debug", "msg": msg, "user_relevant": False})

    def timing(self, step: str, ms: int) -> None:
        self.emit({"type": "timing", "step": step, "ms": ms, "user_relevant": False})


class Stopwatch:
    """Measures a step and logs it as `timing` on exit."""

    def __init__(self, emitter: Emitter, step: str):
        self.emitter = emitter
        self.step = step

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        ms = int((time.perf_counter() - self._start) * 1000)
        self.emitter.timing(self.step, ms)
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def abs_path(path: str) -> str:
    return os.path.realpath(path)


def sanitize_token(text: str, limit: int) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", text)[:limit]


def session_basename(folder: str) -> str:
    base = os.path.basename(folder.rstrip("/"))
    if base == "":
        base = "workdir"
    return sanitize_token(base, 32)


def new_hex_suffix() -> str:
    return secrets.token_hex(4)


def run_subprocess(argv: list[str], timeout: int, env: Optional[dict] = None):
    """One call path for every external program: stdin closed, output
    captured, never streamed to the terminal. Returns None on timeout or a
    failure to even start the process, so callers only need one branch for
    both cases."""
    try:
        return subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None


def decode(data: Optional[bytes]) -> str:
    if data is None:
        return ""
    return data.decode("utf-8", errors="replace")


def first_stdout_line(cp) -> str:
    """The first line of stdout, whitespace trimmed. Not the first
    non-empty one: a harness that opens with a blank line has a blank
    version line, and guessing past it is how two programs come to
    report different versions for the same binary."""
    text = decode(cp.stdout) if cp is not None else ""
    lines = text.splitlines()
    return lines[0].strip() if lines else ""


def git_env() -> dict:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "/bin/true"
    return env


def effective_prompt_length(text: str) -> tuple[int, str]:
    """The counting rule that backs the pointer-prompt limit: trim four
    whitespace codepoints from both ends, split on the same codepoints,
    drop tokens that start with a path separator (they are free), rejoin
    with single spaces, count remaining codepoints. Deliberately blind to
    real path syntax - see the accompanying documentation for why."""
    trimmed = text.strip(WHITESPACE_CODEPOINTS)
    tokens = [tok for tok in WHITESPACE_SPLIT_RE.split(trimmed) if tok]
    kept = [tok for tok in tokens if not tok.startswith("/")]
    joined = " ".join(kept)
    return len(joined), joined


def count_files_bytes(root: str) -> tuple[int, int]:
    """Regular files only, sizes from lstat: the copy preserves symlinks,
    so a size that resolves through them would count a target the copy
    never actually stored."""
    files = 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                st = os.lstat(full)
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode):
                files += 1
                total += st.st_size
    return files, total


def is_nested(outer: str, inner: str) -> bool:
    outer_r = os.path.realpath(outer)
    inner_r = os.path.realpath(inner)
    if outer_r == inner_r:
        return True
    return inner_r.startswith(outer_r.rstrip("/") + "/")


def redact_env() -> dict:
    result = {}
    for name, value in os.environ.items():
        if name in REDACT_EXACT_VARS or any(name.startswith(p) for p in REDACT_PREFIXES):
            if REDACT_NAME_RE.search(name):
                result[name] = "<redacted>"
            else:
                result[name] = value
    return result


# ---------------------------------------------------------------------------
# Model catalogs. Static lists with English descriptions and one shared
# date saying when they were last checked - there is no live query
# against a harness, so a model added yesterday is not in here.
# ---------------------------------------------------------------------------

CATALOG_UPDATED = "2026-08-16"

CATALOG_CLAUDE = [
    ("default", "Account default (Opus 5 on Max/Team/Enterprise/API, Sonnet 5 on Pro)"),
    ("best", "Fable 5 where available, otherwise newest Opus"),
    ("fable", "Claude Fable 5 (opt-in)"),
    ("opus", "Newest Opus"),
    ("sonnet", "Newest Sonnet"),
    ("haiku", "Newest Haiku"),
    ("opus[1m]", "Opus with 1M token context"),
    ("sonnet[1m]", "Sonnet with 1M token context"),
    ("opusplan", "Opus for plan mode, Sonnet for execution"),
    ("claude-opus-5", "Claude Opus 5"),
    ("claude-sonnet-5", "Claude Sonnet 5"),
    ("claude-fable-5", "Claude Fable 5"),
    ("claude-opus-4-8", "Claude Opus 4.8"),
    ("claude-opus-4-7", "Claude Opus 4.7"),
    ("claude-sonnet-4-5", "Claude Sonnet 4.5"),
    ("claude-haiku-4-5", "Claude Haiku 4.5"),
]

CATALOG_CODEX = [
    ("gpt-5.6-sol", "Flagship, deepest reasoning, complex coding"),
    ("gpt-5.6-terra", "Balanced everyday model"),
    ("gpt-5.6-luna", "Fast and cheap"),
    ("gpt-5.3-codex-spark", "Research preview, near-instant iteration (ChatGPT Pro)"),
    ("gpt-5.5", "Prior flagship (ChatGPT plans only)"),
    ("gpt-5.4", "Legacy, retires 2026-08-31"),
    ("gpt-5.4-mini", "Legacy fast and cheap"),
    ("gpt-5.3-codex", "Prior codex-specialist model"),
    ("gpt-5-codex", "Canonical example ID in the official docs"),
]

CATALOG_AGY = [
    ("Gemini 3.1 Pro", "Gemini 3.1 Pro"),
    ("Gemini 3.1 Pro (High)", "Gemini 3.1 Pro, high effort"),
    ("Gemini 3.7 Flash", "Gemini 3.7 Flash"),
    ("Gemini 3.6 Flash", "Gemini 3.6 Flash"),
    ("Gemini 3.5 Flash", "Gemini 3.5 Flash"),
    ("Claude Opus 4.6 (Thinking)", "Claude Opus 4.6 with thinking (paid plans)"),
    ("Claude Sonnet 4.6 (Thinking)", "Claude Sonnet 4.6 with thinking (paid plans)"),
    ("GPT-OSS-120b", "Open-weight GPT-OSS 120b"),
]

CATALOG_OPENCODE = [
    ("anthropic/claude-opus-5", "Anthropic Claude Opus 5"),
    ("anthropic/claude-sonnet-5", "Anthropic Claude Sonnet 5"),
    ("anthropic/claude-sonnet-4-5", "Anthropic Claude Sonnet 4.5"),
    ("anthropic/claude-haiku-4-5", "Anthropic Claude Haiku 4.5"),
    ("openai/gpt-5.6-sol", "OpenAI GPT-5.6 Sol"),
    ("openai/gpt-5.3-codex", "OpenAI GPT-5.3 Codex"),
    ("openai/gpt-5-codex", "OpenAI GPT-5 Codex"),
    ("google/gemini-3-pro", "Google Gemini 3 Pro"),
    ("opencode/big-pickle", "OpenCode Zen Big Pickle (free tier, no login)"),
]

CATALOG_COPILOT = [
    ("claude-opus-5", "Claude Opus 5 via Copilot"),
    ("claude-opus-4.6", "Claude Opus 4.6 via Copilot"),
    ("claude-sonnet-4.6", "Claude Sonnet 4.6 via Copilot"),
    ("claude-sonnet-4.5", "Claude Sonnet 4.5 via Copilot"),
    ("claude-haiku-4.5", "Claude Haiku 4.5 via Copilot"),
    ("gpt-5.3-codex", "GPT-5.3 Codex via Copilot"),
    ("gpt-5-mini", "GPT-5 mini via Copilot"),
    ("gpt-4.1", "GPT-4.1 via Copilot"),
    ("gemini-3-pro", "Gemini 3 Pro via Copilot"),
    ("kimi-k3", "Kimi K3 via Copilot"),
]


# ---------------------------------------------------------------------------
# Handler contract
# ---------------------------------------------------------------------------

@dataclass
class HarnessInfo:
    installed: bool
    path: Optional[str]
    version: Optional[str]


@dataclass
class DuplicateResult:
    status: str
    files: int
    bytes: int
    session_dir: Optional[str]


def generic_detect(binary: str) -> HarnessInfo:
    path = shutil.which(binary)
    if path is None:
        return HarnessInfo(installed=False, path=None, version=None)
    cp = run_subprocess([binary, "--version"], timeout=TMUX_DETECT_TIMEOUT)
    # A version query that fails has no answer, whatever it printed
    # before failing. The binary is still there, so this is a warning
    # and not a missing harness.
    if cp is None or cp.returncode != 0:
        return HarnessInfo(installed=True, path=path, version=None)
    version = first_stdout_line(cp)
    return HarnessInfo(installed=True, path=path, version=version or None)


def line_has_exact(text: str, token: str) -> bool:
    return any(line.strip() == token for line in text.split("\n"))


class Handler:
    """Base class only to give the five handlers a common shape; the core
    never branches on which subclass it holds, it only calls these
    methods through the registry."""

    key: str = ""
    description: str = ""
    binary: str = ""
    prompt_delivery: str = "send_keys"
    resume_support: str = "unsupported"
    duplicate_support: str = "unsupported"
    duplicate_tested: bool = False
    trust_answer: Optional[str] = None
    resume_hint: Optional[str] = None
    duplicate_refusal_hint: Optional[str] = None
    resume_failure_hint: Optional[str] = "no session was found to resume; start again without --resume"

    def detect(self) -> HarnessInfo:
        return generic_detect(self.binary)

    def list_models(self):
        return []

    def launch_argv(self, folder: str, resume: bool) -> list[str]:
        raise NotImplementedError

    def model_argv(self, model: str) -> list[str]:
        raise NotImplementedError

    def prompt_prefix_argv(self) -> list[str]:
        return []

    def detect_prompt_type(self, pane_text: str) -> str:
        return "unknown"

    def session_store_exists(self, path: str) -> bool:
        return False

    def duplicate_session(self, src: str, dst: str) -> DuplicateResult:
        return DuplicateResult(status=self.duplicate_support, files=0, bytes=0, session_dir=None)


def _catalog_models(pairs):
    return [{"key": k, "description": d, "catalog_updated": CATALOG_UPDATED} for k, d in pairs]


class ClaudeHandler(Handler):
    key = "claude"
    description = "Claude Code CLI (Anthropic)"
    binary = "claude"
    prompt_delivery = "argv"
    resume_support = "ok"
    duplicate_support = "ok"
    duplicate_tested = True
    trust_answer = "Down Enter"

    def list_models(self):
        return _catalog_models(CATALOG_CLAUDE)

    def launch_argv(self, folder, resume):
        argv = ["claude"]
        if resume:
            argv.append("--continue")
        return argv

    def model_argv(self, model):
        return ["--model", model]

    def detect_prompt_type(self, pane_text):
        if "Quick safety check" in pane_text or "Yes, I trust this folder" in pane_text:
            return "trust_prompt"
        if "Select login method" in pane_text or "Choose the text style" in pane_text:
            return "auth_prompt"
        if "· thinking)" in pane_text or "esc to interrupt" in pane_text:
            return "busy"
        if line_has_exact(pane_text, "❯"):
            return "ready"
        return "unknown"

    def _config_dir(self) -> str:
        return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")

    @staticmethod
    def _sanitize(path: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "-", path)

    def session_store_exists(self, path):
        return os.path.isdir(os.path.join(self._config_dir(), "projects", self._sanitize(path)))

    def duplicate_session(self, src, dst):
        src_dir = os.path.join(self._config_dir(), "projects", self._sanitize(src))
        dst_dir = os.path.join(self._config_dir(), "projects", self._sanitize(dst))
        if not os.path.isdir(src_dir):
            return DuplicateResult(status="ok", files=0, bytes=0, session_dir=None)
        # Raised through to the core, which turns it into a fatal: a
        # handler never emits, and it never decides an exit code.
        shutil.copytree(src_dir, dst_dir, symlinks=True, dirs_exist_ok=False)
        files, total = count_files_bytes(dst_dir)
        return DuplicateResult(status="ok", files=files, bytes=total, session_dir=dst_dir)


class CodexHandler(Handler):
    key = "codex"
    description = "OpenAI Codex CLI"
    binary = "codex"
    prompt_delivery = "argv"
    resume_support = "experimental"
    duplicate_support = "unsupported"
    duplicate_tested = False
    trust_answer = "1"
    resume_hint = (
        "resume --last continues codex's most recently used session, which may "
        "belong to a different folder; check the pane after the boot wait"
    )
    duplicate_refusal_hint = (
        "codex indexes sessions in ~/.codex/state_5.sqlite, which peeragent does "
        "not modify; copy the folder yourself with 'cp -a' and use 'codex resume "
        "--all <id>' there"
    )

    def list_models(self):
        return _catalog_models(CATALOG_CODEX)

    def launch_argv(self, folder, resume):
        argv = ["codex", "-C", folder]
        if resume:
            argv += ["resume", "--last"]
        return argv

    def model_argv(self, model):
        return ["-m", model]

    def detect_prompt_type(self, pane_text):
        if "Do you trust the contents of this directory" in pane_text:
            return "trust_prompt"
        if "Sign in with ChatGPT" in pane_text:
            return "auth_prompt"
        return "unknown"

    def _home(self) -> str:
        return os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")

    def session_store_exists(self, path):
        token = f'"cwd":"{path}"'
        pattern = os.path.join(self._home(), "sessions", "**", "rollout-*.jsonl")
        for filename in glob.glob(pattern, recursive=True):
            try:
                with open(filename, "r", encoding="utf-8", errors="replace") as fh:
                    if token in fh.read():
                        return True
            except OSError:
                continue
        return False


class AgyHandler(Handler):
    key = "agy"
    description = "Google Antigravity CLI"
    binary = "agy"
    prompt_delivery = "send_keys"
    resume_support = "experimental"
    duplicate_support = "unsupported"
    duplicate_tested = False
    # Its dialog preselects the accepting option, so Enter alone confirms -
    # unlike Claude Code, which preselects the refusing one and needs an
    # arrow key first. Tested 2026-09-29 against agy 1.2.12.
    trust_answer = "Enter"
    resume_hint = (
        "resume behaviour for agy is undocumented; check the pane after the "
        "boot wait to confirm which session was resumed"
    )
    duplicate_refusal_hint = (
        "the session storage location of this harness is undocumented "
        "(credentials live in the system keyring), so peeragent will not copy "
        "it; copy the folder yourself with 'cp -a' and start a fresh session "
        "there"
    )

    def list_models(self):
        return _catalog_models(CATALOG_AGY)

    def launch_argv(self, folder, resume):
        argv = ["agy"]
        if resume:
            argv.append("--continue")
        return argv

    def model_argv(self, model):
        return ["--model", model]

    def detect_prompt_type(self, pane_text):
        if (
            "Do you trust the contents of this project" in pane_text
            or "I trust this folder" in pane_text
        ):
            return "trust_prompt"
        if "Select login method" in pane_text or "not signed in" in pane_text:
            return "auth_prompt"
        for line in pane_text.split("\n"):
            if line.strip() == ">":
                return "ready"
        return "unknown"


class OpencodeHandler(Handler):
    key = "opencode"
    description = "OpenCode (anomalyco)"
    binary = "opencode"
    prompt_delivery = "send_keys"
    resume_support = "experimental"
    duplicate_support = "unsupported"
    duplicate_tested = False
    trust_answer = None
    resume_hint = (
        "opencode resumes the last session in the current project directory; "
        "check the pane after the boot wait"
    )
    duplicate_refusal_hint = (
        "the session database of this harness has no documented schema and "
        "holds authentication tables, so peeragent will not copy it; copy the "
        "folder yourself with 'cp -a' and start a fresh session there"
    )

    def list_models(self):
        return _catalog_models(CATALOG_OPENCODE)

    def launch_argv(self, folder, resume):
        argv = ["opencode"]
        if resume:
            argv.append("--continue")
        return argv

    def model_argv(self, model):
        return ["-m", model]

    def detect_prompt_type(self, pane_text):
        if "Run /connect" in pane_text:
            return "provider_prompt"
        # The input placeholder. The provider question is checked first,
        # so this only decides a screen that is otherwise unclassified.
        # It has never been seen on a configured host - no provider is
        # set up on the test machine - so it rests on the earlier direct
        # check of the harness, not on a run through this program.
        if "Ask anything" in pane_text:
            return "ready"
        return "unknown"


class CopilotHandler(Handler):
    key = "copilot"
    description = "GitHub Copilot CLI"
    binary = "copilot"
    prompt_delivery = "argv"
    resume_support = "experimental"
    duplicate_support = "unsupported"
    duplicate_tested = False
    trust_answer = "1"
    resume_hint = (
        "without a session for this folder, --continue falls back to the "
        "globally most recent session; check the pane after the boot wait"
    )
    duplicate_refusal_hint = (
        "copilot indexes sessions in ~/.copilot/session-store.db, which "
        "peeragent does not modify; copy the folder yourself and use "
        "'copilot --resume <id>' there"
    )

    def list_models(self):
        return _catalog_models(CATALOG_COPILOT)

    def launch_argv(self, folder, resume):
        argv = ["copilot", "-C", folder]
        if resume:
            argv.append("--continue")
        return argv

    def model_argv(self, model):
        return ["--model", model]

    def prompt_prefix_argv(self):
        return ["-i"]

    def detect_prompt_type(self, pane_text):
        if "Confirm folder trust" in pane_text:
            return "trust_prompt"
        if "Please use /login to sign in to use Copilot" in pane_text:
            return "auth_prompt"
        if "esc interrupt" in pane_text:
            return "busy"
        if line_has_exact(pane_text, "❯"):
            return "ready"
        return "unknown"

    def _home(self) -> str:
        return os.environ.get("COPILOT_HOME") or os.path.expanduser("~/.copilot")

    def session_store_exists(self, path):
        pattern = os.path.join(self._home(), "session-state", "*", "workspace.yaml")
        for filename in glob.glob(pattern):
            try:
                with open(filename, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        stripped = line.strip()
                        if stripped.startswith("cwd:"):
                            value = stripped[len("cwd:"):].strip().strip('"').strip("'")
                            if value == path:
                                return True
            except OSError:
                continue
        return False


HANDLERS: dict[str, Handler] = {
    "claude": ClaudeHandler(),
    "codex": CodexHandler(),
    "agy": AgyHandler(),
    "opencode": OpencodeHandler(),
    "copilot": CopilotHandler(),
}


# ---------------------------------------------------------------------------
# tmux runtime
# ---------------------------------------------------------------------------

def run_tmux(args: list[str], timeout: int = TMUX_DETECT_TIMEOUT):
    """tmux calls keep the caller's environment untouched, so a tmux server
    peeragent happens to start does not hand its panes any git-specific
    variables meant only for the git subprocess path."""
    return run_subprocess(["tmux", "-u", *args], timeout=timeout, env=os.environ)


def tmux_detect() -> Optional[str]:
    path = shutil.which("tmux")
    if path is None:
        return None
    cp = run_tmux(["-V"])
    if cp is None or cp.returncode != 0:
        return None
    raw = decode(cp.stdout).strip()
    return raw[len("tmux "):] if raw.startswith("tmux ") else raw


def git_detect() -> Optional[str]:
    path = shutil.which("git")
    if path is None:
        return None
    cp = run_subprocess(["git", "--version"], timeout=TMUX_DETECT_TIMEOUT, env=git_env())
    if cp is None or cp.returncode != 0:
        return None
    raw = decode(cp.stdout).strip()
    prefix = "git version "
    return raw[len(prefix):] if raw.startswith(prefix) else raw


def has_session(name: str) -> bool:
    cp = run_tmux(["has-session", "-t", f"={name}"])
    return cp is not None and cp.returncode == 0


def create_session(name: str, folder: str, argv: list[str]) -> tuple[bool, str]:
    """The session is built empty first and only then respawned into the
    harness (the race-free start): that way a harness
    that dies immediately still leaves a pane the diagnosis step can read,
    instead of a session that vanished before anyone looked at it."""
    cp = run_tmux(["new-session", "-d", "-s", name, "-c", folder, "-x", "200", "-y", "50"])
    if cp is None or cp.returncode != 0:
        stderr = decode(cp.stderr) if cp is not None else "tmux did not respond"
        return False, stderr
    # set-option resolves -t as a pane target even for a session-scoped
    # option; the exact-match session form without a trailing colon does
    # not parse the same way here, so every non-session command below
    # addresses the pane form consistently.
    cp = run_tmux(["set-option", "-t", f"={name}:", "mouse", "on"])
    if cp is None or cp.returncode != 0:
        run_tmux(["kill-session", "-t", f"={name}"])
        return False, decode(cp.stderr) if cp is not None else "tmux did not respond"
    cp = run_tmux(["set-option", "-t", f"={name}:", "-w", "remain-on-exit", "on"])
    if cp is None or cp.returncode != 0:
        run_tmux(["kill-session", "-t", f"={name}"])
        return False, decode(cp.stderr) if cp is not None else "tmux did not respond"
    cp = run_tmux(["respawn-pane", "-k", "-t", f"={name}:", "-c", folder, *argv])
    if cp is None or cp.returncode != 0:
        run_tmux(["kill-session", "-t", f"={name}"])
        return False, decode(cp.stderr) if cp is not None else "tmux did not respond"
    return True, ""


def create_session_with_retry(base_name: str, harness: str, folder: str, argv: list[str],
                                emitter: Emitter, max_attempts: int = 5) -> str:
    for attempt in range(max_attempts):
        suffix = new_hex_suffix()
        name = f"{base_name}-{harness}-{suffix}"
        ok, stderr = create_session(name, folder, argv)
        if ok:
            return name
        if "duplicate session" in stderr:
            continue
        emitter.fatal(
            f"could not create tmux session: {stderr.strip() or 'unknown tmux error'}",
            "check tmux's own diagnostics with: tmux list-sessions",
            1,
        )
    emitter.fatal(
        "could not find a free session name after 5 attempts",
        "retry the command; session names include a random suffix",
        1,
    )


def list_panes_status(name: str) -> Optional[tuple[bool, Optional[int], int]]:
    cp = run_tmux(["list-panes", "-t", f"={name}", "-F", "#{pane_dead},#{pane_dead_status},#{pane_pid}"])
    if cp is None or cp.returncode != 0:
        return None
    line = decode(cp.stdout).splitlines()[0] if decode(cp.stdout).splitlines() else ""
    parts = line.split(",")
    if len(parts) != 3:
        return None
    dead = parts[0] == "1"
    status = int(parts[1]) if parts[1].strip() != "" else None
    pane_pid = int(parts[2])
    return dead, status, pane_pid


def capture_pane(name: str, dead: bool) -> list[str]:
    args = ["capture-pane", "-t", f"={name}:", "-p"]
    if dead:
        args += ["-S", "-"]
    cp = run_tmux(args)
    text = decode(cp.stdout) if cp is not None else ""
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    if dead:
        non_empty = [line for line in lines if line != ""]
        lines = non_empty[-50:]
    return lines


_PASTE_LEFTOVERS: dict = {"buffer": None, "tmp": None}


def paste_prompt(name: str, prompt_text: str) -> tuple[bool, str]:
    """Trailing line breaks are stripped before loading the buffer; Enter is
    always sent afterwards. Bracketed paste (-p) keeps tmux from turning
    embedded newlines into a run of separately submitted lines."""
    content = prompt_text.rstrip("\r\n")
    # A TMPDIR that is set but does not exist falls back, rather than
    # ending the run with a traceback over a scratch file.
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    if not os.path.isdir(tmpdir):
        tmpdir = "/tmp"
    buf_name = f"peeragent-{os.getpid()}"
    fd, tmp_path = tempfile.mkstemp(dir=tmpdir, prefix="peeragent-prompt-")
    # Remembered for the signal handler: it exits without unwinding, so
    # the finally below never runs when a signal arrives mid-paste.
    _PASTE_LEFTOVERS["buffer"] = buf_name
    _PASTE_LEFTOVERS["tmp"] = tmp_path
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        cp = run_tmux(["load-buffer", "-b", buf_name, tmp_path])
        if cp is None or cp.returncode != 0:
            return False, decode(cp.stderr) if cp is not None else "load-buffer did not respond"
        cp = run_tmux(["paste-buffer", "-p", "-t", f"={name}:", "-b", buf_name])
        if cp is None or cp.returncode != 0:
            run_tmux(["delete-buffer", "-b", buf_name])
            return False, decode(cp.stderr) if cp is not None else "paste-buffer did not respond"
        run_tmux(["send-keys", "-t", f"={name}:", "Enter"])
        run_tmux(["delete-buffer", "-b", buf_name])
        return True, ""
    finally:
        _PASTE_LEFTOVERS["buffer"] = None
        _PASTE_LEFTOVERS["tmp"] = None
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def process_tree(pane_pid: int) -> Optional[list[dict]]:
    if shutil.which("ps") is None:
        return None

    def children(ppid: int) -> list[dict]:
        cp = run_subprocess(["ps", "-o", "pid=,comm=,args=", "--ppid", str(ppid)], timeout=TMUX_DETECT_TIMEOUT)
        if cp is None or cp.returncode != 0:
            return []
        result = []
        for line in decode(cp.stdout).splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split(None, 2)
            if len(parts) < 2:
                continue
            pid = int(parts[0])
            comm = parts[1]
            args = parts[2] if len(parts) > 2 else ""
            result.append({"pid": pid, "comm": comm, "args": args})
        return result

    level1 = children(pane_pid)
    level2 = []
    for child in level1:
        level2 += children(child["pid"])
    return level1 + level2


# ---------------------------------------------------------------------------
# Git setup (v1: local `git init` only, behind --git-repo)
# ---------------------------------------------------------------------------

def git_nested_root(folder: str) -> Optional[str]:
    cp = run_subprocess(
        ["git", "-C", folder, "rev-parse", "--show-toplevel"],
        timeout=TMUX_DETECT_TIMEOUT, env=git_env(),
    )
    if cp is None or cp.returncode != 0:
        return None
    root = decode(cp.stdout).strip()
    return root or None


def git_init(folder: str) -> Optional[str]:
    """Runs before anything is emitted about the harness itself: if this
    fails, nothing has been started yet, so the whole operation aborts
    cleanly. The nested-repository check has to happen first, because once
    folder has its own .git this check would only ever see itself."""
    nested_root = git_nested_root(folder)
    cp = run_subprocess(
        ["git", "-C", folder, "init", "-b", "main"],
        timeout=GIT_INIT_TIMEOUT, env=git_env(),
    )
    if cp is None or cp.returncode != 0:
        return decode(cp.stderr).strip() if cp is not None else "git did not respond"
    if nested_root is not None and os.path.realpath(nested_root) != os.path.realpath(folder):
        return "__nested__:" + nested_root
    return None


# ---------------------------------------------------------------------------
# Preflight helpers shared across subcommands
# ---------------------------------------------------------------------------

def require_tmux(emitter: Emitter) -> None:
    version = tmux_detect()
    if version is None:
        emitter.fatal(
            "tmux is not installed",
            "install tmux (>= 3.2) with your package manager; peeragent needs it to run harnesses",
            3,
        )
    emitter.info(f"tmux found: {version}")


def resolve_handler(emitter: Emitter, key: Optional[str]) -> Handler:
    if key is None or key not in HANDLERS:
        emitter.fatal(
            f"unknown harness key: {key}",
            "valid keys are: " + ", ".join(HARNESS_ORDER),
            2,
        )
    return HANDLERS[key]


def require_harness_installed(emitter: Emitter, handler: Handler) -> HarnessInfo:
    info = handler.detect()
    if not info.installed:
        emitter.fatal(
            f"harness {handler.key} is not installed",
            f"install the '{handler.binary}' CLI ({handler.description}); "
            f"see docs/harnesses.md for install instructions",
            3,
        )
    emit_harness_found(emitter, handler, info)
    return info


def emit_harness_found(emitter: Emitter, handler: Handler, info: HarnessInfo) -> None:
    """The success message for a detected harness, in one place.

    An unknown version is always followed by a warning. It was written
    out at four call sites before, and three of them had forgotten the
    warning - which is what a single place is for.
    """
    if info.version is None:
        emitter.info(f"harness {handler.key} found, version unknown")
        emitter.warn(
            f"could not determine the installed version of {handler.key}",
            f"{handler.binary} --version did not produce readable output; the "
            f"harness may still work normally",
        )
    else:
        emitter.info(f"harness {handler.key} found: {info.version}")


def require_git_installed(emitter: Emitter) -> None:
    version = git_detect()
    if version is None:
        emitter.fatal(
            "git is not installed",
            "install git; it is required because --git-repo was given",
            3,
        )
    emitter.info(f"git found: {version}")


def check_prompt_file(emitter: Emitter, path: str) -> tuple[str, int]:
    """Existence/readability plus the pointer-prompt length rule. Returns
    the raw file content and its size in bytes (the size is reported
    unmodified in agent.prompt_sent, before any trailing newline is ever
    stripped)."""
    try:
        st = os.stat(path)
    except OSError:
        emitter.fatal(
            f"prompt file not found or not readable: {path}",
            "pass an existing, readable file via --prompt-file",
            2,
        )
    if not stat.S_ISREG(st.st_mode):
        emitter.fatal(
            f"prompt file is not a regular file: {path}",
            "pass a regular file via --prompt-file",
            2,
        )
    if st.st_size == 0:
        emitter.fatal(
            f"prompt file is empty: {path}",
            "pass a non-empty file via --prompt-file",
            2,
        )
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError:
        emitter.fatal(
            f"prompt file not found or not readable: {path}",
            "pass an existing, readable file via --prompt-file",
            2,
        )
    length, _ = effective_prompt_length(content)
    if length > EFFECTIVE_LENGTH_LIMIT:
        emitter.fatal(
            f"prompt holds {length} effective characters, the limit is {EFFECTIVE_LENGTH_LIMIT}",
            "write the assignment into a file in the working directory and pass a "
            "short prompt that points at it, with the scope and the stopping "
            "condition; paths that start with / and contain no spaces do not "
            "count towards the limit",
            2,
        )
    return content, st.st_size


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_version(emitter: Emitter, json_mode: bool) -> int:
    # Through the emitter in both modes. Printing directly would keep
    # the message out of the log, and the log is meant to hold every
    # message of a run, whatever the output mode was.
    emitter.emit({
        "type": "version", "version": PEERAGENT_VERSION, "impl": IMPL_NAME,
        "user_relevant": False,
    })
    return 0


def cmd_list_harness(emitter: Emitter) -> int:
    for key in HARNESS_ORDER:
        handler = HANDLERS[key]
        info = handler.detect()
        if info.installed:
            emitter.emit({
                "type": "harness.detected", "key": key, "version": info.version,
                "description": handler.description, "path": info.path,
                "user_relevant": False,
            })
            if info.version is None:
                emitter.warn(
                    f"could not determine the installed version of {key}",
                    f"{handler.binary} --version did not produce readable output",
                )
        else:
            emitter.emit({
                "type": "harness.missing", "key": key, "description": handler.description,
                "user_relevant": False,
            })
    return 0


def cmd_list_models(emitter: Emitter, harness_key: Optional[str]) -> int:
    if harness_key is not None:
        handler = resolve_handler(emitter, harness_key)
        info = handler.detect()
        if not info.installed:
            emitter.fatal(
                f"harness {handler.key} is not installed",
                f"install the '{handler.binary}' CLI ({handler.description}); "
                f"see docs/harnesses.md for install instructions",
                3,
            )
        emit_harness_found(emitter, handler, info)
        for model in handler.list_models():
            emitter.emit({
                "type": "model.available", "harness": handler.key, **model,
                "user_relevant": False,
            })
        return 0

    # The preflight checks for all harnesses come first; only then are the
    # catalogs listed, so the info messages form one block.
    installed = []
    for key in HARNESS_ORDER:
        handler = HANDLERS[key]
        info = handler.detect()
        if not info.installed:
            continue
        emit_harness_found(emitter, handler, info)
        installed.append(key)
    for key in installed:
        handler = HANDLERS[key]
        for model in handler.list_models():
            emitter.emit({
                "type": "model.available", "harness": key, **model,
                "user_relevant": False,
            })
    return 0


def cmd_start_agent(emitter: Emitter, ns) -> int:
    if os.environ.get("TMUX"):
        emitter.debug("peeragent is running inside an existing tmux session")

    with Stopwatch(emitter, "preflight"):
        require_tmux(emitter)
        handler = resolve_handler(emitter, ns.harness)
        info = require_harness_installed(emitter, handler)

        folder = abs_path(ns.folder) if ns.folder else None
        if folder is None or not os.path.isdir(folder):
            emitter.fatal(
                f"folder does not exist or is not a directory: {ns.folder}",
                "pass an existing directory via --folder",
                2,
            )
        # A .git entry of any kind counts: in a submodule or a worktree
        # it is a file, not a directory, and this repository is itself a
        # submodule.
        if ns.git_repo and os.path.lexists(os.path.join(folder, ".git")):
            emitter.fatal("folder is already a git repo", "drop --git-repo, or start in a fresh folder", 2)
        if ns.git_repo:
            require_git_installed(emitter)
        if ns.resume and handler.resume_support == "unsupported":
            emitter.fatal(
                f"harness {handler.key} does not support --resume",
                "start without --resume",
                2,
            )
        prompt_content = None
        prompt_bytes = None
        prompt_file_abs = None
        if ns.prompt_file:
            prompt_file_abs = abs_path(ns.prompt_file)
            prompt_content, prompt_bytes = check_prompt_file(emitter, prompt_file_abs)

    if ns.git_repo:
        with Stopwatch(emitter, "git-init"):
            error = git_init(folder)
            if error is not None and error.startswith("__nested__:"):
                emitter.warn(
                    "nested repository: folder is inside an existing git "
                    "repository at " + error[len("__nested__:"):] + "; initializing anyway",
                    "the new repository is independent of the enclosing one; remove the new .git directory if that was not intended",
                )
                error = None
            if error is not None:
                emitter.fatal(f"git init failed: {error}", "inspect the folder's permissions and retry", 1)

    argv = handler.launch_argv(folder, ns.resume)
    if ns.model:
        argv += handler.model_argv(ns.model)
    if prompt_content is not None and handler.prompt_delivery == "argv":
        argv += handler.prompt_prefix_argv()
        # Trailing newlines are stripped on both delivery paths. On the
        # paste path they would submit the prompt before it is complete;
        # here they simply do not belong in an argument, and a shell
        # cannot preserve them anyway, so keeping them would hand the
        # harness different text depending on which program ran.
        argv += [prompt_content.rstrip("\r\n")]

    emitter.emit({
        "type": "agent.starting", "harness": handler.key, "folder": folder,
        "model": ns.model, "resume": bool(ns.resume), "prompt_file": prompt_file_abs,
        "user_relevant": False,
    })

    if ns.resume and handler.resume_support == "experimental":
        emitter.warn(
            f"--resume for {handler.key} is experimental; it may not pick the "
            f"session for this folder",
            hint=handler.resume_hint,
        )

    base_name = f"peeragent-{session_basename(folder)}"
    with Stopwatch(emitter, "tmux-create"):
        session = create_session_with_retry(base_name, handler.key, folder, argv, emitter)

    with Stopwatch(emitter, "boot-wait"):
        time.sleep(ns.boot_wait)

    with Stopwatch(emitter, "diagnose"):
        status = list_panes_status(session)
        if status is None:
            emitter.fatal("could not read back the tmux pane after starting the harness",
                          "inspect the session yourself: tmux attach -r -t '=" + session + "'", 1)
        dead, exit_status, pane_pid = status
        lines = capture_pane(session, dead)
        if dead:
            hint = ("the harness exited during startup; the tmux session was "
                    f"kept: tmux attach -r -t '={session}'")
            if ns.resume and handler.resume_failure_hint:
                hint += "; " + handler.resume_failure_hint
            emitter.emit({
                "type": "agent.exited", "session": session, "exit_status": exit_status,
                "lines": lines, "hint": hint, "user_relevant": True,
            })
            emitter.close()
            return 4

        awaiting = handler.detect_prompt_type("\n".join(lines))
        if awaiting not in ("trust_prompt", "auth_prompt", "provider_prompt"):
            time.sleep(2)
            lines2 = capture_pane(session, dead)
            if lines2 != lines:
                awaiting = "busy"
                lines = lines2

        emitter.emit({
            "type": "agent.pane", "session": session, "awaiting": awaiting,
            "lines": lines, "user_relevant": False,
        })

        if awaiting in ("trust_prompt", "auth_prompt", "provider_prompt", "unknown"):
            if awaiting == "trust_prompt" and handler.trust_answer:
                warn_hint = (
                    f"send '{handler.trust_answer}' to trust: tmux send-keys -t "
                    f"'={session}:' {handler.trust_answer}"
                )
                emitter.warn(f"harness {handler.key} is awaiting trust-prompt confirmation", warn_hint)
            elif awaiting == "trust_prompt":
                # A trust marker without a key sequence: the state is
                # known, the answer is not. Saying so beats reporting an
                # unrecognised screen, which would be untrue.
                emitter.warn(
                    f"harness {handler.key} is awaiting trust-prompt confirmation",
                    "no key sequence is recorded for this harness; look at the "
                    f"pane and answer it yourself: tmux attach -r -t '={session}'",
                )
            elif awaiting == "auth_prompt":
                emitter.warn(
                    f"harness {handler.key} is awaiting authentication",
                    "the harness is not logged in; complete the login outside peeragent, then check the pane again",
                )
            elif awaiting == "provider_prompt":
                emitter.warn(
                    f"harness {handler.key} needs a provider configured",
                    "complete the provider setup outside peeragent, then check the pane again",
                )
            else:
                unknown_hint = "unrecognised screen; show the captured lines to the user and ask how to proceed"
                if ns.resume and handler.resume_failure_hint:
                    unknown_hint += "; " + handler.resume_failure_hint
                emitter.warn(f"harness {handler.key} reached an unrecognised screen", unknown_hint)

    prompt_delivered = prompt_content is None
    if prompt_content is not None:
        if handler.prompt_delivery == "send_keys" and awaiting == "ready":
            with Stopwatch(emitter, "paste"):
                ok, err = paste_prompt(session, prompt_content)
            if ok:
                emitter.emit({
                    "type": "agent.prompt_sent", "session": session, "bytes": prompt_bytes,
                    "user_relevant": False,
                })
                with Stopwatch(emitter, "paste-wait"):
                    time.sleep(2)
                lines = capture_pane(session, False)
                awaiting = handler.detect_prompt_type("\n".join(lines))
                emitter.emit({
                    "type": "agent.pane", "session": session, "awaiting": awaiting,
                    "lines": lines, "user_relevant": False,
                })
                prompt_delivered = True
            else:
                emitter.error(f"could not deliver the prompt to {session}: {err.strip()}",
                              "retry with: peeragent send --session " + session +
                              " --prompt-file " + prompt_file_abs)
                prompt_delivered = True
        elif handler.prompt_delivery == "argv" and awaiting in ("busy", "ready"):
            prompt_delivered = True

        if not prompt_delivered:
            if handler.prompt_delivery == "send_keys":
                hint = f"deliver with: peeragent send --session {session} --prompt-file {prompt_file_abs}"
            else:
                hint = (
                    "the prompt was passed as a command-line argument; once the "
                    "pane has reached a state you understand, capture it - if the "
                    "harness did not pick the prompt up, deliver with: peeragent "
                    f"send --session {session} --prompt-file {prompt_file_abs}"
                )
            emitter.emit({
                "type": "agent.prompt_deferred", "session": session, "prompt_file": prompt_file_abs,
                "awaiting": awaiting, "delivery": handler.prompt_delivery, "hint": hint,
                "user_relevant": True,
            })

    with Stopwatch(emitter, "process-tree"):
        children = process_tree(pane_pid)
        if children is None:
            emitter.warn("ps is not available; the child process list will stay empty",
                         "install procps to get the process image of the launched harness")
            children = []

    emitter.emit({
        "type": "agent.started", "session": session, "pane_pid": pane_pid,
        "child_processes": children,
        "hint": f"watch with: tmux attach -r -t '={session}'",
        "user_relevant": False,
    })
    return 0


def cmd_send(emitter: Emitter, ns) -> int:
    if os.environ.get("TMUX"):
        emitter.debug("peeragent is running inside an existing tmux session")

    require_tmux(emitter)
    session = ns.session
    if not has_session(session):
        emitter.fatal(
            f"no such tmux session: {session}",
            "check 'tmux list-sessions' or the session name from agent.started",
            2,
        )

    match = SESSION_NAME_RE.match(session)
    if match:
        handler = HANDLERS.get(match.group(2))
        if handler is not None:
            info = handler.detect()
            if info.installed:
                emit_harness_found(emitter, handler, info)
            else:
                emitter.warn(f"harness {handler.key} is not installed on this host",
                             "the prompt is delivered anyway; the harness binary is not needed for send")

    prompt_content, prompt_bytes = check_prompt_file(emitter, abs_path(ns.prompt_file))

    status = list_panes_status(session)
    if status is None:
        emitter.fatal("could not read the tmux pane", "check 'tmux list-panes -t \"=" + session + "\"'", 1)
    dead, _exit_status, _pane_pid = status
    if dead:
        emitter.fatal(
            "pane is not alive",
            f"the harness process has exited; inspect it with: tmux attach -r -t '={session}'",
            2,
        )

    lines = capture_pane(session, False)
    awaiting = "unknown"
    if match and HANDLERS.get(match.group(2)):
        awaiting = HANDLERS[match.group(2)].detect_prompt_type("\n".join(lines))
    emitter.emit({
        "type": "agent.pane", "session": session, "awaiting": awaiting,
        "lines": lines, "user_relevant": False,
    })

    ok, err = paste_prompt(session, prompt_content)
    if not ok:
        emitter.fatal(f"could not deliver the prompt: {err.strip()}",
                      "check that the session is still alive and retry", 1)

    emitter.emit({
        "type": "agent.prompt_sent", "session": session, "bytes": prompt_bytes,
        "user_relevant": False,
    })
    time.sleep(ns.wait)
    lines2 = capture_pane(session, False)
    awaiting2 = "unknown"
    if match and HANDLERS.get(match.group(2)):
        awaiting2 = HANDLERS[match.group(2)].detect_prompt_type("\n".join(lines2))
    emitter.emit({
        "type": "agent.pane", "session": session, "awaiting": awaiting2,
        "lines": lines2, "user_relevant": False,
    })
    return 0


def cmd_duplicate(emitter: Emitter, ns) -> int:
    handler = resolve_handler(emitter, ns.harness)
    if handler.duplicate_support == "unsupported":
        emitter.fatal(
            f"duplicate for {handler.key} is not supported in this release",
            handler.duplicate_refusal_hint
            or "copy the folder yourself with 'cp -a' and start a fresh session there",
            2,
        )

    src = abs_path(ns.from_)
    dst = abs_path(ns.to)
    if not os.path.isdir(src):
        emitter.fatal(
            f"source folder does not exist or is not a directory: {ns.from_}",
            "pass an existing directory via --from",
            2,
        )
    parent = os.path.dirname(dst.rstrip("/")) or "/"
    if not os.path.isdir(parent):
        emitter.fatal(
            f"parent directory of destination does not exist: {parent}",
            "create the parent directory first, or pass a different --to",
            2,
        )
    if is_nested(src, dst) or is_nested(dst, src):
        emitter.fatal(
            "destination is nested inside source, or source inside destination",
            "choose independent paths for --from and --to",
            2,
        )

    info = handler.detect()
    if not info.installed:
        emitter.fatal(
            f"harness {handler.key} is not installed",
            f"install the '{handler.binary}' CLI ({handler.description}); "
            f"see docs/harnesses.md for install instructions",
            3,
        )
    emit_harness_found(emitter, handler, info)

    if handler.session_store_exists(dst):
        emitter.fatal(
            "session store for destination already exists",
            "choose a different --to, or remove the existing session store first",
            1,
        )

    if os.path.exists(dst):
        try:
            same = set(os.listdir(src)) == set(os.listdir(dst))
        except OSError:
            same = False
        if not same:
            emitter.fatal(
                "destination exists and differs from source",
                "choose a different --to, or remove the mismatched destination first",
                1,
            )

    if handler.duplicate_support == "experimental":
        emitter.warn(
            f"duplicate for {handler.key} is experimental and not yet verified end to end",
            "check the copied session in the destination before relying on it",
        )

    if not os.path.exists(dst):
        with Stopwatch(emitter, "workspace-copy"):
            try:
                shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=False)
            except (OSError, shutil.Error) as exc:
                # A half-finished copy is the caller's to inspect; saying
                # so is more use than a traceback, and the partial tree is
                # left where it is rather than guessed at.
                emitter.fatal(
                    f"copying the working directory failed: {exc}",
                    f"check permissions and free space; {dst} may hold a "
                    f"partial copy that peeragent did not remove",
                    1,
                )
            files, total = count_files_bytes(dst)
        emitter.info("copied workspace", files=files, bytes_=total)
    else:
        emitter.info("workspace already present, skipped copy")

    with Stopwatch(emitter, "session-copy"):
        try:
            dup = handler.duplicate_session(src, dst)
        except (OSError, shutil.Error) as exc:
            emitter.fatal(
                f"copying the session store failed: {exc}",
                "the working directory was copied; the harness will start a "
                "fresh session in it unless you copy the store by hand",
                1,
            )
    if dup.session_dir is None and dup.files == 0 and dup.bytes == 0:
        emitter.warn("no session store found for source",
                     "the copy has no session history; a resume in the destination will find nothing")
    emitter.emit({
        "type": "harness.duplicated", "key": handler.key, "status": dup.status,
        "files": dup.files, "bytes": dup.bytes, "session_dir": dup.session_dir,
        "user_relevant": False,
    })
    emitter.info(
        "duplicate complete",
        hint="working tree shares origin and branch with source; the first "
             "start in the copy may show a trust prompt",
    )
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

USAGE_TEXT = f"""peeragent {PEERAGENT_VERSION} - start and manage coding-agent harnesses in tmux

Usage:
  peeragent list harness [--json]
  peeragent list models [--harness <key>] [--json]
  peeragent start agent --folder <path> --harness <key> [--prompt-file <path>]
                         [--model <string>] [--resume] [--git-repo]
                         [--boot-wait <seconds>] [--json]
  peeragent send --session <name> --prompt-file <path> [--wait <seconds>] [--json]
  peeragent duplicate --from <path> --to <path> --harness <key> [--json]
  peeragent version [--json]

Global flags:
  --json            JSONL output instead of plain text
  --no-log          do not write a log file
  --log-file <path> write the log to this path instead of the default
  --verbose         also print debug and timing messages
  --no-color        disable ANSI colors in plain-text output
  --help, -h        show this text and exit

See docs/cli.md for the full reference.
"""

GLOBAL_FLAGS_NO_ARG = {"--json", "--no-log", "--verbose", "--no-color"}
GLOBAL_FLAGS_ARG = {"--log-file", "--boot-wait", "--wait"}
SUB_FLAGS_NO_ARG = {"--resume", "--git-repo"}
SUB_FLAGS_ARG = {"--folder", "--harness", "--model", "--prompt-file", "--session", "--from", "--to"}

APPLICABLE_FLAGS = {
    "list_harness": set(),
    "list_models": {"--harness"},
    "list_git_templates": set(),
    "start_agent": {"--folder", "--harness", "--model", "--prompt-file", "--resume",
                     "--git-repo", "--boot-wait"},
    "send": {"--session", "--prompt-file", "--wait"},
    "duplicate": {"--from", "--to", "--harness"},
    "version": set(),
}


class Namespace:
    def __init__(self):
        self.json = False
        self.no_log = False
        self.log_file = None
        self.verbose = False
        self.no_color = False
        self.boot_wait = 5
        self.wait = 2
        self.folder = None
        self.harness = None
        self.model = None
        self.prompt_file = None
        self.resume = False
        self.git_repo = False
        self.session = None
        self.from_ = None
        self.to = None


def determine_action(subcommand: Optional[str], subaction: Optional[str]) -> Optional[str]:
    if subcommand is None:
        return None
    if subcommand == "list":
        if subaction == "harness":
            return "list_harness"
        if subaction == "models":
            return "list_models"
        if subaction == "git-templates":
            return "list_git_templates"
        return None
    if subcommand == "start":
        if subaction == "agent":
            return "start_agent"
        return None
    if subcommand in ("send", "duplicate", "version") and subaction is None:
        return subcommand
    return None


def parse_argv(argv: list[str], emitter: Emitter) -> tuple[str, Namespace]:
    ns = Namespace()
    subcommand = None
    subaction = None
    present_flags: set[str] = set()
    i = 0
    n = len(argv)
    while i < n:
        tok = argv[i]
        if tok in GLOBAL_FLAGS_NO_ARG:
            present_flags.add(tok)
            if tok == "--json":
                ns.json = True
            elif tok == "--no-log":
                ns.no_log = True
            elif tok == "--verbose":
                ns.verbose = True
            elif tok == "--no-color":
                ns.no_color = True
            i += 1
        elif tok in GLOBAL_FLAGS_ARG:
            if i + 1 >= n:
                emitter.fatal(f"missing value for {tok}", "provide a value after " + tok, 2)
            value = argv[i + 1]
            present_flags.add(tok)
            if tok == "--log-file":
                ns.log_file = value
            elif tok == "--boot-wait":
                ns.boot_wait = _parse_int(emitter, tok, value, 1, 120)
            elif tok == "--wait":
                ns.wait = _parse_int(emitter, tok, value, 0, 120)
            i += 2
        elif tok in SUB_FLAGS_NO_ARG:
            present_flags.add(tok)
            if tok == "--resume":
                ns.resume = True
            elif tok == "--git-repo":
                ns.git_repo = True
            i += 1
        elif tok in SUB_FLAGS_ARG:
            if i + 1 >= n:
                emitter.fatal(f"missing value for {tok}", "provide a value after " + tok, 2)
            value = argv[i + 1]
            present_flags.add(tok)
            if tok == "--folder":
                ns.folder = value
            elif tok == "--harness":
                ns.harness = value
            elif tok == "--model":
                ns.model = value
            elif tok == "--prompt-file":
                ns.prompt_file = value
            elif tok == "--session":
                ns.session = value
            elif tok == "--from":
                ns.from_ = value
            elif tok == "--to":
                ns.to = value
            i += 2
        elif tok.startswith("-"):
            emitter.fatal(f"unknown argument: {tok}", "run 'peeragent --help' for usage", 2)
        else:
            if subcommand is None:
                subcommand = tok
            elif subcommand in ("list", "start") and subaction is None:
                subaction = tok
            else:
                emitter.fatal(f"unexpected argument: {tok}", "run 'peeragent --help' for usage", 2)
            i += 1

    if subcommand is None:
        emitter.fatal("no subcommand given", "run 'peeragent --help' for usage", 2)

    if subcommand not in ("list", "start", "send", "duplicate", "version"):
        emitter.fatal(f"unknown subcommand: {subcommand}", "run 'peeragent --help' for usage", 2)

    if subcommand in ("list", "start") and subaction is None:
        emitter.fatal(f"'{subcommand}' needs a second word", "run 'peeragent --help' for usage", 2)

    action = determine_action(subcommand, subaction)
    if action is None:
        emitter.fatal(
            f"unknown subcommand: {subcommand} {subaction}",
            "run 'peeragent --help' for usage",
            2,
        )
    if action == "list_git_templates":
        emitter.fatal(
            "the subcommand 'list git-templates' does not exist in this version",
            "planned for a future release; use 'list harness' or 'list models' for now",
            2,
        )

    allowed = APPLICABLE_FLAGS[action] | GLOBAL_FLAGS_NO_ARG | {"--log-file"}
    for flag in present_flags:
        if flag not in allowed:
            emitter.fatal(
                f"{flag} is not valid for this subcommand",
                "run 'peeragent --help' for usage",
                2,
            )

    if ns.no_log and ns.log_file is not None:
        emitter.fatal(
            "--no-log and --log-file cannot be used together",
            "choose either --no-log or --log-file, not both",
            2,
        )

    if action == "start_agent":
        if ns.folder is None:
            emitter.fatal("--folder is required", "pass --folder <path>", 2)
        if ns.harness is None:
            emitter.fatal("--harness is required", "pass --harness <key>", 2)
    elif action == "send":
        if ns.session is None:
            emitter.fatal("--session is required", "pass --session <name>", 2)
        if ns.prompt_file is None:
            emitter.fatal("--prompt-file is required", "pass --prompt-file <path>", 2)
    elif action == "duplicate":
        if ns.from_ is None:
            emitter.fatal("--from is required", "pass --from <path>", 2)
        if ns.to is None:
            emitter.fatal("--to is required", "pass --to <path>", 2)
        if ns.harness is None:
            emitter.fatal("--harness is required", "pass --harness <key>", 2)

    return action, ns


def _parse_int(emitter: Emitter, flag: str, value: str, low: int, high: int) -> int:
    # Plain decimal digits only. int() would also take a leading sign,
    # surrounding whitespace and digits from other scripts, and then the
    # two programs would accept different arguments.
    if not re.fullmatch(r"[0-9]+", value):
        emitter.fatal(f"invalid value for {flag}: {value}", f"pass an integer between {low} and {high}", 2)
    try:
        parsed = int(value)
    except ValueError:
        emitter.fatal(f"invalid value for {flag}: {value}", f"pass an integer between {low} and {high}", 2)
    if not (low <= parsed <= high):
        emitter.fatal(
            f"value for {flag} out of range: {value}",
            f"pass an integer between {low} and {high}",
            2,
        )
    return parsed


ACTION_TO_LOG_TOKEN = {
    "list_harness": "list-harness",
    "list_models": "list-models",
    "start_agent": "start-agent",
    "send": "send",
    "duplicate": "duplicate",
    "version": "version",
    # An argument error happens before the subcommand is known, and it is
    # exactly the run someone will want to look at afterwards.
    "invalid": "invalid",
}


def default_log_path(action_token: str) -> str:
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d_%H%M%S")
    return os.path.join(
        os.path.expanduser("~/.local/state/peeragent/logs"),
        f"{stamp}_{action_token}_{os.getpid()}.jsonl",
    )


def build_invocation(argv: list[str], timestamp: datetime) -> dict:
    return {
        "type": "invocation",
        "argv": ["peeragent"] + argv,
        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "user_relevant": False,
    }


def build_env() -> dict:
    return {
        "type": "env",
        "impl": IMPL_NAME,
        "impl_version": platform.python_version(),
        "peeragent_version": PEERAGENT_VERSION,
        "tmux": tmux_detect(),
        "git": git_detect(),
        "gh": None,
        "vars": redact_env(),
        "user_relevant": False,
    }


def cleanup_paste_leftovers() -> None:
    """Remove what a paste in flight would otherwise leave behind.

    The signal handler exits with os._exit, which runs no finally
    blocks, so a scratch file and a tmux paste buffer would survive an
    interrupted run. Errors here are ignored on purpose: this is the
    last thing that happens before the process ends.
    """
    buf = _PASTE_LEFTOVERS.get("buffer")
    tmp = _PASTE_LEFTOVERS.get("tmp")
    if buf:
        try:
            run_tmux(["delete-buffer", "-b", buf])
        except Exception:
            pass
    if tmp:
        try:
            os.remove(tmp)
        except OSError:
            pass


def install_signal_handlers(emitter: Emitter) -> None:
    def handler(signum, _frame):
        # Whatever a paste in flight left behind goes first: the frame is
        # closed right after, and os._exit runs no finally blocks.
        cleanup_paste_leftovers()
        emitter.close()
        os._exit(128 + signum)

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, handler)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def main() -> int:
    argv = sys.argv[1:]

    if any(a in ("--help", "-h") for a in argv):
        print(USAGE_TEXT, end="")
        return 0

    json_mode = "--json" in argv
    emitter = Emitter(json_mode=json_mode, verbose="--verbose" in argv, no_color="--no-color" in argv)
    install_signal_handlers(emitter)
    atexit.register(emitter.close)

    start_time = datetime.now(timezone.utc)
    emitter.emit(build_invocation(argv, start_time))
    emitter.emit(build_env())

    action, ns = parse_argv(argv, emitter)
    emitter.verbose = ns.verbose
    emitter.color = (not ns.no_color and os.environ.get("NO_COLOR", "") == "" and sys.stdout.isatty())

    # An empty value counts as a flag that was not given. Otherwise one
    # program reports an empty model string where the other reports none.
    if getattr(ns, "model", None) == "":
        ns.model = None

    log_token = ACTION_TO_LOG_TOKEN[action]
    if ns.no_log:
        log_path = None
        chosen_by_caller = False
    elif ns.log_file:
        log_path = abs_path(ns.log_file)
        chosen_by_caller = True
    else:
        log_path = default_log_path(log_token)
        chosen_by_caller = False
    warning = emitter.open_log(log_path, is_default=not chosen_by_caller)
    if warning is not None:
        emitter.warn(warning, "the run continues without a log file")

    if action == "version":
        code = cmd_version(emitter, ns.json)
    elif action == "list_harness":
        code = cmd_list_harness(emitter)
    elif action == "list_models":
        code = cmd_list_models(emitter, ns.harness)
    elif action == "start_agent":
        code = cmd_start_agent(emitter, ns)
    elif action == "send":
        code = cmd_send(emitter, ns)
    elif action == "duplicate":
        code = cmd_duplicate(emitter, ns)
    else:  # pragma: no cover - determine_action already excludes this
        code = 2

    emitter.close()
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
