"""Founder-only persistent Li operator boundary.

Li is an additive founder capability. It does not create a second ILAIOS Core,
identity authority, policy engine, approval engine, or tool gateway. Access is
bound to one canonical user + tenant pair and fails closed for every other
principal, including customer OWNER memberships.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal

from services.identity import IdentityKind, Principal

MemoryKind = Literal["working", "episodic", "semantic"]
MemorySensitivity = Literal["internal", "private"]

_MEMORY_KINDS: Final = frozenset({"working", "episodic", "semantic"})
_MEMORY_SENSITIVITIES: Final = frozenset({"internal", "private"})
_SECRET_MARKERS: Final = (
    "password=",
    "client_secret",
    "api_key=",
    "authorization: bearer ",
    "ghp_",
    "github_pat_",
    "sk-",
)
_MAX_MEMORY_CHARS: Final = 8_000
_LI_SCHEMA_VERSION: Final = "1"


class LiConfigurationError(ValueError):
    """Li founder configuration is absent, partial, or unsafe."""


class LiAccessError(PermissionError):
    """The caller is not the configured founder principal."""


class LiMemoryError(ValueError):
    """A memory write violates the bounded Li memory contract."""


@dataclass(frozen=True, slots=True)
class LiFounderConfig:
    user_id: str
    tenant_id: str
    database_path: Path

    @classmethod
    def from_environment(
        cls,
        env: Mapping[str, str],
    ) -> LiFounderConfig | None:
        user_id = env.get("ILAIOS_LI_FOUNDER_USER_ID", "").strip()
        tenant_id = env.get("ILAIOS_LI_FOUNDER_TENANT_ID", "").strip()
        raw_database = env.get("ILAIOS_LI_DATABASE_PATH", "").strip()
        configured = (bool(user_id), bool(tenant_id), bool(raw_database))
        if not any(configured):
            return None
        if not all(configured):
            raise LiConfigurationError("Li founder configuration is incomplete")
        database_path = Path(raw_database).expanduser()
        if not database_path.name:
            raise LiConfigurationError("Li database path is invalid")
        return cls(user_id=user_id, tenant_id=tenant_id, database_path=database_path)


@dataclass(frozen=True, slots=True)
class LiMemoryRecord:
    memory_id: str
    owner_user_id: str
    owner_tenant_id: str
    kind: MemoryKind
    content: str
    source: str
    confidence: float
    sensitivity: MemorySensitivity
    created_at: datetime


class LiFounderOperator:
    """Founder-only persistent memory and read-only current-state projection."""

    def __init__(
        self,
        *,
        config: LiFounderConfig,
        identity_database: Path,
        runtime_environment: Mapping[str, str] | None = None,
    ) -> None:
        self.config = config
        self.identity_database = identity_database
        self._runtime_environment = dict(runtime_environment or {})
        self.config.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_memory_database()

    @classmethod
    def from_environment(
        cls,
        *,
        identity_database: Path,
        env: Mapping[str, str],
    ) -> LiFounderOperator | None:
        config = LiFounderConfig.from_environment(env)
        if config is None:
            return None
        return cls(
            config=config,
            identity_database=identity_database,
            runtime_environment=env,
        )

    def authorize(self, principal: Principal) -> None:
        if (
            principal.kind is not IdentityKind.HUMAN
            or principal.principal_id != self.config.user_id
            or principal.tenant_id != self.config.tenant_id
            or "OWNER" not in principal.roles
        ):
            raise LiAccessError("Li access denied")

    def remember(
        self,
        principal: Principal,
        *,
        kind: MemoryKind,
        content: str,
        now: datetime,
        source: str = "founder",
        confidence: float = 1.0,
        sensitivity: MemorySensitivity = "private",
    ) -> LiMemoryRecord:
        self.authorize(principal)
        normalized_kind = str(kind).strip()
        normalized_content = content.strip()
        normalized_source = source.strip()
        normalized_sensitivity = str(sensitivity).strip()
        if normalized_kind not in _MEMORY_KINDS:
            raise LiMemoryError("memory kind is invalid")
        if not normalized_content or normalized_content != content:
            raise LiMemoryError("memory content must be non-blank and trimmed")
        if len(normalized_content) > _MAX_MEMORY_CHARS:
            raise LiMemoryError("memory content is too large")
        if not normalized_source or len(normalized_source) > 128:
            raise LiMemoryError("memory source is invalid")
        if normalized_sensitivity not in _MEMORY_SENSITIVITIES:
            raise LiMemoryError("memory sensitivity is invalid")
        if not 0.0 <= confidence <= 1.0:
            raise LiMemoryError("memory confidence is invalid")
        lowered = normalized_content.casefold()
        if any(marker in lowered for marker in _SECRET_MARKERS):
            raise LiMemoryError("secret-like content is not accepted")
        observed = _aware_utc(now)
        record = LiMemoryRecord(
            memory_id=f"li_mem_{uuid.uuid4().hex}",
            owner_user_id=principal.principal_id,
            owner_tenant_id=principal.tenant_id,
            kind=normalized_kind,  # type: ignore[arg-type]
            content=normalized_content,
            source=normalized_source,
            confidence=confidence,
            sensitivity=normalized_sensitivity,  # type: ignore[arg-type]
            created_at=observed,
        )
        with self._connect_memory() as connection:
            connection.execute(
                """
                INSERT INTO li_memories (
                    memory_id, owner_user_id, owner_tenant_id, kind, content,
                    source, confidence, sensitivity, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.memory_id,
                    record.owner_user_id,
                    record.owner_tenant_id,
                    record.kind,
                    record.content,
                    record.source,
                    record.confidence,
                    record.sensitivity,
                    record.created_at.isoformat(),
                ),
            )
        return record

    def list_memories(
        self,
        principal: Principal,
        *,
        limit: int = 50,
    ) -> tuple[LiMemoryRecord, ...]:
        self.authorize(principal)
        if not 1 <= limit <= 100:
            raise LiMemoryError("memory limit is invalid")
        with self._connect_memory() as connection:
            rows = connection.execute(
                """
                SELECT memory_id, owner_user_id, owner_tenant_id, kind, content,
                       source, confidence, sensitivity, created_at
                  FROM li_memories
                 WHERE owner_user_id = ? AND owner_tenant_id = ?
                 ORDER BY created_at DESC, memory_id DESC
                 LIMIT ?
                """,
                (principal.principal_id, principal.tenant_id, limit),
            ).fetchall()
        return tuple(_memory_record(row) for row in rows)

    def snapshot(
        self,
        principal: Principal,
        *,
        now: datetime,
    ) -> dict[str, object]:
        self.authorize(principal)
        current = _aware_utc(now)
        with sqlite3.connect(self.identity_database) as connection:
            row = connection.execute(
                """
                SELECT u.enabled, t.status, m.status, m.role
                  FROM identity_users AS u
                  JOIN identity_memberships AS m ON m.user_id = u.user_id
                  JOIN identity_tenants AS t ON t.tenant_id = m.tenant_id
                 WHERE u.user_id = ? AND m.tenant_id = ? AND m.is_primary = 1
                """,
                (principal.principal_id, principal.tenant_id),
            ).fetchone()
        if row is None:
            raise LiAccessError("canonical founder membership is unavailable")
        enabled, tenant_status, membership_status, role = row
        if (
            not bool(enabled)
            or tenant_status != "ACTIVE"
            or membership_status != "ACTIVE"
            or str(role).strip() != "OWNER"
        ):
            raise LiAccessError("canonical founder membership is inactive")
        with self._connect_memory() as connection:
            memory_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM li_memories
                     WHERE owner_user_id = ? AND owner_tenant_id = ?
                    """,
                    (principal.principal_id, principal.tenant_id),
                ).fetchone()[0]
            )
        return {
            "name": "Li",
            "founder_operator": True,
            "observed_at": current.isoformat(),
            "source": "live_runtime",
            "identity": {
                "user_id": principal.principal_id,
                "tenant_id": principal.tenant_id,
                "role": "OWNER",
            },
            "system": {
                "service": "app.ilaios.com",
                "identity_database": "ready",
                "tenant_status": tenant_status,
                "membership_status": membership_status,
                "release_sha": self._release_sha(),
            },
            "memory_count": memory_count,
        }

    def _release_sha(self) -> str | None:
        for key in ("ILAIOS_RELEASE_SHA", "RENDER_GIT_COMMIT", "GITHUB_SHA"):
            value = self._runtime_environment.get(key, "").strip().casefold()
            if 7 <= len(value) <= 64 and all(character in "0123456789abcdef" for character in value):
                return value
        return None

    def _initialize_memory_database(self) -> None:
        with self._connect_memory() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS li_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS li_memories (
                    memory_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    owner_tenant_id TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('working', 'episodic', 'semantic')),
                    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 8000),
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
                    sensitivity TEXT NOT NULL CHECK (sensitivity IN ('internal', 'private')),
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_li_memories_owner_created
                    ON li_memories(owner_user_id, owner_tenant_id, created_at DESC);
                """
            )
            existing = connection.execute(
                "SELECT value FROM li_meta WHERE key = 'schema_version'"
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO li_meta (key, value) VALUES ('schema_version', ?)",
                    (_LI_SCHEMA_VERSION,),
                )
            elif str(existing[0]) != _LI_SCHEMA_VERSION:
                raise LiConfigurationError("Li memory schema version is unsupported")

    def _connect_memory(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.config.database_path)
        connection.row_factory = sqlite3.Row
        return connection


def _memory_record(row: sqlite3.Row) -> LiMemoryRecord:
    kind = str(row["kind"])
    sensitivity = str(row["sensitivity"])
    if kind not in _MEMORY_KINDS or sensitivity not in _MEMORY_SENSITIVITIES:
        raise LiMemoryError("stored memory is malformed")
    return LiMemoryRecord(
        memory_id=str(row["memory_id"]),
        owner_user_id=str(row["owner_user_id"]),
        owner_tenant_id=str(row["owner_tenant_id"]),
        kind=kind,  # type: ignore[arg-type]
        content=str(row["content"]),
        source=str(row["source"]),
        confidence=float(row["confidence"]),
        sensitivity=sensitivity,  # type: ignore[arg-type]
        created_at=_aware_utc(datetime.fromisoformat(str(row["created_at"]))),
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LiMemoryError("timezone-aware timestamp is required")
    return value.astimezone(UTC)


__all__ = [
    "LiAccessError",
    "LiConfigurationError",
    "LiFounderConfig",
    "LiFounderOperator",
    "LiMemoryError",
    "LiMemoryRecord",
]
