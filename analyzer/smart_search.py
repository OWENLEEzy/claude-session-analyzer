"""Smart search for Claude Code conversation history."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .core import AnalysisResult, SessionAnalyzer
from .intent_analyzer import IntentAnalysisResult, IntentAnalyzer
from .reranker import RerankingWeights, ResultReranker

logger = logging.getLogger(__name__)


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
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "similarity": self.similarity,
            "goals": self.goals,
            "actions": self.actions,
            "outcome": self.outcome,
            "metadata": self.metadata,
        }


@dataclass
class SmartSearchResult:
    """Complete smart search result including analysis details."""

    query: str
    intent: IntentAnalysisResult
    results: list[SearchResult] = field(default_factory=list)
    total_found: int = 0
    search_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "intent": {
                "concepts": self.intent.concepts,
                "time_hint": self.intent.time_hint,
                "project_hint": self.intent.project_hint,
            },
            "results": [r.to_dict() for r in self.results],
            "total_found": self.total_found,
            "search_time_ms": self.search_time_ms,
        }

    def get_top_sessions(self, limit: int = 5) -> list[SearchResult]:
        """Get top N sessions."""
        return self.results[:limit]


class LocalSessionSearcher:
    """Search Claude Code sessions from local filesystem."""

    def __init__(self, claude_dir: Path | None = None):
        """Initialize the local session searcher.

        Args:
            claude_dir: Path to Claude config directory. Defaults to ~/.claude
        """
        self.claude_dir = claude_dir or Path.home() / ".claude"
        self.projects_dir = self.claude_dir / "projects"
        self.analyzer = SessionAnalyzer()

    def find_all_sessions(self) -> list[Path]:
        """Find all session JSONL files in Claude projects directory.

        Returns:
            List of paths to session files
        """
        sessions: list[Path] = []

        if not self.projects_dir.exists():
            logger.warning(f"Claude projects directory not found: {self.projects_dir}")
            return sessions

        # Each project has its own directory with session JSONL files
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                for session_file in project_dir.glob("*.jsonl"):
                    sessions.append(session_file)

        return sessions

    def extract_session_id(self, session_path: Path) -> str:
        """Extract session ID from file path.

        Args:
            session_path: Path to session file

        Returns:
            Session ID (filename without extension)
        """
        return session_path.stem

    def extract_project_name(self, session_path: Path) -> str:
        """Extract project name from session path.

        Args:
            session_path: Path to session file

        Returns:
            Project name
        """
        # Parent directory name is the project path (encoded)
        project_dir = session_path.parent.name
        # Decode the project path (e.g., "-Users-foo-projects-myapp" -> "/Users/foo/projects/myapp")
        if project_dir.startswith("-"):
            return project_dir.replace("-", "/")
        return project_dir

    def read_session_content(self, session_path: Path) -> str:
        """Read and concatenate all text content from a session file.

        Args:
            session_path: Path to session JSONL file

        Returns:
            Combined text content
        """
        content_parts = []

        try:
            with open(session_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            # Extract text from different entry types
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
        except Exception as e:
            logger.debug(f"Error reading session {session_path}: {e}")

        return " ".join(content_parts)

    def search(
        self,
        query: str | list[str],
        mode: str = "text",  # noqa: ARG002
        limit: int = 10,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[SearchResult]:
        """Search for sessions matching the query.

        Args:
            query: Search query string or list of concept strings
            mode: Search mode (kept for API compatibility)
            limit: Maximum number of results
            since: Filter sessions modified after this datetime
            until: Filter sessions modified before this datetime

        Returns:
            List of SearchResult objects
        """
        # Convert list to string if needed
        if isinstance(query, list):
            query = " ".join(query)

        query_lower = query.lower()
        query_words = set(re.findall(r"\w+", query_lower))

        # If no query words, return all sessions (filtered by time if specified)
        list_all_mode = not query_words

        results: list[tuple[float, SearchResult]] = []
        sessions = self.find_all_sessions()

        for session_path in sessions:
            try:
                # Read session content
                content = self.read_session_content(session_path)
                content_lower = content.lower()

                # Calculate simple similarity score
                content_words = set(re.findall(r"\w+", content_lower))
                common_words = query_words & content_words

                # Skip if no match (unless listing all sessions)
                if not list_all_mode and not common_words:
                    continue

                # Jaccard-like similarity with boost for multiple matches
                if list_all_mode:
                    # In list all mode, sort by timestamp (most recent first)
                    similarity = 1.0
                else:
                    similarity = len(common_words) / max(len(query_words), 1)
                    # Boost score if multiple query words match
                    if len(common_words) > 1:
                        similarity *= 1.5

                # Get session metadata using the analyzer
                session_id = self.extract_session_id(session_path)
                project_path = self.extract_project_name(session_path)

                # Try to analyze the session for goals/actions
                goals: list[str] = []
                actions: list[str] = []
                outcome = ""
                summary = content[:200] + "..." if len(content) > 200 else content

                try:
                    analysis: AnalysisResult = self.analyzer.analyze(session_path)
                    goals = analysis.goals
                    actions = analysis.actions
                    outcome = analysis.outcome or ""
                    if analysis.summary:
                        summary = analysis.summary
                except Exception as e:
                    logger.debug(f"Could not analyze session {session_id}: {e}")

                # Get file modification time as timestamp
                timestamp = datetime.fromtimestamp(session_path.stat().st_mtime)

                # Apply time filtering
                if since and timestamp < since:
                    continue
                if until and timestamp > until:
                    continue

                result = SearchResult(
                    session_id=session_id,
                    project_path=project_path,
                    summary=summary,
                    timestamp=timestamp,
                    similarity=min(similarity, 1.0),  # Cap at 1.0
                    goals=goals,
                    actions=actions,
                    outcome=outcome,
                )

                results.append((similarity, result))

            except Exception as e:
                logger.debug(f"Error processing session {session_path}: {e}")
                continue

        # Sort by similarity (descending) or by timestamp (most recent first) when listing all
        if list_all_mode:
            results.sort(key=lambda x: x[1].timestamp or datetime.min, reverse=True)
        else:
            results.sort(key=lambda x: x[0], reverse=True)

        # Return top results
        return [r for _, r in results[:limit]]


class SmartSearch:
    """Intelligent search for Claude Code conversation history."""

    intent_analyzer: IntentAnalyzer | None
    local_searcher: LocalSessionSearcher
    reranker: ResultReranker

    def __init__(
        self,
        api_key: str | None = None,
        current_project: str | None = None,
        weights: RerankingWeights | None = None,
        model: str = "claude-sonnet-4-20250514",
        claude_dir: Path | None = None,
    ):
        """Initialize smart search.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            current_project: Current project path for project matching.
            weights: Custom reranking weights.
            model: Claude model to use for intent analysis.
            claude_dir: Path to Claude config directory.
        """
        # Initialize components
        self._init_intent_analyzer(api_key, model)
        self._init_local_searcher(claude_dir)
        self._init_reranker(current_project, weights)

    def _init_intent_analyzer(self, api_key: str | None, model: str) -> None:
        """Initialize intent analyzer."""
        try:
            self.intent_analyzer = IntentAnalyzer(api_key=api_key, model=model)
        except ValueError as e:
            logger.warning(f"Failed to initialize intent analyzer: {e}")
            self.intent_analyzer = None

    def _init_local_searcher(self, claude_dir: Path | None) -> None:
        """Initialize local session searcher."""
        self.local_searcher = LocalSessionSearcher(claude_dir=claude_dir)

    def _init_reranker(
        self,
        current_project: str | None,
        weights: RerankingWeights | None,
    ) -> None:
        """Initialize reranker."""
        self.reranker = ResultReranker(
            weights=weights,
            current_project=current_project,
        )

    def search(
        self,
        query: str,
        limit: int = 5,
        fetch_limit: int = 10,
    ) -> SmartSearchResult:
        """Perform smart search for conversations.

        Args:
            query: Natural language search query
            limit: Number of results to return
            fetch_limit: Number of results to fetch before reranking

        Returns:
            SmartSearchResult with ranked results
        """
        import time

        start_time = time.time()

        result = SmartSearchResult(query=query, intent=IntentAnalysisResult())

        # Step 1: Analyze intent
        if self.intent_analyzer:
            result.intent = self.intent_analyzer.analyze(query)
        else:
            # Fallback: simple keyword extraction
            result.intent = self._fallback_intent_analysis(query)

        logger.info(f"Intent analysis: concepts={result.intent.concepts}")

        # Step 2: Search using local searcher
        try:
            raw_results = self.local_searcher.search(
                query=result.intent.concepts,
                limit=fetch_limit,
            )
            result.total_found = len(raw_results)
            logger.info(f"Local search returned {len(raw_results)} results")
        except Exception as e:
            logger.error(f"Local search failed: {e}")
            raw_results = []

        # Step 3: Rerank results
        if raw_results:
            result.results = self.reranker.rerank(
                results=raw_results,
                project_hint=result.intent.project_hint,
                time_hint=result.intent.time_hint,
            )
            result.results = result.results[:limit]

        result.search_time_ms = (time.time() - start_time) * 1000

        return result

    def _fallback_intent_analysis(self, query: str) -> IntentAnalysisResult:
        """Fallback intent analysis when LLM is not available."""
        # Simple keyword extraction
        stopwords = {"继续", "做", "搞", "想", "要", "the", "for", "to", "a", "an", "and", "or"}
        words = re.findall(r"[\w\u4e00-\u9fff]+", query.lower())

        concepts = [w for w in words if w not in stopwords and len(w) > 1][:5]

        # Detect time hint
        time_hint = "all_time"
        if any(kw in query for kw in ["最近", "上次", "刚才", "recent", "last"]):
            time_hint = "recent"

        return IntentAnalysisResult(
            concepts=concepts,
            time_hint=time_hint,
            project_hint=None,
        )

    def set_current_project(self, project_path: str) -> None:
        """Set current project for better project matching."""
        self.reranker.set_current_project(project_path)

    def search_and_format(
        self,
        query: str,
        limit: int = 5,
        format_type: str = "text",
    ) -> str:
        """Search and return formatted results.

        Args:
            query: Natural language search query
            limit: Number of results to return
            format_type: "text", "json", or "markdown"

        Returns:
            Formatted string of search results
        """
        result = self.search(query, limit=limit)

        if format_type == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

        if format_type == "markdown":
            lines = [f"## Search Results for: {query}\n"]
            lines.append(f"**Concepts:** {', '.join(result.intent.concepts)}\n")

            if not result.results:
                lines.append("\n*No results found.*\n")
            else:
                for i, r in enumerate(result.results, 1):
                    lines.append(f"\n### {i}. {r.session_id[:20]}...")
                    lines.append(f"- **Project:** {r.project_path}")
                    lines.append(f"- **Summary:** {r.summary[:100]}...")
                    lines.append(f"- **Score:** {r.similarity:.3f}")

            return "\n".join(lines)

        # Default text format
        lines = [f"Search: {query}"]
        lines.append(f"Concepts: {', '.join(result.intent.concepts)}")
        lines.append("")

        if not result.results:
            lines.append("No results found.")
        else:
            for i, r in enumerate(result.results, 1):
                lines.append(f"\n{i}. [{r.session_id[:16]}...] Score: {r.similarity:.3f}")
                lines.append(f"   Project: {r.project_path}")
                lines.append(f"   Summary: {r.summary[:80]}...")

        return "\n".join(lines)


# Convenience function for quick searches
def quick_search(
    query: str,
    limit: int = 5,
    current_project: str | None = None,  # noqa: ARG001
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[SearchResult]:
    """Quick smart search function.

    Args:
        query: Natural language search query
        limit: Number of results to return
        current_project: Current project path (kept for API compatibility)
        since: Filter sessions modified after this datetime
        until: Filter sessions modified before this datetime

    Returns:
        List of SearchResult objects
    """
    # Use LocalSessionSearcher directly for time filtering support
    searcher = LocalSessionSearcher()
    return searcher.search(query, limit=limit, since=since, until=until)
