#!/usr/bin/env python3
"""Inventory JS/TS and Python tests, with heuristic signals.

This script does not decide whether a test is good. It builds a deterministic
worklist: every test unit, its exact line range, simple stats, and a small set
of high-precision signals that deserve a human (or agent) look. The reviewer
must confirm every signal by reading the test and the production code.

Usage:
    python scan_tests.py --root .
    python scan_tests.py --root . --changed --out scan.json
    python scan_tests.py --root . --path src/components --stdout
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    SKIP_DIRS,
    fail,
    git_changed_files,
    git_files,
    is_within,
    line_of,
    line_starts,
    now_iso,
    read_text,
    relpath,
    truncate,
    write_json,
)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

SCHEMA = "test-value-review/scan/v1"

JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}
PY_EXTS = {".py"}
OUT_OF_SCOPE_SUFFIXES = (
    "Test.java",
    "Tests.java",
    "Test.kt",
    "Tests.kt",
    "Test.cs",
    "Tests.cs",
    "_test.go",
    "Test.php",
    "Test.rb",
    "spec.rb",
)

JS_TEST_FILE_RE = re.compile(
    r"(?:\.(?:test|spec|cy)\.(?:js|jsx|ts|tsx|mjs|cjs|mts|cts))$"
    r"|(?:^|/)__tests__/.*\.(?:js|jsx|ts|tsx|mjs|cjs|mts|cts)$",
    re.I,
)
PY_TEST_FILE_RE = re.compile(r"(?:^|/)(?:test_.+\.py|.+_test\.py)$", re.I)
PY_TESTS_DIR_RE = re.compile(r"(?:^|/)tests?/.*\.py$", re.I)

JS_CALL_RE = re.compile(
    r"\b(it|test|specify|describe|xit|xtest|xdescribe)"
    r"((?:\.(?:only|skip|todo|concurrent|sequential|fails|each|describe|shuffle))*)\s*\("
)

JS_IMPORT_FROM_RE = re.compile(
    r"""\bimport\s+(?:type\s+)?(?:[^'"]+?\s+from\s+)?['"]([^'"]+)['"]"""
)
JS_REQUIRE_RE = re.compile(r"""\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)""")
JS_MOCK_RE = re.compile(r"""\b(?:vi|jest)\.mock\s*\(\s*['"]([^'"]+)['"]""")

MOCK_ASSERTION_NAMES = {
    "assert_called",
    "assert_called_once",
    "assert_called_with",
    "assert_called_once_with",
    "assert_any_call",
    "assert_has_calls",
    "assert_not_called",
}

