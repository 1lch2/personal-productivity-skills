#!/usr/bin/env python3
"""Temporarily apply one literal mutation to production code and run one test.

This is the strongest evidence for "would this test fail if the behaviour
changed?". It is deliberately gated: exactly one occurrence, a backup, a
restore in ``finally``, and a hash check after restoring. It is still a source
modification, so the skill only uses it after the user explicitly allows it.

Usage:
    python probe_mutation.py --root . \
        --file src/discount.ts --find "0.15" --replace "0.05" \
        --test-file src/discount.test.ts --name "applies the silver discount"

    python probe_mutation.py --root . --file src/x.py --find "return a + b" \
        --replace "return a - b" --test-file tests/test_x.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    DEFAULT_TIMEOUT,
    fail,
    git_file_dirty,
    is_within,
    now_iso,
    relpath,
    sanitize_filename,
    sha256_bytes,
    temp_root,
    truncate,
    write_json,
)

# run_test is a sibling module, not a _common export.
import run_test  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

SCHEMA = "test-value-review/mutation/v1"


def _read_source(path: Path) -> tuple[bytes, str, bool]:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        fail(
            f"Source file is not valid UTF-8: {relpath(path, path.parent)}",
            f"Convert it to UTF-8 before mutation probing ({exc}).",
        )
    return raw, text, bom


def _encode(text: str, bom: bool) -> bytes:
    return (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8")


def _restore(path: Path, raw: bytes, expected_hash: str, backup: Path) -> bool:
    path.write_bytes(raw)
    actual = sha256_bytes(path.read_bytes())
    if actual != expected_hash:
        print(
            f"RESTORE FAILED: {path}\nBackup: {backup}\n"
            f"Expected sha256 {expected_hash}, got {actual}. Restore the backup manually.",
            file=sys.stderr,
        )
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply one temporary source mutation and run one test.")
    parser.add_argument("--root", default=".", help="Project root (default: current directory).")
    parser.add_argument("--file", required=True, help="Production source file to mutate.")
    parser.add_argument("--find", required=True, help="Exact text to replace; must occur exactly once.")
    parser.add_argument("--replace", required=True, help="Replacement text (may be empty).")
    parser.add_argument("--test-file", required=True, help="Test file to run.")
    parser.add_argument("--name", help="Test name or pytest node suffix.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Seconds per run (default: 120).")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow an uncommitted or untracked source file.")
    parser.add_argument("--skip-baseline", action="store_true", help="Skip the pre-mutation test run.")
    parser.add_argument("--dry-run", action="store_true", help="Validate the mutation without writing or running.")
    parser.add_argument("--out", help="Write JSON here (default: system temp directory).")
    parser.add_argument("--stdout", action="store_true", help="Print JSON to stdout and suppress the summary.")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    source = Path(args.file).expanduser()
    if not source.is_absolute():
        source = (root / source).resolve()
    test_file = Path(args.test_file).expanduser()
    if not test_file.is_absolute():
        test_file = (root / test_file).resolve()

    if not root.is_dir():
        fail(f"Project root not found: {root}", "Pass --root with an existing directory.")
    if not source.is_file():
        fail(f"Source file not found: {source}", "Pass --file with an existing file.")
    if not test_file.is_file():
        fail(f"Test file not found: {test_file}", "Pass --test-file with an existing file.")
    if not is_within(source, root):
        fail(f"Source file is outside the project root: {source}", "Keep mutations inside --root.")
    if not is_within(test_file, root):
        fail(f"Test file is outside the project root: {test_file}", "Keep the test inside --root.")
    if not args.find:
        fail("--find must not be empty.", "Choose a concrete piece of behaviour to change.")
    if "\\n" in args.find and "\n" not in args.find:
        # Common mistake: passing a literal \n from a shell.
        args.find = args.find.replace("\\n", "\n")
    if "\\n" in args.replace and "\n" not in args.replace:
        args.replace = args.replace.replace("\\n", "\n")

    raw, text, bom = _read_source(source)
    if len(raw) > 2 * 1024 * 1024:
        fail(f"Source file is too large to mutate safely: {len(raw)} bytes", "Choose a smaller file.")

    occurrences = text.count(args.find)
    if occurrences != 1:
        fail(
            f"--find occurs {occurrences} times in {relpath(source, root)}; expected exactly once.",
            "Include more surrounding context so the mutation targets one place.",
        )
    index = text.index(args.find)
    line = text[:index].count("\n") + 1

    if args.dry_run:
        preview = {
            "schema": SCHEMA,
            "root": str(root),
            "file": relpath(source, root),
            "line": line,
            "find": args.find,
            "replace": args.replace,
            "test_file": relpath(test_file, root),
            "test_name": args.name,
            "verdict": "dry_run",
            "restored": False,
            "restore_verified": True,
        }
        if args.stdout:
            print(json.dumps(preview, ensure_ascii=False, indent=2))
        else:
            print(f"DRY RUN  {relpath(source, root)}:{line}  {args.find!r} -> {args.replace!r}")
            print(f"test: {relpath(test_file, root)}  name: {args.name or '(whole file)'}")
        return 0

    dirty = git_file_dirty(root, source)
    if dirty is True and not args.allow_dirty:
        fail(
            f"{relpath(source, root)} has uncommitted changes.",
            "Commit/stash it, or pass --allow-dirty after confirming a backup still protects you.",
        )
    if dirty is None and not args.allow_dirty:
        fail(
            "The source file is not tracked by git, so a crash could leave the mutation behind.",
            "Pass --allow-dirty to accept that risk; the script still backs up and restores in finally.",
        )

    backup_dir = temp_root() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (
        f"{sanitize_filename(source.stem)}-"
        f"{now_iso().replace(':', '').replace('+', '-')}-"
        f"{uuid.uuid4().hex[:8]}.bak"
    )
    backup.write_bytes(raw)
    original_hash = sha256_bytes(raw)

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "root": str(root),
        "file": relpath(source, root),
        "line": line,
        "find": args.find,
        "replace": args.replace,
        "test_file": relpath(test_file, root),
        "test_name": args.name,
        "backup": str(backup),
        "baseline": None,
        "mutated_run": None,
        "verdict": "not_run",
        "restored": False,
        "restore_verified": True,
    }

    mutated_text = text[:index] + args.replace + text[index + len(args.find) :]
    mutated_raw = _encode(mutated_text, bom)

    if not args.stdout:
        print(f"Temporarily mutating {relpath(source, root)}:{line}: {args.find!r} -> {args.replace!r}")
        print(f"backup: {backup}")
        print("The file is restored in a finally block; do not interrupt the process.")

    baseline_passed = None
    try:
        if not args.skip_baseline:
            baseline = run_test.execute(
                root=root,
                test_file=test_file,
                name=args.name,
                timeout=args.timeout,
            )
            result["baseline"] = _compact_run(baseline)
            baseline_passed = baseline["passed"]
            if not args.stdout:
                print(f"BASELINE {'PASS' if baseline_passed else 'FAIL'}  {baseline.get('summary', '')}")
            if baseline.get("setup_error") or baseline.get("zero_tests"):
                result["verdict"] = "baseline_error"
                result["restored"] = True
                return _finish(result, args)
            if not baseline_passed:
                result["verdict"] = "baseline_failed"
                result["restored"] = True
                return _finish(result, args)
        elif not args.stdout:
            print("BASELINE skipped (--skip-baseline)")

        source.write_bytes(mutated_raw)
        mutated = run_test.execute(
            root=root,
            test_file=test_file,
            name=args.name,
            timeout=args.timeout,
        )
        result["mutated_run"] = _compact_run(mutated)
        if args.skip_baseline:
            result["verdict"] = "survived_unverified_baseline" if mutated["passed"] else "inconclusive"
        elif mutated.get("setup_error") or mutated.get("zero_tests"):
            result["verdict"] = "inconclusive"
        elif mutated["timed_out"]:
            result["verdict"] = "timeout"
        elif mutated["passed"]:
            result["verdict"] = "survived"
        else:
            result["verdict"] = "killed"
    finally:
        restored = _restore(source, raw, original_hash, backup)
        result["restored"] = True
        result["restore_verified"] = restored
        if not restored:
            result["verdict"] = "restore_failed"

    return _finish(result, args)


def _compact_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "runner": run.get("runner"),
        "passed": run.get("passed"),
        "exit_code": run.get("exit_code"),
        "timed_out": run.get("timed_out"),
        "zero_tests": run.get("zero_tests"),
        "setup_error": run.get("setup_error"),
        "duration_ms": run.get("duration_ms"),
        "summary": run.get("summary", ""),
        "stdout_tail": truncate(run.get("stdout_tail", ""), 2000),
        "stderr_tail": truncate(run.get("stderr_tail", ""), 2000),
    }


def _finish(result: dict[str, Any], args: argparse.Namespace) -> int:
    if args.stdout:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["restore_verified"] else 3

    written = write_json(result, Path(args.out).expanduser() if args.out else None, name="mutation")
    verdict = result["verdict"]
    label = {
        "killed": "KILLED (the test caught the change)",
        "survived": "SURVIVED (the test did not catch the change)",
        "survived_unverified_baseline": "SURVIVED (baseline was skipped; unverified)",
        "inconclusive": "INCONCLUSIVE (the run could not be attributed to the mutation)",
        "timeout": "TIMEOUT (inconclusive; the mutated run did not finish)",
        "baseline_failed": "BASELINE FAILED (nothing mutated)",
        "baseline_error": "BASELINE ERROR (runner could not start or found no tests)",
        "dry_run": "DRY RUN",
        "restore_failed": "RESTORE FAILED",
    }.get(verdict, verdict)
    print(f"VERDICT  {label}")
    print(f"restored: {result['restored']}  verified: {result['restore_verified']}")
    print(f"json: {written}")
    return 0 if result["restore_verified"] else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted; if the process was killed before the finally block ran, use the printed backup.", file=sys.stderr)
        raise SystemExit(130)
