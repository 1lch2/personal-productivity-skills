#!/usr/bin/env python3
"""Check the scanner's signals against the calibration fixtures.

This does not grade the reviewer's prose. It verifies the deterministic part:
every expected case exists and the scanner emitted the expected signals. The
labels in expected.json are a checklist for a human or agent run.

Usage:
    python evals/check_fixtures.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
EXPECTED = ROOT / "expected.json"
SCANNER = ROOT.parent / "scripts" / "scan_tests.py"


def main() -> int:
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    proc = subprocess.run(
        [sys.executable, str(SCANNER), "--root", str(FIXTURES), "--stdout"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        print("scanner failed:", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return 2
    scan = json.loads(proc.stdout)
    units = {(unit["file"], unit["name"]): unit for unit in scan["units"]}

    failures: list[str] = []
    print(f"scanned {scan['summary']['units']} units in {scan['summary']['files']} files\n")
    print(f"{'label':8} {'importance':10} {'file:line':42} name")
    print("-" * 100)

    for case in expected["cases"]:
        key = (case["file"], case["name"])
        unit = units.get(key)
        if unit is None:
            failures.append(f"missing unit: {case['file']} :: {case['name']}")
            print(f"{case['label']:8} {case['importance']:10} {'MISSING':42} {case['name']}")
            continue
        actual = {signal["code"] for signal in unit["signals"]}
        missing = set(case.get("scanner_signals", [])) - actual
        if missing:
            failures.append(
                f"{case['file']} :: {case['name']} missing signals {sorted(missing)}; got {sorted(actual)}"
            )
        location = f"{case['file']}:{unit['start_line']}"
        flag = " !" if missing else ""
        print(f"{case['label']:8} {case['importance']:10} {location:42} {case['name']}{flag}")

    expected_keys = {(case["file"], case["name"]) for case in expected["cases"]}
    extras = sorted(set(units) - expected_keys)
    if extras:
        print("\nunits not in the calibration set (fine, just not asserted):")
        for file, name in extras:
            print(f"  {file} :: {name}")

    print()
    if failures:
        print(f"FAIL: {len(failures)} problem(s)")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OK: scanner signals match the calibration set")
    print("Next: run the test-value-review skill on evals/fixtures and compare its labels/reasons.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
