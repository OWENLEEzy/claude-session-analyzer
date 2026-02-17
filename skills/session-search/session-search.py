#!/usr/bin/env python3
"""Search Claude Code sessions - self-contained skill script."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class SearchResult:
    """A single search result from Claude Code sessions."""

    session_id: str
    project_path: str
    summary: str
    timestamp: datetime | None = None
    similarity: float = 0.0
    goals: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    outcome: str = ""


def parse_date(date_str: str, end_of_day: bool = False) -> datetime | None:
    """Parse date string to datetime.

    Supports:
    - YYYY-MM-DD format
    - Relative dates: 'yesterday', 'today', '7days', '30days', etc.

    Args:
        date_str: Date string to parse
        end_of_day: If True, return end of day (23:59:59) instead of start (00:00:00)
    """
    date_str = date_str.lower().strip()
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
        try:
            base = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    if end_of_day:
        return base.replace(hour=23, minute=59, second=59)
    return base


def find_all_sessions(claude_dir: Path) -> list[Path]:
    """Find all session JSONL files in Claude projects directory."""
    sessions = []
    projects_dir = claude_dir / "projects"

    if not projects_dir.exists():
        return sessions

    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir():
            for session_file in project_dir.glob("*.jsonl"):
                sessions.append(session_file)

    return sessions


def extract_session_id(session_path: Path) -> str:
    """Extract session ID from file path."""
    return session_path.stem


def extract_project_name(session_path: Path) -> str:
    """Extract project name from session path."""
    project_dir = session_path.parent.name
    if project_dir.startswith("-"):
        return project_dir.replace("-", "/")
    return project_dir


def read_session_content(session_path: Path) -> str:
    """Read and concatenate all text content from a session file."""
    content_parts = []

    try:
        with open(session_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if "message" in entry:
                            msg = entry["message"]
                            if isinstance(msg, dict) and "content" in msg:
                                msg_content = msg["content"]
                                if isinstance(msg_content, str):
                                    content_parts.append(msg_content)
                                elif isinstance(msg_content, list):
                                    for block in msg_content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            content_parts.append(block.get("text", ""))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass

    return " ".join(content_parts)


def search_sessions(
    query: str,
    limit: int = 5,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[SearchResult]:
    """Search for sessions matching the query."""
    claude_dir = Path.home() / ".claude"

    query_lower = query.lower()
    query_words = set(re.findall(r"\w+", query_lower))

    # If no query words, list all sessions (filtered by time if specified)
    list_all_mode = not query_words

    results: list[tuple[float, SearchResult]] = []
    sessions = find_all_sessions(claude_dir)

    for session_path in sessions:
        try:
            content = read_session_content(session_path)
            content_lower = content.lower()

            content_words = set(re.findall(r"\w+", content_lower))
            common_words = query_words & content_words

            # Skip if no match (unless listing all sessions)
            if not list_all_mode and not common_words:
                continue

            timestamp = datetime.fromtimestamp(session_path.stat().st_mtime)

            # Apply time filtering
            if since and timestamp < since:
                continue
            if until and timestamp > until:
                continue

            # Calculate similarity
            if list_all_mode:
                similarity = 1.0
            else:
                similarity = len(common_words) / max(len(query_words), 1)
                if len(common_words) > 1:
                    similarity *= 1.5

            session_id = extract_session_id(session_path)
            project_path = extract_project_name(session_path)

            summary = content[:200] + "..." if len(content) > 200 else content

            result = SearchResult(
                session_id=session_id,
                project_path=project_path,
                summary=summary,
                timestamp=timestamp,
                similarity=min(similarity, 1.0),
            )

            results.append((similarity, result))

        except Exception:
            continue

    # Sort by similarity or timestamp
    if list_all_mode:
        results.sort(key=lambda x: x[1].timestamp or datetime.min, reverse=True)
    else:
        results.sort(key=lambda x: x[0], reverse=True)

    return [r for _, r in results[:limit]]


def format_results(results: list[SearchResult], query: str, time_desc: str = "") -> str:
    """Format search results for display."""
    if not results:
        if query:
            return f"No sessions found matching: {query}"
        else:
            return f"No sessions found{time_desc}"

    if query:
        lines = [f'Found {len(results)} sessions matching "{query}"{time_desc}:\n']
    else:
        lines = [f"Found {len(results)} sessions{time_desc}:\n"]

    for i, r in enumerate(results, 1):
        time_str = ""
        if r.timestamp:
            time_str = r.timestamp.strftime("%Y-%m-%d %H:%M")

        session_id = r.session_id
        session_id_short = session_id[:16] + "..." if len(session_id) > 16 else session_id

        lines.append(f"{i}. [{session_id_short}] {time_str}  {r.project_path}")

        if r.goals:
            goals_str = ", ".join(r.goals[:3])
            lines.append(f"   Goals: {goals_str}")

        if r.actions:
            actions_str = ", ".join(r.actions[:3])
            lines.append(f"   Actions: {actions_str}")

        if r.outcome:
            lines.append(f"   Outcome: {r.outcome}")

        lines.append(f"   Resume: claude --resume {session_id}")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search Claude Code conversation history",
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Search query (can be empty to list all sessions)",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=5,
        help="Number of results (default: 5)",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Start date (YYYY-MM-DD or 'yesterday', '7days', etc.)",
    )
    parser.add_argument(
        "--until",
        type=str,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="List all sessions",
    )

    args = parser.parse_args()

    query = " ".join(args.query) if args.query else ""
    limit = 9999 if args.all else args.limit

    since = parse_date(args.since) if args.since else None
    until = parse_date(args.until, end_of_day=True) if args.until else None

    # Build time description
    time_desc = ""
    if since or until:
        parts = []
        if since:
            parts.append(f"since {since.strftime('%Y-%m-%d')}")
        if until:
            parts.append(f"until {until.strftime('%Y-%m-%d')}")
        time_desc = f" ({', '.join(parts)})"

    try:
        results = search_sessions(query, limit=limit, since=since, until=until)
        output = format_results(results, query, time_desc)
        print(output)
    except Exception as e:
        print(f"Error searching sessions: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
