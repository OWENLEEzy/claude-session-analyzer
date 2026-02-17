"""LLM-based intent analyzer for session search queries."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from anthropic import Anthropic


@dataclass
class IntentAnalysisResult:
    """Result of intent analysis for a search query."""

    concepts: list[str] = field(default_factory=list)
    time_hint: str = "all_time"  # "recent" | "all_time"
    project_hint: str | None = None
    raw_response: str = ""


INTENT_ANALYSIS_PROMPT = """你是一个会话搜索助手。用户想找到之前的历史会话继续工作。
分析用户的查询，提取 2-5 个核心搜索概念。

用户查询：{query}

返回 JSON 格式（不要包含```json标记）：
{{
  "concepts": ["概念1", "概念2", "概念3"],
  "time_hint": "recent" 或 "all_time",
  "project_hint": "可能的项目名或 null"
}}

规则：
1. concepts 应该是 2-5 个关键词，用于向量搜索
2. time_hint: 如果用户提到"最近"、"上次"、"刚才"等设为 "recent"，否则 "all_time"
3. project_hint: 如果用户提到项目名则提取，否则 null

只返回 JSON，不要其他内容。"""


class IntentAnalyzer:
    """Analyzes user search queries using LLM to extract search intent."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        """Initialize the intent analyzer.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            model: Claude model to use for analysis.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key parameter."
            )
        self.model = model
        self.client = Anthropic(api_key=self.api_key)

    def analyze(self, query: str) -> IntentAnalysisResult:
        """Analyze user query and extract search intent.

        Args:
            query: User's natural language search query

        Returns:
            IntentAnalysisResult with extracted concepts, time hint, and project hint
        """
        prompt = INTENT_ANALYSIS_PROMPT.format(query=query)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            text_content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text_content += block.text

            # Parse JSON response
            result = self._parse_response(text_content)
            result.raw_response = text_content
            return result

        except Exception as e:
            # Fallback: use simple keyword extraction
            return self._fallback_analysis(query, str(e))

    def _parse_response(self, response_text: str) -> IntentAnalysisResult:
        """Parse LLM JSON response into IntentAnalysisResult."""
        # Clean up response - remove markdown code blocks if present
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            # Remove code block markers
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            data = json.loads(cleaned)
            return IntentAnalysisResult(
                concepts=data.get("concepts", []),
                time_hint=data.get("time_hint", "all_time"),
                project_hint=data.get("project_hint"),
            )
        except json.JSONDecodeError:
            return IntentAnalysisResult()

    def _fallback_analysis(self, query: str, error: str) -> IntentAnalysisResult:
        """Fallback analysis when LLM fails.

        Uses simple heuristics to extract concepts.
        """
        # Simple keyword extraction fallback
        concepts: list[str] = []

        # Split by common delimiters and filter
        text = query.replace("继续", " ").replace("做", " ").replace("搞", " ")
        text = text.replace("the", " ").replace("for", " ").replace("to", " ")
        words = text.split()

        for word in words:
            if len(word) > 1 and word not in ["继续", "做", "想", "要"]:
                concepts.append(word)
                if len(concepts) >= 3:
                    break

        # Detect time hint
        time_hint = "all_time"
        recent_keywords = ["最近", "上次", "刚才", "刚才", "recent", "last", "yesterday"]
        if any(kw in query for kw in recent_keywords):
            time_hint = "recent"

        return IntentAnalysisResult(
            concepts=concepts[:5],
            time_hint=time_hint,
            project_hint=None,
            raw_response=f"Fallback analysis due to error: {error}",
        )

    def analyze_batch(self, queries: list[str]) -> list[IntentAnalysisResult]:
        """Analyze multiple queries."""
        return [self.analyze(q) for q in queries]
