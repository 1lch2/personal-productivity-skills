"""Shared helpers for the test-value-review scripts.

Standard library only. These helpers are intentionally small and boring:
path normalisation, JSON output, subprocess execution with a timeout, and
git-aware file discovery. Nothing here judges a test.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, NoReturn

SCHEMA_PREFIX = "test-value-review"
DEFAULT_TIMEOUT = 120.0
MAX_CAPTURE = 6000

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".agents",
    ".dsh",
    ".claude",
    ".codex",
    ".cursor",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".coverage",
    ".next",
    ".nuxt",
    ".output",
    ".svelte-kit",
    ".turbo",
    ".cache",
    "vendor",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "target",
    "obj",
    "bin",
    "out",
    "Pods",
    "DerivedData",
    "__snapshots__",
}


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def fail(message: str, hint: str | None = None, code: int = 2) -> NoReturn:
    payload: dict[str, Any] = {"error": message}
    if hint:
        payload["hint"] = hint
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(code)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def temp_root() -> Path:
    path = Path(tempfile.gettempdir()) / SCHEMA_PREFIX
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(data: Any, out: Path | None = None, name: str = "result") -> Path:
    if out is None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        out = temp_root() / f"{name}-{stamp}.json"
    out = out.expanduser()
    if not out.is_absolute():
        out = Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, out)
    return out


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def truncate(text: str, limit: int = MAX_CAPTURE) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def sanitize_filename(value: str, limit: int = 60) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return (cleaned or "item")[:limit]


def line_starts(text: str) -> list[int]:
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    return starts


def line_of(starts: list[int], index: int) -> int:
    import bisect

    return bisect.bisect_right(starts, index)


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def kill_process_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _wrap_command(cmd: list[str]) -> list[str]:
    """Run .cmd/.bat shims through cmd.exe on Windows."""
    if os.name == "nt" and cmd and cmd[0].lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", subprocess.list2cmdline(cmd)]
    return cmd


def run_process(
    cmd: list[str] | str,
    cwd: Path,
    timeout: float = DEFAULT_TIMEOUT,
    env_extra: dict[str, str] | None = None,
    shell: bool = False,
) -> dict[str, Any]:
    """Run a command, capture output, and always report a structured result.

    A test failure is data, not a script failure: callers get ``passed: false``
    and decide what it means. A timeout is reported separately from an exit code.
    """
    env = os.environ.copy()
    env.update(
        {
            "CI": "1",
            "NO_COLOR": "1",
            "FORCE_COLOR": "0",
            "PYTHONUNBUFFERED": "1",
            # Isolate bytecode caches per run. A same-size mutation written in
            # the same mtime second would otherwise be ignored by a stale .pyc.
            "PYTHONPYCACHEPREFIX": str(temp_root() / "pycache" / uuid.uuid4().hex),
        }
    )
    if env_extra:
        env.update(env_extra)

    actual: list[str] | str = cmd if shell else _wrap_command(cmd)
    popen_kwargs: dict[str, Any] = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "env": env,
        "shell": shell,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    start = time.monotonic()
    proc = subprocess.Popen(actual, **popen_kwargs)  # type: ignore[arg-type]
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_tree(proc)
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out, err = "", ""
    duration_ms = int((time.monotonic() - start) * 1000)

    return {
        "command": actual,
        "cwd": str(cwd),
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "passed": (not timed_out and proc.returncode == 0),
        "duration_ms": duration_ms,
        "stdout": out or "",
        "stderr": err or "",
    }


def _git(root: Path, args: Iterable[str], timeout: float = 20.0) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def git_toplevel(root: Path) -> Path | None:
    data = _git(root, ["rev-parse", "--show-toplevel"])
    if data is None:
        return None
    raw = data.decode("utf-8", "replace").strip()
    return Path(raw) if raw else None


def git_files(root: Path) -> list[Path] | None:
    """Tracked plus untracked-but-not-ignored files under root, or None outside git."""
    top = git_toplevel(root)
    if top is None:
        return None
    data = _git(root, ["ls-files", "-z", "--full-name", "--cached", "--others", "--exclude-standard"])
    if data is None:
        return None
    result: list[Path] = []
    for item in data.decode("utf-8", "replace").split("\0"):
        if not item:
            continue
        path = top / item
        if is_within(path, root):
            result.append(path)
    return result


def git_changed_files(root: Path) -> list[Path] | None:
    """Files changed versus HEAD plus untracked files under root.

    Returns ``[]`` when git works but nothing changed, and ``None`` when git is
    unavailable, so callers can distinguish "no changes" from "no git".
    """
    top = git_toplevel(root)
    if top is None:
        return None
    changed: set[str] = set()
    diff = _git(root, ["diff", "--name-only", "--diff-filter=ACMR", "-z", "HEAD"])
    if diff is not None:
        changed.update(item for item in diff.decode("utf-8", "replace").split("\0") if item)
    untracked = _git(root, ["ls-files", "-z", "--full-name", "--others", "--exclude-standard"])
    if untracked is not None:
        changed.update(item for item in untracked.decode("utf-8", "replace").split("\0") if item)
    result: list[Path] = []
    for item in sorted(changed):
        path = top / item
        if is_within(path, root):
            result.append(path)
    return result


def detect_package_manager(root: Path) -> str | None:
    for filename, manager in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"),
        ("bun.lock", "bun"),
        ("package-lock.json", "npm"),
    ):
        if (root / filename).exists():
            return manager
    package_json = root / "package.json"
    if not package_json.exists():
        return None
    match = re.search(r'"packageManager"\s*:\s*"([^"]+)"', read_text(package_json))
    if match:
        return match.group(1).split("@")[0]
    return "npm"


def local_bin(root: Path, name: str) -> Path | None:
    """Find a local node_modules/.bin executable, checking two parent levels."""
    suffixes: list[str] = [".cmd", ".exe", ""] if os.name == "nt" else [""]
    bases = [root, root.parent, root.parent.parent]
    for base in bases:
        for suffix in suffixes:
            candidate = base / "node_modules" / ".bin" / (name + suffix)
            if candidate.exists():
                return candidate
    return None


def which(name: str) -> str | None:
    import shutil

    return shutil.which(name)


def git_file_dirty(root: Path, path: Path) -> bool | None:
    """True/False from git, or None when git or the path is unavailable."""
    if not is_within(path, root):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", relpath(path, root)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip())


def is_git_repo(root: Path) -> bool:
    return _git(root, ["rev-parse", "--is-inside-work-tree"]) is not None


def json_line(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
