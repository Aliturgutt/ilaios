"""Fail-closed authorization-aware retrieval for the shared Knowledge/RAG plane.

This module intentionally provides a deterministic bounded retrieval foundation. It does
not claim vector-search, embedding, managed-provider, or production deployment evidence.
Authorization is evaluated before any context is returned, and every accepted result is
bound to immutable source/provenance evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class RetrievalError(ValueError):
    """A retrieval request or knowledge record violates a fail-closed boundary."""


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    chunk_id: str
    tenant_id: str
    project_id: str
    source_id: str
    content: str
    content_sha256: str
    classification: str
    residency: str
    allowed_principal_ids: frozenset[str]
    allowed_purposes: frozenset[str]
    authorization_epoch: int
    retention_valid: bool
    provenance: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    tenant_id: str
    project_id: str
    principal_id: str
    purpose: str
    query: str
    allowed_classifications: frozenset[str]
    required_residency: str
    authorization_epoch: int
    max_results: int = 5


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunk_id: str
    source_id: str
    content: str
    content_sha256: str
    classification: str
    residency: str
    score: float
    provenance: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class RetrievalEvidence:
    tenant_id: str
    project_id: str
    principal_id: str
    purpose: str
    query_sha256: str
    authorization_epoch: int
    result_ids: tuple[str, ...]
    result_sha256s: tuple[str, ...]
    evidence_sha256: str


class AuthorizationAwareRetriever:
    """In-memory bounded index that never returns context before authorization checks."""

    def __init__(self) -> None:
        self._chunks: dict[str, KnowledgeChunk] = {}
        self._revoked_sources: set[str] = set()

    def register_chunk(
        self,
        chunk_id: str,
        *,
        tenant_id: str,
        project_id: str,
        source_id: str,
        content: str,
        classification: str,
        residency: str,
        allowed_principal_ids: frozenset[str],
        allowed_purposes: frozenset[str],
        authorization_epoch: int,
        retention_valid: bool = True,
        provenance: dict[str, str] | None = None,
    ) -> KnowledgeChunk:
        for value, field in (
            (chunk_id, "chunk_id"),
            (tenant_id, "tenant_id"),
            (project_id, "project_id"),
            (source_id, "source_id"),
            (classification, "classification"),
            (residency, "residency"),
        ):
            _require_id(value, field)
        if chunk_id in self._chunks:
            raise RetrievalError("chunk_id already exists")
        if not content or not content.strip():
            raise RetrievalError("content must be non-blank")
        if not allowed_principal_ids:
            raise RetrievalError("at least one principal authorization is required")
        if not allowed_purposes:
            raise RetrievalError("at least one purpose authorization is required")
        _require_clean_set(allowed_principal_ids, "allowed_principal_ids")
        _require_clean_set(allowed_purposes, "allowed_purposes")
        if authorization_epoch < 1:
            raise RetrievalError("authorization_epoch must be positive")
        normalized_provenance = tuple(sorted((provenance or {}).items()))
        if not normalized_provenance:
            raise RetrievalError("provenance is required")
        if any(
            not key or key != key.strip() or not value or value != value.strip()
            for key, value in normalized_provenance
        ):
            raise RetrievalError("provenance keys and values must be non-blank and trimmed")
        content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        chunk = KnowledgeChunk(
            chunk_id=chunk_id,
            tenant_id=tenant_id,
            project_id=project_id,
            source_id=source_id,
            content=content,
            content_sha256=content_sha256,
            classification=classification,
            residency=residency,
            allowed_principal_ids=allowed_principal_ids,
            allowed_purposes=allowed_purposes,
            authorization_epoch=authorization_epoch,
            retention_valid=retention_valid,
            provenance=normalized_provenance,
        )
        self._chunks[chunk_id] = chunk
        return chunk

    def revoke_source(self, source_id: str) -> None:
        _require_id(source_id, "source_id")
        if not any(chunk.source_id == source_id for chunk in self._chunks.values()):
            raise RetrievalError("source_id does not exist")
        self._revoked_sources.add(source_id)

    def retrieve(
        self, request: RetrievalRequest
    ) -> tuple[tuple[RetrievalResult, ...], RetrievalEvidence]:
        _validate_request(request)
        query_tokens = _tokens(request.query)
        candidates: list[RetrievalResult] = []
        for chunk in self._chunks.values():
            self._verify_integrity(chunk)
            if not self._is_authorized(chunk, request):
                continue
            overlap = len(query_tokens & _tokens(chunk.content))
            if overlap == 0:
                continue
            score = overlap / max(len(query_tokens), 1)
            candidates.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    content=chunk.content,
                    content_sha256=chunk.content_sha256,
                    classification=chunk.classification,
                    residency=chunk.residency,
                    score=score,
                    provenance=chunk.provenance,
                )
            )
        ranked = tuple(
            sorted(candidates, key=lambda item: (-item.score, item.chunk_id))[
                : request.max_results
            ]
        )
        evidence = _build_evidence(request, ranked)
        return ranked, evidence

    def _verify_integrity(self, chunk: KnowledgeChunk) -> None:
        actual = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        if actual != chunk.content_sha256:
            raise RetrievalError("knowledge chunk integrity mismatch")

    def _is_authorized(self, chunk: KnowledgeChunk, request: RetrievalRequest) -> bool:
        return (
            chunk.tenant_id == request.tenant_id
            and chunk.project_id == request.project_id
            and chunk.source_id not in self._revoked_sources
            and request.principal_id in chunk.allowed_principal_ids
            and request.purpose in chunk.allowed_purposes
            and chunk.classification in request.allowed_classifications
            and chunk.residency == request.required_residency
            and chunk.authorization_epoch == request.authorization_epoch
            and chunk.retention_valid
        )


def _build_evidence(
    request: RetrievalRequest, results: tuple[RetrievalResult, ...]
) -> RetrievalEvidence:
    query_sha256 = hashlib.sha256(request.query.encode("utf-8")).hexdigest()
    material = {
        "tenant_id": request.tenant_id,
        "project_id": request.project_id,
        "principal_id": request.principal_id,
        "purpose": request.purpose,
        "query_sha256": query_sha256,
        "authorization_epoch": request.authorization_epoch,
        "result_ids": [result.chunk_id for result in results],
        "result_sha256s": [result.content_sha256 for result in results],
        "provenance": [list(result.provenance) for result in results],
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    evidence_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return RetrievalEvidence(
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        principal_id=request.principal_id,
        purpose=request.purpose,
        query_sha256=query_sha256,
        authorization_epoch=request.authorization_epoch,
        result_ids=tuple(result.chunk_id for result in results),
        result_sha256s=tuple(result.content_sha256 for result in results),
        evidence_sha256=evidence_sha256,
    )


def _validate_request(request: RetrievalRequest) -> None:
    for value, field in (
        (request.tenant_id, "tenant_id"),
        (request.project_id, "project_id"),
        (request.principal_id, "principal_id"),
        (request.purpose, "purpose"),
        (request.required_residency, "required_residency"),
    ):
        _require_id(value, field)
    if not request.query or not request.query.strip():
        raise RetrievalError("query must be non-blank")
    if not request.allowed_classifications:
        raise RetrievalError("allowed_classifications must not be empty")
    _require_clean_set(request.allowed_classifications, "allowed_classifications")
    if request.authorization_epoch < 1:
        raise RetrievalError("authorization_epoch must be positive")
    if request.max_results < 1 or request.max_results > 20:
        raise RetrievalError("max_results must be between 1 and 20")


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise RetrievalError(f"{field} must be non-blank and trimmed")


def _require_clean_set(values: frozenset[str], field: str) -> None:
    if any(not value or value != value.strip() for value in values):
        raise RetrievalError(f"{field} must contain non-blank trimmed values")


def _tokens(value: str) -> frozenset[str]:
    return frozenset(token.casefold() for token in _TOKEN_RE.findall(value))
