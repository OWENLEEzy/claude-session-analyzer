#!/usr/bin/env python3
"""Search Claude Code sessions - self-contained skill script."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


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
                                        if (
                                            isinstance(block, dict)
                                            and block.get("type") == "text"
                                        ):
                                            content_parts.append(block.get("text", ""))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass

    return " ".join(content_parts)


def search_sessions(query: str, limit: int = 5) -> list[SearchResult]:
    """Search for sessions matching the query."""
    claude_dir = Path.home() / ".claude"

    query_lower = query.lower()
    query_words = set(re.findall(r"\w+", query_lower))

    results: list[tuple[float, SearchResult]] = []
    sessions = find_all_sessions(claude_dir)

    for session_path in sessions:
        try:
            content = read_session_content(session_path)
            content_lower = content.lower()

            content_words = set(re.findall(r"\w+", content_lower))
            common_words = query_words & content_words

            if not common_words:
                continue

            similarity = len(common_words) / max(len(query_words), 1)
            if len(common_words) > 1:
                similarity *= 1.5

            session_id = extract_session_id(session_path)
            project_path = extract_project_name(session_path)

            summary = content[:200] + "..." if len(content) > 200 else content

            timestamp = datetime.fromtimestamp(session_path.stat().st_mtime)

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

    results.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in results[:limit]]


def format_results(results: list[SearchResult], query: str) -> str:
    """Format search results for display."""
    if not results:
        return f"No sessions found matching: {query}"

    lines = [f'Found {len(results)} sessions matching "{query}":\n']

    for i, r in enumerate(results, 1):
        time_str = ""
        if r.timestamp:
            time_str = r.timestamp.strftime("%Y-%m-%d %H:%M")

        session_id = r.session_id
        session_id_short = (
            session_id[:16] + "..." if len(session_id) > 16 else session_id
        )

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
    if len(sys.argv) < 2:
        print("Usage: session-search.py <query>")
        print("\nSearch your Claude Code conversation history.")
        print("Example: session-search.py authentication")
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    try:
        results = search_sessions(query, limit=5)
        output = format_results(results, query)
        print(output)
    except Exception as e:
        print(f"Error searching sessions: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