SIGNAL_WEIGHTS = {
    "no_assertion": 100,
    "tautological": 95,
    "assert_in_try": 90,
    "mock_interaction_only": 85,
    "click_spy_only": 80,
    "snapshot_only": 70,
    "mock_echo": 60,
    "conditional_assert": 45,
    "helper_assertion_only": 25,
    "literal_ui_query": 25,
    "no_await_after_action": 15,
    "todo_test": 10,
}


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def _is_skipped_dir(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def walk_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in names:
            files.append(Path(current) / name)
    return files


def discover(root: Path) -> tuple[list[Path], list[Path]]:
    """Return (in-scope test candidates, out-of-scope test files)."""
    candidates = git_files(root)
    if candidates is None:
        candidates = walk_files(root)

    in_scope: list[Path] = []
    out_of_scope: list[Path] = []
    for path in candidates:
        if not path.is_file() or _is_skipped_dir(path.relative_to(root) if is_within(path, root) else path):
            continue
        name = path.name
        suffix = path.suffix.lower()
        if suffix in JS_EXTS and JS_TEST_FILE_RE.search(path.as_posix()):
            in_scope.append(path)
            continue
        if suffix in PY_EXTS and (
            PY_TEST_FILE_RE.search(path.as_posix()) or PY_TESTS_DIR_RE.search(path.as_posix())
        ):
            in_scope.append(path)
            continue
        if name.endswith(OUT_OF_SCOPE_SUFFIXES):
            out_of_scope.append(path)
    return sorted(set(in_scope)), sorted(set(out_of_scope))


def read_project_frameworks(root: Path) -> list[dict[str, str]]:
    frameworks: list[dict[str, str]] = []
    package_json = root / "package.json"
    if package_json.exists():
        text = read_text(package_json)
        for name in ("vitest", "jest", "@playwright/test", "cypress", "mocha", "@storybook/test"):
            if re.search(rf'"{re.escape(name)}"\s*:', text):
                frameworks.append({"name": name, "evidence": "package.json"})
    for filename, name in (
        ("vitest.config.ts", "vitest"),
        ("vitest.config.js", "vitest"),
        ("vitest.config.mts", "vitest"),
        ("jest.config.js", "jest"),
        ("jest.config.ts", "jest"),
        ("playwright.config.ts", "playwright"),
        ("playwright.config.js", "playwright"),
        ("cypress.config.ts", "cypress"),
        ("cypress.config.js", "cypress"),
    ):
        if (root / filename).exists() and not any(item["name"] == name for item in frameworks):
            frameworks.append({"name": name, "evidence": filename})

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = read_text(pyproject)
        if "pytest" in text:
            frameworks.append({"name": "pytest", "evidence": "pyproject.toml"})
    for filename in ("pytest.ini", "tox.ini", "setup.cfg"):
        path = root / filename
        if path.exists() and "pytest" in read_text(path):
            frameworks.append({"name": "pytest", "evidence": filename})
            break
    if (root / "tests" / "__init__.py").exists() and not any(f["name"] == "pytest" for f in frameworks):
        frameworks.append({"name": "unittest", "evidence": "tests/__init__.py"})

    # Deduplicate by name, keeping the first evidence.
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in frameworks:
        if item["name"] not in seen:
            seen.add(item["name"])
            unique.append(item)
    return unique


# ---------------------------------------------------------------------------
# JavaScript / TypeScript masking and parsing
# ---------------------------------------------------------------------------


def _string_end(text: str, start: int, quote: str) -> int:
    """End index (exclusive) of a JS string, or -1 when it is not a string.

    Single- and double-quoted strings may not contain a raw newline. Treating
    an apostrophe in JSX text ("Don't") as a string would swallow code, so a
    quote without a same-line close is left as ordinary text.
    """
    index = start + 1
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == quote:
            return index + 1
        if quote != "`" and char == "\n":
            return -1
        index += 1
    return -1


REGEX_PRECEDERS = set("=(:,[!&|?{};+-*%^~<>")
REGEX_WORDS = {
    "return",
    "case",
    "typeof",
    "instanceof",
    "in",
    "of",
    "new",
    "delete",
    "void",
    "yield",
    "await",
    "else",
    "do",
}


def _looks_like_regex(text: str, index: int) -> bool:
    previous = index - 1
    while previous >= 0 and text[previous].isspace():
        previous -= 1
    if previous < 0:
        return True
    if text[previous] in REGEX_PRECEDERS:
        return True
    end = previous + 1
    start = previous
    while start >= 0 and (text[start].isalnum() or text[start] in "_$"):
        start -= 1
    return text[start + 1 : end] in REGEX_WORDS


def _regex_end(text: str, start: int) -> int:
    index = start + 1
    in_class = False
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "[":
            in_class = True
        elif char == "]":
            in_class = False
        elif char == "/" and not in_class:
            return index + 1
        elif char == "\n":
            return -1
        index += 1
    return -1


def mask_js(text: str) -> str:
    """Blank comments, strings and regex literals while preserving offsets."""
    chars = list(text)
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "/" and index + 1 < length and text[index + 1] == "/":
            end = text.find("\n", index + 2)
            if end == -1:
                end = length
            for pos in range(index, end):
                chars[pos] = " "
            index = end
            continue
        if char == "/" and index + 1 < length and text[index + 1] == "*":
            end = text.find("*/", index + 2)
            end = length if end == -1 else end + 2
            for pos in range(index, end):
                if text[pos] != "\n":
                    chars[pos] = " "
            index = end
            continue
        if char == "/" and _looks_like_regex(text, index):
            end = _regex_end(text, index)
            if end != -1:
                for pos in range(index, end):
                    if text[pos] != "\n":
                        chars[pos] = " "
                index = end
                continue
        if char in "'\"`":
            end = _string_end(text, index, char)
            if end == -1:
                index += 1
                continue
            for pos in range(index, end):
                if text[pos] != "\n":
                    chars[pos] = " "
            index = end
            continue
        index += 1
    return "".join(chars)


def match_pair(masked: str, open_index: int, open_char: str, close_char: str) -> int | None:
    if open_index < 0 or open_index >= len(masked) or masked[open_index] != open_char:
        return None
    depth = 0
    for index in range(open_index, len(masked)):
        char = masked[index]
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
    return None


def find_top_level_comma(masked: str, start: int, end: int) -> int:
    depth = 0
    for index in range(start, end):
        char = masked[index]
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            return index
    return -1


def find_callback_body(masked: str, start: int, end: int) -> tuple[int, int] | None:
    segment = masked[start:end]
    arrow = segment.find("=>")
    function = re.search(r"\bfunction\b", segment)
    if arrow == -1 and function is None:
        return None
    if arrow != -1 and (function is None or arrow < function.start()):
        position = start + arrow + 2
        while position < end and masked[position].isspace():
            position += 1
        if position < end and masked[position] == "{":
            close = match_pair(masked, position, "{", "}")
            if close is None:
                return None
            return position + 1, close
        return position, end
    brace = masked.find("{", start + function.start(), end)  # type: ignore[union-attr]
    if brace == -1:
        return None
    close = match_pair(masked, brace, "{", "}")
    if close is None:
        return None
    return brace + 1, close


def extract_name(text: str, start: int, end: int) -> str:
    raw = text[start:end].strip().rstrip(",").strip()
    if not raw:
        return "<unnamed>"
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"`":
        inner = raw[1:-1].strip()
        return inner.replace("\\n", " ") or "<unnamed>"
    return raw[:160]


# ---------------------------------------------------------------------------
# JavaScript / TypeScript stats and signals
# ---------------------------------------------------------------------------

EXPECT_RE = re.compile(r"\bexpect(?:\.(?:soft|poll))?\s*\(")
HELPER_ASSERT_RE = re.compile(r"\b(?:assert|verify|check|ensure)[A-Za-z0-9_]*\s*\(")
MOCK_ASSERT_RE = re.compile(
    r"\.(?:toHaveBeenCalled|toBeCalled|toHaveBeenNthCalledWith|toHaveBeenLastCalledWith"
    r"|toHaveBeenCalledTimes|toHaveBeenCalledWith)\b"
)
SNAPSHOT_RE = re.compile(r"\.(?:toMatchSnapshot|toMatchInlineSnapshot|toMatchFileSnapshot)\b")
MOCK_DEF_RE = re.compile(r"\b(?:jest|vi)\.fn\s*\(|\b(?:jest|vi)\.spyOn\s*\(|\.mockReturnValue\s*\(|\.mockResolvedValue\s*\(")
MOCK_RETURN_RE = re.compile(
    r"\.(?:mockReturnValue|mockResolvedValue|mockReturnValueOnce|mockResolvedValueOnce)"
    r"\(\s*([^()]*?)\s*\)"
)
USER_EVENT_RE = re.compile(r"\b(?:userEvent|fireEvent)\.")
RENDER_RE = re.compile(r"\b(?:render|renderHook|mount|shallow)\s*\(")
LITERAL_QUERY_RE = re.compile(
    r"\b(?:get|find|query)(?:ByText|ByLabelText|ByPlaceholderText|ByRole|ByTestId|ByTitle|ByDisplayValue)\s*\(\s*['\"`]"
)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    return ""


def _normalise_expression(value: str) -> str:
    return re.sub(r"\s+", "", value).strip(",")


def _extract_call_args(masked: str, open_index: int) -> tuple[str, int] | None:
    close = match_pair(masked, open_index, "(", ")")
    if close is None:
        return None
    return masked[open_index + 1 : close], close


def empty_js_stats() -> dict[str, Any]:
    return {
        "assertions": 0,
        "total_assertions": 0,
        "helper_assertions": 0,
        "mock_assertions": 0,
        "snapshots": 0,
        "mocks": 0,
        "user_events": 0,
        "awaits": 0,
        "conditional_assertions": False,
        "literal_queries": 0,
    }


def analyse_js_body(
    body: str, masked_body: str, ui: bool, body_start_line: int = 1
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    body_lines = line_starts(body)

    def at_line(offset: int) -> int:
        return body_start_line + line_of(body_lines, offset) - 1

    signal_line = body_start_line
    stats: dict[str, Any] = {
        "assertions": 0,
        "helper_assertions": 0,
        "mock_assertions": 0,
        "snapshots": 0,
        "mocks": 0,
        "user_events": 0,
        "awaits": 0,
        "conditional_assertions": False,
        "literal_queries": 0,
    }
    signals: list[dict[str, Any]] = []

    expect_calls: list[dict[str, Any]] = []
    for match in EXPECT_RE.finditer(masked_body):
        open_index = match.end() - 1
        parsed = _extract_call_args(masked_body, open_index)
        if parsed is None:
            continue
        args, close = parsed
        after = masked_body[close + 1 :]
        matcher_match = re.match(r"\s*\.\s*(?:not\s*\.\s*)?(\w+)\s*\(", after)
        if matcher_match is None:
            expect_calls.append({"args": args, "matcher": None, "matcher_args": "", "line": at_line(match.start())})
            continue
        matcher_name = matcher_match.group(1)
        matcher_open = close + 1 + matcher_match.end() - 1
        matcher_parsed = _extract_call_args(masked_body, matcher_open)
        matcher_args = matcher_parsed[0] if matcher_parsed else ""
        expect_calls.append(
            {
                "args": args,
                "matcher": matcher_name,
                "matcher_args": matcher_args,
                "line": at_line(match.start()),
            }
        )

    stats["assertions"] = len(expect_calls)
    stats["mock_assertions"] = sum(
        1 for call in expect_calls if call["matcher"] and MOCK_ASSERT_RE.search(f".{call['matcher']}")
    )
    stats["snapshots"] = sum(
        1 for call in expect_calls if call["matcher"] and SNAPSHOT_RE.search(f".{call['matcher']}")
    )
    stats["helper_assertions"] = len(HELPER_ASSERT_RE.findall(masked_body))
    stats["total_assertions"] = stats["assertions"] + stats["helper_assertions"]
    stats["mocks"] = len(MOCK_DEF_RE.findall(masked_body))
    stats["user_events"] = len(USER_EVENT_RE.findall(masked_body))
    stats["awaits"] = len(re.findall(r"\bawait\b", masked_body))
    stats["literal_queries"] = len(LITERAL_QUERY_RE.findall(body))

    # Tautology: expect(X).toBe/toEqual(X)
    for call in expect_calls:
        if call["matcher"] in {"toBe", "toEqual", "toStrictEqual", "not.toBe"}:
            if _normalise_expression(call["args"]) == _normalise_expression(call["matcher_args"]) and len(
                _normalise_expression(call["args"])
            ) > 0:
                signals.append(
                    {
                        "code": "tautological",
                        "line": call["line"],
                        "confidence": "high",
                        "snippet": f"expect({call['args'][:80]}).{call['matcher']}({call['matcher_args'][:80]})",
                        "note": "两边的表达式相同；实现怎么错，测试都会绿。",
                    }
                )
                break

    # Self-reference: expected = f(x); expect(f(x)).toBe(expected)
    assignments = re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;]+);", masked_body)
    normalised_assignments = {name: _normalise_expression(value) for name, value in assignments}
    for call in expect_calls:
        if call["matcher"] not in {"toBe", "toEqual", "toStrictEqual"}:
            continue
        arg = _normalise_expression(call["args"])
        expected = _normalise_expression(call["matcher_args"])
        for name, value in normalised_assignments.items():
            if expected == name and value and value in arg:
                signals.append(
                    {
                        "code": "mock_echo" if "mock" in value.lower() else "tautological",
                        "line": call["line"],
                        "confidence": "medium",
                        "snippet": f"expect({call['args'][:60]}).{call['matcher']}({name})",
                        "note": "期望值来自被测表达式或 mock 的返回值，双方可能同错。",
                    }
                )
                break

    mock_literals: set[str] = set()
    for match in MOCK_RETURN_RE.finditer(masked_body):
        value = match.group(1).strip()
        if re.fullmatch(
            r"""(?:'[^']*'|"[^"]*"|`[^`]*`|-?\d+(?:\.\d+)?|true|false|null|undefined)""",
            value,
        ):
            mock_literals.add(_normalise_expression(value))
    if mock_literals:
        for call in expect_calls:
            if call["matcher"] not in {"toBe", "toEqual", "toStrictEqual"}:
                continue
            if _normalise_expression(call["matcher_args"]) in mock_literals:
                signals.append(
                    {
                        "code": "mock_echo",
                        "line": call["line"],
                        "confidence": "medium",
                        "snippet": f"expect({call['args'][:60]}).{call['matcher']}({call['matcher_args'][:60]})",
                        "note": "断言值等于 mock 的预设返回值；可能只是在验证 mock 自己。",
                    }
                )
                break

    if stats["assertions"] == 0 and stats["helper_assertions"] == 0:
        signals.append(
            {
                "code": "no_assertion",
                "line": signal_line,
                "confidence": "high",
                "snippet": "",
                "note": "没有找到 expect/assert；确认是否漏掉了自定义断言 helper。",
            }
        )
    elif stats["assertions"] == 0 and stats["helper_assertions"] > 0:
        signals.append(
            {
                "code": "helper_assertion_only",
                "line": signal_line,
                "confidence": "low",
                "snippet": "",
                "note": "只调用了断言 helper；确认 helper 真的会失败，而不是吞错。",
            }
        )

    if (
        stats["assertions"] > 0
        and stats["mock_assertions"] == stats["assertions"]
        and stats["snapshots"] == 0
        and stats["user_events"] == 0
    ):
        signals.append(
            {
                "code": "mock_interaction_only",
                "line": signal_line,
                "confidence": "high",
                "snippet": "",
                "note": "唯一断言是 mock 被调用；除非交互本身就是契约，否则没有验证结果。",
            }
        )

    if stats["assertions"] > 0 and stats["snapshots"] == stats["assertions"]:
        signals.append(
            {
                "code": "snapshot_only",
                "line": signal_line,
                "confidence": "high",
                "snippet": "",
                "note": "只有快照断言；--updateSnapshot 会把它变成橡皮图章。",
            }
        )

    if stats["user_events"] > 0 and stats["assertions"] > 0 and stats["mock_assertions"] == stats["assertions"]:
        signals.append(
            {
                "code": "click_spy_only",
                "line": signal_line,
                "confidence": "high",
                "snippet": "",
                "note": "点击后只断言 spy 被调用；没有验证用户可见结果。",
            }
        )

    if re.search(r"\bif\s*\(", masked_body) and stats["assertions"] > 0:
        signals.append(
            {
                "code": "conditional_assert",
                "line": signal_line,
                "confidence": "medium",
                "snippet": "",
                "note": "断言在条件分支里；某些路径可能根本没执行。",
            }
        )

    for try_match in re.finditer(r"\btry\s*\{", masked_body):
        try_open = try_match.end() - 1
        try_close = match_pair(masked_body, try_open, "{", "}")
        if try_close is None:
            continue
        catch_match = re.search(r"\bcatch\b[^{]*\{", masked_body[try_close + 1 :])
        if catch_match is None:
            continue
        catch_open = try_close + 1 + catch_match.end() - 1
        catch_close = match_pair(masked_body, catch_open, "{", "}")
        if catch_close is None:
            continue
        catch_body = masked_body[catch_open + 1 : catch_close]
        if not re.search(r"\b(?:throw|expect|assert|fail)\b", catch_body):
            signals.append(
                {
                    "code": "assert_in_try",
                    "line": at_line(try_match.start()),
                    "confidence": "high",
                    "snippet": truncate(catch_body.strip(), 120),
                    "note": "try/catch 吞掉了失败；测试可能永远不会红。",
                }
            )
            break

    if ui and stats["literal_queries"] > 0:
        signals.append(
            {
                "code": "literal_ui_query",
                "line": signal_line,
                "confidence": "low",
                "snippet": "",
                "note": "UI 查询用了字面量；确认它是契约文案，且是否有第二个值验证绑定。",
            }
        )

    direct_events = len(re.findall(r"\buserEvent\.", masked_body))
    awaited_events = len(
        re.findall(
            r"\bawait\s+[\w.$]+\.(?:click|type|dblClick|tripleClick|hover|selectOptions|upload|tab|keyboard)\s*\(",
            masked_body,
        )
    )
    if ui and direct_events > awaited_events:
        signals.append(
            {
                "code": "no_await_after_action",
                "line": signal_line,
                "confidence": "low",
                "snippet": "",
                "note": "userEvent 调用没有 await；同步断言可能读到旧状态。",
            }
        )

    return stats, _dedupe_signals(signals)


