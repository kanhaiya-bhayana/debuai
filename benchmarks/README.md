# DebugAI Phase 1 Benchmark

This directory establishes a reproducible baseline for DebugAI before parser or diagnosis changes.

## Scope

The first pass focuses on deterministic extraction: trace segmentation, exception/panic type, and failure-origin frame. AI diagnosis quality is evaluated separately because model output can vary between runs.

## Run

From the repository root, with the project installed in editable mode:

```bash
pip install -e ".[dev]"
python benchmarks/run_parser_benchmark.py
```

The runner uses the current implementation in `debugai/`; it does not call an AI provider and requires no API key.

## Dataset format

`parser_cases.jsonl` contains one JSON object per line:

- `id`: stable case identifier
- `category`: case family
- `input`: log text supplied to DebugAI
- `expected.trace_count`: expected number of extracted traces
- `expected.exception_types`: expected exception/panic type for each extracted trace
- `expected.origins`: expected failure-origin frame for each trace

Cases are synthetic and designed to be safely shareable. They are an initial smoke benchmark, not yet a broad representative production dataset.

## Metrics

The runner reports exact-match rates for trace count, exception types, and origins, plus an overall case pass rate. Keep per-case output: the aggregate alone hides failure patterns.

## AI diagnosis benchmark (next step)

For each diagnosis case, record the provider/model, prompt version, run date, root-cause assessment, evidence grounding, actionability/safety, confidence calibration, and unsupported claims. Score each dimension from 0–2 (maximum 10). Run cases multiple times and do not treat a plausible explanation as proven unless the supplied log/context supports it.

## Baseline discipline

1. Run this benchmark against the unchanged baseline.
2. Save the output with the commit SHA and Python version.
3. Change one behavior at a time.
4. Re-run the same cases after each change and compare per-case results.
