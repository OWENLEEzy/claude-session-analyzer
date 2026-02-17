"""Unit tests for core analysis module."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from analyzer.core import AnalysisResult, SessionAnalyzer


@pytest.fixture
def analyzer() -> SessionAnalyzer:
    """Create analyzer instance."""
    return SessionAnalyzer()


@pytest.fixture
def sample_session() -> str:
    """Create sample session content."""
    return json.dumps(
        {
            "text": """
        我想要实现用户认证功能。
        我会创建 AuthModule.ts 文件。
        运行测试，所有测试通过。
        成功完成了用户认证模块的实现。
        """,
        }
    )


@pytest.fixture
def temp_session_file(sample_session: str) -> Generator[Path, None, None]:
    """Create temporary session file."""
    fd, path = tempfile.mkstemp(suffix=".jsonl", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(sample_session)
        yield Path(path)
    finally:
        os.unlink(path)


class TestSessionAnalyzer:
    """Tests for SessionAnalyzer class."""

    def test_analyzer_initialization(self, analyzer: SessionAnalyzer) -> None:
        """Test analyzer can be initialized."""
        assert analyzer is not None

    def test_extract_keywords(self, analyzer: SessionAnalyzer) -> None:
        """Test keyword extraction."""
        text = "我想要实现用户认证功能"
        keywords = analyzer._extract_keywords(text)

        assert len(keywords) > 0
        assert "实现" in keywords or "用户" in keywords

    def test_extract_goals(self, analyzer: SessionAnalyzer) -> None:
        """Test goal extraction."""
        text = "我想要实现用户认证功能，请帮我完成这个任务。"
        keywords = analyzer._extract_keywords(text)
        goals = analyzer._extract_goals(text, keywords)

        assert len(goals) > 0
        assert any("认证" in g for g in goals)

    def test_extract_actions(self, analyzer: SessionAnalyzer) -> None:
        """Test action extraction."""
        text = "我修改了 AuthModule.ts 文件，并运行了测试。"
        keywords = analyzer._extract_keywords(text)
        actions = analyzer._extract_actions(text, keywords)

        assert len(actions) > 0
        assert any("AuthModule.ts" in a for a in actions)

    def test_determine_outcome_success(self, analyzer: SessionAnalyzer) -> None:
        """Test outcome determination for success case."""
        text = "所有测试通过，成功完成了任务。"
        outcome = analyzer._determine_outcome(text)

        assert outcome == "success"

    def test_determine_outcome_failure(self, analyzer: SessionAnalyzer) -> None:
        """Test outcome determination for failure case."""
        text = "出现错误，测试失败了。"
        outcome = analyzer._determine_outcome(text)

        assert outcome == "failure"

    def test_determine_outcome_partial(self, analyzer: SessionAnalyzer) -> None:
        """Test outcome determination for partial case."""
        text = "部分功能已实现，还有一些待处理的问题。"
        outcome = analyzer._determine_outcome(text)

        assert outcome == "partial"

    def test_calculate_confidence(
        self,
        analyzer: SessionAnalyzer,
    ) -> None:
        """Test confidence calculation."""
        result = AnalysisResult(
            goals=["实现认证"],
            actions=["创建文件", "运行测试"],
            outcome="success",
        )
        confidence = analyzer._calculate_confidence(result)

        assert confidence >= 0.5
        assert confidence <= 1.0

    def test_generate_summary(self, analyzer: SessionAnalyzer) -> None:
        """Test summary generation."""
        result = AnalysisResult(
            goals=["实现认证"],
            actions=["创建 AuthModule.ts"],
            outcome="success",
            confidence=0.8,
        )
        summary = analyzer._generate_summary(result)

        assert "【目标】" in summary
        assert "【行动】" in summary
        assert "【结果】" in summary

    def test_analyze_file(
        self,
        analyzer: SessionAnalyzer,
        temp_session_file: Path,
    ) -> None:
        """Test full analysis of a session file."""
        result = analyzer.analyze(temp_session_file)

        assert isinstance(result, AnalysisResult)
        assert len(result.goals) > 0 or len(result.actions) > 0
        assert result.confidence >= 0.0

    def test_analyze_nonexistent_file(self, analyzer: SessionAnalyzer) -> None:
        """Test analyzing a non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/path.jsonl")


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values are correct."""
        result = AnalysisResult()

        assert result.goals == []
        assert result.actions == []
        assert result.outcome is None
        assert result.confidence == 0.0
        assert result.summary == ""
        assert result.raw_keywords == []

    def test_custom_values(self) -> None:
        """Test custom values are set correctly."""
        result = AnalysisResult(
            goals=["实现认证"],
            actions=["创建文件"],
            outcome="success",
            confidence=0.9,
            summary="测试摘要",
        )

        assert result.goals == ["实现认证"]
        assert result.actions == ["创建文件"]
        assert result.outcome == "success"
        assert result.confidence == 0.9
        assert result.summary == "测试摘要"


class TestSessionAnalyzerExtended:
    """Extended tests for SessionAnalyzer to improve coverage."""

    @pytest.fixture
    def analyzer(self) -> SessionAnalyzer:
        """Create analyzer instance."""
        return SessionAnalyzer()

    def test_analyze_with_user_dict(self, tmp_path: Path) -> None:
        """Test analyzer with custom user dictionary."""
        dict_path = tmp_path / "user_dict.txt"
        dict_path.write_text("自定义词\n")
        analyzer = SessionAnalyzer(user_dict_path=str(dict_path))
        assert analyzer is not None

    def test_read_session_invalid_json(self, analyzer: SessionAnalyzer, tmp_path: Path) -> None:
        """Test reading session with invalid JSON lines."""
        session_file = tmp_path / "test.jsonl"
        session_file.write_text('{"text": "valid"}\ninvalid json\n{"text": "also valid"}\n')
        content = analyzer._read_session(session_file)
        assert len(content) == 2  # Invalid line should be skipped

    def test_extract_text_with_message(self, analyzer: SessionAnalyzer) -> None:
        """Test extracting text from message format."""
        content = [{"message": "test message"}]
        text = analyzer._extract_text(content)
        assert "test message" in text

    def test_extract_text_with_dict_message(self, analyzer: SessionAnalyzer) -> None:
        """Test extracting text from dict message format."""
        content = [{"message": {"content": "dict content"}}]
        text = analyzer._extract_text(content)
        assert "dict content" in text

    def test_extract_text_with_nested_content(self, analyzer: SessionAnalyzer) -> None:
        """Test extracting text from nested content format."""
        content = [{"content": [{"text": "nested text"}]}]
        text = analyzer._extract_text(content)
        assert "nested text" in text

    def test_extract_goals_no_match(self, analyzer: SessionAnalyzer) -> None:
        """Test goal extraction with no matching keywords."""
        text = "这是一段普通的文本，没有任何关键词。"
        keywords = analyzer._extract_keywords(text)
        goals = analyzer._extract_goals(text, keywords)
        assert goals == []

    def test_extract_actions_no_match(self, analyzer: SessionAnalyzer) -> None:
        """Test action extraction with no matching keywords."""
        text = "这是一段普通的文本。"
        keywords = analyzer._extract_keywords(text)
        actions = analyzer._extract_actions(text, keywords)
        assert actions == []

    def test_determine_outcome_no_indicators(self, analyzer: SessionAnalyzer) -> None:
        """Test outcome determination with no indicators."""
        text = "这是一段普通的文本。"
        outcome = analyzer._determine_outcome(text)
        assert outcome is None

    def test_determine_outcome_mixed_indicators(self, analyzer: SessionAnalyzer) -> None:
        """Test outcome determination with mixed indicators."""
        text = "成功完成了一些任务，但还有一些问题需要处理。"
        outcome = analyzer._determine_outcome(text)
        # Should be partial when both success and partial indicators exist
        assert outcome in ["success", "partial"]

    def test_calculate_confidence_low(self, analyzer: SessionAnalyzer) -> None:
        """Test confidence calculation with minimal data."""
        result = AnalysisResult()
        confidence = analyzer._calculate_confidence(result)
        assert confidence == 0.0

    def test_calculate_confidence_medium(self, analyzer: SessionAnalyzer) -> None:
        """Test confidence calculation with medium data."""
        result = AnalysisResult(
            goals=["目标1"],
            outcome="success",
        )
        confidence = analyzer._calculate_confidence(result)
        assert confidence >= 0.4

    def test_generate_summary_no_outcome(self, analyzer: SessionAnalyzer) -> None:
        """Test summary generation without outcome."""
        result = AnalysisResult(
            goals=["目标1"],
            actions=["行动1"],
            confidence=0.7,
        )
        summary = analyzer._generate_summary(result)
        assert "【目标】" in summary
        assert "【结果】" not in summary

    def test_generate_summary_failure(self, analyzer: SessionAnalyzer) -> None:
        """Test summary generation with failure outcome."""
        result = AnalysisResult(
            goals=["目标1"],
            outcome="failure",
            confidence=0.5,
        )
        summary = analyzer._generate_summary(result)
        assert "遇到问题" in summary

    def test_analyze_batch(self, analyzer: SessionAnalyzer, tmp_path: Path) -> None:
        """Test batch analysis."""
        # Create multiple session files
        for i in range(3):
            session_file = tmp_path / f"session_{i}.jsonl"
            session_file.write_text(f'{{"text": "测试会话 {i}。实现功能。成功完成。"}}')

        paths = [tmp_path / f"session_{i}.jsonl" for i in range(3)]
        results = analyzer.analyze_batch(paths)
        assert len(results) == 3

    def test_extract_goal_phrase_long_sentence(self, analyzer: SessionAnalyzer) -> None:
        """Test goal phrase extraction with long sentence."""
        long_sentence = "我想要实现一个非常非常非常非常非常非常非常非常非常非常非常长的目标功能"
        phrase = analyzer._extract_goal_phrase(long_sentence)
        assert len(phrase) <= 53  # 50 chars + "..."

    def test_extract_action_phrase_long_sentence(self, analyzer: SessionAnalyzer) -> None:
        """Test action phrase extraction with long sentence."""
        long_sentence = "我修改了一个非常非常非常非常非常非常非常非常非常非常非常长的文件路径"
        phrase = analyzer._extract_action_phrase(long_sentence)
        assert len(phrase) <= 43  # 40 chars + "..."