# ---------------------------------------------------------------------------
# Python parsing, stats and signals
# ---------------------------------------------------------------------------


def _py_call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _py_call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _py_call_name(node.func)
    return ""


def _is_test_class(node: ast.ClassDef) -> bool:
    if node.name.startswith("Test"):
        return True
    return any(_py_call_name(base).endswith("TestCase") for base in node.bases)


def _catches_assertion_error(handler: ast.ExceptHandler) -> bool:
    """Whether an except handler can swallow an AssertionError.

    A narrow ``except ValueError`` does not catch a failed ``assert``; only a
    bare except, Exception/BaseException, or AssertionError itself does.
    """
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name):
        names = [handler.type.id]
    elif isinstance(handler.type, ast.Tuple):
        names = [_py_call_name(element) for element in handler.type.elts]
    else:
        names = [_py_call_name(handler.type)]
    return any(name in {"Exception", "BaseException", "AssertionError"} for name in names)


def analyse_py_node(node: ast.AST) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    asserts = [item for item in ast.walk(node) if isinstance(item, ast.Assert)]
    calls = [item for item in ast.walk(node) if isinstance(item, ast.Call)]
    with_items = [item for item in ast.walk(node) if isinstance(item, ast.With)] + [
        item for item in ast.walk(node) if isinstance(item, ast.AsyncWith)
    ]

    raises_contexts: list[ast.Call] = []
    for item in with_items:
        for entry in item.items:
            context = entry.context_expr
            if isinstance(context, ast.Call):
                name = _py_call_name(context.func)
                if name.endswith("raises") or name.endswith("assertRaises"):
                    raises_contexts.append(context)
    raises_ids = {id(call) for call in raises_contexts}
    raises_calls = [
        call
        for call in calls
        if id(call) not in raises_ids
        and (_py_call_name(call.func) == "raises" or _py_call_name(call.func).endswith(".raises"))
    ]

    direct_assertion_calls: list[ast.Call] = []
    helper_calls: list[ast.Call] = []
    mock_assertions: list[ast.Call] = []
    snapshots: list[ast.Call] = []
    for call in calls:
        name = _py_call_name(call.func)
        short = name.split(".")[-1]
        if short in MOCK_ASSERTION_NAMES:
            mock_assertions.append(call)
        elif short in {"assert_match", "assert_snapshot", "assert_snapshot_match"}:
            snapshots.append(call)
        elif name.startswith(("self.", "cls.")) and short.startswith("assert") and id(call) not in raises_ids:
            direct_assertion_calls.append(call)
        elif re.match(r"^(?:assert_|expect_|verify_|check_|ensure_)", short):
            helper_calls.append(call)

    total = (
        len(asserts)
        + len(direct_assertion_calls)
        + len(helper_calls)
        + len(mock_assertions)
        + len(raises_contexts)
        + len(raises_calls)
        + len(snapshots)
    )
    stats: dict[str, Any] = {
        "assertions": total,
        "total_assertions": total,
        "direct_assertions": len(direct_assertion_calls),
        "helper_assertions": len(helper_calls),
        "mock_assertions": len(mock_assertions),
        "snapshots": len(snapshots),
        "mocks": 0,
        "raises": len(raises_contexts),
        "conditional_assertions": False,
        "literal_queries": 0,
    }
    for call in calls:
        name = _py_call_name(call.func).split(".")[-1]
        if name in {"Mock", "MagicMock", "patch", "AsyncMock"}:
            stats["mocks"] += 1

    signals: list[dict[str, Any]] = []
    signal_line = getattr(node, "lineno", 1)

    for statement in asserts:
        if isinstance(statement.test, ast.Constant) and statement.test.value is True:
            signals.append(
                {
                    "code": "tautological",
                    "line": statement.lineno,
                    "confidence": "high",
                    "snippet": "assert True",
                    "note": "断言的是常量 True；无论实现如何都通过。",
                }
            )
        if isinstance(statement.test, ast.Compare) and len(statement.test.ops) == 1 and isinstance(
            statement.test.ops[0], ast.Eq
        ):
            left = ast.dump(statement.test.left)
            right = ast.dump(statement.test.comparators[0])
            if left == right:
                signals.append(
                    {
                        "code": "tautological",
                        "line": statement.lineno,
                        "confidence": "high",
                        "snippet": ast.unparse(statement.test) if hasattr(ast, "unparse") else "",
                        "note": "断言两边是同一个表达式；实现错了也会通过。",
                    }
                )

    assignments: dict[str, str] = {}
    for item in ast.walk(node):
        if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
            if isinstance(item.value, ast.Call):
                assignments[item.targets[0].id] = ast.dump(item.value)
    for statement in asserts:
        if not isinstance(statement.test, ast.Compare) or len(statement.test.ops) != 1:
            continue
        if not isinstance(statement.test.ops[0], ast.Eq):
            continue
        sides = [statement.test.left, statement.test.comparators[0]]
        for index, side in enumerate(sides):
            other = sides[1 - index]
            if isinstance(side, ast.Name) and side.id in assignments:
                if assignments[side.id] in ast.dump(other):
                    signals.append(
                        {
                            "code": "tautological",
                            "line": statement.lineno,
                            "confidence": "medium",
                            "snippet": ast.unparse(statement.test) if hasattr(ast, "unparse") else "",
                            "note": "期望值来自被测调用本身，双方可能同错。",
                        }
                    )

    return_value_constants: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Attribute):
            if item.targets[0].attr == "return_value" and isinstance(item.value, ast.Constant):
                return_value_constants.add(repr(item.value.value))
    for statement in asserts:
        if isinstance(statement.test, ast.Compare) and len(statement.test.ops) == 1 and isinstance(
            statement.test.ops[0], ast.Eq
        ):
            sides = [statement.test.left, statement.test.comparators[0]]
            for side in sides:
                if isinstance(side, ast.Constant) and repr(side.value) in return_value_constants:
                    signals.append(
                        {
                            "code": "mock_echo",
                            "line": statement.lineno,
                            "confidence": "medium",
                            "snippet": ast.unparse(statement.test) if hasattr(ast, "unparse") else "",
                            "note": "断言值等于 mock 的预设返回值；可能只是在验证 mock 自己。",
                        }
                    )
                    break

    for call in [*direct_assertion_calls, *helper_calls]:
        short = _py_call_name(call.func).split(".")[-1]
        if short in {"assertTrue", "assertFalse"} and call.args:
            value = call.args[0]
            always_passes = (
                isinstance(value, ast.Constant)
                and isinstance(value.value, bool)
                and ((short == "assertTrue" and value.value is True) or (short == "assertFalse" and value.value is False))
            )
            if always_passes:
                signals.append(
                    {
                        "code": "tautological",
                        "line": call.lineno,
                        "confidence": "high",
                        "snippet": f"{short}({value.value})",
                        "note": "断言的是常量布尔值；无论实现如何都通过。",
                    }
                )
                break

    if total == 0:
        signals.append(
            {
                "code": "no_assertion",
                "line": signal_line,
                "confidence": "high",
                "snippet": "",
                "note": "没有 assert、pytest.raises 或断言 helper；测试只执行了代码。",
            }
        )
    elif (
        len(asserts) == 0
        and len(direct_assertion_calls) == 0
        and raises_contexts == []
        and len(helper_calls) > 0
    ):
        signals.append(
            {
                "code": "helper_assertion_only",
                "line": signal_line,
                "confidence": "low",
                "snippet": "",
                "note": "只调用了断言 helper；确认 helper 真的会失败。",
            }
        )

    if total > 0 and len(mock_assertions) == total and len(snapshots) == 0:
        signals.append(
            {
                "code": "mock_interaction_only",
                "line": signal_line,
                "confidence": "high",
                "snippet": "",
                "note": "唯一断言是 mock 被调用；没有验证结果。",
            }
        )
    if total > 0 and len(snapshots) == total:
        signals.append(
            {
                "code": "snapshot_only",
                "line": signal_line,
                "confidence": "high",
                "snippet": "",
                "note": "只有快照断言。",
            }
        )

    for item in ast.walk(node):
        if isinstance(item, ast.If):
            if any(isinstance(child, ast.Assert) for child in ast.walk(item)):
                stats["conditional_assertions"] = True
                signals.append(
                    {
                        "code": "conditional_assert",
                        "line": item.lineno,
                        "confidence": "medium",
                        "snippet": "",
                        "note": "断言在条件分支里；某些路径可能没执行。",
                    }
                )
                break

    for item in ast.walk(node):
        if isinstance(item, ast.Try):
            has_assert = any(isinstance(child, ast.Assert) for child in ast.walk(item))
            if not has_assert:
                continue
            swallows = False
            for handler in item.handlers:
                if not _catches_assertion_error(handler):
                    continue
                body = handler.body
                if any(isinstance(child, (ast.Raise, ast.Assert)) for child in ast.walk(handler)):
                    continue
                if any(
                    isinstance(child, ast.Expr) and isinstance(child.value, ast.Call)
                    and _py_call_name(child.value.func).split(".")[-1]
                    not in {"print", "warning", "warn", "info", "debug", "error", "exception", "critical", "log"}
                    for child in body
                ):
                    continue
                swallows = True
                break
            if swallows:
                signals.append(
                    {
                        "code": "assert_in_try",
                        "line": item.lineno,
                        "confidence": "high",
                        "snippet": "",
                        "note": "try/except 捕获了 AssertionError 却没有重新失败；测试可能永远不会红。",
                    }
                )
                break

    return stats, _dedupe_signals(signals)


