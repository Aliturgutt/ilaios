"""Canonical bounded Knowledge/RAG plane for ILAIOS.

The implementation is provider-neutral and tenant isolated. The default
embedding and index adapters are deterministic local verification adapters;
they are not production-scale vector infrastructure or model-quality claims.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol


class KnowledgeRAGError(ValueError):
    """A Knowledge/RAG contract or invariant was violated."""


class AuthorizationDenied(KnowledgeRAGError):
    """A caller attempted an unauthorized Knowledge/RAG operation."""


class SourceState(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    DELETED = "DELETED"


class VersionState(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    DELETED = "DELETED"


class RetrievalStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    DENIED = "DENIED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    source_id: str
    tenant_id: str
    project_id: str
    locator: str
    trusted: bool
    classifications: frozenset[str]
    purposes: frozenset[str]
    residency: str
    state: SourceState
    latest_version: int


@dataclass(frozen=True, slots=True)
class SourceVersion:
    source_id: str
    version: int
    tenant_id: str
    project_id: str
    content_sha256: str
    state: VersionState


@dataclass(frozen=True, slots=True)
class KnowledgeUnit:
    unit_id: str
    source_id: str
    source_version: int
    tenant_id: str
    project_id: str
    sequence: int
    text: str
    content_sha256: str
    classifications: frozenset[str]
    purposes: frozenset[str]
    residency: str
    quarantined_reason: str | None = None


@dataclass(frozen=True, slots=True)
class PrincipalScope:
    principal_id: str
    tenant_id: str
    project_id: str
    allowed_classifications: frozenset[str]
    allowed_purposes: frozenset[str]
    allowed_residencies: frozenset[str]
    allowed_source_ids: frozenset[str] | None = None


@dataclass(frozen=True, slots=True)
class RetrievalBudget:
    max_top_k: int = 20
    max_candidate_scan: int = 100
    max_context_chars: int = 20_000

    def __post_init__(self) -> None:
        if self.max_top_k < 1:
            raise KnowledgeRAGError("max_top_k must be positive")
        if self.max_candidate_scan < self.max_top_k:
            raise KnowledgeRAGError("max_candidate_scan must be >= max_top_k")
        if self.max_context_chars < 256:
            raise KnowledgeRAGError("max_context_chars must be at least 256")


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    retrieval_id: str
    scope: PrincipalScope
    query: str
    purpose: str
    top_k: int = 5
    candidate_limit: int = 25
    max_context_chars: int = 8_000


@dataclass(frozen=True, slots=True)
class Citation:
    citation_id: str
    source_id: str
    source_version: int
    unit_id: str
    locator: str
    source_content_sha256: str
    unit_content_sha256: str


@dataclass(frozen=True, slots=True)
class RetrievedUnit:
    unit_id: str
    source_id: str
    source_version: int
    text: str
    semantic_score: float
    lexical_score: float
    final_score: float
    citation: Citation


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    retrieval_id: str
    status: RetrievalStatus
    units: tuple[RetrievedUnit, ...]
    query_sha256: str
    eligible_count: int
    scored_count: int
    context_chars: int
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class AuthorizedContext:
    context_id: str
    tenant_id: str
    project_id: str
    retrieval_id: str
    purpose: str
    query_sha256: str
    safety_boundary: str
    units: tuple[RetrievedUnit, ...]
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    unit_id: str
    semantic_score: float


class EmbeddingProvider(Protocol):
    @property
    def provider_id(self) -> str:
        """Stable provider/adapter identity."""

    def embed(self, text: str) -> tuple[float, ...]:
        """Return an embedding for text."""


class VectorIndex(Protocol):
    def upsert(self, unit_id: str, vector: tuple[float, ...]) -> None:
        """Insert or replace an indexed unit."""

    def delete(self, unit_ids: frozenset[str]) -> None:
        """Delete exact unit IDs."""

    def search(
        self,
        query_vector: tuple[float, ...],
        eligible_unit_ids: frozenset[str],
        limit: int,
    ) -> tuple[ScoredCandidate, ...]:
        """Score only the already-authorized candidate set."""


class ContentGuard(Protocol):
    def inspect(self, text: str) -> str | None:
        """Return quarantine reason or None."""


class DeterministicHashEmbeddingProvider:
    """Pure-stdlib deterministic verification embedding adapter."""

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions < 8:
            raise KnowledgeRAGError("embedding dimensions must be at least 8")
        self._dimensions = dimensions

    @property
    def provider_id(self) -> str:
        return f"deterministic-hash-v1:{self._dimensions}"

    def embed(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self._dimensions
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self._dimensions
            vector[index] += -1.0 if digest[2] & 1 else 1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0.0:
            return tuple(vector)
        return tuple(value / magnitude for value in vector)


class InMemoryVectorIndex:
    """Deterministic bounded verification vector index."""

    def __init__(self) -> None:
        self._vectors: dict[str, tuple[float, ...]] = {}

    def upsert(self, unit_id: str, vector: tuple[float, ...]) -> None:
        _require_id(unit_id, "unit_id")
        if not vector:
            raise KnowledgeRAGError("vector must not be empty")
        self._vectors[unit_id] = vector

    def delete(self, unit_ids: frozenset[str]) -> None:
        for unit_id in unit_ids:
            self._vectors.pop(unit_id, None)

    def search(
        self,
        query_vector: tuple[float, ...],
        eligible_unit_ids: frozenset[str],
        limit: int,
    ) -> tuple[ScoredCandidate, ...]:
        if limit < 1:
            raise KnowledgeRAGError("search limit must be positive")
        scored: list[ScoredCandidate] = []
        for unit_id in sorted(eligible_unit_ids):
            vector = self._vectors.get(unit_id)
            if vector is None:
                continue
            if len(vector) != len(query_vector):
                raise KnowledgeRAGError("embedding dimension mismatch")
            score = sum(a * b for a, b in zip(query_vector, vector, strict=True))
            scored.append(ScoredCandidate(unit_id, score))
        scored.sort(key=lambda item: (-item.semantic_score, item.unit_id))
        return tuple(scored[:limit])


class BoundedRAGContentGuard:
    """High-confidence RAG quarantine checks used as defense in depth."""

    _INJECTION_PATTERNS = (
        re.compile(
            r"\bignore\s+(?:all\s+|any\s+|the\s+)?previous\s+instructions\b",
            re.I,
        ),
        re.compile(r"\breveal\b.{0,40}\bsystem\s+prompt\b", re.I | re.S),
        re.compile(r"\bbegin\s+system\s+prompt\b", re.I),
        re.compile(r"\bdeveloper\s+message\b.{0,30}\boverride\b", re.I | re.S),
        re.compile(r"\bjailbreak\b", re.I),
    )
    _SECRET_PATTERNS = (
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    )

    def inspect(self, text: str) -> str | None:
        for pattern in self._SECRET_PATTERNS:
            if pattern.search(text):
                return "credential_pattern"
        for pattern in self._INJECTION_PATTERNS:
            if pattern.search(text):
                return "prompt_injection_pattern"
        return None


@dataclass(frozen=True, slots=True)
class RAGMetricsSnapshot:
    ingested_sources: int
    updated_sources: int
    revoked_sources: int
    deleted_sources: int
    quarantined_units: int
    retrievals: int
    empty_retrievals: int
    scored_candidates: int
    active_units: int


@dataclass(slots=True)
class _MutableMetrics:
    ingested_sources: int = 0
    updated_sources: int = 0
    revoked_sources: int = 0
    deleted_sources: int = 0
    quarantined_units: int = 0
    retrievals: int = 0
    empty_retrievals: int = 0
    scored_candidates: int = 0


@dataclass(frozen=True, slots=True)
class RAGSnapshot:
    tenant_id: str
    project_id: str
    provider_id: str
    sources: tuple[KnowledgeSource, ...]
    versions: tuple[SourceVersion, ...]
    units: tuple[KnowledgeUnit, ...]
    active_unit_ids: frozenset[str]
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    case_id: str
    request: RetrievalRequest
    expected_source_ids: frozenset[str]
    forbidden_source_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationReport:
    total: int
    passed: int
    failed_case_ids: tuple[str, ...]
    leakage_detected: bool
    evidence_sha256: str


class KnowledgeRAG:
    """Single canonical bounded Knowledge/RAG service boundary."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        vector_index: VectorIndex | None = None,
        content_guard: ContentGuard | None = None,
        budget: RetrievalBudget | None = None,
        chunk_size_words: int = 120,
        chunk_overlap_words: int = 20,
    ) -> None:
        if chunk_size_words < 10:
            raise KnowledgeRAGError("chunk_size_words must be at least 10")
        if chunk_overlap_words < 0 or chunk_overlap_words >= chunk_size_words:
            raise KnowledgeRAGError(
                "chunk overlap must be >= 0 and smaller than chunk size"
            )
        self._embedding = embedding_provider or DeterministicHashEmbeddingProvider()
        self._index = vector_index or InMemoryVectorIndex()
        self._guard = content_guard or BoundedRAGContentGuard()
        self._budget = budget or RetrievalBudget()
        self._chunk_size_words = chunk_size_words
        self._chunk_overlap_words = chunk_overlap_words
        self._sources: dict[str, KnowledgeSource] = {}
        self._versions: dict[tuple[str, int], SourceVersion] = {}
        self._units: dict[str, KnowledgeUnit] = {}
        self._active_unit_ids: set[str] = set()
        self._metrics = _MutableMetrics()

    @property
    def embedding_provider_id(self) -> str:
        return self._embedding.provider_id

    def ingest_source(
        self,
        source_id: str,
        *,
        tenant_id: str,
        project_id: str,
        locator: str,
        content: str,
        trusted: bool,
        classifications: frozenset[str] = frozenset(),
        purposes: frozenset[str] = frozenset(),
        residency: str = "global",
    ) -> KnowledgeSource:
        _require_id(source_id, "source_id")
        _require_id(tenant_id, "tenant_id")
        _require_id(project_id, "project_id")
        _require_text(locator, "locator")
        _require_text(content, "content")
        _validate_labels(classifications, "classifications")
        _validate_labels(purposes, "purposes")
        _require_id(residency, "residency")
        if source_id in self._sources:
            raise KnowledgeRAGError("source_id already exists")
        source = KnowledgeSource(
            source_id=source_id,
            tenant_id=tenant_id,
            project_id=project_id,
            locator=locator,
            trusted=trusted,
            classifications=classifications,
            purposes=purposes,
            residency=residency,
            state=SourceState.ACTIVE,
            latest_version=1,
        )
        self._sources[source_id] = source
        self._create_version(source, 1, content)
        self._metrics.ingested_sources += 1
        return source

    def update_source(
        self,
        source_id: str,
        *,
        tenant_id: str,
        project_id: str,
        content: str,
    ) -> KnowledgeSource:
        _require_text(content, "content")
        source = self._require_scoped_source(source_id, tenant_id, project_id)
        if source.state is not SourceState.ACTIVE:
            raise KnowledgeRAGError("only ACTIVE sources may be updated")
        current_key = (source_id, source.latest_version)
        self._versions[current_key] = replace(
            self._versions[current_key], state=VersionState.SUPERSEDED
        )
        old_units = self._active_ids_for_source(source_id)
        self._index.delete(old_units)
        self._active_unit_ids.difference_update(old_units)
        next_version = source.latest_version + 1
        updated = replace(source, latest_version=next_version)
        self._sources[source_id] = updated
        self._create_version(updated, next_version, content)
        self._metrics.updated_sources += 1
        return updated

    def revoke_source(
        self,
        source_id: str,
        *,
        tenant_id: str,
        project_id: str,
    ) -> KnowledgeSource:
        source = self._require_scoped_source(source_id, tenant_id, project_id)
        if source.state is SourceState.DELETED:
            raise KnowledgeRAGError("deleted source cannot be revoked")
        if source.state is SourceState.REVOKED:
            return source
        revoked = replace(source, state=SourceState.REVOKED)
        self._sources[source_id] = revoked
        key = (source_id, source.latest_version)
        self._versions[key] = replace(self._versions[key], state=VersionState.REVOKED)
        active_ids = self._active_ids_for_source(source_id)
        self._index.delete(active_ids)
        self._active_unit_ids.difference_update(active_ids)
        self._metrics.revoked_sources += 1
        return revoked

    def delete_source(
        self,
        source_id: str,
        *,
        tenant_id: str,
        project_id: str,
    ) -> KnowledgeSource:
        source = self._require_scoped_source(source_id, tenant_id, project_id)
        if source.state is SourceState.DELETED:
            return source
        deleted = replace(source, state=SourceState.DELETED)
        self._sources[source_id] = deleted
        active_ids = self._active_ids_for_source(source_id)
        self._index.delete(active_ids)
        self._active_unit_ids.difference_update(active_ids)
        for key, version in tuple(self._versions.items()):
            if key[0] == source_id:
                self._versions[key] = replace(version, state=VersionState.DELETED)
        for unit_id, unit in tuple(self._units.items()):
            if unit.source_id == source_id:
                self._units[unit_id] = replace(
                    unit,
                    text="",
                    quarantined_reason="deleted",
                )
        self._metrics.deleted_sources += 1
        return deleted

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        self._validate_request(request)
        eligible = frozenset(
            unit_id
            for unit_id in self._active_unit_ids
            if self._is_authorized(
                self._units[unit_id], request.scope, request.purpose
            )
        )
        self._metrics.retrievals += 1
        query_sha = _sha256_text(request.query)
        if not eligible:
            self._metrics.empty_retrievals += 1
            return RetrievalResult(
                retrieval_id=request.retrieval_id,
                status=RetrievalStatus.SUCCEEDED,
                units=(),
                query_sha256=query_sha,
                eligible_count=0,
                scored_count=0,
                context_chars=0,
                evidence_sha256=_retrieval_evidence(
                    request.retrieval_id, query_sha, (), 0
                ),
            )

        candidates = self._index.search(
            self._embedding.embed(request.query),
            eligible,
            min(request.candidate_limit, self._budget.max_candidate_scan),
        )
        self._metrics.scored_candidates += len(candidates)
        query_tokens = frozenset(_tokens(request.query))
        reranked: list[tuple[float, float, ScoredCandidate, KnowledgeUnit]] = []
        for candidate in candidates:
            if candidate.unit_id not in eligible:
                raise KnowledgeRAGError("vector index returned an unauthorized unit")
            unit = self._units[candidate.unit_id]
            lexical = _lexical_overlap(query_tokens, frozenset(_tokens(unit.text)))
            final_score = 0.75 * candidate.semantic_score + 0.25 * lexical
            if not math.isfinite(final_score):
                raise KnowledgeRAGError("retrieval score must be finite")
            reranked.append((final_score, lexical, candidate, unit))
        reranked.sort(key=lambda item: (-item[0], item[3].unit_id))

        selected: list[RetrievedUnit] = []
        context_chars = 0
        effective_context_limit = min(
            request.max_context_chars, self._budget.max_context_chars
        )
        for final_score, lexical, candidate, unit in reranked:
            if len(selected) >= request.top_k:
                break
            if context_chars + len(unit.text) > effective_context_limit:
                continue
            source = self._sources[unit.source_id]
            version = self._versions[(unit.source_id, unit.source_version)]
            citation = Citation(
                citation_id=f"cite:{unit.unit_id}",
                source_id=unit.source_id,
                source_version=unit.source_version,
                unit_id=unit.unit_id,
                locator=source.locator,
                source_content_sha256=version.content_sha256,
                unit_content_sha256=unit.content_sha256,
            )
            selected.append(
                RetrievedUnit(
                    unit_id=unit.unit_id,
                    source_id=unit.source_id,
                    source_version=unit.source_version,
                    text=unit.text,
                    semantic_score=candidate.semantic_score,
                    lexical_score=lexical,
                    final_score=final_score,
                    citation=citation,
                )
            )
            context_chars += len(unit.text)

        if not selected:
            self._metrics.empty_retrievals += 1
        units = tuple(selected)
        return RetrievalResult(
            retrieval_id=request.retrieval_id,
            status=RetrievalStatus.SUCCEEDED,
            units=units,
            query_sha256=query_sha,
            eligible_count=len(eligible),
            scored_count=len(candidates),
            context_chars=context_chars,
            evidence_sha256=_retrieval_evidence(
                request.retrieval_id, query_sha, units, len(candidates)
            ),
        )

    def build_authorized_context(
        self,
        request: RetrievalRequest,
        result: RetrievalResult,
    ) -> AuthorizedContext:
        """Bind only an untampered, still-authorized result to worker context."""
        self._validate_request(request)
        if result.retrieval_id != request.retrieval_id:
            raise KnowledgeRAGError("retrieval result does not match request")
        if result.status is not RetrievalStatus.SUCCEEDED:
            raise KnowledgeRAGError("only successful retrieval may form context")
        expected_query_sha = _sha256_text(request.query)
        if result.query_sha256 != expected_query_sha:
            raise KnowledgeRAGError("retrieval query hash mismatch")
        if len(result.units) > request.top_k:
            raise KnowledgeRAGError("retrieval result exceeds top_k")
        if result.scored_count > request.candidate_limit:
            raise KnowledgeRAGError("retrieval result exceeds candidate limit")
        context_chars = sum(len(item.text) for item in result.units)
        if context_chars != result.context_chars:
            raise KnowledgeRAGError("retrieval context size mismatch")
        if context_chars > request.max_context_chars:
            raise KnowledgeRAGError("retrieval result exceeds context budget")
        expected_evidence = _retrieval_evidence(
            result.retrieval_id,
            result.query_sha256,
            result.units,
            result.scored_count,
        )
        if expected_evidence != result.evidence_sha256:
            raise KnowledgeRAGError("retrieval evidence hash mismatch")
        for returned in result.units:
            self._validate_returned_unit(request, returned)
        context_evidence = _sha256_text(
            "|".join(
                (
                    request.scope.principal_id,
                    request.scope.tenant_id,
                    request.scope.project_id,
                    request.purpose,
                    result.query_sha256,
                    result.evidence_sha256,
                )
            )
        )
        return AuthorizedContext(
            context_id=f"context:{context_evidence[:24]}",
            tenant_id=request.scope.tenant_id,
            project_id=request.scope.project_id,
            retrieval_id=request.retrieval_id,
            purpose=request.purpose,
            query_sha256=result.query_sha256,
            safety_boundary="UNTRUSTED_KNOWLEDGE_DATA",
            units=result.units,
            evidence_sha256=context_evidence,
        )

    def snapshot(self, *, tenant_id: str, project_id: str) -> RAGSnapshot:
        _require_id(tenant_id, "tenant_id")
        _require_id(project_id, "project_id")
        sources = tuple(
            sorted(
                (
                    source
                    for source in self._sources.values()
                    if source.tenant_id == tenant_id
                    and source.project_id == project_id
                ),
                key=lambda item: item.source_id,
            )
        )
        source_ids = frozenset(source.source_id for source in sources)
        versions = tuple(
            sorted(
                (
                    version
                    for (source_id, _), version in self._versions.items()
                    if source_id in source_ids
                ),
                key=lambda item: (item.source_id, item.version),
            )
        )
        units = tuple(
            sorted(
                (unit for unit in self._units.values() if unit.source_id in source_ids),
                key=lambda item: item.unit_id,
            )
        )
        known_unit_ids = frozenset(unit.unit_id for unit in units)
        active = frozenset(
            unit_id for unit_id in self._active_unit_ids if unit_id in known_unit_ids
        )
        digest = _snapshot_evidence(
            tenant_id,
            project_id,
            self.embedding_provider_id,
            sources,
            versions,
            units,
            active,
        )
        return RAGSnapshot(
            tenant_id=tenant_id,
            project_id=project_id,
            provider_id=self.embedding_provider_id,
            sources=sources,
            versions=versions,
            units=units,
            active_unit_ids=active,
            evidence_sha256=digest,
        )

    def restore(self, snapshot: RAGSnapshot) -> None:
        """Restore an integrity-checked single-tenant/project snapshot."""
        if self._sources or self._versions or self._units or self._active_unit_ids:
            raise KnowledgeRAGError("restore requires an empty KnowledgeRAG instance")
        _require_id(snapshot.tenant_id, "snapshot tenant_id")
        _require_id(snapshot.project_id, "snapshot project_id")
        if snapshot.provider_id != self.embedding_provider_id:
            raise KnowledgeRAGError("snapshot embedding provider mismatch")
        expected = _snapshot_evidence(
            snapshot.tenant_id,
            snapshot.project_id,
            snapshot.provider_id,
            snapshot.sources,
            snapshot.versions,
            snapshot.units,
            snapshot.active_unit_ids,
        )
        if expected != snapshot.evidence_sha256:
            raise KnowledgeRAGError("snapshot evidence hash mismatch")

        sources = {source.source_id: source for source in snapshot.sources}
        if len(sources) != len(snapshot.sources):
            raise KnowledgeRAGError("snapshot contains duplicate sources")
        for source in snapshot.sources:
            if (
                source.tenant_id != snapshot.tenant_id
                or source.project_id != snapshot.project_id
            ):
                raise KnowledgeRAGError("snapshot source scope mismatch")

        versions = {
            (version.source_id, version.version): version
            for version in snapshot.versions
        }
        if len(versions) != len(snapshot.versions):
            raise KnowledgeRAGError("snapshot contains duplicate source versions")
        for key, version in versions.items():
            version_source = sources.get(version.source_id)
            if version_source is None:
                raise KnowledgeRAGError("snapshot version references unknown source")
            if (
                version.tenant_id != snapshot.tenant_id
                or version.project_id != snapshot.project_id
            ):
                raise KnowledgeRAGError("snapshot version scope mismatch")
            if key != (version.source_id, version.version) or version.version < 1:
                raise KnowledgeRAGError("snapshot source version identity is invalid")
        for source in snapshot.sources:
            if (source.source_id, source.latest_version) not in versions:
                raise KnowledgeRAGError("snapshot latest source version is missing")

        units = {unit.unit_id: unit for unit in snapshot.units}
        if len(units) != len(snapshot.units):
            raise KnowledgeRAGError("snapshot contains duplicate units")
        for unit in snapshot.units:
            unit_source = sources.get(unit.source_id)
            unit_version = versions.get((unit.source_id, unit.source_version))
            if unit_source is None or unit_version is None:
                raise KnowledgeRAGError("snapshot unit lineage is incomplete")
            if (
                unit.tenant_id != snapshot.tenant_id
                or unit.project_id != snapshot.project_id
            ):
                raise KnowledgeRAGError("snapshot unit scope mismatch")
            if unit.text:
                if _sha256_text(unit.text) != unit.content_sha256:
                    raise KnowledgeRAGError("snapshot unit content hash mismatch")
            elif unit_source.state is not SourceState.DELETED:
                raise KnowledgeRAGError("non-deleted snapshot unit has empty content")

        if not snapshot.active_unit_ids <= units.keys():
            raise KnowledgeRAGError("snapshot references unknown active unit")
        for unit_id in snapshot.active_unit_ids:
            unit = units[unit_id]
            active_source = sources[unit.source_id]
            active_version = versions[(unit.source_id, unit.source_version)]
            if active_source.state is not SourceState.ACTIVE:
                raise KnowledgeRAGError("inactive source cannot have active unit")
            if active_version.state is not VersionState.ACTIVE:
                raise KnowledgeRAGError("inactive source version cannot have active unit")
            if unit.quarantined_reason is not None or not unit.text:
                raise KnowledgeRAGError("quarantined or empty unit cannot be active")

        self._sources = sources
        self._versions = versions
        self._units = units
        self._active_unit_ids = set(snapshot.active_unit_ids)
        for unit_id in sorted(self._active_unit_ids):
            unit = self._units[unit_id]
            self._index.upsert(unit_id, self._embedding.embed(unit.text))

    def metrics(self) -> RAGMetricsSnapshot:
        return RAGMetricsSnapshot(
            ingested_sources=self._metrics.ingested_sources,
            updated_sources=self._metrics.updated_sources,
            revoked_sources=self._metrics.revoked_sources,
            deleted_sources=self._metrics.deleted_sources,
            quarantined_units=self._metrics.quarantined_units,
            retrievals=self._metrics.retrievals,
            empty_retrievals=self._metrics.empty_retrievals,
            scored_candidates=self._metrics.scored_candidates,
            active_units=len(self._active_unit_ids),
        )

    def evaluate(
        self,
        cases: tuple[RetrievalEvaluationCase, ...],
    ) -> RetrievalEvaluationReport:
        failed: list[str] = []
        leakage = False
        evidence_parts: list[str] = []
        for case in cases:
            _require_id(case.case_id, "case_id")
            result = self.retrieve(case.request)
            returned = frozenset(unit.source_id for unit in result.units)
            missing = case.expected_source_ids - returned
            leaked = returned & case.forbidden_source_ids
            if missing or leaked:
                failed.append(case.case_id)
            if leaked:
                leakage = True
            evidence_parts.append(
                f"{case.case_id}:{result.evidence_sha256}:{','.join(sorted(returned))}"
            )
        return RetrievalEvaluationReport(
            total=len(cases),
            passed=len(cases) - len(failed),
            failed_case_ids=tuple(failed),
            leakage_detected=leakage,
            evidence_sha256=_sha256_text("|".join(evidence_parts)),
        )

    def source(self, source_id: str) -> KnowledgeSource:
        try:
            return self._sources[source_id]
        except KeyError as exc:
            raise KnowledgeRAGError("unknown source") from exc

    def units_for_source(self, source_id: str) -> tuple[KnowledgeUnit, ...]:
        if source_id not in self._sources:
            raise KnowledgeRAGError("unknown source")
        return tuple(
            sorted(
                (unit for unit in self._units.values() if unit.source_id == source_id),
                key=lambda item: (item.source_version, item.sequence),
            )
        )

    def _create_version(
        self,
        source: KnowledgeSource,
        version_number: int,
        content: str,
    ) -> None:
        version = SourceVersion(
            source_id=source.source_id,
            version=version_number,
            tenant_id=source.tenant_id,
            project_id=source.project_id,
            content_sha256=_sha256_text(content),
            state=VersionState.ACTIVE,
        )
        self._versions[(source.source_id, version_number)] = version
        chunks = _chunk_words(
            content,
            size=self._chunk_size_words,
            overlap=self._chunk_overlap_words,
        )
        for sequence, text in enumerate(chunks):
            unit_id = f"{source.source_id}:v{version_number}:u{sequence}"
            reason = self._guard.inspect(text)
            unit = KnowledgeUnit(
                unit_id=unit_id,
                source_id=source.source_id,
                source_version=version_number,
                tenant_id=source.tenant_id,
                project_id=source.project_id,
                sequence=sequence,
                text=text,
                content_sha256=_sha256_text(text),
                classifications=source.classifications,
                purposes=source.purposes,
                residency=source.residency,
                quarantined_reason=reason,
            )
            self._units[unit_id] = unit
            if reason is not None:
                self._metrics.quarantined_units += 1
                continue
            self._active_unit_ids.add(unit_id)
            self._index.upsert(unit_id, self._embedding.embed(text))

    def _require_scoped_source(
        self,
        source_id: str,
        tenant_id: str,
        project_id: str,
    ) -> KnowledgeSource:
        source = self._sources.get(source_id)
        if source is None:
            raise KnowledgeRAGError("unknown source")
        if source.tenant_id != tenant_id or source.project_id != project_id:
            raise AuthorizationDenied("source scope mismatch")
        return source

    def _active_ids_for_source(self, source_id: str) -> frozenset[str]:
        return frozenset(
            unit_id
            for unit_id in self._active_unit_ids
            if self._units[unit_id].source_id == source_id
        )

    def _is_authorized(
        self,
        unit: KnowledgeUnit,
        scope: PrincipalScope,
        purpose: str,
    ) -> bool:
        if unit.tenant_id != scope.tenant_id or unit.project_id != scope.project_id:
            return False
        if unit.quarantined_reason is not None:
            return False
        if scope.allowed_source_ids is not None and unit.source_id not in scope.allowed_source_ids:
            return False
        if purpose not in scope.allowed_purposes:
            return False
        if unit.purposes and purpose not in unit.purposes:
            return False
        if not unit.classifications <= scope.allowed_classifications:
            return False
        if unit.residency not in scope.allowed_residencies:
            return False
        source = self._sources.get(unit.source_id)
        version = self._versions.get((unit.source_id, unit.source_version))
        if source is None or version is None:
            return False
        return source.state is SourceState.ACTIVE and version.state is VersionState.ACTIVE

    def _validate_returned_unit(
        self,
        request: RetrievalRequest,
        returned: RetrievedUnit,
    ) -> None:
        canonical = self._units.get(returned.unit_id)
        if canonical is None:
            raise KnowledgeRAGError("retrieval result references unknown unit")
        if not self._is_authorized(canonical, request.scope, request.purpose):
            raise AuthorizationDenied("retrieval result contains unauthorized unit")
        if (
            returned.source_id != canonical.source_id
            or returned.source_version != canonical.source_version
            or returned.text != canonical.text
        ):
            raise KnowledgeRAGError("retrieval unit content or lineage mismatch")
        if not all(
            math.isfinite(score)
            for score in (
                returned.semantic_score,
                returned.lexical_score,
                returned.final_score,
            )
        ):
            raise KnowledgeRAGError("retrieval scores must be finite")
        source = self._sources[canonical.source_id]
        version = self._versions[(canonical.source_id, canonical.source_version)]
        citation = returned.citation
        if (
            citation.citation_id != f"cite:{canonical.unit_id}"
            or citation.source_id != canonical.source_id
            or citation.source_version != canonical.source_version
            or citation.unit_id != canonical.unit_id
            or citation.locator != source.locator
            or citation.source_content_sha256 != version.content_sha256
            or citation.unit_content_sha256 != canonical.content_sha256
        ):
            raise KnowledgeRAGError("retrieval citation provenance mismatch")

    def _validate_request(self, request: RetrievalRequest) -> None:
        _require_id(request.retrieval_id, "retrieval_id")
        _require_id(request.scope.principal_id, "principal_id")
        _require_id(request.scope.tenant_id, "tenant_id")
        _require_id(request.scope.project_id, "project_id")
        _require_text(request.query, "query")
        _require_id(request.purpose, "purpose")
        _validate_labels(request.scope.allowed_classifications, "allowed_classifications")
        _validate_labels(request.scope.allowed_purposes, "allowed_purposes")
        _validate_labels(request.scope.allowed_residencies, "allowed_residencies")
        if request.scope.allowed_source_ids is not None:
            _validate_labels(request.scope.allowed_source_ids, "allowed_source_ids")
        if request.purpose not in request.scope.allowed_purposes:
            raise AuthorizationDenied("requested purpose is not authorized")
        if request.top_k < 1 or request.top_k > self._budget.max_top_k:
            raise KnowledgeRAGError("top_k exceeds retrieval budget")
        if request.candidate_limit < request.top_k:
            raise KnowledgeRAGError("candidate_limit must be >= top_k")
        if request.candidate_limit > self._budget.max_candidate_scan:
            raise KnowledgeRAGError("candidate_limit exceeds retrieval budget")
        if request.max_context_chars < 256:
            raise KnowledgeRAGError("max_context_chars must be at least 256")
        if request.max_context_chars > self._budget.max_context_chars:
            raise KnowledgeRAGError("max_context_chars exceeds retrieval budget")


