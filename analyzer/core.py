"""Core analysis module for Claude session transcripts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import jieba


@dataclass
class AnalysisResult:
    """Structured analysis result for a session."""

    goals: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    outcome: str | None = None  # "success" | "failure" | "partial" | None
    confidence: float = 0.0
    summary: str = ""
    raw_keywords: list[str] = field(default_factory=list)


# Goal indicator keywords (what the user wants to achieve)
GOAL_KEYWORDS = {
    "实现",
    "添加",
    "创建",
    "修复",
    "优化",
    "重构",
    "部署",
    "编写",
    "完成",
    "解决",
    "处理",
    "改进",
    "设计",
    "开发",
    "implement",
    "add",
    "create",
    "fix",
    "optimize",
    "refactor",
    "deploy",
    "write",
    "complete",
    "solve",
    "improve",
    "design",
}

# Action indicator keywords (what was actually done)
ACTION_KEYWORDS = {
    "修改",
    "删除",
    "更新",
    "新建",
    "编辑",
    "运行",
    "测试",
    "提交",
    "合并",
    "安装",
    "配置",
    "添加",
    "移除",
    "调整",
    "modify",
    "delete",
    "update",
    "create",
    "edit",
    "run",
    "test",
    "commit",
    "merge",
    "install",
    "configure",
    "add",
    "remove",
}

# Success indicator keywords
SUCCESS_KEYWORDS = {
    "成功",
    "完成",
    "通过",
    "正常",
    "已解决",
    "已实现",
    "✅",
    "succeeded",
    "completed",
    "passed",
    "done",
    "resolved",
    "✓",
}

# Failure indicator keywords
FAILURE_KEYWORDS = {
    "失败",
    "错误",
    "异常",
    "问题",
    "报错",
    "崩溃",
    "❌",
    "failed",
    "error",
    "exception",
    "issue",
    "crash",
    "✗",
}

# Partial success indicators
PARTIAL_KEYWORDS = {
    "部分",
    "待处理",
    "进行中",
    "未完成",
    "需要",
    "partial",
    "pending",
    "in progress",
    "todo",
    "remaining",
}

# File patterns to extract (matches full filenames including dots in name)
# Use non-capturing group to get full match from findall
FILE_PATTERN = re.compile(r"\b[a-zA-Z_][\w./]*\.(?:ts|tsx|js|jsx|py|md|json|yaml|yml)\b")

# Confidence thresholds
HIGH_CONFIDENCE = 0.8
MEDIUM_CONFIDENCE = 0.5


class SessionAnalyzer:
    """Analyzes Claude Code session transcripts using NLP."""

    def __init__(self, user_dict_path: str | None = None):
        """Initialize analyzer with optional custom dictionary.

        Args:
            user_dict_path: Path to custom jieba dictionary
        """
        if user_dict_path:
            jieba.load_userdict(user_dict_path)

        # Add technical terms to jieba dictionary
        technical_terms = [
            "TypeScript",
            "JavaScript",
            "React",
            "Vue",
            "Python",
            "API",
            "REST",
            "GraphQL",
            "JWT",
            "OAuth",
            "测试",
            "单元测试",
            "集成测试",
            "E2E",
            "部署",
            "CI/CD",
            "Docker",
            "Kubernetes",
            "数据库",
            "PostgreSQL",
            "MySQL",
            "MongoDB",
        ]
        for term in technical_terms:
            jieba.add_word(term)

    def analyze(self, session_path: str | Path) -> AnalysisResult:
        """Analyze a session transcript file.

        Args:
            session_path: Path to .jsonl session file

        Returns:
            AnalysisResult with extracted goals, actions, and outcome
        """
        path = Path(session_path)
        if not path.exists():
            raise FileNotFoundError(f"Session file not found: {path}")

        # Read and parse session content
        content = self._read_session(path)
        text = self._extract_text(content)

        # Extract components
        result = AnalysisResult()
        result.raw_keywords = self._extract_keywords(text)
        result.goals = self._extract_goals(text, result.raw_keywords)
        result.actions = self._extract_actions(text, result.raw_keywords)
        result.outcome = self._determine_outcome(text)
        result.confidence = self._calculate_confidence(result)

        # Generate summary only if confidence is high enough
        if result.confidence >= MEDIUM_CONFIDENCE:
            result.summary = self._generate_summary(result)

        return result

    def _read_session(self, path: Path) -> list[dict]:
        """Read JSONL session file."""
        content = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        content.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return content

    def _extract_text(self, content: list[dict]) -> str:
        """Extract text content from session messages."""
        texts = []
        for entry in content:
            # Handle different message formats
            if "text" in entry:
                texts.append(entry["text"])
            elif "content" in entry:
                if isinstance(entry["content"], str):
                    texts.append(entry["content"])
                elif isinstance(entry["content"], list):
                    for item in entry["content"]:
                        if isinstance(item, dict) and "text" in item:
                            texts.append(item["text"])
            elif "message" in entry:
                msg = entry["message"]
                if isinstance(msg, str):
                    texts.append(msg)
                elif isinstance(msg, dict) and "content" in msg:
                    texts.append(str(msg["content"]))
        return " ".join(texts)

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords using jieba segmentation."""
        words = jieba.lcut(text)
        # Filter out single characters and common stop words
        keywords = [w for w in words if len(w) > 1 and not w.isspace() and not w.isnumeric()]
        return keywords

    def _extract_goals(self, text: str, _keywords: list[str]) -> list[str]:
        """Extract session goals from text."""
        goals = []

        # Find sentences with goal keywords
        sentences = re.split(r"[。.!?\n]", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check for goal keywords
            words = set(jieba.lcut(sentence))
            if words & GOAL_KEYWORDS:
                # Extract the main goal phrase
                goal = self._extract_goal_phrase(sentence)
                if goal and goal not in goals:
                    goals.append(goal)

        return goals[:3]  # Limit to top 3 goals

    def _extract_goal_phrase(self, sentence: str) -> str | None:
        """Extract the core goal phrase from a sentence."""
        # Remove common prefixes
        sentence = re.sub(r"^(请|帮我|我想要|需要|Let me|I want to)\s*", "", sentence)

        # Limit length
        if len(sentence) > 50:
            sentence = sentence[:50] + "..."

        return sentence.strip() if sentence.strip() else None

    def _extract_actions(self, text: str, _keywords: list[str]) -> list[str]:
        """Extract actions taken during session."""
        actions = []

        # Find file modifications (use findall to get full match, not just group)
        file_matches = FILE_PATTERN.findall(text)
        for f in file_matches[:5]:  # Limit to 5 files
            action = f"修改 {f}"
            if action not in actions:
                actions.append(action)

        # Find sentences with action keywords
        sentences = re.split(r"[。.!?\n]", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            words = set(jieba.lcut(sentence))
            if words & ACTION_KEYWORDS:
                action_phrase = self._extract_action_phrase(sentence)
                if action_phrase and action_phrase not in actions:
                    actions.append(action_phrase)

        return actions[:5]  # Limit to top 5 actions

    def _extract_action_phrase(self, sentence: str) -> str | None:
        """Extract the core action phrase from a sentence."""
        # Keep sentences short
        if len(sentence) > 40:
            sentence = sentence[:40] + "..."

        return sentence.strip() if sentence.strip() else None

    def _determine_outcome(self, text: str) -> str | None:
        """Determine the outcome of the session."""
        text_lower = text.lower()

        success_count = sum(1 for kw in SUCCESS_KEYWORDS if kw.lower() in text_lower)
        failure_count = sum(1 for kw in FAILURE_KEYWORDS if kw.lower() in text_lower)
        partial_count = sum(1 for kw in PARTIAL_KEYWORDS if kw.lower() in text_lower)

        total = success_count + failure_count + partial_count
        if total == 0:
            return None

        if success_count > failure_count and success_count > partial_count:
            return "success"
        elif failure_count > success_count:
            return "failure"
        elif partial_count > 0:
            return "partial"

        return None

    def _calculate_confidence(self, result: AnalysisResult) -> float:
        """Calculate confidence score for the analysis."""
        score = 0.0

        # Goals found
        if result.goals:
            score += 0.3
            if len(result.goals) >= 2:
                score += 0.1

        # Actions found
        if result.actions:
            score += 0.3
            if len(result.actions) >= 2:
                score += 0.1

        # Outcome determined
        if result.outcome:
            score += 0.2

        # Minimum confidence if we found something
        if score > 0:
            score = max(score, 0.4)

        return min(score, 1.0)

    def _generate_summary(self, result: AnalysisResult) -> str:
        """Generate human-readable summary."""
        parts = []

        if result.goals:
            goals_str = "、".join(result.goals[:2])
            parts.append(f"【目标】{goals_str}")

        if result.actions:
            actions_str = "、".join(
                a[:20] + ("..." if len(a) > 20 else "") for a in result.actions[:3]
            )
            parts.append(f"【行动】{actions_str}")

        if result.outcome:
            outcome_map = {
                "success": "成功完成",
                "failure": "遇到问题",
                "partial": "部分完成",
            }
            parts.append(f"【结果】{outcome_map.get(result.outcome, result.outcome)}")

        return " → ".join(parts) if parts else ""

    def analyze_batch(self, paths: list[str | Path]) -> list[AnalysisResult]:
        """Analyze multiple session files."""
        return [self.analyze(p) for p in paths]
