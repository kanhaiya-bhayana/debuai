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


## AI diagnosis benchmark

The diagnosis benchmark calls a selected provider and writes every response to a JSONL artifact for human review. It is intentionally separate from parser correctness: diagnosis scores must not hide parser failures.

Install the project and configure exactly one provider key, then run from the repository root:

```bash
pip install -e ".[dev]"
export OPENAI_API_KEY=...
python benchmarks/run_diagnosis_benchmark.py --provider openai --repeat 3
```

Use `--provider anthropic` or `--provider nvidia` to compare another provider. The provider is explicit (no failover), and the selected model, prompt version, commit, UTC timestamp, per-case latency, raw structured result, and errors are recorded. Keep API keys out of command history and never put secrets in benchmark cases.

By default, results are saved to `benchmarks/results/diagnosis-<timestamp>.jsonl`. Results contain synthetic case data and model responses; review them before publishing. Do not commit results unless you intentionally want to publish the provider output and accept the associated cost/privacy implications.

### Human scoring rubric

Score each dimension from 0 to 2 for each response. The runner leaves review fields blank deliberately; semantic quality should not be guessed using brittle keyword matching.

- **Root-cause correctness:** 0 = wrong / unsupported; 1 = partially correct or too vague; 2 = matches the evidence and states important uncertainty.
- **Evidence grounding:** 0 = material unsupported claims; 1 = mixed grounding; 2 = claims are tied to the supplied log/context.
- **Safe actionability:** 0 = unsafe or irrelevant; 1 = partly useful but incomplete; 2 = practical, proportionate, and safe.
- **Confidence calibration:** 0 = clearly over/under-confident; 1 = defensible but imperfect; 2 = confidence matches evidence strength.
- **Unsupported claims:** 0 = significant unsupported claim(s); 1 = minor overreach; 2 = no material unsupported claims.

Maximum: 10 points per response. Record the dimension scores in the `review` object in the output JSONL. The runner's `unsupported_claim_flags` are literal phrase checks only and can produce false positives/negatives; they are reviewer hints, not a score.

Run at least three repeats before comparing providers. Report mean score, per-dimension mean, score spread, case-level failures, and API errors. Keep the dataset and prompt version fixed when comparing providers. Do not treat one small synthetic dataset as proof of production-level accuracy.

## Baseline discipline

1. Run this benchmark against the unchanged baseline.
2. Save the output with the commit SHA and Python version.
3. Change one behavior at a time.
4. Re-run the same cases after each change and compare per-case results.
