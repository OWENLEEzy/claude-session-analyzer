"""Command-line interface for Claude Session Analyzer."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .core import AnalysisResult, SessionAnalyzer
from .smart_search import quick_search


def format_result(result: AnalysisResult, format_type: str = "text") -> str:
    """Format analysis result for output.

    Args:
        result: Analysis result to format
        format_type: "text", "json", or "markdown"

    Returns:
        Formatted string
    """
    if format_type == "json":
        return json.dumps(
            {
                "goals": result.goals,
                "actions": result.actions,
                "outcome": result.outcome,
                "confidence": result.confidence,
                "summary": result.summary,
            },
            ensure_ascii=False,
            indent=2,
        )

    if format_type == "markdown":
        lines = ["## Session Analysis\n"]
        if result.goals:
            lines.append("**Goals:**")
            for g in result.goals:
                lines.append(f"- {g}")
            lines.append("")
        if result.actions:
            lines.append("**Actions:**")
            for a in result.actions:
                lines.append(f"- {a}")
            lines.append("")
        if result.outcome:
            lines.append(f"**Outcome:** {result.outcome}")
            lines.append("")
        lines.append(f"**Confidence:** {result.confidence:.2f}")
        lines.append("")
        if result.summary:
            lines.append(f"**Summary:** {result.summary}")
        return "\n".join(lines)

    # Default text format
    lines = []
    if result.goals:
        lines.append("Goals:")
        for g in result.goals:
            lines.append(f"  - {g}")
    if result.actions:
        lines.append("Actions:")
        for a in result.actions:
            lines.append(f"  - {a}")
    if result.outcome:
        lines.append(f"Outcome: {result.outcome}")
    lines.append(f"Confidence: {result.confidence:.2f}")
    if result.summary:
        lines.append(f"\nSummary: {result.summary}")
    return "\n".join(lines)


def parse_date(date_str: str, end_of_day: bool = False) -> datetime | None:
    """Parse date string to datetime.

    Supports:
    - YYYY-MM-DD format
    - Relative dates: 'yesterday', 'today', '7days', '30days', etc.

    Args:
        date_str: Date string to parse
        end_of_day: If True, return end of day (23:59:59) instead of start (00:00:00)

    Returns:
        datetime object or None if parsing fails
    """
    from datetime import timedelta

    date_str = date_str.lower().strip()

    # Handle relative dates
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if date_str == "today":
        base = today
    elif date_str == "yesterday":
        base = today - timedelta(days=1)
    elif date_str == "week" or date_str == "7days":
        base = today - timedelta(days=7)
    elif date_str == "month" or date_str == "30days":
        base = today - timedelta(days=30)
    else:
        # Handle YYYY-MM-DD format
        try:
            base = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    if end_of_day:
        return base.replace(hour=23, minute=59, second=59)
    return base


def cmd_search(args: argparse.Namespace) -> int:
    """Handle search command."""
    console = Console()

    query = " ".join(args.query) if args.query else ""

    # Handle --all flag
    limit = 9999 if args.all else args.limit

    # Parse time filters
    since = None
    until = None

    if args.since:
        since = parse_date(args.since)
        if since is None:
            console.print(f"[red]Error: 无法解析日期: {args.since}[/red]")
            return 1

    if args.until:
        until = parse_date(args.until, end_of_day=True)
        if until is None:
            console.print(f"[red]Error: 无法解析日期: {args.until}[/red]")
            return 1

    try:
        results = quick_search(query, limit=limit, since=since, until=until)

        if not results:
            if query:
                console.print(f"[yellow]No sessions found matching: {query}[/yellow]")
            else:
                console.print("[yellow]No sessions found[/yellow]")
            return 0

        # Build time filter description
        time_desc = ""
        if since or until:
            parts = []
            if since:
                parts.append(f"since {since.strftime('%Y-%m-%d')}")
            if until:
                parts.append(f"until {until.strftime('%Y-%m-%d')}")
            time_desc = f" ({', '.join(parts)})"

        if args.format == "json":
            output = []
            for r in results:
                output.append(
                    {
                        "session_id": r.session_id,
                        "project_path": r.project_path,
                        "summary": r.summary,
                        "goals": r.goals,
                        "actions": r.actions,
                        "outcome": r.outcome,
                        "similarity": r.similarity,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    }
                )
            print(json.dumps(output, ensure_ascii=False, indent=2))
        elif args.format == "table":
            title = f"Search Results: {query}" if query else "Sessions"
            table = Table(title=title + time_desc)
            table.add_column("#", style="dim", width=3)
            table.add_column("Session ID", style="cyan", width=20)
            table.add_column("Project", style="green", width=25)
            table.add_column("Goals", style="white", width=30)
            table.add_column("Outcome", style="yellow", width=10)

            for i, r in enumerate(results, 1):
                goals = ", ".join(r.goals[:2]) if r.goals else "-"
                table.add_row(
                    str(i),
                    r.session_id[:20] if r.session_id else "-",
                    r.project_path[:25] if r.project_path else "-",
                    goals[:30],
                    r.outcome or "-",
                )
            console.print(table)
            console.print("\n[dim]Resume a session with: claude --resume <session-id>[/dim]")
        else:
            if query:
                console.print(
                    f'\n[bold green]Found {len(results)} sessions matching "{query}"{time_desc}:[/bold green]\n'
                )
            else:
                console.print(
                    f"\n[bold green]Found {len(results)} sessions{time_desc}:[/bold green]\n"
                )
            for i, r in enumerate(results, 1):
                # Format timestamp
                time_str = ""
                if r.timestamp:
                    time_str = r.timestamp.strftime("%Y-%m-%d %H:%M")

                # Session ID (truncate for display)
                session_id = r.session_id
                session_id_short = session_id[:16] + "..." if len(session_id) > 16 else session_id

                console.print(
                    f"[bold]{i}[/bold]. [cyan][{session_id_short}][/cyan] {time_str}  [dim]{r.project_path}[/dim]"
                )

                # Goals
                if r.goals:
                    goals_str = ", ".join(r.goals[:3])
                    console.print(f"   [green]Goals:[/green] {goals_str}")

                # Actions
                if r.actions:
                    actions_str = ", ".join(r.actions[:3])
                    console.print(f"   [blue]Actions:[/blue] {actions_str}")

                # Outcome
                if r.outcome:
                    outcome_color = (
                        "green"
                        if r.outcome == "success"
                        else "red"
                        if r.outcome == "failure"
                        else "yellow"
                    )
                    console.print(f"   [{outcome_color}]Outcome:[/{outcome_color}] {r.outcome}")

                # Resume command
                console.print(f"   [dim]Resume: claude --resume {session_id}[/dim]")
                console.print()

        return 0
    except Exception as e:
        console.print(f"[red]Search failed: {e}[/red]")
        return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """Handle analyze command."""
    console = Console()
    analyzer = SessionAnalyzer()

    paths = [Path(p) for p in args.sessions]
    results = []

    for path in paths:
        try:
            result = analyzer.analyze(path)
            results.append((path.name, result))
        except FileNotFoundError:
            console.print(f"[red]Error: File not found: {path}[/red]")
            return 1
        except Exception as e:
            console.print(f"[red]Error analyzing {path}: {e}[/red]")
            return 1

    if args.format == "json":
        output = []
        for name, result in results:
            output.append(
                {
                    "file": name,
                    "goals": result.goals,
                    "actions": result.actions,
                    "outcome": result.outcome,
                    "confidence": result.confidence,
                    "summary": result.summary,
                }
            )
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.format == "table":
        table = Table(title="Session Analysis Results")
        table.add_column("File", style="cyan")
        table.add_column("Goals", style="green")
        table.add_column("Outcome", style="yellow")
        table.add_column("Confidence", style="magenta")

        for name, result in results:
            goals = ", ".join(result.goals[:2]) if result.goals else "-"
            table.add_row(
                name[:30],
                goals[:40],
                result.outcome or "-",
                f"{result.confidence:.2f}",
            )
        console.print(table)
    else:
        for name, result in results:
            console.print(f"\n[bold cyan]{name}[/bold cyan]")
            console.print(format_result(result, "text"))

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="csa",
        description="Analyze Claude Code session transcripts",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze session files",
    )
    analyze_parser.add_argument(
        "sessions",
        nargs="+",
        help="Session files to analyze (.jsonl)",
    )
    analyze_parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json", "table", "markdown"],
        default="text",
        help="Output format",
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    # Search command
    search_parser = subparsers.add_parser(
        "search",
        help="搜索历史会话",
    )
    search_parser.add_argument(
        "query",
        nargs="*",
        help="搜索关键词或自然语言描述 (可为空以列出所有会话)",
    )
    search_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=5,
        help="返回结果数量 (默认: 5)",
    )
    search_parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json", "table"],
        default="text",
        help="输出格式",
    )
    search_parser.add_argument(
        "--since",
        type=str,
        help="起始时间 (YYYY-MM-DD 或相对日期如 'yesterday', '7days')",
    )
    search_parser.add_argument(
        "--until",
        type=str,
        help="结束时间 (YYYY-MM-DD)",
    )
    search_parser.add_argument(
        "--all",
        action="store_true",
        help="列出所有会话 (等同于设置很大的 limit)",
    )
    search_parser.set_defaults(func=cmd_search)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    result = args.func(args)
    return int(result) if result is not None else 0


if __name__ == "__main__":
    sys.exit(main())
