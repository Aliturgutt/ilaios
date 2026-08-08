"""Versioned canonical contracts shared across ILAIOS boundaries."""

from .schemas import (
    CANONICAL_JOB_STATE,
    ContractEnvelope,
    ContractKind,
    ReleaseState,
    SchemaCompatibilityError,
    SchemaVersion,
    require_compatible_schema,
)

__all__ = [
    "CANONICAL_JOB_STATE",
    "ContractEnvelope",
    "ContractKind",
    "ReleaseState",
    "SchemaCompatibilityError",
    "SchemaVersion",
    "require_compatible_schema",
]
