"""
Tests for debugai/analyzer.py — exception extraction, origin, chain, source file,
and multi-trace extraction.
"""
import pytest
from debugai.analyzer import (
    extract_exception_type,
    extract_failure_origin,
    extract_stack_chain,
    detect_source_file,
    extract_all_stack_traces,
    explain_error,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

PYTHON_MULTI_FRAME = """\
Traceback (most recent call last):
  File "server.py", line 10, in handle_request
    result = process_data(payload)
  File "processor.py", line 25, in process_data
    value = parse_input(raw)
  File "parser.py", line 8, in parse_input
    return int(raw)
ValueError: invalid literal for int() with base 10: 'abc'"""

PYTHON_TYPE_ERROR = """\
Traceback (most recent call last):
  File "utils.py", line 3, in add
    return a + b
TypeError: unsupported operand type(s) for +: 'int' and 'str'"""

PYTHON_ATTRIBUTE_ERROR = """\
Traceback (most recent call last):
  File "model.py", line 14, in predict
    return self.model.predict(x)
AttributeError: 'NoneType' object has no attribute 'predict'"""

CSHARP_TRACE = """\
System.NullReferenceException
at OrderService.CalculateTotal()
at OrderController.PlaceOrder()"""

EMPTY_INPUT = ""
GARBAGE_INPUT = "INFO: Server started on port 8080\nDEBUG: Connected to database"

MULTI_TRACE_LOG = """\
2024-01-01 10:00:00 INFO Starting up

Traceback (most recent call last):
  File "worker.py", line 5, in run
    process()
ValueError: bad value

2024-01-01 10:01:00 INFO Retrying

Traceback (most recent call last):
  File "worker.py", line 5, in run
    process()
  File "processor.py", line 12, in process
    parse(data)
KeyError: 'id'"""


# ── extract_exception_type ────────────────────────────────────────────────────

class TestExtractExceptionType:

    def test_python_value_error(self):
        assert extract_exception_type(PYTHON_MULTI_FRAME) == "ValueError"

    def test_python_type_error(self):
        assert extract_exception_type(PYTHON_TYPE_ERROR) == "TypeError"

    def test_python_attribute_error(self):
        assert extract_exception_type(PYTHON_ATTRIBUTE_ERROR) == "AttributeError"

    def test_csharp_null_reference(self):
        assert extract_exception_type(CSHARP_TRACE) == "NullReferenceException"

    def test_unknown_falls_back(self):
        assert extract_exception_type(GARBAGE_INPUT) == "UnknownException"

    def test_empty_input_falls_back(self):
        assert extract_exception_type(EMPTY_INPUT) == "UnknownException"


# ── extract_failure_origin ────────────────────────────────────────────────────

class TestExtractFailureOrigin:

    def test_python_innermost_frame(self):
        """Origin must be the innermost frame, not the outermost."""
        assert extract_failure_origin(PYTHON_MULTI_FRAME) == "parse_input"

    def test_python_single_frame(self):
        trace = """\
Traceback (most recent call last):
  File "app.py", line 1, in main
    do_thing()
RuntimeError: something broke"""
        assert extract_failure_origin(trace) == "main"

    def test_csharp_origin(self):
        assert extract_failure_origin(CSHARP_TRACE) == "OrderService.CalculateTotal()"

    def test_no_frames_returns_unknown(self):
        assert extract_failure_origin(GARBAGE_INPUT) == "Unknown origin"


# ── extract_stack_chain ───────────────────────────────────────────────────────

class TestExtractStackChain:

    def test_python_chain_order(self):
        """Chain must read top-down: outermost → innermost."""
        chain = extract_stack_chain(PYTHON_MULTI_FRAME)
        lines = chain.split("\n   ↓\n")
        assert lines[0] == "handle_request"
        assert lines[-1] == "parse_input"

    def test_python_chain_length(self):
        chain = extract_stack_chain(PYTHON_MULTI_FRAME)
        assert chain.count("↓") == 2  # 3 frames = 2 arrows

    def test_no_trace_message(self):
        assert extract_stack_chain(GARBAGE_INPUT) == "No stack trace detected"


# ── detect_source_file ────────────────────────────────────────────────────────

class TestDetectSourceFile:

    def test_python_extracts_py_file(self):
        result = detect_source_file(PYTHON_MULTI_FRAME, "parse_input")
        # Should return the innermost .py file
        assert result.endswith(".py")

    def test_csharp_derives_cs_file(self):
        result = detect_source_file(CSHARP_TRACE, "OrderService.CalculateTotal()")
        assert result == "OrderService.cs"

    def test_unknown_origin_no_crash(self):
        result = detect_source_file(GARBAGE_INPUT, "")
        assert result == "Unknown file"

    def test_node_extracts_js_file(self):
        node_trace = """\
TypeError: Cannot read properties of undefined
    at Object.handler (/app/routes/user.js:22:18)"""
        result = detect_source_file(node_trace, "handler")
        assert result.endswith(".js")


# ── extract_all_stack_traces ──────────────────────────────────────────────────

class TestExtractAllStackTraces:

    def test_single_python_trace(self):
        traces = extract_all_stack_traces(PYTHON_MULTI_FRAME)
        assert len(traces) == 1
        assert "ValueError" in traces[0]

    def test_multiple_traces_in_log(self):
        traces = extract_all_stack_traces(MULTI_TRACE_LOG)
        assert len(traces) == 2

    def test_first_trace_correct(self):
        traces = extract_all_stack_traces(MULTI_TRACE_LOG)
        assert "ValueError" in traces[0]

    def test_second_trace_correct(self):
        traces = extract_all_stack_traces(MULTI_TRACE_LOG)
        assert "KeyError" in traces[1]

    def test_empty_input_returns_empty_list(self):
        assert extract_all_stack_traces(EMPTY_INPUT) == []

    def test_garbage_input_returns_empty_list(self):
        assert extract_all_stack_traces(GARBAGE_INPUT) == []

    def test_csharp_trace_detected(self):
        traces = extract_all_stack_traces(CSHARP_TRACE)
        assert len(traces) >= 1
        assert "NullReferenceException" in traces[0]

    def test_go_trace_detected_as_single_block(self):
        """A Go panic + its goroutine dump (with an internal blank line) must be
        captured as ONE block — previously it was dropped entirely."""
        go_log = (
            "panic: runtime error: index out of range [3] with length 3\n"
            "\n"
            "goroutine 1 [running]:\n"
            "main.processItems(0xc000012080, 0x3, 0x3)\n"
            "\t/home/user/app/processor.go:22 +0x1d\n"
            "main.main()\n"
            "\t/home/user/app/main.go:5 +0x25\n"
        )
        traces = extract_all_stack_traces(go_log)
        assert len(traces) == 1
        assert "panic:" in traces[0]
        assert "processor.go" in traces[0]  # goroutine dump kept in the same block

    def test_go_block_parses_end_to_end(self):
        go_log = (
            "panic: runtime error: index out of range [3] with length 3\n"
            "\n"
            "goroutine 1 [running]:\n"
            "main.processItems(0xc000012080, 0x3, 0x3)\n"
            "\t/home/user/app/processor.go:22 +0x1d\n"
        )
        traces = extract_all_stack_traces(go_log)
        assert len(traces) == 1
        assert explain_error(traces[0])["exception"] != "UnknownException"

    def test_mixed_language_log_splits_per_block(self):
        mixed = (
            'Traceback (most recent call last):\n'
            '  File "app.py", line 3, in main\n'
            '    x = int(raw)\n'
            'ValueError: bad int\n'
            '\n'
            'Exception in thread "main" java.lang.NullPointerException\n'
            '    at com.example.OrderService.calc(OrderService.java:42)\n'
            '\n'
            'panic: runtime error: index out of range\n'
            '\n'
            'goroutine 1 [running]:\n'
            'main.handler()\n'
            '\t/app/main.go:20 +0x1d\n'
        )
        traces = extract_all_stack_traces(mixed)
        assert len(traces) == 3
        assert "ValueError" in traces[0]
        assert "NullPointerException" in traces[1]
        assert "panic:" in traces[2] and "main.go" in traces[2]


# ── explain_error (integration) ───────────────────────────────────────────────

class TestExplainError:

    def test_returns_all_keys(self):
        result = explain_error(PYTHON_MULTI_FRAME)
        assert set(result.keys()) >= {"exception", "origin", "chain", "source"}

    def test_python_exception_correct(self):
        result = explain_error(PYTHON_MULTI_FRAME)
        assert result["exception"] == "ValueError"

    def test_python_origin_correct(self):
        result = explain_error(PYTHON_MULTI_FRAME)
        assert result["origin"] == "parse_input"

    def test_csharp_exception_correct(self):
        result = explain_error(CSHARP_TRACE)
        assert result["exception"] == "NullReferenceException"