def _dedupe_signals(signals: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int]] = set()
    result: list[dict[str, Any]] = []
    for signal in signals:
        key = (signal["code"], int(signal.get("line") or 0))
        if key in seen:
            continue
        seen.add(key)
        result.append(signal)
    return result


# ---------------------------------------------------------------------------
# Source mapping
# ---------------------------------------------------------------------------


def resolve_js_import(test_path: Path, spec: str, root: Path) -> Path | None:
    if spec.startswith("."):
        base = (test_path.parent / spec).resolve()
    elif spec.startswith("/"):
        base = (root / spec.lstrip("/")).resolve()
    else:
        return None
    candidates = [base]
    for extension in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".svelte"):
        candidates.append(base.with_suffix(extension))
    for extension in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".svelte"):
        candidates.append(base / ("index" + extension))
    for candidate in candidates:
        if candidate.is_file() and is_within(candidate, root):
            return candidate.resolve()
    return None


def resolve_py_import(test_path: Path, module: str | None, level: int, root: Path) -> Path | None:
    base = test_path.parent
    for _ in range(max(level - 1, 0)):
        base = base.parent
    parts = module.split(".") if module else []
    if level > 0:
        targets = [base.joinpath(*parts)]
    else:
        # pytest puts the test file's directory on sys.path; try both the
        # project root and that sibling directory for absolute imports.
        targets = [root.joinpath(*parts), test_path.parent.joinpath(*parts)]
    for target in targets:
        candidates = []
        if target.suffix == ".py":
            candidates.append(target)
        else:
            candidates.append(target.with_suffix(".py"))
            candidates.append(target / "__init__.py")
        for candidate in candidates:
            if candidate.is_file() and is_within(candidate, root):
                return candidate.resolve()
    return None


