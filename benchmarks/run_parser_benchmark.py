"""Run the deterministic Phase 1 parser benchmark without an AI provider."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from debugai.analyzer import (  # noqa: E402
    extract_all_stack_traces,
    extract_exception_type,
    extract_failure_origin,
)


def load_cases(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc


def evaluate(case):
    traces = extract_all_stack_traces(case["input"])
    actual = {
        "trace_count": len(traces),
        "exception_types": [extract_exception_type(trace) for trace in traces],
        "origins": [extract_failure_origin(trace) for trace in traces],
    }
    expected = case["expected"]
    checks = {key: actual[key] == expected[key] for key in expected}
    return actual, checks


def main():
    path = Path(__file__).with_name("parser_cases.jsonl")
    cases = list(load_cases(path))
    totals = {"trace_count": 0, "exception_types": 0, "origins": 0}
    passed = 0

    print(f"DebugAI parser benchmark — {len(cases)} cases")
    print(f"Dataset: {path.relative_to(ROOT)}")
    print("-" * 72)

    for case in cases:
        actual, checks = evaluate(case)
        case_passed = all(checks.values())
        passed += int(case_passed)
        for key, ok in checks.items():
            totals[key] += int(ok)
        status = "PASS" if case_passed else "FAIL"
        print(f"{status} {case['id']} [{case['category']}]")
        if not case_passed:
            print(f"  expected: {json.dumps(case['expected'], ensure_ascii=False)}")
            print(f"  actual:   {json.dumps(actual, ensure_ascii=False)}")
            print(f"  checks:   {json.dumps(checks)}")

    print("-" * 72)
    print(f"Case pass rate: {passed}/{len(cases)} ({passed / len(cases):.1%})")
    for metric, correct in totals.items():
        print(f"{metric} exact match: {correct}/{len(cases)} ({correct / len(cases):.1%})")


if __name__ == "__main__":
    main()
