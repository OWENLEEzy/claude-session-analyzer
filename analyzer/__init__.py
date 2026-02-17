"""Claude Session Analyzer - NLP-based session transcript analysis."""

from .core import AnalysisResult, SessionAnalyzer
from .intent_analyzer import IntentAnalysisResult, IntentAnalyzer
from .reranker import RerankingWeights, ResultReranker
from .smart_search import (
    LocalSessionSearcher,
    SearchResult,
    SmartSearch,
    SmartSearchResult,
    quick_search,
)

__version__ = "0.1.0"
__all__ = [
    # Core analysis
    "SessionAnalyzer",
    "AnalysisResult",
    # Intent analysis
    "IntentAnalyzer",
    "IntentAnalysisResult",
    # Local search
    "LocalSessionSearcher",
    "SearchResult",
    # Reranking
    "ResultReranker",
    "RerankingWeights",
    # Smart search
    "SmartSearch",
    "SmartSearchResult",
    "quick_search",
]
