"""
Tests for debugai/parser/ — match() and extract_frames() for each parser.
"""
import pytest
from debugai.parser.python import PythonParser
from debugai.parser.java import JavaParser
from debugai.parser.go import GoParser
from debugai.parser.csharp import CSharpParser
from debugai.parser.node import NodeParser
from debugai.parser.registry import get_parser

# ── Fixtures ──────────────────────────────────────────────────────────────────

PYTHON_TRACE = """\
Traceback (most recent call last):
  File "server.py", line 10, in handle_request
    result = process_data(payload)
  File "processor.py", line 25, in process_data
    value = parse_input(raw)
  File "parser.py", line 8, in parse_input
    return int(raw)
ValueError: invalid literal for int() with base 10: 'abc'"""

PYTHON_TRACE_SINGLE_FRAME = """\
Traceback (most recent call last):
  File "app.py", line 42, in process
    result = int(value)
ValueError: invalid literal for int() with base 10: 'abc'"""

PYTHON_TRACE_KEY_ERROR = """\
Traceback (most recent call last):
  File "config.py", line 5, in load
    return data["missing_key"]
KeyError: 'missing_key'"""

CSHARP_TRACE = """\
System.NullReferenceException
at TradeService.CalculatePnl()
at PricingService.ProcessTrade()
at TradeController.ExecuteTrade()"""

JAVA_TRACE = """\
java.lang.NullPointerException
\tat com.example.OrderService.calculateTotal(OrderService.java:42)
\tat com.example.OrderController.placeOrder(OrderController.java:18)
\tat com.example.MainApp.main(MainApp.java:10)"""

JAVA_SPRING_TRACE = """\
org.springframework.web.util.NestedServletException: Request processing failed
\tat com.example.api.UserController.getUser(UserController.java:55)
\tat com.example.service.UserService.findById(UserService.java:30)
\tat com.example.repository.UserRepository.query(UserRepository.java:12)"""

GO_TRACE = """\
goroutine 1 [running]:
main.divide(0x5, 0x0)
\t/home/user/app/main.go:15 +0x52
main.calculate(...)
\t/home/user/app/main.go:9
main.main()
\t/home/user/app/main.go:4 +0x25"""

GO_PANIC_TRACE = """\
panic: runtime error: index out of range [3] with length 3

goroutine 1 [running]:
main.processItems(0xc000012080, 0x3, 0x3)
\t/home/user/app/processor.go:22 +0x1d
main.run()
\t/home/user/app/main.go:10 +0x39
main.main()
\t/home/user/app/main.go:5 +0x25"""

NODE_TRACE = """\
TypeError: Cannot read properties of undefined
    at processTicksAndRejections (node:internal/process/task_queues:95:5)
    at Object.handler (/app/routes/user.js:22:18)"""


# ── PythonParser ──────────────────────────────────────────────────────────────

class TestPythonParser:
    parser = PythonParser()

    def test_match_standard_traceback(self):
        assert self.parser.match(PYTHON_TRACE) is True

    def test_match_single_frame(self):
        assert self.parser.match(PYTHON_TRACE_SINGLE_FRAME) is True

    def test_no_match_csharp(self):
        assert self.parser.match(CSHARP_TRACE) is False

    def test_no_match_plain_text(self):
        assert self.parser.match("Everything is fine, nothing to see here.") is False

    def test_no_match_java(self):
        assert self.parser.match(JAVA_TRACE) is False

    def test_no_match_go(self):
        assert self.parser.match(GO_TRACE) is False

    def test_extract_frames_order(self):
        frames = self.parser.extract_frames(PYTHON_TRACE)
        assert frames[0] == "parse_input"

    def test_extract_frames_full_chain(self):
        frames = self.parser.extract_frames(PYTHON_TRACE)
        assert frames == ["parse_input", "process_data", "handle_request"]

    def test_extract_frames_single(self):
        frames = self.parser.extract_frames(PYTHON_TRACE_SINGLE_FRAME)
        assert frames == ["process"]

    def test_extract_exception_type_value_error(self):
        assert self.parser.extract_exception_type(PYTHON_TRACE) == "ValueError"

    def test_extract_exception_type_key_error(self):
        assert self.parser.extract_exception_type(PYTHON_TRACE_KEY_ERROR) == "KeyError"


# ── JavaParser ────────────────────────────────────────────────────────────────

class TestJavaParser:
    parser = JavaParser()

    def test_match_java(self):
        assert self.parser.match(JAVA_TRACE) is True

    def test_match_spring_trace(self):
        assert self.parser.match(JAVA_SPRING_TRACE) is True

    def test_no_match_csharp(self):
        assert self.parser.match(CSHARP_TRACE) is False

    def test_no_match_python(self):
        assert self.parser.match(PYTHON_TRACE) is False

    def test_no_match_plain_text(self):
        assert self.parser.match("no error here") is False

    def test_extract_frames_not_empty(self):
        frames = self.parser.extract_frames(JAVA_TRACE)
        assert len(frames) > 0

    def test_extract_frames_innermost_first(self):
        frames = self.parser.extract_frames(JAVA_TRACE)
        assert "calculateTotal" in frames[0]

    def test_extract_frames_full_chain(self):
        frames = self.parser.extract_frames(JAVA_TRACE)
        assert len(frames) == 3

    def test_extract_exception_type_null_pointer(self):
        result = self.parser.extract_exception_type(JAVA_TRACE)
        assert result == "NullPointerException"

    def test_extract_exception_type_short_name(self):
        result = self.parser.extract_exception_type(JAVA_TRACE)
        assert "." not in result

    def test_extract_location(self):
        file, line, func = self.parser.extract_location(JAVA_TRACE)
        assert file == "OrderService.java"
        assert line == "42"


