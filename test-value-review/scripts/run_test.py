#!/usr/bin/env python3
"""Run one test file or one named test, with a timeout and no watch mode.

The reviewer uses this to confirm a baseline (does the test currently pass?)
before drawing conclusions that depend on runtime behavior. A red test is data,
not a script failure: the process exits 0 when the test command ran, and the
JSON carries ``passed``. Exit 2 means the command could not be built or started.

Usage:
    python run_test.py --root . --file src/foo.test.ts --name "renders the title"
    python run_test.py --root . --file tests/test_discount.py --name test_silver
    python run_test.py --root . --file src/foo.test.ts --command "npx vitest run src/foo.test.ts"
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    DEFAULT_TIMEOUT,
    fail,
    local_bin,
    module_available,
    read_text,
    relpath,
    run_process,
    truncate,
    which,
    write_json,
)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

SCHEMA = "test-value-review/run/v1"


def _js_runner(root: Path, test_file: Path | None = None) -> tuple[str | None, str]:
    if test_file is not None:
        text = read_text(test_file)
        if re.search(r"""['"]vitest['"]""", text) or "vitest." in text:
            return "vitest", "test imports"
        if re.search(r"""['"]@jest/globals['"]""", text) or re.search(r"\bjest\.", text):
            return "jest", "test imports"
        if re.search(r"""['"]@playwright/test['"]""", text):
            return "playwright", "test imports"
        if re.search(r"""['"]cypress['"]""", text):
            return "cypress", "test imports"
        if re.search(r"""['"]mocha['"]""", text):
            return "mocha", "test imports"
    package_json = root / "package.json"
    if package_json.exists():
        text = read_text(package_json)
        for name in ("vitest", "jest", "@playwright/test", "cypress", "mocha"):
            if re.search(rf'"{re.escape(name)}"\s*:', text):
                return name, "package.json"
    for filename, name in (
        ("vitest.config.ts", "vitest"),
        ("vitest.config.js", "vitest"),
        ("jest.config.js", "jest"),
        ("jest.config.ts", "jest"),
        ("playwright.config.ts", "playwright"),
        ("playwright.config.js", "playwright"),
        ("cypress.config.ts", "cypress"),
        ("cypress.config.js", "cypress"),
    ):
        if (root / filename).exists():
            return name, filename
    return None, "not found"


def _js_command(root: Path, test_file: Path, name: str | None) -> tuple[list[str], str, list[str]]:
    runner, _ = _js_runner(root, test_file)
    if runner is None:
        fail(
            "Could not detect a JS/TS test runner.",
            "Pass --command with the project's single-test command, or add vitest/jest/playwright/cypress/mocha to package.json.",
        )
    assert runner is not None
    notes: list[str] = []
    if runner == "@playwright/test":
        runner = "playwright"
    bin_name = runner
    binary = local_bin(root, bin_name)
    if binary is not None:
        prefix: list[str] = [str(binary)]
    else:
        npx = which("npx") or "npx"
        prefix = [npx, "--no-install", bin_name]
        notes.append(f"No local node_modules/.bin/{bin_name}; falling back to npx --no-install.")

    rel = relpath(test_file, root)
    if runner == "vitest":
        args = ["run", rel]
        if name:
            args.extend(["-t", name])
    elif runner == "jest":
        args = [rel, "--runInBand", "--ci", "--coverage=false"]
        if name:
            args.extend(["-t", name])
    elif runner == "playwright":
        args = ["test", rel, "--reporter=line"]
        if name:
            args.extend(["-g", name])
    elif runner == "cypress":
        args = ["run", "--spec", rel]
        notes.append(
            "Cypress component tests usually need `cypress run --component --spec ...`; "
            "pass --command if auto-detection uses the E2E mode."
        )
        if name:
            notes.append("Cypress has no per-test name filter here; the whole spec will run.")
    elif runner == "mocha":
        args = [rel]
        if name:
            args.extend(["--grep", name])
    else:
        fail(f"Unsupported runner: {runner}", "Pass --command explicitly.")
    return prefix + args, runner, notes


def _pytest_available() -> bool:
    return module_available("pytest")


def _python_command(
    root: Path, test_file: Path, name: str | None, dry_run: bool = False
) -> tuple[list[str], str, list[str]]:
    notes: list[str] = []
    if _pytest_available() or dry_run:
        node = relpath(test_file, root)
        if name:
            node = f"{node}::{name}"
        if not _pytest_available():
            notes.append("pytest is not installed for this Python; this command will fail until it is.")
        return (
            [sys.executable, "-m", "pytest", node, "-q", "--no-header", "-p", "no:cacheprovider"],
            "pytest",
            notes,
        )

    text = read_text(test_file)
    if "TestCase" in text or "unittest.TestCase" in text:
        args = [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(test_file.parent),
            "-p",
            test_file.name,
            "-v",
        ]
        if name:
            args.extend(["-k", name.split("::")[-1]])
        notes.append("pytest is unavailable; used unittest discovery.")
        return args, "unittest", notes

    fail(
        "pytest is not available in this Python and the file has no unittest.TestCase.",
        "Install the project's test dependencies, or pass --command with the exact single-test command.",
    )
    raise AssertionError("unreachable")


