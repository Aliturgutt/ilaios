# mypy: disable-error-code=misc
from datetime import datetime, timedelta, timezone

import pytest

from src.core.audit_engine import (
    AuditEngine,
    AuditRecord,
    AuditValidationError,
)


def test_record_appends_immutable_audit_record() -> None:
    engine = AuditEngine()
    details = {"tool": "filesystem"}

    record = engine.record(
        component="tool_gateway",
        action="dispatch",
        status="success",
        details=details,
    )

    details["tool"] = "modified"

    assert engine.count() == 1
    assert engine.get_latest() == record
    assert record.details["tool"] == "filesystem"

    with pytest.raises(TypeError):
        record.details["tool"] = "network"  # type: ignore[index]


def test_get_records_returns_append_order() -> None:
    engine = AuditEngine()

    first = engine.record(
        component="bootstrap_validator",
        action="validate_git_identity",
        status="success",
    )
    second = engine.record(
        component="tool_gateway",
        action="dispatch",
        status="failure",
    )

    assert engine.get_records() == (first, second)


def test_get_records_filters_records() -> None:
    engine = AuditEngine()

    matching = engine.record(
        component="tool_gateway",
        action="dispatch",
        status="success",
    )
    engine.record(
        component="tool_gateway",
        action="dispatch",
        status="failure",
    )
    engine.record(
        component="bootstrap_validator",
        action="validate_git_identity",
        status="success",
    )

    assert engine.get_records(
        component="tool_gateway",
        action="dispatch",
        status="success",
    ) == (matching,)


def test_get_latest_returns_none_for_empty_engine() -> None:
    assert AuditEngine().get_latest() is None


@pytest.mark.parametrize("value", ["", " ", "\t"])
def test_record_rejects_empty_component(value: str) -> None:
    engine = AuditEngine()

    with pytest.raises(
        AuditValidationError,
        match="Audit component must not be empty",
    ):
        engine.record(
            component=value,
            action="dispatch",
            status="success",
        )


@pytest.mark.parametrize("value", ["", " ", "\t"])
def test_record_rejects_empty_action(value: str) -> None:
    engine = AuditEngine()

    with pytest.raises(
        AuditValidationError,
        match="Audit action must not be empty",
    ):
        engine.record(
            component="tool_gateway",
            action=value,
            status="success",
        )


def test_record_rejects_invalid_status() -> None:
    engine = AuditEngine()

    with pytest.raises(AuditValidationError, match="Audit status must be"):
        engine.record(
            component="tool_gateway",
            action="dispatch",
            status="unknown",
        )


def test_record_rejects_naive_timestamp() -> None:
    engine = AuditEngine()

    with pytest.raises(AuditValidationError, match="timezone-aware"):
        engine.record(
            component="tool_gateway",
            action="dispatch",
            status="success",
            timestamp=datetime(2026, 7, 23, 12, 0, 0),  # noqa: DTZ001
        )


def test_record_rejects_non_utc_timestamp() -> None:
    engine = AuditEngine()
    non_utc_timezone = timezone(timedelta(hours=3))

    with pytest.raises(AuditValidationError, match="must use UTC"):
        engine.record(
            component="tool_gateway",
            action="dispatch",
            status="success",
            timestamp=datetime(
                2026,
                7,
                23,
                12,
                0,
                0,
                tzinfo=non_utc_timezone,
            ),
        )


def test_audit_record_is_frozen() -> None:
    record = AuditRecord(
        timestamp=datetime.now(timezone.utc),
        component="tool_gateway",
        action="dispatch",
        status="success",
        details={},
    )

    with pytest.raises(AttributeError):
        record.status = "failure"