# ── GoParser ──────────────────────────────────────────────────────────────────

class TestGoParser:
    parser = GoParser()

    def test_match_goroutine_trace(self):
        assert self.parser.match(GO_TRACE) is True

    def test_match_panic_trace(self):
        assert self.parser.match(GO_PANIC_TRACE) is True

    def test_no_match_python(self):
        assert self.parser.match(PYTHON_TRACE) is False

    def test_no_match_java(self):
        assert self.parser.match(JAVA_TRACE) is False

    def test_no_match_csharp(self):
        assert self.parser.match(CSHARP_TRACE) is False

    def test_no_match_plain_text(self):
        assert self.parser.match("no error here") is False

    def test_extract_frames_not_empty(self):
        frames = self.parser.extract_frames(GO_TRACE)
        assert len(frames) > 0

    def test_extract_frames_filters_runtime(self):
        trace = """\
goroutine 1 [running]:
runtime.gopanic(0x10a3e00, 0xc000012080)
\t/usr/local/go/src/runtime/panic.go:522
main.doWork()
\t/home/user/app/worker.go:14 +0x45"""
        frames = self.parser.extract_frames(trace)
        user_frames = [f for f in frames if "main." in f]
        assert len(user_frames) > 0

    def test_extract_exception_type_index_out_of_range(self):
        result = self.parser.extract_exception_type(GO_PANIC_TRACE)
        assert result == "IndexOutOfRangeError"

    def test_extract_exception_type_general_panic(self):
        result = self.parser.extract_exception_type(GO_TRACE)
        assert result == "GoPanic"


# ── CSharpParser ──────────────────────────────────────────────────────────────

class TestCSharpParser:
    parser = CSharpParser()

    def test_match_csharp(self):
        assert self.parser.match(CSHARP_TRACE) is True

    def test_no_match_java(self):
        assert self.parser.match(JAVA_TRACE) is False

    def test_no_match_plain_text(self):
        assert self.parser.match("no error here") is False

    def test_extract_frames_csharp(self):
        frames = self.parser.extract_frames(CSHARP_TRACE)
        assert len(frames) > 0
        assert any("TradeService" in f for f in frames)

    def test_extract_frames_innermost_first(self):
        frames = self.parser.extract_frames(CSHARP_TRACE)
        assert "TradeService.CalculatePnl()" in frames[0]

    def test_extract_exception_type(self):
        assert self.parser.extract_exception_type(CSHARP_TRACE) == "NullReferenceException"


# ── NodeParser ────────────────────────────────────────────────────────────────

class TestNodeParser:
    parser = NodeParser()

    def test_match_node(self):
        assert self.parser.match(NODE_TRACE) is True

    def test_no_match_python(self):
        assert self.parser.match(PYTHON_TRACE) is False

    def test_no_match_java(self):
        assert self.parser.match(JAVA_TRACE) is False

    def test_extract_frames_node(self):
        frames = self.parser.extract_frames(NODE_TRACE)
        assert len(frames) > 0

    def test_extract_location_skips_internal_and_uses_user_frame(self):
        # innermost frame is a node:internal core frame; location should be the
        # first real .js frame instead.
        file, line, _ = self.parser.extract_location(NODE_TRACE)
        assert file == "/app/routes/user.js"
        assert line == "22"

    def test_extract_location_anonymous_frame(self):
        trace = (
            "TypeError: boom\n"
            "    at /srv/app/index.js:8:3\n"
        )
        file, line, func = self.parser.extract_location(trace)
        assert file == "/srv/app/index.js"
        assert line == "8"
        assert func is None

    def test_extract_location_none_without_js_frame(self):
        trace = (
            "TypeError: boom\n"
            "    at processTicksAndRejections (node:internal/process/task_queues:95:5)\n"
        )
        assert self.parser.extract_location(trace) == (None, None, None)


# ── Registry ──────────────────────────────────────────────────────────────────

class TestRegistry:

    def test_routes_python(self):
        assert isinstance(get_parser(PYTHON_TRACE), PythonParser)

    def test_routes_java(self):
        assert isinstance(get_parser(JAVA_TRACE), JavaParser)

    def test_routes_go(self):
        assert isinstance(get_parser(GO_TRACE), GoParser)

    def test_routes_go_panic(self):
        assert isinstance(get_parser(GO_PANIC_TRACE), GoParser)

    def test_routes_csharp(self):
        assert isinstance(get_parser(CSHARP_TRACE), CSharpParser)

    def test_routes_node(self):
        assert isinstance(get_parser(NODE_TRACE), NodeParser)

    def test_java_not_stolen_by_csharp(self):
        parser = get_parser(JAVA_TRACE)
        assert not isinstance(parser, CSharpParser)

    def test_returns_none_for_garbage(self):
        assert get_parser("this is not a stack trace at all") is None