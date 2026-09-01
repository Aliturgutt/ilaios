"""Durable governed Knowledge/RAG runtime bound to the canonical identity authority."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from services.identity import (
    AccessRequest,
    AuthorizationEngine,
    AuthorizationRule,
    IdentityKind,
    Principal,
)
from services.knowledge_rag import (
    AuthorizedContext,
    EmbeddingProvider,
    InMemoryVectorIndex,
    KnowledgeRAG,
    PrincipalScope,
    RetrievalRequest,
    RetrievalResult,
)
from services.knowledge_rag_production import SQLiteVectorIndex
from services.rag14_embedding_provider import (
    embedding_provider_from_environment,
    query_embedding_context,
)


class KnowledgeRuntimeError(ValueError):
    """Durable Knowledge runtime state or request violated a runtime invariant."""


@dataclass(frozen=True, slots=True)
class KnowledgeRuntimePolicy:
    principal_id: str
    tenant_id: str
    project_id: str
    allowed_classifications: frozenset[str]
    allowed_purposes: frozenset[str]
    allowed_residencies: frozenset[str]

    def __post_init__(self) -> None:
        for name, value in (
            ("principal_id", self.principal_id),
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
        ):
            if not value or value != value.strip():
                raise KnowledgeRuntimeError(f"{name} must be non-empty and trimmed")
        for name, values in (
            ("allowed_classifications", self.allowed_classifications),
            ("allowed_purposes", self.allowed_purposes),
            ("allowed_residencies", self.allowed_residencies),
        ):
            if not values or any(not value or value != value.strip() for value in values):
                raise KnowledgeRuntimeError(f"{name} must contain trimmed values")


@dataclass(frozen=True, slots=True)
class KnowledgeRuntimeConfig:
    metadata_database: Path
    vector_database: Path
    policy: KnowledgeRuntimePolicy


class DurableKnowledgeRuntime:
    """Single durable runtime wrapper around the canonical KnowledgeRAG service.

    Tenant/project scope is fixed by server-side configuration. Callers never
    submit an authoritative tenant or project identity. Mutations are persisted
    as an integrity-chained event log and deterministically replayed on restart.
    """

    _ACTIONS = (
        "knowledge.ingest",
        "knowledge.update",
        "knowledge.revoke",
        "knowledge.delete",
        "knowledge.retrieve",
    )

    def __init__(self, config: KnowledgeRuntimeConfig) -> None:
        self._config = config
        config.metadata_database.parent.mkdir(parents=True, exist_ok=True)
        config.vector_database.parent.mkdir(parents=True, exist_ok=True)
        self._principal = Principal(
            principal_id=config.policy.principal_id,
            tenant_id=config.policy.tenant_id,
            kind=IdentityKind.SERVICE,
            roles=frozenset({"knowledge-runtime"}),
            attributes=frozenset({("project_id", config.policy.project_id)}),
            authentication_methods=frozenset(),
        )
        self._authorization = AuthorizationEngine(
            tuple(
                AuthorizationRule(
                    action=action,
                    roles=frozenset({"knowledge-runtime"}),
                    subject_attributes=frozenset(
                        {("project_id", config.policy.project_id)}
                    ),
                    resource_attributes=frozenset(
                        {("project_id", config.policy.project_id)}
                    ),
                    identity_kinds=frozenset({IdentityKind.SERVICE}),
                )
                for action in self._ACTIONS
            )
        )
        self._embedding_provider: EmbeddingProvider | None = (
            embedding_provider_from_environment()
        )
        self._index = SQLiteVectorIndex(config.vector_database)
        with self._connect() as connection:
            connection.executescript(
                "CREATE TABLE IF NOT EXISTS knowledge_events ("
                "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
                "operation TEXT NOT NULL, payload_json TEXT NOT NULL, "
                "occurred_at TEXT NOT NULL, previous_hash TEXT NOT NULL, "
                "record_hash TEXT UNIQUE NOT NULL);"
                "CREATE TABLE IF NOT EXISTS knowledge_retrievals ("
                "retrieval_id TEXT PRIMARY KEY, query_sha256 TEXT NOT NULL, "
                "result_evidence_sha256 TEXT NOT NULL, "
                "context_evidence_sha256 TEXT NOT NULL, "
                "citation_json TEXT NOT NULL, occurred_at TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS knowledge_runtime_scope ("
                "scope_id INTEGER PRIMARY KEY CHECK (scope_id = 1), "
                "principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL, "
                "project_id TEXT NOT NULL, binding_sha256 TEXT NOT NULL);"
            )
            self._bind_or_verify_scope(connection)
        self._rag = KnowledgeRAG(
            embedding_provider=self._embedding_provider,
            vector_index=self._index,
        )
        self._rebuild()

    @property
    def tenant_id(self) -> str:
        return self._config.policy.tenant_id

    @property
    def project_id(self) -> str:
        return self._config.policy.project_id

    @property
    def metadata_database(self) -> Path:
        return self._config.metadata_database

    @property
    def vector_database(self) -> Path:
        return self._config.vector_database

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._config.metadata_database)
        connection.row_factory = sqlite3.Row
        return connection

    def _scope_binding(self) -> tuple[str, str, str, str]:
        policy = self._config.policy
        payload = {
            "principal_id": policy.principal_id,
            "project_id": policy.project_id,
            "tenant_id": policy.tenant_id,
        }
        material = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return (
            policy.principal_id,
            policy.tenant_id,
            policy.project_id,
            hashlib.sha256(material.encode("utf-8")).hexdigest(),
        )

    def _bind_or_verify_scope(self, connection: sqlite3.Connection) -> None:
        expected = self._scope_binding()
        row = connection.execute(
            "SELECT principal_id, tenant_id, project_id, binding_sha256 "
            "FROM knowledge_runtime_scope WHERE scope_id = 1"
        ).fetchone()
        if row is None:
            event_count = int(
                connection.execute("SELECT COUNT(*) FROM knowledge_events").fetchone()[0]
            )
            retrieval_count = int(
                connection.execute("SELECT COUNT(*) FROM knowledge_retrievals").fetchone()[0]
            )
            if event_count or retrieval_count or self._index.health().row_count:
                raise KnowledgeRuntimeError(
                    "legacy Knowledge state lacks an immutable runtime scope binding"
                )
            connection.execute(
                "INSERT INTO knowledge_runtime_scope "
                "(scope_id, principal_id, tenant_id, project_id, binding_sha256) "
                "VALUES (1, ?, ?, ?, ?)",
                expected,
            )
            return
        actual = (
            str(row["principal_id"]),
            str(row["tenant_id"]),
            str(row["project_id"]),
            str(row["binding_sha256"]),
        )
        if actual != expected:
            raise KnowledgeRuntimeError(
                "persisted Knowledge runtime scope binding mismatch or integrity failure"
            )

    def _verify_scope_binding(self) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT principal_id, tenant_id, project_id, binding_sha256 "
                "FROM knowledge_runtime_scope WHERE scope_id = 1"
            ).fetchone()
        if row is None:
            raise KnowledgeRuntimeError("persisted Knowledge runtime scope binding is missing")
        actual = (
            str(row["principal_id"]),
            str(row["tenant_id"]),
            str(row["project_id"]),
            str(row["binding_sha256"]),
        )
        if actual != self._scope_binding():
            raise KnowledgeRuntimeError(
                "persisted Knowledge runtime scope binding mismatch or integrity failure"
            )

    def ingest_source(
        self,
        *,
        source_id: str,
        locator: str,
        content: str,
        trusted: bool,
        classifications: frozenset[str],
        purposes: frozenset[str],
        residency: str,
    ) -> dict[str, object]:
        self._authorize("knowledge.ingest")
        if not classifications <= self._config.policy.allowed_classifications:
            raise KnowledgeRuntimeError("source classification exceeds runtime policy")
        if not purposes <= self._config.policy.allowed_purposes:
            raise KnowledgeRuntimeError("source purpose exceeds runtime policy")
        if residency not in self._config.policy.allowed_residencies:
            raise KnowledgeRuntimeError("source residency exceeds runtime policy")
        payload = {
            "source_id": source_id,
            "locator": locator,
            "content": content,
            "trusted": trusted,
            "classifications": sorted(classifications),
            "purposes": sorted(purposes),
            "residency": residency,
        }
        self._commit_event("ingest", payload)
        source = self._rag.source(source_id)
        return self._source_json(source)

    def update_source(self, *, source_id: str, content: str) -> dict[str, object]:
        self._authorize("knowledge.update")
        self._commit_event("update", {"source_id": source_id, "content": content})
        return self._source_json(self._rag.source(source_id))

    def revoke_source(self, *, source_id: str) -> dict[str, object]:
        self._authorize("knowledge.revoke")
        self._commit_event("revoke", {"source_id": source_id})
        return self._source_json(self._rag.source(source_id))

    def delete_source(self, *, source_id: str) -> dict[str, object]:
        self._authorize("knowledge.delete")
        self._commit_event("delete", {"source_id": source_id})
        return self._source_json(self._rag.source(source_id))

    def retrieve(
        self,
        *,
        retrieval_id: str,
        query: str,
        purpose: str,
        top_k: int,
        candidate_limit: int,
        max_context_chars: int,
    ) -> dict[str, object]:
        self._authorize("knowledge.retrieve")
        if purpose not in self._config.policy.allowed_purposes:
            raise KnowledgeRuntimeError("retrieval purpose exceeds runtime policy")
        request = RetrievalRequest(
            retrieval_id=retrieval_id,
            scope=self._principal_scope(),
            query=query,
            purpose=purpose,
            top_k=top_k,
            candidate_limit=candidate_limit,
            max_context_chars=max_context_chars,
        )
        with query_embedding_context():
            result = self._rag.retrieve(request)
        context = self._rag.build_authorized_context(request, result)
        self._record_retrieval(result, context)
        return self._context_json(context, result)

    def state(self) -> dict[str, object]:
        events = self._verified_events()
        with self._connect() as connection:
            retrieval_count = int(
                connection.execute("SELECT COUNT(*) FROM knowledge_retrievals").fetchone()[0]
            )
        health = self._index.health()
        metrics = self._rag.metrics()
        return {
            "status": "ready",
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "embedding_provider_id": self._rag.embedding_provider_id,
            "event_count": len(events),
            "retrieval_count": retrieval_count,
            "vector_index": {
                "adapter_id": health.adapter_id,
                "row_count": health.row_count,
                "integrity_ok": health.integrity_ok,
                "evidence_sha256": health.evidence_sha256,
            },
            "metrics": {
                "ingested_sources": metrics.ingested_sources,
                "updated_sources": metrics.updated_sources,
                "revoked_sources": metrics.revoked_sources,
                "deleted_sources": metrics.deleted_sources,
                "quarantined_units": metrics.quarantined_units,
                "retrievals": metrics.retrievals,
                "empty_retrievals": metrics.empty_retrievals,
                "scored_candidates": metrics.scored_candidates,
                "active_units": metrics.active_units,
            },
        }

    def verify(self) -> dict[str, object]:
        events = self._verified_events()
        health = self._index.health()
        return {
            "event_chain": "verified",
            "event_count": len(events),
            "embedding_provider_id": self._rag.embedding_provider_id,
            "vector_index_integrity": health.integrity_ok,
            "vector_index_evidence_sha256": health.evidence_sha256,
        }

    def _authorize(self, action: str) -> None:
        self._verify_scope_binding()
        self._authorization.authorize(
            self._principal,
            AccessRequest(
                tenant_id=self.tenant_id,
                resource_tenant_id=self.tenant_id,
                action=action,
                resource_attributes=frozenset({("project_id", self.project_id)}),
            ),
            datetime.now(timezone.utc),
        )

    def _principal_scope(self) -> PrincipalScope:
        policy = self._config.policy
        return PrincipalScope(
            principal_id=policy.principal_id,
            tenant_id=policy.tenant_id,
            project_id=policy.project_id,
            allowed_classifications=policy.allowed_classifications,
            allowed_purposes=policy.allowed_purposes,
            allowed_residencies=policy.allowed_residencies,
        )

    def _commit_event(self, operation: str, payload: dict[str, object]) -> None:
        candidate = (*self._verified_events(), (operation, payload))
        self._replay(candidate, persistent=False)
        occurred_at = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record_hash FROM knowledge_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = "0" * 64 if row is None else str(row["record_hash"])
            record_hash = self._event_hash(
                operation, payload_json, occurred_at, previous_hash
            )
            connection.execute(
                "INSERT INTO knowledge_events "
                "(operation, payload_json, occurred_at, previous_hash, record_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                (operation, payload_json, occurred_at, previous_hash, record_hash),
            )
        self._rebuild()

    def _verified_events(self) -> tuple[tuple[str, dict[str, object]], ...]:
        self._verify_scope_binding()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT operation, payload_json, occurred_at, previous_hash, record_hash "
                "FROM knowledge_events ORDER BY sequence"
            ).fetchall()
        previous_hash = "0" * 64
        events: list[tuple[str, dict[str, object]]] = []
        for row in rows:
            operation = str(row["operation"])
            payload_json = str(row["payload_json"])
            occurred_at = str(row["occurred_at"])
            if str(row["previous_hash"]) != previous_hash:
                raise KnowledgeRuntimeError("knowledge event chain previous hash mismatch")
            expected = self._event_hash(
                operation, payload_json, occurred_at, previous_hash
            )
            if str(row["record_hash"]) != expected:
                raise KnowledgeRuntimeError("knowledge event chain integrity failed")
            raw: object = json.loads(payload_json)
            if not isinstance(raw, dict):
                raise KnowledgeRuntimeError("knowledge event payload is invalid")
            events.append((operation, cast(dict[str, object], raw)))
            previous_hash = expected
        return tuple(events)

    @staticmethod
    def _event_hash(
        operation: str, payload_json: str, occurred_at: str, previous_hash: str
    ) -> str:
        material = "|".join((operation, payload_json, occurred_at, previous_hash))
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _rebuild(self) -> None:
        self._index.reset()
        self._rag = self._replay(self._verified_events(), persistent=True)

    def _replay(
        self,
        events: tuple[tuple[str, dict[str, object]], ...],
        *,
        persistent: bool,
    ) -> KnowledgeRAG:
        rag = KnowledgeRAG(
            embedding_provider=self._embedding_provider,
            vector_index=self._index if persistent else InMemoryVectorIndex(),
        )
        for operation, payload in events:
            source_id = self._payload_string(payload, "source_id")
            if operation == "ingest":
                raw_trusted = payload.get("trusted")
                if not isinstance(raw_trusted, bool):
                    raise KnowledgeRuntimeError("persisted trusted flag is invalid")
                rag.ingest_source(
                    source_id,
                    tenant_id=self.tenant_id,
                    project_id=self.project_id,
                    locator=self._payload_string(payload, "locator"),
                    content=self._payload_string(payload, "content"),
                    trusted=raw_trusted,
                    classifications=self._payload_string_set(
                        payload, "classifications"
                    ),
                    purposes=self._payload_string_set(payload, "purposes"),
                    residency=self._payload_string(payload, "residency"),
                )
            elif operation == "update":
                rag.update_source(
                    source_id,
                    tenant_id=self.tenant_id,
                    project_id=self.project_id,
                    content=self._payload_string(payload, "content"),
                )
            elif operation == "revoke":
                rag.revoke_source(
                    source_id,
                    tenant_id=self.tenant_id,
                    project_id=self.project_id,
                )
            elif operation == "delete":
                rag.delete_source(
                    source_id,
                    tenant_id=self.tenant_id,
                    project_id=self.project_id,
                )
            else:
                raise KnowledgeRuntimeError("unknown persisted knowledge operation")
        return rag

    def _record_retrieval(
        self, result: RetrievalResult, context: AuthorizedContext
    ) -> None:
        citations = [
            {
                "source_id": unit.citation.source_id,
                "source_version": unit.citation.source_version,
                "unit_id": unit.citation.unit_id,
                "source_content_sha256": unit.citation.source_content_sha256,
                "unit_content_sha256": unit.citation.unit_content_sha256,
            }
            for unit in context.units
        ]
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO knowledge_retrievals VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        result.retrieval_id,
                        result.query_sha256,
                        result.evidence_sha256,
                        context.evidence_sha256,
                        json.dumps(citations, sort_keys=True, separators=(",", ":")),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise KnowledgeRuntimeError("retrieval_id already exists") from error

    @staticmethod
    def _source_json(source: object) -> dict[str, object]:
        from services.knowledge_rag import KnowledgeSource

        if not isinstance(source, KnowledgeSource):
            raise KnowledgeRuntimeError("invalid knowledge source result")
        return {
            "source_id": source.source_id,
            "tenant_id": source.tenant_id,
            "project_id": source.project_id,
            "locator": source.locator,
            "trusted": source.trusted,
            "classifications": sorted(source.classifications),
            "purposes": sorted(source.purposes),
            "residency": source.residency,
            "state": source.state.value,
            "latest_version": source.latest_version,
        }

    @staticmethod
    def _context_json(
        context: AuthorizedContext, result: RetrievalResult
    ) -> dict[str, object]:
        return {
            "context_id": context.context_id,
            "retrieval_id": context.retrieval_id,
            "tenant_id": context.tenant_id,
            "project_id": context.project_id,
            "purpose": context.purpose,
            "query_sha256": context.query_sha256,
            "safety_boundary": context.safety_boundary,
            "result_evidence_sha256": result.evidence_sha256,
            "context_evidence_sha256": context.evidence_sha256,
            "units": [
                {
                    "unit_id": unit.unit_id,
                    "source_id": unit.source_id,
                    "source_version": unit.source_version,
                    "text": unit.text,
                    "final_score": unit.final_score,
                    "citation": {
                        "citation_id": unit.citation.citation_id,
                        "locator": unit.citation.locator,
                        "source_content_sha256": unit.citation.source_content_sha256,
                        "unit_content_sha256": unit.citation.unit_content_sha256,
                    },
                }
                for unit in context.units
            ],
        }

    @staticmethod
    def _payload_string(payload: dict[str, object], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str):
            raise KnowledgeRuntimeError(f"persisted {key} must be a string")
        return value

    @staticmethod
    def _payload_string_set(payload: dict[str, object], key: str) -> frozenset[str]:
        value = payload.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise KnowledgeRuntimeError(f"persisted {key} must be a string array")
        return frozenset(cast(list[str], value))
