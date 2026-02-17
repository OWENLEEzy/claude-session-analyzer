"""Unit tests for intent analyzer module."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from analyzer.intent_analyzer import IntentAnalysisResult, IntentAnalyzer


class TestIntentAnalysisResult:
    """Tests for IntentAnalysisResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values are correct."""
        result = IntentAnalysisResult()
        assert result.concepts == []
        assert result.time_hint == "all_time"
        assert result.project_hint is None
        assert result.raw_response == ""

    def test_custom_values(self) -> None:
        """Test custom values are set correctly."""
        result = IntentAnalysisResult(
            concepts=["用户认证", "JWT"],
            time_hint="recent",
            project_hint="my-project",
            raw_response="test response",
        )
        assert result.concepts == ["用户认证", "JWT"]
        assert result.time_hint == "recent"
        assert result.project_hint == "my-project"
        assert result.raw_response == "test response"


class TestIntentAnalyzerMethods:
    """Tests for IntentAnalyzer methods that don't require API key."""

    def test_parse_response_valid_json(self) -> None:
        """Test parsing valid JSON response."""
        # Create analyzer without actually initializing Anthropic client
        analyzer = object.__new__(IntentAnalyzer)
        analyzer.api_key = "test-key"
        analyzer.model = "test-model"

        json_response = """{"concepts": ["认证", "JWT"], "time_hint": "recent", "project_hint": "auth-system"}"""
        result = analyzer._parse_response(json_response)

        assert result.concepts == ["认证", "JWT"]
        assert result.time_hint == "recent"
        assert result.project_hint == "auth-system"

    def test_parse_response_with_markdown(self) -> None:
        """Test parsing JSON wrapped in markdown code block."""
        analyzer = object.__new__(IntentAnalyzer)
        analyzer.api_key = "test-key"
        analyzer.model = "test-model"

        markdown_response = """```json
{"concepts": ["认证"], "time_hint": "all_time", "project_hint": null}
```"""
        result = analyzer._parse_response(markdown_response)

        assert result.concepts == ["认证"]
        assert result.time_hint == "all_time"
        assert result.project_hint is None

    def test_parse_response_invalid_json(self) -> None:
        """Test parsing invalid JSON returns empty result."""
        analyzer = object.__new__(IntentAnalyzer)
        analyzer.api_key = "test-key"
        analyzer.model = "test-model"

        result = analyzer._parse_response("not valid json")
        assert result.concepts == []

    def test_fallback_analysis(self) -> None:
        """Test fallback analysis when LLM fails."""
        analyzer = object.__new__(IntentAnalyzer)
        analyzer.api_key = "test-key"
        analyzer.model = "test-model"

        result = analyzer._fallback_analysis(
            "继续做用户认证功能",
            "test error",
        )

        assert isinstance(result, IntentAnalysisResult)
        assert len(result.concepts) > 0
        assert "test error" in result.raw_response

    def test_fallback_detects_recent_time(self) -> None:
        """Test fallback detects recent time hint."""
        analyzer = object.__new__(IntentAnalyzer)
        analyzer.api_key = "test-key"
        analyzer.model = "test-model"

        result = analyzer._fallback_analysis("最近做用户认证", "error")
        assert result.time_hint == "recent"

        result = analyzer._fallback_analysis("做用户认证", "error")
        assert result.time_hint == "all_time"


class TestIntentAnalyzerInit:
    """Tests for IntentAnalyzer initialization."""

    def test_init_without_api_key_raises(self) -> None:
        """Test initialization without API key raises error."""
        with patch.dict(os.environ, {}, clear=True), pytest.raises(ValueError, match="API key"):
            IntentAnalyzer()

    def test_analyze_fallback_on_error(self) -> None:
        """Test fallback is used when LLM raises error."""
        with patch("analyzer.intent_analyzer.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("API error")
            mock_anthropic.return_value = mock_client

            analyzer = IntentAnalyzer(api_key="test-key")
            result = analyzer.analyze("继续做用户认证功能")

            # Should use fallback
            assert isinstance(result, IntentAnalysisResult)
            assert len(result.concepts) > 0
            assert "error" in result.raw_response.lower()

    def test_analyze_success(self) -> None:
        """Test successful analysis with mocked LLM."""
        with patch("analyzer.intent_analyzer.Anthropic") as mock_anthropic:
            # Setup mock response
            mock_response = MagicMock()
            mock_block = MagicMock()
            mock_block.text = (
                '{"concepts": ["用户认证", "JWT"], "time_hint": "recent", "project_hint": null}'
            )
            mock_response.content = [mock_block]

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            analyzer = IntentAnalyzer(api_key="test-key")
            result = analyzer.analyze("继续做用户认证功能")

            assert "用户认证" in result.concepts
            assert result.time_hint == "recent"
