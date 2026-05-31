import sys
import os
import json
import typer
import random
import subprocess
from debugai.constants.spinner_verbs import SPINNER_VERBS
from debugai.constants.completion_spinner import COMPLETION_PHRASES
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from debugai.analyzer import extract_all_stack_traces, explain_error
from debugai.ai_analyzer import analyze_with_ai
from debugai.scorer.relevance import select_most_relevant
from debugai.issue_search import search_github_issues

app = typer.Typer()
console = Console()

_CONFIDENCE_STYLE = {
    "high":   "bold green",
    "medium": "bold yellow",
    "low":    "bold red",
}
_CONFIDENCE_ICON = {
    "high":   "🟢",
    "medium": "🟡",
    "low":    "🔴",
}
_STATE_ICON = {
    "closed": "✅",
    "open":   "🔴",
}


@app.command()
def explain(
    input_value: str = typer.Argument(None),
    ai: bool = typer.Option(False, "--ai", help="Enable AI analysis"),
    paste: bool = typer.Option(False, "--paste", help="Read input from clipboard"),
    provider: str = typer.Option(
        None,
        "--provider",
        help="AI provider: openai, anthropic, nvidia (default: auto-detect)"
    ),
    top: int = typer.Option(
        1,
        "--top",
        help="Number of recent errors to analyze"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as clean JSON (suppresses Rich formatting)"
    ),
    issues: bool = typer.Option(
        False,
        "--issues",
        help="Search GitHub for related issues"
    ),
):
    MAX_LINES = 300

    def trim_log(log: str) -> str:
        lines = log.splitlines()
        if len(lines) > MAX_LINES:
            return "\n".join(lines[-MAX_LINES:])
        return log

    # ── Input resolution ──────────────────────────────────────────────
    if paste:
        try:
            log = subprocess.check_output("pbpaste").decode("utf-8")
        except Exception:
            if not json_output:
                console.print("[red]Failed to read clipboard[/red]")
            raise typer.Exit()

    elif not sys.stdin.isatty():
        log = sys.stdin.read()

    elif input_value and os.path.exists(input_value):
        with open(input_value, encoding="utf-8", errors="replace") as f:
            log = f.read()

    elif input_value:
        log = input_value

    else:
        if not json_output:
            console.print("[red]No input provided. Pass a file, pipe a log, or use --paste.[/red]")
        raise typer.Exit()

    log = trim_log(log)
    traces = extract_all_stack_traces(log)

    if not traces:
        if json_output:
            print(json.dumps({"error": "No stack trace detected in input."}))
        else:
            console.print("[yellow]No stack trace detected in input.[/yellow]")
        return

    top = int(top)
    selected_trace = (
        traces[-top:] if top > 1 and len(traces) >= top
        else traces if top > 1
        else [select_most_relevant(traces)]
    )

    # ── JSON mode ─────────────────────────────────────────────────────
    if json_output:
        output = []
        for trace in selected_trace:
            result = explain_error(trace)
            entry = {
                "exception":       result["exception"],
                "failure_origin":  result["origin"],
                "execution_chain": result["chain"].split("\n   ↓\n"),
                "source_file":     result["source"],
                "language":        _detect_language(trace),
            }
            if ai:
                ai_result = analyze_with_ai(trace, provider_name=provider)
                entry["ai"] = {
                    "root_cause":  ai_result.get("root_cause", ""),
                    "fix":         ai_result.get("fix", ""),
                    "prevention":  ai_result.get("prevention", ""),
                    "confidence":  ai_result.get("confidence", "low"),
                }
            if issues:
                github_issues = search_github_issues(
                    result["exception"], result["origin"]
                )
                entry["github_issues"] = github_issues

            output.append(entry)

        print(json.dumps(output[0] if len(output) == 1 else output, indent=2))
        return

    # ── Rich mode ─────────────────────────────────────────────────────
    for i, trace in enumerate(selected_trace, 1):
        console.print(f"\n[bold cyan]Error #{i}[/bold cyan]")
        result = explain_error(trace)

        console.print(Panel(result["exception"], title="🔥 Exception Type", title_align="left"))
        console.print(Panel(result["origin"],    title="📍 Failure Origin", title_align="left"))
        console.print(Panel(result["chain"],     title="🔗 Execution Chain", title_align="left"))

        if ai:
            verb = random.choice(SPINNER_VERBS)
            with console.status(f"[bold cyan]🧠 {verb}..."):
                ai_result = analyze_with_ai(trace, provider_name=provider)

            confidence = ai_result.get("confidence", "low")
            style = _CONFIDENCE_STYLE.get(confidence, "bold red")
            icon  = _CONFIDENCE_ICON.get(confidence, "🔴")

            console.print(Panel(
                ai_result.get("root_cause", ""),
                title="[bold magenta]🤖 AI Root Cause[/bold magenta]",
                title_align="left", expand=False
            ))
            console.print(Panel(
                ai_result.get("fix", ""),
                title="[bold cyan]🛠 Suggested Fix[/bold cyan]",
                title_align="left", expand=False
            ))
            console.print(Panel(
                ai_result.get("prevention", ""),
                title="[bold yellow]🛡 Prevention[/bold yellow]",
                title_align="left", expand=False
            ))
            console.print(f"[{style}]{icon} Confidence: {confidence.upper()}[/{style}]")

            phrase = random.choice(COMPLETION_PHRASES)
            console.print(f"[green]🍳 {phrase}![/green]")

        if issues:
            _render_issues(result["exception"], result["origin"])


def _render_issues(exception_type: str, top_frame: str):
    """Fetch and render related GitHub issues in a Rich table."""
    with console.status("[bold blue]🔍 Searching GitHub issues..."):
        results = search_github_issues(exception_type, top_frame)

    if not results:
        console.print(
            Panel(
                f"No related GitHub issues found for [bold]{exception_type}[/bold].\n"
                "Try searching manually at github.com/search?type=issues",
                title="🔍 GitHub Issues",
                title_align="left",
                expand=False
            )
        )
        return

    table = Table(
        show_header=True,
        header_style="bold blue",
        border_style="blue",
        expand=False,
        title="🔍 Related GitHub Issues",
        title_style="bold blue"
    )
    table.add_column("#",        style="dim",        width=3)
    table.add_column("Title",    style="white",       max_width=52)
    table.add_column("Repo",     style="cyan",        max_width=28)
    table.add_column("Comments", justify="center",    width=9)
    table.add_column("State",    justify="center",    width=8)

    for i, issue in enumerate(results, 1):
        state_icon = _STATE_ICON.get(issue["state"], "❓")
        table.add_row(
            str(i),
            f"[link={issue['url']}]{issue['title'][:52]}[/link]",
            issue["repo"],
            str(issue["comments"]),
            state_icon,
        )

    console.print(table)
    console.print("[dim]↑ Click any title to open the issue on GitHub[/dim]\n")


def _detect_language(trace: str) -> str:
    if "Traceback (most recent call last)" in trace:
        return "python"
    if ".java:" in trace:
        return "java"
    if "goroutine" in trace or "panic:" in trace:
        return "go"
    if ".js:" in trace:
        return "node"
    return "csharp"