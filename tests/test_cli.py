"""Tests for CLI module."""

from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from analyzer.cli import format_result, main
from analyzer.core import AnalysisResult


class TestFormatResult:
    """Tests for format_result function."""

    def test_format_text(self) -> None:
        """Test text format output."""
        result = AnalysisResult(
            goals=["实现认证"],
            actions=["创建文件"],
            outcome="success",
            confidence=0.85,
            summary="测试摘要",
        )
        output = format_result(result, "text")

        assert "Goals:" in output
        assert "实现认证" in output
        assert "Actions:" in output
        assert "Confidence: 0.85" in output

    def test_format_json(self) -> None:
        """Test JSON format output."""
        result = AnalysisResult(
            goals=["实现认证"],
            actions=["创建文件"],
            outcome="success",
            confidence=0.85,
        )
        output = format_result(result, "json")
        data = json.loads(output)

        assert data["goals"] == ["实现认证"]
        assert data["actions"] == ["创建文件"]
        assert data["outcome"] == "success"
        assert data["confidence"] == 0.85

    def test_format_markdown(self) -> None:
        """Test markdown format output."""
        result = AnalysisResult(
            goals=["实现认证"],
            actions=["创建文件"],
            outcome="success",
            confidence=0.85,
        )
        output = format_result(result, "markdown")

        assert "## Session Analysis" in output
        assert "**Goals:**" in output
        assert "**Actions:**" in output
        assert "**Outcome:**" in output

    def test_format_text_empty_result(self) -> None:
        """Test text format with empty result."""
        result = AnalysisResult()
        output = format_result(result, "text")
        assert "Confidence: 0.00" in output

    def test_format_text_with_summary(self) -> None:
        """Test text format includes summary."""
        result = AnalysisResult(
            goals=["实现认证"],
            confidence=0.8,
            summary="这是一个测试摘要",
        )
        output = format_result(result, "text")
        assert "Summary: 这是一个测试摘要" in output

    def test_format_markdown_partial_result(self) -> None:
        """Test markdown format with partial result."""
        result = AnalysisResult(
            goals=["目标1"],
            outcome="partial",
            confidence=0.6,
        )
        output = format_result(result, "markdown")
        assert "**Outcome:** partial" in output


class TestCLI:
    """Tests for CLI commands."""

    def test_main_no_args(self) -> None:
        """Test main with no arguments shows help."""
        result = main([])
        assert result == 0

    def test_analyze_nonexistent_file(self) -> None:
        """Test analyzing non-existent file returns error."""
        result = main(["analyze", "/nonexistent/file.jsonl"])
        assert result == 1

    def test_analyze_single_file_json_format(self) -> None:
        """Test analyzing single file with JSON output."""
        # Create temporary session file
        content = json.dumps({"text": "我想要实现认证功能。成功完成了。"})

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".jsonl",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = main(["analyze", temp_path, "-f", "json"])
            assert result == 0
        finally:
            Path(temp_path).unlink()

    def test_analyze_table_format(self) -> None:
        """Test analyzing with table format."""
        content = json.dumps({"text": "实现认证功能。成功完成了。"})

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".jsonl",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            # Capture stdout to verify table output
            with patch("sys.stdout", new_callable=StringIO):
                result = main(["analyze", temp_path, "-f", "table"])
                assert result == 0
        finally:
            Path(temp_path).unlink()

    def test_analyze_multiple_files(self) -> None:
        """Test analyzing multiple files."""
        content1 = json.dumps({"text": "实现认证功能。"})
        content2 = json.dumps({"text": "实现API功能。"})

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f1:
            f1.write(content1)
            temp_path1 = f1.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f2:
            f2.write(content2)
            temp_path2 = f2.name

        try:
            result = main(["analyze", temp_path1, temp_path2, "-f", "json"])
            assert result == 0
        finally:
            Path(temp_path1).unlink()
            Path(temp_path2).unlink()

    def test_analyze_text_format(self) -> None:
        """Test analyzing with default text format."""
        content = json.dumps({"text": "实现认证功能。成功完成了。"})

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".jsonl",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = main(["analyze", temp_path])
            assert result == 0
        finally:
            Path(temp_path).unlink()

    def test_analyze_markdown_format(self) -> None:
        """Test analyzing with markdown format."""
        content = json.dumps({"text": "实现认证功能。"})

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".jsonl",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = main(["analyze", temp_path, "-f", "markdown"])
            assert result == 0
        finally:
            Path(temp_path).unlink()
