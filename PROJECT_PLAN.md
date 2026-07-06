# DebugAI Roadmap

This document tracks the development progress and planned features for DebugAI.

DebugAI is a CLI tool that analyzes stack traces and logs to help developers quickly identify the root cause of failures using structured parsing and AI assistance.

---

# Phase 1 – MVP (Completed)

Goal: Build a working AI-powered CLI stack trace analyzer.

## Core CLI
- [x] CLI interface using Typer
- [x] Local installation via pip
- [x] Command: `debuai error.log`

## Stack Trace Parsing
- [x] Extract exception type
- [x] Identify failure origin
- [x] Reconstruct execution chain
- [x] Guess likely source file

## Output Formatting
- [x] Rich terminal panels
- [x] Structured output sections

## AI Integration
- [x] AI root cause analysis
- [x] Suggested fix generation
- [x] Prevention suggestions

## UX Improvements
- [x] CLI help command
- [x] AI progress spinner
- [x] JSON response parsing for AI

---

# Phase 2 – Developer Workflow Integration (In Progress)

Goal: Make DebugAI useful in real developer environments.

## Input Handling
- [x] Support input from STDIN  
  Example:  
  `cat error.log | debuai --ai`

- [x] Allow direct error message input  
  Example:  
  `debuai "NullReferenceException at TradeService"`

- [x] Clipboard support (macOS)  
  Example:  
  `pbpaste | debuai --ai`

## Log Analysis
- [x] Detect stack traces inside raw logs
- [x] Extract multiple errors from log files
- [x] Highlight the most relevant stack trace

## Language Support
- [x] Python stack traces
- [x] Java stack traces
- [x] Node.js stack traces
- [x] Go stack traces
- [x] C# / .NET stack traces

## AI Improvements
- [x] Confidence score for AI diagnosis
- [ ] Structured AI reasoning steps
- [ ] Better prompt design for debugging context

---

# Phase 3 – Context-Aware Debugging (Future)

Goal: Provide deeper debugging insights using code context.

## Source Code Context
- [ ] Detect source file automatically
- [ ] Extract surrounding code snippet
- [ ] Send method body to AI for analysis

Example:

TradeService.CalculatePnl()

↓

TradeService.cs (lines 35–60)

---

## GitHub Integration
- [ ] Search similar GitHub issues
- [ ] Suggest existing fixes

---

## CI/CD Integration
- [ ] GitHub Action for CI failures
- [ ] Auto-debug failing builds

Example:

CI fails → DebugAI analyzes logs → comment on PR

---

# Phase 4 – Advanced Debugging Intelligence

Goal: Turn DebugAI into a real debugging assistant.

## Observability Integration
- [ ] Kubernetes logs
- [ ] Docker logs
- [ ] Cloud log ingestion

## Pattern Learning
- [ ] Store previously seen errors
- [ ] Suggest known fixes

---

# Long-Term Vision

DebugAI becomes a developer debugging assistant that can analyze:

- stack traces
- logs
- source code
- CI failures

and produce structured debugging insights.

---

# Contribution

Contributions and ideas are welcome.

Open an issue to discuss new features.
