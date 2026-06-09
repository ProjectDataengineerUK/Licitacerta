#!/usr/bin/env python3
"""Check eval pass rate from JUnit XML; exits 1 if below threshold."""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET


def parse_junit(junit_path: str) -> tuple[int, int]:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    # JUnit XML: <testsuite tests="N" failures="F" errors="E">
    suites = root.findall(".//testsuite") or [root]
    total = sum(int(s.get("tests", 0)) for s in suites)
    failures = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    return total, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True, help="Path to JUnit XML report")
    parser.add_argument("--min-pass-rate", type=float, default=0.80)
    args = parser.parse_args()

    try:
        total, failures = parse_junit(args.junit)
    except FileNotFoundError:
        print(f"ERROR: JUnit file not found: {args.junit}")
        return 1

    if total == 0:
        print("WARNING: no tests found in JUnit report")
        return 0

    passed = total - failures
    rate = passed / total
    print(f"Eval results: {passed}/{total} passed ({rate:.1%})")
    print(f"Threshold:    {args.min_pass_rate:.1%}")

    if rate < args.min_pass_rate:
        print(f"FAIL: pass rate {rate:.1%} is below threshold {args.min_pass_rate:.1%}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
