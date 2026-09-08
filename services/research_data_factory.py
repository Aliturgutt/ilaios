"""Bounded Research/Data Factory with deterministic provenance and claim gates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
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
    verification_mode: str = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class ClaimEvidence:
    source_id: str
    excerpt_sha256: str
    stance: str
    validator_evidence_ref: str
    published_on: str


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
        self._source_contents: dict[str, bytes] = {}
        self._claims: dict[str, ResearchClaim] = {}
        self._claim_evidence: dict[str, dict[str, ClaimEvidence]] = {}
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
        self._source_contents[source_id] = bytes(content)
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
        self._claim_evidence[claim_id] = {}
        return claim

    def register_claim_evidence(
        self,
        claim_id: str,
        *,
        source_id: str,
        excerpt: bytes,
        stance: str,
        validator_evidence_ref: str,
        published_on: str,
    ) -> ClaimEvidence:
        """Bind one exact source excerpt and validator decision to a claim.

        The factory does not infer semantics itself. A factual verification path must
        carry an existing validator evidence reference, while this gate proves that
        the reviewed excerpt is byte-for-byte present in the registered source.
        """

        claim = self._claims.get(claim_id)
        if claim is None:
            raise ResearchDataError("claim does not exist")
        if source_id not in claim.source_ids:
            raise ResearchDataError("claim evidence source is not bound to claim")
        if not excerpt:
            raise ResearchDataError("claim evidence excerpt must not be empty")
        source_content = self._source_contents[source_id]
        if excerpt not in source_content:
            raise ResearchDataError("claim evidence excerpt is not present in source content")
        normalized_stance = stance.strip().upper()
        if normalized_stance not in {"SUPPORTS", "CONTRADICTS"}:
            raise ResearchDataError("claim evidence stance must be SUPPORTS or CONTRADICTS")
        _require_text(validator_evidence_ref, "validator_evidence_ref")
        parsed_published_on = _parse_iso_date(published_on, "published_on")
        evidence = ClaimEvidence(
            source_id=source_id,
            excerpt_sha256=hashlib.sha256(excerpt).hexdigest(),
            stance=normalized_stance,
            validator_evidence_ref=validator_evidence_ref.strip(),
            published_on=parsed_published_on.isoformat(),
        )
        evidence_by_source = self._claim_evidence.setdefault(claim_id, {})
        if source_id in evidence_by_source:
            raise ResearchDataError("claim evidence already exists for source")
        evidence_by_source[source_id] = evidence
        return evidence

    def verify_claim(self, claim_id: str, *, min_independent_sources: int = 2) -> ResearchClaim:
        """Legacy bounded trust-threshold verification kept for compatibility."""

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
        verified = ResearchClaim(
            claim.claim_id,
            claim.statement,
            claim.source_ids,
            True,
            "TRUST_THRESHOLD",
        )
        self._claims[claim_id] = verified
        return verified

    def verify_factual_claim(
        self,
        claim_id: str,
        *,
        as_of: str,
        max_source_age_days: int,
        min_independent_sources: int = 2,
    ) -> ResearchClaim:
        """Fail closed unless evidence is content-bound, non-conflicting and fresh.

        This stricter path is intended for factual publication workflows. It requires
        exact source excerpts plus an upstream semantic-validator evidence reference;
        it never treats source count alone as factual correctness.
        """

        if min_independent_sources < 1:
            raise ResearchDataError("min_independent_sources must be positive")
        if max_source_age_days < 0:
            raise ResearchDataError("max_source_age_days must not be negative")
        claim = self._claims.get(claim_id)
        if claim is None:
            raise ResearchDataError("claim does not exist")
        as_of_date = _parse_iso_date(as_of, "as_of")
        evidence_by_source = self._claim_evidence.get(claim_id, {})
        if not evidence_by_source:
            raise ResearchDataError("factual claim lacks content-bound validation evidence")

        trusted_evidence: list[ClaimEvidence] = []
        publisher_keys: set[str] = set()
        for source_id in claim.source_ids:
            source = self._sources[source_id]
            evidence = evidence_by_source.get(source_id)
            if not source.trusted or evidence is None:
                continue
            if evidence.stance == "CONTRADICTS":
                raise ResearchDataError("factual claim has contradictory trusted evidence")
            published_date = _parse_iso_date(evidence.published_on, "published_on")
            age_days = (as_of_date - published_date).days
            if age_days < 0:
                raise ResearchDataError("source publication date is after verification date")
            if age_days > max_source_age_days:
                raise ResearchDataError("factual claim has stale trusted evidence")
            publisher = _metadata_value(source, "publisher")
            if publisher is None:
                raise ResearchDataError("factual verification requires publisher metadata")
            if publisher in publisher_keys:
                raise ResearchDataError("factual verification requires independent publishers")
            publisher_keys.add(publisher)
            trusted_evidence.append(evidence)

        if len(trusted_evidence) < min_independent_sources:
            raise ResearchDataError(
                "factual claim lacks sufficient fresh trusted content-bound evidence"
            )

        verified = ResearchClaim(
            claim.claim_id,
            claim.statement,
            claim.source_ids,
            True,
            "CONTENT_BOUND_FACTUAL",
        )
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
        claim_evidence = self._claim_evidence.get(claim_id, {})
        evidence = [
            {
                "node_id": f"evidence:{source_id}",
                "node_type": "Evidence",
                "source_id": source_id,
                "locator": self._sources[source_id].locator,
                "content_sha256": self._sources[source_id].content_sha256,
                **(
                    {
                        "excerpt_sha256": claim_evidence[source_id].excerpt_sha256,
                        "stance": claim_evidence[source_id].stance,
                        "validator_evidence_ref": claim_evidence[source_id].validator_evidence_ref,
                        "published_on": claim_evidence[source_id].published_on,
                    }
                    if source_id in claim_evidence
                    else {}
                ),
            }
            for source_id in claim.source_ids
        ]
        fact = {
            "node_id": f"fact:{claim.claim_id}",
            "node_type": "Fact",
            "statement": claim.statement,
            "verified": True,
            "verification_mode": claim.verification_mode,
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


def _metadata_value(source: ResearchSource, key: str) -> str | None:
    for metadata_key, value in source.metadata:
        if metadata_key == key:
            return value
    return None


def _parse_iso_date(value: str, field: str) -> date:
    _require_text(value, field)
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ResearchDataError(f"{field} must be an ISO-8601 date") from exc


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