def build_command(
    root: Path, test_file: Path, name: str | None, command: str | None, dry_run: bool = False
) -> tuple[list[str] | str, str, bool, list[str]]:
    if command:
        return command, "custom", True, ["Custom command supplied; runner detection skipped."]
    suffix = test_file.suffix.lower()
    if suffix == ".py":
        cmd, runner, notes = _python_command(root, test_file, name, dry_run)
        return cmd, runner, False, notes
    if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}:
        cmd, runner, notes = _js_command(root, test_file, name)
        return cmd, runner, False, notes
    fail(f"Unsupported test file type: {test_file.suffix}", "Pass --command explicitly.")
    raise AssertionError("unreachable")


def extract_summary(stdout: str, stderr: str) -> str:
    text = (stdout + "\n" + stderr).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    patterns = [
        r"Tests:\s+.*",
        r"Test Files\s+.*",
        r"Tests\s+\d+.*",
        r"\d+\s+passed.*",
        r"\d+\s+failed.*",
        r"OK\b.*",
        r"FAILED\b.*",
        r"=+ .* =+",
    ]
    for pattern in patterns:
        for line in reversed(lines):
            if re.search(pattern, line):
                return line[:300]
    return lines[-1][:300] if lines else ""


def execute(
    root: Path,
    test_file: Path,
    name: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    command: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    test_file = test_file.resolve()
    if not test_file.is_file():
        fail(f"Test file not found: {test_file}", "Pass --file with an existing test file.")
    if not root.is_dir():
        fail(f"Project root not found: {root}", "Pass --root with an existing directory.")

    cmd, runner, shell, notes = build_command(root, test_file, name, command, dry_run)
    display = cmd if isinstance(cmd, str) else " ".join(shlex.quote(part) for part in cmd)
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "runner": runner,
        "command": cmd,
        "command_display": display,
        "shell": shell,
        "cwd": str(root),
        "test_file": relpath(test_file, root),
        "test_name": name,
        "dry_run": dry_run,
        "notes": notes,
    }
    if dry_run:
        result.update(
            {
                "exit_code": None,
                "timed_out": False,
                "passed": None,
                "zero_tests": None,
                "setup_error": None,
                "duration_ms": 0,
                "summary": "",
                "stdout_tail": "",
                "stderr_tail": "",
            }
        )
        return result

    ran = run_process(cmd, root, timeout=timeout, shell=shell)
    combined = ran["stdout"] + "\n" + ran["stderr"]
    zero_tests = bool(re.search(r"Ran 0 tests", combined))
    setup_error = any(
        re.search(pattern, combined, re.IGNORECASE)
        for pattern in (
            r"npx canceled due to missing packages",
            r"Cannot find (?:module|package)",
            r"ERR_MODULE_NOT_FOUND",
            r"No module named pytest",
            r"command not found",
            r"not recognized as an internal or external command",
            r"npm ERR! missing script",
        )
    )
    if zero_tests:
        result["notes"].append("No tests were discovered (Ran 0 tests); treating this as not passed.")
    if setup_error:
        result["notes"].append("The runner could not start; this is not evidence that the test is weak.")
    result.update(
        {
            "exit_code": ran["exit_code"],
            "timed_out": ran["timed_out"],
            "passed": ran["passed"] and not zero_tests and not setup_error,
            "zero_tests": zero_tests,
            "setup_error": setup_error,
            "duration_ms": ran["duration_ms"],
            "summary": extract_summary(ran["stdout"], ran["stderr"]),
            "stdout_tail": truncate(ran["stdout"]),
            "stderr_tail": truncate(ran["stderr"]),
        }
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one test file or named test.")
    parser.add_argument("--root", default=".", help="Project root (default: current directory).")
    parser.add_argument("--file", required=True, help="Test file, relative to root or absolute.")
    parser.add_argument("--name", help="Test name or pytest node suffix (for example Class::test_x).")
    parser.add_argument("--command", help="Exact command to run instead of auto-detection.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Seconds (default: 120).")
    parser.add_argument("--dry-run", action="store_true", help="Print the detected command without running it.")
    parser.add_argument("--out", help="Write JSON here (default: system temp directory).")
    parser.add_argument("--stdout", action="store_true", help="Print JSON to stdout and suppress the summary.")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    test_file = Path(args.file).expanduser()
    if not test_file.is_absolute():
        test_file = (root / test_file).resolve()

    result = execute(
        root=root,
        test_file=test_file,
        name=args.name,
        timeout=args.timeout,
        command=args.command,
        dry_run=args.dry_run,
    )

    if args.stdout:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    written = write_json(result, Path(args.out).expanduser() if args.out else None, name="run")
    if args.dry_run:
        print(f"DRY RUN  {result['runner']}  {result['command_display']}")
        print(f"json: {written}")
        return 0
    status = "TIMEOUT" if result["timed_out"] else ("PASS" if result["passed"] else "FAIL")
    if result.get("setup_error"):
        status = "SETUP ERROR"
    elif result.get("zero_tests"):
        status = "NO TESTS"
    summary = f"  {result['summary']}" if result["summary"] else ""
    print(f"{status}  {result['test_file']}  ({result['duration_ms']} ms, exit {result['exit_code']}){summary}")
    for note in result["notes"]:
        print(f"note: {note}")
    print(f"json: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
