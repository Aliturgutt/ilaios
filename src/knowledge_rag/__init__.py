"""Authorization-aware Knowledge/RAG primitives for the canonical ILAIOS knowledge plane."""

from .retrieval import (
    AuthorizationAwareRetriever,
    KnowledgeChunk,
    RetrievalError,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievalResult,
)

__all__ = [
    "AuthorizationAwareRetriever",
    "KnowledgeChunk",
    "RetrievalError",
    "RetrievalEvidence",
    "RetrievalRequest",
    "RetrievalResult",
]
