"""Compatibility and semantic-uniqueness tests for PLATFORM.P04 contracts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from packages.contracts.ilaios_contracts import (
    CANONICAL_JOB_STATE,
    ContractEnvelope,
    ContractKind,
    ReleaseState,
    SchemaCompatibilityError,
    SchemaVersion,
    require_compatible_schema,
)
from src.video_automation.models import JobState


def test_contract_envelope_is_versioned_and_immutable() -> None:
    envelope = ContractEnvelope(
        schema_version=SchemaVersion.V1,
        contract_id="command-001",
        kind=ContractKind.COMMAND,
        occurred_at=datetime.now(timezone.utc),
        payload={"job_id": "job-001"},
    )
    assert envelope.payload["job_id"] == "job-001"
    with pytest.raises(TypeError):
        envelope.payload["job_id"] = "changed"  # type: ignore[index]


def test_schema_compatibility_accepts_canonical_version() -> None:
    require_compatible_schema(SchemaVersion.V1)


def test_contract_rejects_naive_timestamp() -> None:
    with pytest.raises(SchemaCompatibilityError, match="timezone-aware"):
        ContractEnvelope(
            SchemaVersion.V1,
            "event-001",
            ContractKind.EVENT,
            datetime.now(timezone.utc).replace(tzinfo=None),
            {},
        )


def test_job_lifecycle_reuses_existing_canonical_enum() -> None:
    assert CANONICAL_JOB_STATE is JobState


def test_release_state_is_separate_from_job_lifecycle() -> None:
    assert ReleaseState.NOT_DEPLOYED.value == "NOT_DEPLOYED"
    assert set(ReleaseState).isdisjoint(set(JobState))
