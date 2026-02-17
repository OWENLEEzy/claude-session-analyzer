"""Unit tests for smart search module."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from analyzer.intent_analyzer import IntentAnalysisResult
from analyzer.reranker import ResultReranker
from analyzer.smart_search import (
    LocalSessionSearcher,
    SearchResult,
    SmartSearch,
    SmartSearchResult,
    quick_search,
)


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        result = SearchResult(
            session_id="test-1",
            project_path="/test",
            summary="Test summary",
        )
        assert result.session_id == "test-1"
        assert result.project_path == "/test"
        assert result.summary == "Test summary"
        assert result.similarity == 0.0
        assert result.goals == []
        assert result.actions == []
        assert result.outcome == ""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = SearchResult(
            session_id="s-1",
            project_path="/p",
            summary="Test",
            similarity=0.9,
            goals=["goal1"],
            actions=["action1"],
            outcome="success",
        )

        d = result.to_dict()

        assert d["session_id"] == "s-1"
        assert d["project_path"] == "/p"
        assert d["summary"] == "Test"
        assert d["similarity"] == 0.9
        assert d["goals"] == ["goal1"]
        assert d["actions"] == ["action1"]
        assert d["outcome"] == "success"


class TestSmartSearchResult:
    """Tests for SmartSearchResult."""

    def test_default_values(self) -> None:
        """Test default values."""
        result = SmartSearchResult(
            query="test",
            intent=IntentAnalysisResult(),
        )
        assert result.query == "test"
        assert result.results == []
        assert result.total_found == 0
        assert result.search_time_ms == 0.0

    def test_get_top_sessions(self) -> None:
        """Test getting top sessions."""
        results = [
            SearchResult(session_id=f"s-{i}", project_path="/p", summary=f"Result {i}")
            for i in range(10)
        ]

        search_result = SmartSearchResult(
            query="test",
            intent=IntentAnalysisResult(),
            results=results,
        )

        top_5 = search_result.get_top_sessions(5)
        assert len(top_5) == 5
        assert top_5[0].session_id == "s-0"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        intent = IntentAnalysisResult(
            concepts=["auth", "JWT"],
            time_hint="recent",
            project_hint="my-project",
        )
        results = [
            SearchResult(
                session_id="s-1",
                project_path="/p",
                summary="Test",
                similarity=0.9,
            ),
        ]

        search_result = SmartSearchResult(
            query="test query",
            intent=intent,
            results=results,
            total_found=1,
            search_time_ms=100.0,
        )

        d = search_result.to_dict()

        assert d["query"] == "test query"
        assert d["intent"]["concepts"] == ["auth", "JWT"]
        assert len(d["results"]) == 1
        assert d["total_found"] == 1


class TestLocalSessionSearcher:
    """Tests for LocalSessionSearcher."""

    def test_extract_session_id(self, tmp_path: Path) -> None:
        """Test extracting session ID from path."""
        searcher = LocalSessionSearcher(claude_dir=tmp_path)
        session_path = tmp_path / "project" / "abc123.jsonl"
        assert searcher.extract_session_id(session_path) == "abc123"

    def test_extract_project_name(self, tmp_path: Path) -> None:
        """Test extracting project name from path."""
        searcher = LocalSessionSearcher(claude_dir=tmp_path)

        # Test with encoded path
        session_path = tmp_path / "-Users-foo-projects-myapp" / "session.jsonl"
        assert searcher.extract_project_name(session_path) == "/Users/foo/projects/myapp"

    def test_find_all_sessions_empty(self, tmp_path: Path) -> None:
        """Test finding sessions in empty directory."""
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()

        searcher = LocalSessionSearcher(claude_dir=tmp_path)
        sessions = searcher.find_all_sessions()

        assert sessions == []

    def test_find_all_sessions(self, tmp_path: Path) -> None:
        """Test finding sessions."""
        projects_dir = tmp_path / "projects"
        project_dir = projects_dir / "my-project"
        project_dir.mkdir(parents=True)

        # Create some session files
        (project_dir / "session1.jsonl").touch()
        (project_dir / "session2.jsonl").touch()

        searcher = LocalSessionSearcher(claude_dir=tmp_path)
        sessions = searcher.find_all_sessions()

        assert len(sessions) == 2

    def test_read_session_content(self, tmp_path: Path) -> None:
        """Test reading session content."""
        projects_dir = tmp_path / "projects"
        project_dir = projects_dir / "my-project"
        project_dir.mkdir(parents=True)

        session_file = project_dir / "session.jsonl"
        session_file.write_text('{"message": {"content": "Hello world"}}\n')

        searcher = LocalSessionSearcher(claude_dir=tmp_path)
        content = searcher.read_session_content(session_file)

        assert "Hello world" in content


class TestSmartSearch:
    """Tests for SmartSearch class."""

    @pytest.fixture
    def mock_searcher(self) -> SmartSearch:
        """Create SmartSearch with mock components."""
        searcher = object.__new__(SmartSearch)
        searcher.intent_analyzer = None  # Will use fallback
        searcher.local_searcher = MagicMock()
        searcher.reranker = ResultReranker()
        return searcher

    def test_fallback_intent_analysis(self, mock_searcher: SmartSearch) -> None:
        """Test fallback intent analysis."""
        result = mock_searcher._fallback_intent_analysis("继续做用户认证功能")

        assert len(result.concepts) > 0
        assert result.time_hint in ["recent", "all_time"]

    def test_fallback_detects_recent(self, mock_searcher: SmartSearch) -> None:
        """Test fallback detects recent time hint."""
        result = mock_searcher._fallback_intent_analysis("最近做认证")
        assert result.time_hint == "recent"

    def test_search_returns_result(self, mock_searcher: SmartSearch) -> None:
        """Test search returns SmartSearchResult."""
        mock_results = [
            SearchResult(
                session_id="test-1",
                project_path="/p",
                summary="Test result",
                similarity=0.8,
            ),
        ]
        mock_searcher.local_searcher.search.return_value = mock_results

        result = mock_searcher.search("test query")

        assert isinstance(result, SmartSearchResult)
        assert result.query == "test query"

    def test_search_respects_limit(self, mock_searcher: SmartSearch) -> None:
        """Test search respects limit parameter."""
        mock_results = [
            SearchResult(session_id=f"s-{i}", project_path="/p", summary=f"R{i}", similarity=0.5)
            for i in range(10)
        ]
        mock_searcher.local_searcher.search.return_value = mock_results

        result = mock_searcher.search("test", limit=3)

        assert len(result.results) <= 3

    def test_set_current_project(self, mock_searcher: SmartSearch) -> None:
        """Test setting current project."""
        mock_searcher.set_current_project("/my/project")
        assert mock_searcher.reranker.current_project == "/my/project"

    def test_search_and_format_text(self, mock_searcher: SmartSearch) -> None:
        """Test search_and_format with text format."""
        mock_results = [
            SearchResult(
                session_id="test-session-id-123",
                project_path="/project/test",
                summary="Test result summary",
                similarity=0.85,
            ),
        ]
        mock_searcher.local_searcher.search.return_value = mock_results

        output = mock_searcher.search_and_format("test", format_type="text")

        assert "test" in output
        assert "Test result summary" in output

    def test_search_and_format_json(self, mock_searcher: SmartSearch) -> None:
        """Test search_and_format with JSON format."""
        import json

        mock_results = [
            SearchResult(
                session_id="test-1",
                project_path="/p",
                summary="Test",
                similarity=0.8,
            ),
        ]
        mock_searcher.local_searcher.search.return_value = mock_results

        output = mock_searcher.search_and_format("test", format_type="json")

        # Should be valid JSON
        data = json.loads(output)
        assert "query" in data
        assert "results" in data

    def test_search_and_format_markdown(self, mock_searcher: SmartSearch) -> None:
        """Test search_and_format with markdown format."""
        mock_results = [
            SearchResult(
                session_id="test-1",
                project_path="/p",
                summary="Test result",
                similarity=0.9,
            ),
        ]
        mock_searcher.local_searcher.search.return_value = mock_results

        output = mock_searcher.search_and_format("test", format_type="markdown")

        assert "##" in output  # Markdown headers
        assert "Test result" in output

    def test_search_no_results(self, mock_searcher: SmartSearch) -> None:
        """Test search with no results."""
        mock_searcher.local_searcher.search.return_value = []

        result = mock_searcher.search("nonexistent")

        assert result.total_found == 0
        assert result.results == []

    def test_search_and_format_no_results(self, mock_searcher: SmartSearch) -> None:
        """Test search_and_format with no results."""
        mock_searcher.local_searcher.search.return_value = []

        output = mock_searcher.search_and_format("nonexistent", format_type="text")

        assert "No results" in output


class TestSmartSearchConvenience:
    """Tests for convenience function."""

    def test_quick_search_function(self) -> None:
        """Test quick_search convenience function."""
        mock_results = [
            SearchResult(
                session_id="test-1",
                project_path="/p",
                summary="Test",
                similarity=0.8,
            ),
        ]

        # Create a proper mock searcher
        mock_searcher = object.__new__(SmartSearch)
        mock_searcher.intent_analyzer = None
        mock_searcher.local_searcher = MagicMock()
        mock_searcher.local_searcher.search.return_value = mock_results
        mock_searcher.reranker = ResultReranker()

        with patch("analyzer.smart_search.SmartSearch", return_value=mock_searcher):
            results = quick_search("test query")
            assert isinstance(results, list)


class TestSmartSearchErrorHandling:
    """Tests for error handling in SmartSearch."""

    def test_search_with_searcher_error(self) -> None:
        """Test search handles searcher errors gracefully."""
        # Create searcher with mock that raises error
        searcher = object.__new__(SmartSearch)
        searcher.intent_analyzer = None
        searcher.reranker = ResultReranker()

        # Create a mock searcher that raises an error
        mock_local_searcher = MagicMock()
        mock_local_searcher.search.side_effect = Exception("Search error")
        searcher.local_searcher = mock_local_searcher

        # Search should not crash
        result = searcher.search("test query")
        assert result.total_found == 0

    def test_search_with_project_hint(self) -> None:
        """Test search with project hint in results."""
        mock_results = [
            SearchResult(
                session_id="test-1",
                project_path="/project/auth-service",
                summary="Auth implementation",
                timestamp=datetime.now(),
                similarity=0.9,
            ),
        ]

        searcher = object.__new__(SmartSearch)
        searcher.intent_analyzer = None
        searcher.local_searcher = MagicMock()
        searcher.local_searcher.search.return_value = mock_results
        searcher.reranker = ResultReranker(current_project="/project/auth")

        result = searcher.search("auth")
        assert len(result.results) > 0

    def test_search_with_recent_time_hint(self) -> None:
        """Test search with recent time hint."""
        now = datetime.now()
        mock_results = [
            SearchResult(
                session_id="recent",
                project_path="/p",
                summary="Recent work",
                timestamp=now - timedelta(hours=1),
                similarity=0.7,
            ),
            SearchResult(
                session_id="old",
                project_path="/p",
                summary="Old work",
                timestamp=now - timedelta(days=30),
                similarity=0.7,
            ),
        ]

        searcher = object.__new__(SmartSearch)
        searcher.intent_analyzer = None
        searcher.local_searcher = MagicMock()
        searcher.local_searcher.search.return_value = mock_results
        searcher.reranker = ResultReranker()

        # Search with "recent" keyword
        result = searcher.search("最近做认证")
        assert len(result.results) > 0
        # Recent should be ranked higher
        assert result.results[0].session_id == "recent"

    def test_search_and_format_with_project_hint(self) -> None:
        """Test search_and_format includes project hint."""
        mock_results = [
            SearchResult(
                session_id="test-1",
                project_path="/project/auth",
                summary="Test",
                similarity=0.8,
            ),
        ]

        searcher = object.__new__(SmartSearch)
        searcher.intent_analyzer = None
        searcher.local_searcher = MagicMock()
        searcher.local_searcher.search.return_value = mock_results
        searcher.reranker = ResultReranker()

        output = searcher.search_and_format("auth project")
        assert "auth project" in output