def collect_sources(
    path: Path, text: str, language: str, root: Path
) -> tuple[list[str], list[str], list[str], list[str]]:
    sources: list[str] = []
    unresolved: list[str] = []
    mocked: list[str] = []

    if language == "js":
        imports = set(JS_IMPORT_FROM_RE.findall(text)) | set(JS_REQUIRE_RE.findall(text))
        mocked = sorted(set(JS_MOCK_RE.findall(text)))
        for spec in sorted(imports):
            if spec.startswith(".") or spec.startswith("/"):
                resolved = resolve_js_import(path, spec, root)
                if resolved and resolved != path.resolve():
                    sources.append(relpath(resolved, root))
                elif resolved is None:
                    unresolved.append(spec)
    else:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return [], [], [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                resolved = resolve_py_import(path, node.module, node.level, root)
                if resolved and resolved != path.resolve():
                    sources.append(relpath(resolved, root))
                elif resolved is None and node.level > 0:
                    unresolved.append(node.module or ".")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = resolve_py_import(path, alias.name, 0, root)
                    if resolved and resolved != path.resolve():
                        sources.append(relpath(resolved, root))

    return sorted(set(sources)), sorted(set(unresolved)), sorted(set(mocked)), []


def detect_file_framework(text: str, language: str) -> str | None:
    if language == "js":
        if re.search(r"""['"]vitest['"]""", text) or "vitest." in text:
            return "vitest"
        if re.search(r"""['"]@jest/globals['"]""", text) or re.search(r"\bjest\.", text):
            return "jest"
        if re.search(r"""['"]@playwright/test['"]""", text):
            return "playwright"
        if re.search(r"""['"]cypress['"]""", text):
            return "cypress"
        if re.search(r"""['"]mocha['"]""", text):
            return "mocha"
        return None
    if re.search(r"^\s*import\s+pytest\b", text, re.M) or re.search(r"\bpytest\.", text):
        return "pytest"
    if re.search(r"^\s*import\s+unittest\b", text, re.M) or "TestCase" in text:
        return "unittest"
    if "TestCase" not in text and re.search(r"^\s*(?:async\s+)?def\s+test\w*\s*\(", text, re.M):
        return "pytest"
    return None


def detect_ui(path: Path, text: str, language: str) -> bool:
    if language != "js":
        return False
    if path.suffix.lower() in {".tsx", ".jsx"}:
        return True
    if re.search(r"""['"](?:react|react-dom|@testing-library/[^'"]+|@vue/test-utils|enzyme|svelte)['"]""", text):
        return True
    return bool(re.search(r"\b(?:screen\.|userEvent\.|fireEvent\.|renderHook\s*\()", text))


# ---------------------------------------------------------------------------
# Unit construction
# ---------------------------------------------------------------------------


def _unit_dict(
    *,
    path: Path,
    root: Path,
    start_line: int,
    end_line: int,
    name: str,
    suite: list[str],
    language: str,
    framework: str | None,
    kind: str,
    skipped: bool,
    todo: bool,
    body: str,
    stats: dict[str, Any],
    signals: list[dict[str, Any]],
    sources: list[str],
    unresolved: list[str],
    mocked: list[str],
) -> dict[str, Any]:
    score = 0
    for signal in signals:
        score = max(score, SIGNAL_WEIGHTS.get(signal["code"], 0))
    score += max(0, len(signals) - 1) * 2
    return {
        "id": "",
        "file": relpath(path, root),
        "start_line": start_line,
        "end_line": end_line,
        "name": name,
        "suite": suite,
        "language": language,
        "framework": framework,
        "kind": kind,
        "skipped": skipped,
        "todo": todo,
        "body_analyzed": True,
        "stats": stats,
        "signals": signals,
        "suspect_score": score,
        "sources": sources,
        "unresolved_sources": unresolved,
        "mocked_modules": mocked,
        "body_preview": truncate(body.strip(), 500),
    }


def parse_js_file(
    path: Path, text: str, root: Path, framework: str | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    masked = mask_js(text)
    starts = line_starts(text)
    ui = detect_ui(path, text, "js")
    sources, unresolved, mocked, _ = collect_sources(path, text, "js", root)
    units: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def build(
        match: re.Match[str],
        open_index: int,
        close_index: int,
        name: str,
        suite: list[str],
        skipped: bool,
        todo: bool,
    ) -> None:
        comma = find_top_level_comma(masked, open_index + 1, close_index)
        body_range = None if todo else find_callback_body(
            masked, comma + 1 if comma != -1 else close_index, close_index
        )
        body_analyzed = body_range is not None
        if body_range is None:
            body = ""
            masked_body = ""
            if not todo:
                warnings.append(
                    {
                        "file": relpath(path, root),
                        "line": line_of(starts, match.start()),
                        "message": f"测试 '{name}' 的回调不是内联函数；未分析函数体，请手工阅读。",
                    }
                )
        else:
            body = text[body_range[0] : body_range[1]]
            masked_body = masked[body_range[0] : body_range[1]]
        body_start_line = (
            line_of(starts, body_range[0]) if body_range is not None else line_of(starts, match.start())
        )
        if body_analyzed:
            stats, signals = analyse_js_body(body, masked_body, ui, body_start_line)
        else:
            stats, signals = empty_js_stats(), []
        unit_kind = "ui" if ui or RENDER_RE.search(masked_body) else "unit"
        units.append(
            _unit_dict(
                path=path,
                root=root,
                start_line=line_of(starts, match.start()),
                end_line=line_of(starts, close_index),
                name=name,
                suite=suite,
                language="js",
                framework=framework,
                kind=unit_kind,
                skipped=skipped,
                todo=todo,
                body=body,
                stats=stats,
                signals=signals,
                sources=sources,
                unresolved=unresolved,
                mocked=mocked,
            )
        )
        units[-1]["body_analyzed"] = body_analyzed
        if todo:
            units[-1]["signals"].append(
                {
                    "code": "todo_test",
                    "line": line_of(starts, match.start()),
                    "confidence": "medium",
                    "snippet": "",
                    "note": "test.todo 不执行，不提供任何保护。",
                }
            )

    def parse_range(start: int, end: int, suite: list[str], skipped_context: bool) -> None:
        index = start
        while index < end:
            match = JS_CALL_RE.search(masked, index, end)
            if match is None:
                break
            prefix = masked[max(0, match.start() - 16) : match.start()]
            if re.search(r"\bfunction\s*$", prefix):
                # A local helper declaration named `test(...)`, not a test call.
                index = match.end()
                continue
            base = match.group(1)
            suffixes = match.group(2) or ""
            open_index = match.end() - 1

            is_each = "each" in suffixes
            if is_each:
                each_close = match_pair(masked, open_index, "(", ")")
                if each_close is None:
                    warnings.append(
                        {
                            "file": relpath(path, root),
                            "line": line_of(starts, match.start()),
                            "message": "无法解析 .each 调用的数据表；已跳过该测试。",
                        }
                    )
                    index = open_index + 1
                    continue
                cursor = each_close + 1
                while cursor < end and masked[cursor].isspace():
                    cursor += 1
                if cursor < end and masked[cursor] == "(":
                    open_index = cursor
                else:
                    warnings.append(
                        {
                            "file": relpath(path, root),
                            "line": line_of(starts, match.start()),
                            "message": "无法定位 .each 的实际测试调用；已跳过。",
                        }
                    )
                    index = each_close + 1
                    continue

            close_index = match_pair(masked, open_index, "(", ")")
            if close_index is None:
                warnings.append(
                    {
                        "file": relpath(path, root),
                        "line": line_of(starts, match.start()),
                        "message": "括号不匹配，无法确定测试边界；已跳过。",
                    }
                )
                index = open_index + 1
                continue

            comma = find_top_level_comma(masked, open_index + 1, close_index)
            name_end = comma if comma != -1 else close_index
            name = extract_name(text, open_index + 1, name_end)
            is_suite = base in {"describe", "xdescribe"} or "describe" in suffixes
            skipped = skipped_context or base.startswith("x") or "skip" in suffixes
            todo = "todo" in suffixes

            if is_suite:
                body = find_callback_body(
                    masked, comma + 1 if comma != -1 else close_index, close_index
                )
                if body is not None:
                    parse_range(body[0], body[1], suite + [name], skipped)
                else:
                    warnings.append(
                        {
                            "file": relpath(path, root),
                            "line": line_of(starts, match.start()),
                            "message": f"describe '{name}' 没有内联回调，嵌套测试未扫描。",
                        }
                    )
            else:
                build(match, open_index, close_index, name, suite, skipped, todo)
            index = close_index + 1

    parse_range(0, len(masked), [], False)
    return units, warnings


def parse_py_file(
    path: Path, text: str, root: Path, framework: str | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [], [
            {
                "file": relpath(path, root),
                "line": exc.lineno or 0,
                "message": f"Python 语法错误：{exc.msg}",
            }
        ]

    sources, unresolved, mocked, _ = collect_sources(path, text, "python", root)
    units: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[str] = []
            self.class_depth = 0

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_depth += 1
            try:
                if _is_test_class(node):
                    self.class_stack.append(node.name)
                    self.generic_visit(node)
                    self.class_stack.pop()
                else:
                    self.generic_visit(node)
            finally:
                self.class_depth -= 1

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._handle(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._handle(node)

        def _handle(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            in_test_class = bool(self.class_stack)
            at_module_level = self.class_depth == 0
            is_test = node.name.startswith("test") and (in_test_class or at_module_level)
            if is_test:
                decorators = [decorator.lineno for decorator in node.decorator_list if hasattr(decorator, "lineno")]
                start_line = min([node.lineno, *decorators]) if decorators else node.lineno
                body = ast.get_source_segment(text, node) or ""
                stats, signals = analyse_py_node(node)
                units.append(
                    _unit_dict(
                        path=path,
                        root=root,
                        start_line=start_line,
                        end_line=getattr(node, "end_lineno", node.lineno) or node.lineno,
                        name=node.name,
                        suite=list(self.class_stack),
                        language="python",
                        framework=framework,
                        kind="unit",
                        skipped=False,
                        todo=False,
                        body=body,
                        stats=stats,
                        signals=signals,
                        sources=sources,
                        unresolved=unresolved,
                        mocked=mocked,
                    )
                )
                return
            self.generic_visit(node)

    Visitor().visit(tree)
    return units, warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _matches_paths(path: Path, root: Path, filters: list[Path]) -> bool:
    if not filters:
        return True
    target = path.resolve()
    for item in filters:
        candidate = item.resolve()
        if target == candidate or is_within(target, candidate):
            return True
    return False


def _changed_sources(changed: Iterable[Path], root: Path) -> set[str]:
    return {relpath(path, root) for path in changed}


def build_report(
    root: Path,
    files: list[Path],
    out_of_scope: list[Path],
    path_filters: list[Path],
    changed_only: bool,
    max_units: int,
) -> dict[str, Any]:
    project_frameworks = read_project_frameworks(root)
    changed = git_changed_files(root) if changed_only else None
    changed_mode = changed_only and changed is not None
    changed_rel = _changed_sources(changed, root) if changed else set()

    all_units: list[dict[str, Any]] = []
    file_entries: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    skipped_files: list[dict[str, Any]] = []
    if changed_only and changed is None:
        warnings.append(
            {
                "file": "",
                "line": 0,
                "message": "--changed 需要 git 仓库；当前目录不可用，已改为扫描全部文件。",
            }
        )

    for path in files:
        if not _matches_paths(path, root, path_filters):
            continue
        try:
            text = read_text(path)
        except OSError as exc:
            warnings.append({"file": relpath(path, root), "line": 0, "message": f"读取失败：{exc}"})
            continue
        language = "js" if path.suffix.lower() in JS_EXTS else "python"
        framework = detect_file_framework(text, language)
        if framework is None:
            project_names = {item["name"] for item in project_frameworks}
            if language == "js":
                for candidate in ("vitest", "jest", "playwright", "cypress", "mocha"):
                    if candidate in project_names:
                        framework = candidate
                        break
            else:
                for candidate in ("pytest", "unittest"):
                    if candidate in project_names:
                        framework = candidate
                        break

        if language == "js":
            units, file_warnings = parse_js_file(path, text, root, framework)
            ui = detect_ui(path, text, language)
        else:
            units, file_warnings = parse_py_file(path, text, root, framework)
            ui = False
        warnings.extend(file_warnings)

        # A file under tests/ that contains no test units is a helper, not a test file.
        if not units:
            skipped_files.append(
                {
                    "file": relpath(path, root),
                    "reason": "no test functions"
                    if language == "python"
                    else "no test calls found",
                }
            )
            continue

        if changed_mode:
            unit_matches = relpath(path, root) in changed_rel or any(
                source in changed_rel for unit in units for source in unit["sources"]
            )
            if not unit_matches:
                continue

        all_units.extend(units)
        file_entries.append(
            {
                "path": relpath(path, root),
                "language": language,
                "framework": framework,
                "ui": ui,
                "units": len(units),
                "sources": sorted({source for unit in units for source in unit["sources"]}),
                "unresolved_sources": sorted(
                    {source for unit in units for source in unit["unresolved_sources"]}
                ),
                "mocked_modules": sorted({module for unit in units for module in unit["mocked_modules"]}),
            }
        )

    all_units.sort(key=lambda unit: (unit["file"], unit["start_line"], unit["name"]))
    for index, unit in enumerate(all_units, start=1):
        unit["id"] = f"T{index:04d}"

    file_frameworks: dict[str, int] = {}
    for entry in file_entries:
        name = entry["framework"] or "unknown"
        file_frameworks[name] = file_frameworks.get(name, 0) + 1

    truncated = False
    if max_units and len(all_units) > max_units:
        # Keep the highest-signal units; this is a bounded worklist, not a verdict.
        keep = sorted(all_units, key=lambda unit: (-unit["suspect_score"], unit["file"], unit["start_line"]))[
            :max_units
        ]
        all_units = sorted(keep, key=lambda unit: (unit["file"], unit["start_line"], unit["name"]))
        truncated = True

    by_signal: dict[str, int] = {}
    for unit in all_units:
        for signal in unit["signals"]:
            by_signal[signal["code"]] = by_signal.get(signal["code"], 0) + 1

    top_suspects = sorted(
        [unit for unit in all_units if unit["signals"]],
        key=lambda unit: (-unit["suspect_score"], unit["file"], unit["start_line"]),
    )[:12]
    top_suspects = [
        {
            "id": unit["id"],
            "file": unit["file"],
            "line": unit["start_line"],
            "name": unit["name"],
            "signals": [signal["code"] for signal in unit["signals"]],
            "score": unit["suspect_score"],
        }
        for unit in top_suspects
    ]

    return {
        "schema": SCHEMA,
        "generated_at": now_iso(),
        "root": str(root),
        "scope": {
            "paths": [relpath(path, root) for path in path_filters] or ["."],
            "changed_only": changed_only,
            "max_units": max_units,
            "truncated": truncated,
        },
        "frameworks": project_frameworks,
        "file_frameworks": dict(sorted(file_frameworks.items(), key=lambda item: (-item[1], item[0]))),
        "summary": {
            "files": len({unit["file"] for unit in all_units}),
            "units": len(all_units),
            "ui_units": sum(1 for unit in all_units if unit["kind"] == "ui"),
            "skipped_units": sum(1 for unit in all_units if unit["skipped"]),
            "todo_units": sum(1 for unit in all_units if unit["todo"]),
            "unanalyzed_units": sum(1 for unit in all_units if not unit.get("body_analyzed", True)),
            "assertions": sum(
                int(unit["stats"].get("total_assertions", unit["stats"].get("assertions", 0)))
                for unit in all_units
            ),
            "units_with_signals": sum(1 for unit in all_units if unit["signals"]),
            "parse_warnings": len(warnings),
            "out_of_scope_files": len(out_of_scope),
        },
        "signals": dict(sorted(by_signal.items(), key=lambda item: (-item[1], item[0]))),
        "top_suspects": top_suspects,
        "files": file_entries,
        "units": all_units,
        "parse_warnings": warnings,
        "skipped_files": skipped_files[:50],
        "out_of_scope_files": [relpath(path, root) for path in out_of_scope[:50]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inventory JS/TS and Python tests with heuristic signals.")
    parser.add_argument("--root", default=".", help="Project root (default: current directory).")
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Limit to a file or directory (repeatable, relative to root).",
    )
    parser.add_argument("--changed", action="store_true", help="Only test files affected by git changes.")
    parser.add_argument("--out", help="Write JSON here (default: system temp directory).")
    parser.add_argument("--stdout", action="store_true", help="Print JSON to stdout and suppress the summary.")
    parser.add_argument("--max-units", type=int, default=0, help="Keep at most N units (0 = all).")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        fail(f"Project root is not a directory: {root}", "Pass --root with an existing directory.")

    try:
        files, out_of_scope = discover(root)
    except OSError as exc:
        fail(f"Could not scan {root}: {exc}", "Check file permissions and retry.")

    path_filters = [(root / item).resolve() for item in args.path]
    for item in path_filters:
        if not item.exists():
            fail(f"--path does not exist: {item}", "Pass a file or directory inside the project.")

    report = build_report(root, files, out_of_scope, path_filters, args.changed, args.max_units)

    if args.stdout:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    out_path = Path(args.out).expanduser() if args.out else None
    written = write_json(report, out_path, name="scan")
    summary = report["summary"]
    print("test-value-review scan")
    print(f"root: {root}")
    print(
        f"files: {summary['files']}  units: {summary['units']}  "
        f"ui: {summary['ui_units']}  assertions: {summary['assertions']}"
    )
    frameworks = ", ".join(item["name"] for item in report["frameworks"])
    if not frameworks:
        frameworks = ", ".join(f"{name} ({count})" for name, count in report["file_frameworks"].items())
    if not frameworks:
        frameworks = "not detected"
    print(f"frameworks: {frameworks}")
    print(
        f"signals: {summary['units_with_signals']} units  "
        + (", ".join(f"{key}={value}" for key, value in report["signals"].items()) or "none")
    )
    if report["top_suspects"]:
        print("top suspects:")
        for item in report["top_suspects"][:8]:
            print(f"  {item['id']}  {item['file']}:{item['line']}  {item['name']}  [{', '.join(item['signals'])}]")
    if report["parse_warnings"]:
        print(f"parse warnings: {len(report['parse_warnings'])} (see JSON; read those tests manually)")
    if report["scope"]["truncated"]:
        print(f"WARNING: worklist truncated to {summary['units']} units; rerun without --max-units for full inventory")
    print(f"json: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
