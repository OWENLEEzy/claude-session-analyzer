"""Result reranker for multi-signal fusion ranking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .smart_search import SearchResult


@dataclass
class RerankingWeights:
    """Weights for different ranking signals."""

    similarity: float = 0.5
    time_decay: float = 0.2
    project_match: float = 0.3

    def __post_init__(self) -> None:
        """Validate weights sum to 1.0."""
        total = self.similarity + self.time_decay + self.project_match
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


class ResultReranker:
    """Reranks search results using multi-signal fusion."""

    def __init__(
        self,
        weights: RerankingWeights | None = None,
        current_project: str | None = None,
        half_life_days: float = 7.0,
    ):
        """Initialize the reranker.

        Args:
            weights: Custom weights for ranking signals.
            current_project: Current project path for project matching bonus.
            half_life_days: Half-life for time decay in days.
        """
        self.weights = weights or RerankingWeights()
        self.current_project = current_project
        self.half_life_days = half_life_days

    def rerank(
        self,
        results: list[SearchResult],
        project_hint: str | None = None,
        time_hint: str = "all_time",
    ) -> list[SearchResult]:
        """Rerank search results using multi-signal fusion.

        Args:
            results: List of search results to rerank.
            project_hint: Project name hint from intent analysis.
            time_hint: Time hint from intent analysis ("recent" or "all_time").

        Returns:
            Reranked list of search results.
        """
        if not results:
            return results

        # Calculate time boost for recent queries
        time_boost = 1.5 if time_hint == "recent" else 1.0

        # Calculate final score for each result
        scored_results = []
        for result in results:
            score = self._calculate_score(result, project_hint, time_boost)
            result.similarity = score  # Store final score in similarity field
            scored_results.append(result)

        # Sort by score descending
        scored_results.sort(key=lambda r: r.similarity, reverse=True)

        return scored_results

    def _calculate_score(
        self,
        result: SearchResult,
        project_hint: str | None,
        time_boost: float,
    ) -> float:
        """Calculate final score for a result.

        final_score = similarity * 0.5 + time_decay * 0.2 + project_match * 0.3
        """
        similarity_score = self._normalize_similarity(result.similarity)
        time_score = self._calculate_time_decay(result.timestamp, time_boost)
        project_score = self._calculate_project_match(result, project_hint)

        final_score = (
            similarity_score * self.weights.similarity
            + time_score * self.weights.time_decay
            + project_score * self.weights.project_match
        )

        return final_score

    def _normalize_similarity(self, similarity: float) -> float:
        """Normalize similarity score to [0, 1] range."""
        # Assume similarity is already in [0, 1] or [0, 100]
        # If value > 10, assume it's a percentage (0-100)
        if similarity > 10.0:
            similarity = similarity / 100.0
        return min(max(similarity, 0.0), 1.0)

    def _calculate_time_decay(
        self,
        timestamp: datetime | None,
        boost: float = 1.0,
    ) -> float:
        """Calculate time decay score.

        Uses exponential decay: score = e^(-days / half_life) * boost
        """
        if not timestamp:
            return 0.5  # Neutral score if no timestamp

        now = datetime.now()
        if timestamp.tzinfo:
            from datetime import timezone

            now = datetime.now(timezone.utc)

        age = now - timestamp
        days: float = age.total_seconds() / 86400  # Convert to days

        # Exponential decay
        decay: float = 0.5 ** (days / self.half_life_days)

        return float(min(decay * boost, 1.0))

    def _calculate_project_match(
        self,
        result: SearchResult,
        project_hint: str | None,
    ) -> float:
        """Calculate project match score.

        Returns 1.0 if project matches current project or hint,
        0.5 otherwise (neutral).
        """
        result_project = result.project_path.lower()
        hint_lower = project_hint.lower() if project_hint else None
        current_lower = self.current_project.lower() if self.current_project else None

        # Check if result matches project hint
        if hint_lower and hint_lower in result_project:
            return 1.0

        # Check if result matches current project
        if current_lower and current_lower in result_project:
            return 0.9

        # Check partial match with hint
        if hint_lower:
            # Split into words and check partial matches
            hint_words = hint_lower.replace("-", " ").replace("_", " ").split()
            result_words = result_project.replace("-", " ").replace("_", " ").split()

            matches = sum(1 for w in hint_words if any(w in rw for rw in result_words))
            if matches > 0:
                return 0.7 + (0.1 * min(matches, 3))

        return 0.5  # Neutral score

    def set_current_project(self, project_path: str) -> None:
        """Set the current project for project matching."""
        self.current_project = project_path
