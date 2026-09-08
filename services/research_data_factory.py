"""Bounded Research/Data Factory with governed ingestion, provenance and persistence."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import fmean
from typing import Any, Protocol
from urllib.parse import urlsplit


class ResearchDataError(ValueError):
    """Research/Data work cannot satisfy a required provenance or validation gate."""


class ResearchToolGateway(Protocol):
    """Narrow dispatch contract implemented by the canonical ToolGateway."""

    def dispatch(
        self,
        tool_name: str,
        *args: Any,
        path: str | None = None,
        **kwargs: Any,
    ) -> Any: ...


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


@dataclass(frozen=True, slots=True)
class FetchedResearchSource:
    """Exact payload returned by a governed external-source ToolGateway handler."""

    final_locator: str
    content: bytes
    retrieved_at: str
    media_type: str
    provider_evidence_ref: str
    tenant_id: str


@dataclass(frozen=True, slots=True)
class IngestionRecord:
    ingestion_id: str
    source_id: str
    source_format: str
    final_locator: str
    retrieved_at: str
    media_type: str
    provider_evidence_ref: str
    content_sha256: str


class ResearchDataFactory:
    """Create bounded research evidence using the incumbent governance authorities.

    In-memory construction remains supported for backward compatibility. Durable or
    external execution requires an explicit tenant. External reads are never fetched
    directly by this factory: they must cross the canonical ToolGateway and return a
    content/provenance receipt through ``FetchedResearchSource``.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        tenant_id: str | None = None,
        tool_gateway: ResearchToolGateway | None = None,
    ) -> None:
        self._sources: dict[str, ResearchSource] = {}
        self._source_contents: dict[str, bytes] = {}
        self._claims: dict[str, ResearchClaim] = {}
        self._claim_evidence: dict[str, dict[str, ClaimEvidence]] = {}
        self._analyses: dict[str, DataAnalysis] = {}
        self._ingestions: dict[str, IngestionRecord] = {}
        self._database_path = str(database_path) if database_path is not None else None
        self._tenant_id = tenant_id.strip() if tenant_id is not None else None
        self._tool_gateway = tool_gateway

        if tenant_id is not None:
            _require_id(self._tenant_id or "", "tenant_id")
        if self._database_path is not None:
            if self._tenant_id is None:
                raise ResearchDataError("durable Research/Data storage requires tenant_id")
            self._migrate()
            self._load_persisted_state()

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
        self._persist_source(source, bytes(content))
        self._sources[source_id] = source
        self._source_contents[source_id] = bytes(content)
        return source

    def ingest_external_source(
        self,
        source_id: str,
        *,
        locator: str,
        source_format: str,
        trusted: bool,
        metadata: dict[str, str] | None = None,
        tool_name: str = "research.fetch_source",
        max_bytes: int = 5_000_000,
    ) -> IngestionRecord:
        """Fetch, validate, register and durably record one governed data source."""

        if self._tenant_id is None:
            raise ResearchDataError("external ingestion requires tenant_id")
        if self._tool_gateway is None:
            raise ResearchDataError("external ingestion requires canonical ToolGateway")
        _require_public_https_locator(locator)
        normalized_format = source_format.strip().lower()
        if normalized_format not in {"json", "csv"}:
            raise ResearchDataError("source_format must be json or csv")
        if max_bytes < 1 or max_bytes > 25_000_000:
            raise ResearchDataError("max_bytes is outside the bounded ingestion limit")
        _require_id(tool_name, "tool_name")

        fetched = self._tool_gateway.dispatch(
            tool_name,
            locator=locator,
            tenant_id=self._tenant_id,
            max_bytes=max_bytes,
        )
        if not isinstance(fetched, FetchedResearchSource):
            raise ResearchDataError("research source adapter returned an invalid receipt")
        if fetched.tenant_id != self._tenant_id:
            raise ResearchDataError("research source adapter crossed tenant boundary")
        _require_public_https_locator(fetched.final_locator)
        if not fetched.content:
            raise ResearchDataError("research source adapter returned empty content")
        if len(fetched.content) > max_bytes:
            raise ResearchDataError("research source exceeds bounded ingestion limit")
        _require_text(fetched.retrieved_at, "retrieved_at")
        _require_text(fetched.media_type, "media_type")
        _require_text(fetched.provider_evidence_ref, "provider_evidence_ref")
        self._validate_ingested_content(fetched.content, normalized_format)

        ingestion_id = hashlib.sha256(
            (
                self._tenant_id
                + "\n"
                + source_id
                + "\n"
                + fetched.final_locator
                + "\n"
                + fetched.retrieved_at
                + "\n"
                + hashlib.sha256(fetched.content).hexdigest()
            ).encode("utf-8")
        ).hexdigest()
        source_metadata = dict(metadata or {})
        source_metadata.update(
            {
                "ingestion_id": ingestion_id,
                "source_format": normalized_format,
                "retrieved_at": fetched.retrieved_at,
                "media_type": fetched.media_type,
                "provider_evidence_ref": fetched.provider_evidence_ref,
            }
        )
        source = self.register_source(
            source_id,
            locator=fetched.final_locator,
            content=fetched.content,
            trusted=trusted,
            metadata=source_metadata,
        )
        record = IngestionRecord(
            ingestion_id=ingestion_id,
            source_id=source_id,
            source_format=normalized_format,
            final_locator=fetched.final_locator,
            retrieved_at=fetched.retrieved_at,
            media_type=fetched.media_type,
            provider_evidence_ref=fetched.provider_evidence_ref,
            content_sha256=source.content_sha256,
        )
        self._persist_ingestion(record)
        self._ingestions[ingestion_id] = record
        return record

    def ingestion_record(self, ingestion_id: str) -> IngestionRecord:
        _require_id(ingestion_id, "ingestion_id")
        try:
            return self._ingestions[ingestion_id]
        except KeyError as exc:
            raise ResearchDataError("ingestion record does not exist") from exc

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
        self._persist_claim(claim)
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
        """Bind one exact source excerpt and validator decision to a claim."""

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
        self._persist_claim_evidence(claim_id, evidence)
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
        self._persist_claim_verification(verified)
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
        """Fail closed unless evidence is content-bound, non-conflicting and fresh."""

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
        self._persist_claim_verification(verified)
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
        self._persist_analysis(analysis)
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

    @staticmethod
    def _validate_ingested_content(content: bytes, source_format: str) -> None:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ResearchDataError("ingested source must be UTF-8") from exc
        if source_format == "json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                raise ResearchDataError("ingested JSON source is invalid") from exc
            return
        try:
            rows = csv.reader(io.StringIO(text))
            header = next(rows)
        except (csv.Error, StopIteration) as exc:
            raise ResearchDataError("ingested CSV source is invalid") from exc
        if not header or any(not column.strip() for column in header):
            raise ResearchDataError("ingested CSV source requires a non-empty header")

    def _migrate(self) -> None:
        assert self._database_path is not None
        if self._database_path != ":memory:":
            Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_sources (
                    tenant_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    locator TEXT NOT NULL,
                    content BLOB NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    trusted INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, source_id)
                );
                CREATE TABLE IF NOT EXISTS research_claims (
                    tenant_id TEXT NOT NULL,
                    claim_id TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    verified INTEGER NOT NULL,
                    verification_mode TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, claim_id)
                );
                CREATE TABLE IF NOT EXISTS research_claim_sources (
                    tenant_id TEXT NOT NULL,
                    claim_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    source_id TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, claim_id, ordinal)
                );
                CREATE TABLE IF NOT EXISTS research_claim_evidence (
                    tenant_id TEXT NOT NULL,
                    claim_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    excerpt_sha256 TEXT NOT NULL,
                    stance TEXT NOT NULL,
                    validator_evidence_ref TEXT NOT NULL,
                    published_on TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, claim_id, source_id)
                );
                CREATE TABLE IF NOT EXISTS research_analyses (
                    tenant_id TEXT NOT NULL,
                    analysis_id TEXT NOT NULL,
                    values_sha256 TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    minimum REAL NOT NULL,
                    maximum REAL NOT NULL,
                    mean REAL NOT NULL,
                    PRIMARY KEY (tenant_id, analysis_id)
                );
                CREATE TABLE IF NOT EXISTS research_ingestions (
                    tenant_id TEXT NOT NULL,
                    ingestion_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_format TEXT NOT NULL,
                    final_locator TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    provider_evidence_ref TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, ingestion_id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        if self._database_path is None:
            raise ResearchDataError("durable Research/Data storage is not configured")
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _load_persisted_state(self) -> None:
        assert self._tenant_id is not None
        with self._connect() as connection:
            for row in connection.execute(
                """
                SELECT source_id, locator, content, content_sha256, trusted, metadata_json
                FROM research_sources WHERE tenant_id = ? ORDER BY source_id
                """,
                (self._tenant_id,),
            ):
                content = bytes(row["content"])
                if hashlib.sha256(content).hexdigest() != row["content_sha256"]:
                    raise ResearchDataError("persisted research source checksum mismatch")
                metadata_raw = json.loads(row["metadata_json"])
                if not isinstance(metadata_raw, dict):
                    raise ResearchDataError("persisted research source metadata is invalid")
                metadata = tuple(sorted((str(k), str(v)) for k, v in metadata_raw.items()))
                source = ResearchSource(
                    source_id=str(row["source_id"]),
                    locator=str(row["locator"]),
                    content_sha256=str(row["content_sha256"]),
                    trusted=bool(row["trusted"]),
                    metadata=metadata,
                )
                self._sources[source.source_id] = source
                self._source_contents[source.source_id] = content

            claim_sources: dict[str, list[str]] = {}
            for row in connection.execute(
                """
                SELECT claim_id, source_id FROM research_claim_sources
                WHERE tenant_id = ? ORDER BY claim_id, ordinal
                """,
                (self._tenant_id,),
            ):
                claim_sources.setdefault(str(row["claim_id"]), []).append(str(row["source_id"]))
            for row in connection.execute(
                """
                SELECT claim_id, statement, verified, verification_mode
                FROM research_claims WHERE tenant_id = ? ORDER BY claim_id
                """,
                (self._tenant_id,),
            ):
                claim_id = str(row["claim_id"])
                sources = tuple(claim_sources.get(claim_id, []))
                if not sources or any(source_id not in self._sources for source_id in sources):
                    raise ResearchDataError("persisted research claim source binding is invalid")
                self._claims[claim_id] = ResearchClaim(
                    claim_id=claim_id,
                    statement=str(row["statement"]),
                    source_ids=sources,
                    verified=bool(row["verified"]),
                    verification_mode=str(row["verification_mode"]),
                )
                self._claim_evidence[claim_id] = {}

            for row in connection.execute(
                """
                SELECT claim_id, source_id, excerpt_sha256, stance,
                       validator_evidence_ref, published_on
                FROM research_claim_evidence WHERE tenant_id = ?
                ORDER BY claim_id, source_id
                """,
                (self._tenant_id,),
            ):
                claim_id = str(row["claim_id"])
                source_id = str(row["source_id"])
                claim = self._claims.get(claim_id)
                if claim is None or source_id not in claim.source_ids:
                    raise ResearchDataError("persisted claim evidence binding is invalid")
                self._claim_evidence[claim_id][source_id] = ClaimEvidence(
                    source_id=source_id,
                    excerpt_sha256=str(row["excerpt_sha256"]),
                    stance=str(row["stance"]),
                    validator_evidence_ref=str(row["validator_evidence_ref"]),
                    published_on=str(row["published_on"]),
                )

            for row in connection.execute(
                """
                SELECT analysis_id, values_sha256, count, minimum, maximum, mean
                FROM research_analyses WHERE tenant_id = ? ORDER BY analysis_id
                """,
                (self._tenant_id,),
            ):
                analysis = DataAnalysis(
                    analysis_id=str(row["analysis_id"]),
                    values_sha256=str(row["values_sha256"]),
                    count=int(row["count"]),
                    minimum=float(row["minimum"]),
                    maximum=float(row["maximum"]),
                    mean=float(row["mean"]),
                )
                self._analyses[analysis.analysis_id] = analysis

            for row in connection.execute(
                """
                SELECT ingestion_id, source_id, source_format, final_locator,
                       retrieved_at, media_type, provider_evidence_ref, content_sha256
                FROM research_ingestions WHERE tenant_id = ? ORDER BY ingestion_id
                """,
                (self._tenant_id,),
            ):
                source_id = str(row["source_id"])
                source = self._sources.get(source_id)
                if source is None or source.content_sha256 != row["content_sha256"]:
                    raise ResearchDataError("persisted ingestion source binding is invalid")
                record = IngestionRecord(
                    ingestion_id=str(row["ingestion_id"]),
                    source_id=source_id,
                    source_format=str(row["source_format"]),
                    final_locator=str(row["final_locator"]),
                    retrieved_at=str(row["retrieved_at"]),
                    media_type=str(row["media_type"]),
                    provider_evidence_ref=str(row["provider_evidence_ref"]),
                    content_sha256=str(row["content_sha256"]),
                )
                self._ingestions[record.ingestion_id] = record

    def _persist_source(self, source: ResearchSource, content: bytes) -> None:
        if self._database_path is None:
            return
        assert self._tenant_id is not None
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO research_sources
                    (tenant_id, source_id, locator, content, content_sha256, trusted, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._tenant_id,
                        source.source_id,
                        source.locator,
                        content,
                        source.content_sha256,
                        int(source.trusted),
                        json.dumps(dict(source.metadata), sort_keys=True, separators=(",", ":")),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ResearchDataError("source_id already exists in durable storage") from exc

    def _persist_ingestion(self, record: IngestionRecord) -> None:
        if self._database_path is None:
            return
        assert self._tenant_id is not None
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_ingestions
                (tenant_id, ingestion_id, source_id, source_format, final_locator,
                 retrieved_at, media_type, provider_evidence_ref, content_sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._tenant_id,
                    record.ingestion_id,
                    record.source_id,
                    record.source_format,
                    record.final_locator,
                    record.retrieved_at,
                    record.media_type,
                    record.provider_evidence_ref,
                    record.content_sha256,
                ),
            )

    def _persist_claim(self, claim: ResearchClaim) -> None:
        if self._database_path is None:
            return
        assert self._tenant_id is not None
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO research_claims
                    (tenant_id, claim_id, statement, verified, verification_mode)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        self._tenant_id,
                        claim.claim_id,
                        claim.statement,
                        int(claim.verified),
                        claim.verification_mode,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO research_claim_sources
                    (tenant_id, claim_id, ordinal, source_id) VALUES (?, ?, ?, ?)
                    """,
                    [
                        (self._tenant_id, claim.claim_id, ordinal, source_id)
                        for ordinal, source_id in enumerate(claim.source_ids)
                    ],
                )
        except sqlite3.IntegrityError as exc:
            raise ResearchDataError("claim_id already exists in durable storage") from exc

    def _persist_claim_evidence(self, claim_id: str, evidence: ClaimEvidence) -> None:
        if self._database_path is None:
            return
        assert self._tenant_id is not None
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO research_claim_evidence
                    (tenant_id, claim_id, source_id, excerpt_sha256, stance,
                     validator_evidence_ref, published_on)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._tenant_id,
                        claim_id,
                        evidence.source_id,
                        evidence.excerpt_sha256,
                        evidence.stance,
                        evidence.validator_evidence_ref,
                        evidence.published_on,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ResearchDataError("claim evidence already exists in durable storage") from exc

    def _persist_claim_verification(self, claim: ResearchClaim) -> None:
        if self._database_path is None:
            return
        assert self._tenant_id is not None
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE research_claims
                SET verified = ?, verification_mode = ?
                WHERE tenant_id = ? AND claim_id = ?
                """,
                (int(claim.verified), claim.verification_mode, self._tenant_id, claim.claim_id),
            )
            if cursor.rowcount != 1:
                raise ResearchDataError("durable claim verification target is missing")

    def _persist_analysis(self, analysis: DataAnalysis) -> None:
        if self._database_path is None:
            return
        assert self._tenant_id is not None
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO research_analyses
                    (tenant_id, analysis_id, values_sha256, count, minimum, maximum, mean)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._tenant_id,
                        analysis.analysis_id,
                        analysis.values_sha256,
                        analysis.count,
                        analysis.minimum,
                        analysis.maximum,
                        analysis.mean,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ResearchDataError("analysis_id already exists in durable storage") from exc


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


def _require_public_https_locator(value: str) -> None:
    _require_text(value, "locator")
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError as exc:
        raise ResearchDataError("research source locator is malformed") from exc
    if parsed.scheme.casefold() != "https" or parsed.hostname is None:
        raise ResearchDataError("external research source must use HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ResearchDataError("external research source cannot contain userinfo")
    host = parsed.hostname.casefold().rstrip(".")
    if not host or host == "localhost" or host.endswith(".localhost"):
        raise ResearchDataError("external research source cannot be local")
    if port is not None and (port < 1 or port > 65535):
        raise ResearchDataError("external research source port is invalid")


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


__all__ = [
    "ClaimEvidence",
    "DataAnalysis",
    "FetchedResearchSource",
    "IngestionRecord",
    "ResearchClaim",
    "ResearchDataError",
    "ResearchDataFactory",
    "ResearchSource",
]
