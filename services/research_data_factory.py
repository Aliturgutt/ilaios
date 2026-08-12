"""Bounded Research/Data Factory with deterministic provenance and claim gates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from statistics import fmean
from typing import Any


class ResearchDataError(ValueError):
    """Research/Data work cannot satisfy a required provenance or validation gate."""


@dataclass(frozen=True, slots=True)
class ResearchSource:
    source_id: str
    locator: str
    content_sha256: str
    trusted: bool
    metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ResearchClaim:
    claim_id: str
    statement: str
    source_ids: tuple[str, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class DataAnalysis:
    analysis_id: str
    values_sha256: str
    count: int
    minimum: float
    maximum: float
    mean: float


class ResearchDataFactory:
    """Create bounded research evidence without fetching arbitrary external data."""

    def __init__(self) -> None:
        self._sources: dict[str, ResearchSource] = {}
        self._claims: dict[str, ResearchClaim] = {}
        self._analyses: dict[str, DataAnalysis] = {}

    def register_source(
        self,
        source_id: str,
        *,
        locator: str,
        content: bytes,
        trusted: bool,
        metadata: dict[str, str] | None = None,
    ) -> ResearchSource:
        _require_id(source_id, "source_id")
        _require_text(locator, "locator")
        if not content:
            raise ResearchDataError("source content must not be empty")
        if source_id in self._sources:
            raise ResearchDataError("source_id already exists")
        normalized_metadata = tuple(sorted((metadata or {}).items()))
        if any(not key or not value for key, value in normalized_metadata):
            raise ResearchDataError("source metadata keys and values must be non-empty")
        source = ResearchSource(
            source_id,
            locator,
            hashlib.sha256(content).hexdigest(),
            trusted,
            normalized_metadata,
        )
        self._sources[source_id] = source
        return source

    def propose_claim(
        self,
        claim_id: str,
        *,
        statement: str,
        source_ids: tuple[str, ...],
    ) -> ResearchClaim:
        _require_id(claim_id, "claim_id")
        _require_text(statement, "statement")
        if claim_id in self._claims:
            raise ResearchDataError("claim_id already exists")
        normalized_sources = _unique_ids(source_ids, "source_ids")
        missing = [item for item in normalized_sources if item not in self._sources]
        if missing:
            raise ResearchDataError(f"claim references unknown sources: {missing}")
        claim = ResearchClaim(claim_id, statement, normalized_sources, False)
        self._claims[claim_id] = claim
        return claim

    def verify_claim(self, claim_id: str, *, min_independent_sources: int = 2) -> ResearchClaim:
        if min_independent_sources < 1:
            raise ResearchDataError("min_independent_sources must be positive")
        claim = self._claims.get(claim_id)
        if claim is None:
            raise ResearchDataError("claim does not exist")
        trusted_sources = tuple(
            source_id
            for source_id in claim.source_ids
            if self._sources[source_id].trusted
        )
        if len(trusted_sources) < min_independent_sources:
            raise ResearchDataError("claim lacks sufficient trusted independent sources")
        verified = ResearchClaim(claim.claim_id, claim.statement, claim.source_ids, True)
        self._claims[claim_id] = verified
        return verified

    def analyze_numeric(self, analysis_id: str, values: tuple[float, ...]) -> DataAnalysis:
        _require_id(analysis_id, "analysis_id")
        if analysis_id in self._analyses:
            raise ResearchDataError("analysis_id already exists")
        if not values:
            raise ResearchDataError("analysis requires at least one numeric value")
        canonical = json.dumps(values, separators=(",", ":"), allow_nan=False)
        analysis = DataAnalysis(
            analysis_id,
            hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            len(values),
            min(values),
            max(values),
            fmean(values),
        )
        self._analyses[analysis_id] = analysis
        return analysis

    def knowledge_projection(self, claim_id: str) -> dict[str, Any]:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise ResearchDataError("claim does not exist")
        if not claim.verified:
            raise ResearchDataError("only verified claims may project as facts")
        evidence = [
            {
                "node_id": f"evidence:{source_id}",
                "node_type": "Evidence",
                "source_id": source_id,
                "locator": self._sources[source_id].locator,
                "content_sha256": self._sources[source_id].content_sha256,
            }
            for source_id in claim.source_ids
        ]
        fact = {
            "node_id": f"fact:{claim.claim_id}",
            "node_type": "Fact",
            "statement": claim.statement,
            "verified": True,
        }
        edges = [
            {
                "edge_id": f"derived:{claim.claim_id}:{source_id}",
                "source_id": fact["node_id"],
                "target_id": f"evidence:{source_id}",
                "edge_type": "derived_from",
            }
            for source_id in claim.source_ids
        ]
        return {"fact": fact, "evidence": evidence, "edges": edges}


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise ResearchDataError(f"{field} must be non-blank and trimmed")


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise ResearchDataError(f"{field} must be non-blank")


def _unique_ids(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not values:
        raise ResearchDataError(f"{field} must not be empty")
    if any(not item or item != item.strip() for item in values):
        raise ResearchDataError(f"{field} must contain trimmed IDs")
    if len(values) != len(set(values)):
        raise ResearchDataError(f"{field} must not contain duplicates")
    return values
