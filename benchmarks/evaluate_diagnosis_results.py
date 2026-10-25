#!/usr/bin/env python3
"""Offline structural and evidence-cue checks for diagnosis benchmark JSONL results.

This is a deterministic triage aid, not a semantic judge of diagnosis quality.
It does not call a model or require an API key.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "benchmarks" / "diagnosis_cases.jsonl"


def read_jsonl(path):
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(str(path) + ":" + str(line_number) + ": invalid JSON: " + str(exc)) from exc
    return records


def response_text(actual):
    if not isinstance(actual, dict):
        return ""
    return " ".join(str(actual.get(key, "")) for key in ("root_cause", "fix", "prevention")).casefold()


def evaluate(record, case):
    actual = record.get("actual")
    checks = []
    text = response_text(actual)
    if record.get("error"):
        checks.append({"check": "provider_error_absent", "passed": False, "detail": record["error"]})
    else:
        checks.append({"check": "provider_error_absent", "passed": True, "detail": ""})

    is_object = isinstance(actual, dict)
    checks.append({"check": "actual_is_object", "passed": is_object, "detail": "" if is_object else "actual response is missing or not an object"})
    required_fields = ("root_cause", "fix", "prevention", "confidence")
    missing = [field for field in required_fields if not isinstance(actual, dict) or not str(actual.get(field, "")).strip()]
    checks.append({"check": "required_fields_nonempty", "passed": not missing, "detail": "missing/empty: " + ", ".join(missing) if missing else ""})

    confidence = actual.get("confidence") if isinstance(actual, dict) else None
    valid_confidence = isinstance(confidence, str) and confidence.strip().casefold() in {"high", "medium", "low"}
    checks.append({"check": "confidence_is_valid", "passed": valid_confidence, "detail": "expected high, medium, or low; got " + repr(confidence) if not valid_confidence else ""})

    cue_results = []
    for index, alternatives in enumerate(case.get("checks", {}).get("required_any", []), 1):
        alternatives = [str(item).casefold() for item in alternatives]
        matched = [item for item in alternatives if item in text]
        cue_results.append({"group": index, "passed": bool(matched), "matched": matched, "alternatives": alternatives})
    missing_cues = [item for item in cue_results if not item["passed"]]
    checks.append({
        "check": "required_evidence_cues",
        "passed": not missing_cues,
        "detail": "missing cue groups: " + ", ".join(str(item["group"]) for item in missing_cues) if missing_cues else "",
        "groups": cue_results,
    })

    forbidden = []
    review_only_matches = []
    review_only_phrases = case.get("checks", {}).get("review_only_phrases", [])
    for phrase in case.get("checks", {}).get("forbidden_any", []):
        if str(phrase).casefold() in text:
            (review_only_matches if phrase in review_only_phrases else forbidden).append(str(phrase))
    expected = case.get("expected", {})
    for phrase in expected.get("must_not_claim", []):
        if str(phrase).casefold() in text and phrase not in forbidden and phrase not in review_only_matches:
            (review_only_matches if phrase in review_only_phrases else forbidden).append(str(phrase))
    phrase_check_passed = False if forbidden else (None if review_only_matches else True)
    checks.append({
        "check": "literal_unsupported_phrase_flags",
        "passed": phrase_check_passed,
        "review_required": bool(review_only_matches),
        "detail": (
            "human review required: literal matching cannot determine whether these phrases are quoted or followed"
            if review_only_matches else
            "review these phrase matches; literal checks can produce false positives and false negatives"
        ),
        "matches": forbidden,
        "review_only_matches": review_only_matches,
    })

    passed = sum(1 for item in checks if item["passed"] is True)
    automatic_total = sum(1 for item in checks if item["passed"] is not None)
    return {
        "case_id": record.get("case_id", record.get("id", "unknown")),
        "run_index": record.get("run_index"),
        "provider": record.get("provider"),
        "model": record.get("model"),
        "automatic_checks_passed": passed,
        "automatic_checks_total": automatic_total,
        "human_review_required": [
            item["check"] for item in checks if item.get("review_required")
        ],
        "human_review_notes": case.get("human_review_notes", []),
        "checks": checks,
        "interpretation": "Triage only; passing checks does not prove semantic correctness.",
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate saved diagnosis JSONL results without API calls.")
    parser.add_argument("--input", type=Path, required=True, help="Saved output from run_diagnosis_benchmark.py")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES, help="Diagnosis dataset used for the run")
    parser.add_argument("--output", type=Path, help="Optional report JSONL path; otherwise print summary only")
    args = parser.parse_args()

    try:
        cases = read_jsonl(args.cases)
        records = read_jsonl(args.input)
    except (OSError, ValueError) as exc:
        print("Input error: " + str(exc), file=sys.stderr)
        return 2

    case_map = {case["id"]: case for case in cases}
    reports = []
    unknown_ids = []
    for record in records:
        case_id = record.get("case_id", record.get("id"))
        case = case_map.get(case_id)
        if case is None:
            unknown_ids.append(case_id)
            continue
        reports.append(evaluate(record, case))

    check_counts = Counter()
    for report in reports:
        for check in report["checks"]:
            outcome = (
                "review_required" if check.get("review_required") else
                "passed" if check["passed"] is True else
                "failed"
            )
            check_counts[check["check"] + ":" + outcome] += 1

    total_checks = sum(report["automatic_checks_total"] for report in reports)
    passed_checks = sum(report["automatic_checks_passed"] for report in reports)
    review_required_count = sum(len(report["human_review_required"]) for report in reports)
    print("DebugAI offline diagnosis evaluation")
    print("Input records: " + str(len(records)))
    print("Evaluated records: " + str(len(reports)))
    print("Unknown case IDs: " + str(len(unknown_ids)))
    if unknown_ids:
        print("Unknown IDs: " + ", ".join(str(item) for item in unknown_ids))
    print("Deterministic checks passed: " + str(passed_checks) + "/" + str(total_checks))
    print("Checks requiring human review: " + str(review_required_count))
    print("NOTE: this is not a diagnosis-accuracy score; phrase/cue checks require human interpretation.")
    for name in ("provider_error_absent", "actual_is_object", "required_fields_nonempty", "confidence_is_valid", "required_evidence_cues", "literal_unsupported_phrase_flags"):
        passed = check_counts[name + ":passed"]
        failed = check_counts[name + ":failed"]
        review = check_counts[name + ":review_required"]
        print("  " + name + ": " + str(passed) + " passed, " + str(failed) + " flagged, " + str(review) + " review required")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as handle:
            for report in reports:
                handle.write(json.dumps(report, ensure_ascii=False) + "\n")
        print("Report saved to: " + str(args.output))

    return 1 if unknown_ids or any(
        not check["passed"]
        for report in reports
        for check in report["checks"]
        if check["check"] in {"provider_error_absent", "actual_is_object", "required_fields_nonempty", "confidence_is_valid"}
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
