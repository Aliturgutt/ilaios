"""Canonical versioned command, query, event, lifecycle, and release schemas."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any

from src.video_automation.models import JobState


class SchemaCompatibilityError(ValueError):
    """Raised when a contract is malformed or schema-incompatible."""


class SchemaVersion(str, Enum):
    V1 = "1.0"


class ContractKind(str, Enum):
    COMMAND = "command"
    QUERY = "query"
    EVENT = "event"


class ReleaseState(str, Enum):
    """Release state remains independent from implementation maturity."""

    NOT_DEPLOYED = "NOT_DEPLOYED"
    CANARY = "CANARY"
    LIMITED = "LIMITED"
    PRODUCTION = "PRODUCTION"


# Reuse the existing accepted lifecycle enum rather than defining a competitor.
CANONICAL_JOB_STATE = JobState


@dataclass(frozen=True, slots=True)
class ContractEnvelope:
    """Provider-neutral immutable envelope for boundary contracts."""

    schema_version: SchemaVersion
    contract_id: str
    kind: ContractKind
    occurred_at: datetime
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.contract_id or self.contract_id != self.contract_id.strip():
            raise SchemaCompatibilityError(
                "contract_id must be non-blank and trimmed"
            )
        if self.occurred_at.tzinfo is None:
            raise SchemaCompatibilityError("occurred_at must be timezone-aware")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


def require_compatible_schema(
    actual: SchemaVersion,
    supported: SchemaVersion = SchemaVersion.V1,
) -> None:
    """Fail closed unless producer and consumer use the same schema version."""

    if actual is not supported:
        raise SchemaCompatibilityError(
            f"unsupported schema version: {actual.value}; expected {supported.value}"
        )