def _chunk_words(text: str, *, size: int, overlap: int) -> tuple[str, ...]:
    words = text.split()
    if not words:
        raise KnowledgeRAGError("content must contain non-whitespace text")
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
        start += size - overlap
    return tuple(chunks)


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z0-9_]+", text.casefold()))


def _lexical_overlap(
    query_tokens: frozenset[str], unit_tokens: frozenset[str]
) -> float:
    if not query_tokens or not unit_tokens:
        return 0.0
    return len(query_tokens & unit_tokens) / len(query_tokens | unit_tokens)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _retrieval_evidence(
    retrieval_id: str,
    query_sha256: str,
    units: tuple[RetrievedUnit, ...],
    scored_count: int,
) -> str:
    parts = [retrieval_id, query_sha256, str(scored_count)]
    for unit in units:
        parts.extend(
            (
                unit.unit_id,
                unit.citation.source_content_sha256,
                unit.citation.unit_content_sha256,
                f"{unit.semantic_score:.12f}",
                f"{unit.lexical_score:.12f}",
                f"{unit.final_score:.12f}",
            )
        )
    return _sha256_text("|".join(parts))


def _snapshot_evidence(
    tenant_id: str,
    project_id: str,
    provider_id: str,
    sources: tuple[KnowledgeSource, ...],
    versions: tuple[SourceVersion, ...],
    units: tuple[KnowledgeUnit, ...],
    active_unit_ids: frozenset[str],
) -> str:
    parts = [tenant_id, project_id, provider_id]
    for source in sources:
        parts.append(
            ":".join(
                (
                    source.source_id,
                    source.tenant_id,
                    source.project_id,
                    source.state.value,
                    str(source.latest_version),
                    source.locator,
                    str(source.trusted),
                    ",".join(sorted(source.classifications)),
                    ",".join(sorted(source.purposes)),
                    source.residency,
                )
            )
        )
    for version in versions:
        parts.append(
            ":".join(
                (
                    version.source_id,
                    str(version.version),
                    version.tenant_id,
                    version.project_id,
                    version.content_sha256,
                    version.state.value,
                )
            )
        )
    for unit in units:
        parts.append(
            ":".join(
                (
                    unit.unit_id,
                    unit.source_id,
                    str(unit.source_version),
                    unit.tenant_id,
                    unit.project_id,
                    str(unit.sequence),
                    unit.content_sha256,
                    ",".join(sorted(unit.classifications)),
                    ",".join(sorted(unit.purposes)),
                    unit.residency,
                    unit.quarantined_reason or "",
                )
            )
        )
    parts.extend(sorted(active_unit_ids))
    return _sha256_text("|".join(parts))


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise KnowledgeRAGError(f"{field} must be non-blank and trimmed")


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise KnowledgeRAGError(f"{field} must be non-blank")


def _validate_labels(values: frozenset[str], field: str) -> None:
    if any(not value or value != value.strip() for value in values):
        raise KnowledgeRAGError(f"{field} must contain non-blank trimmed values")
