"""Tests for Validation Pipeline."""

from datetime import datetime, timezone

import pytest

from src.core.audit_engine import AuditRecord
from src.core.validation_pipeline import ValidationPipeline


def make_record() -> AuditRecord:
    return AuditRecord(
        timestamp=datetime.now(timezone.utc),
        component="test_component",
        action="test_action",
        status="success",
        details={},
    )


def test_empty_pipeline_passes() -> None:
    pipeline = ValidationPipeline([])
    result = pipeline.validate(make_record())
    assert result.passed is True
    assert result.errors == ()


def test_successful_rule_passes() -> None:
    def passing_rule(record: AuditRecord) -> str | None:
        return None

    pipeline = ValidationPipeline([passing_rule])
    result = pipeline.validate(make_record())
    assert result.passed is True
    assert result.errors == ()


def test_failing_rule_returns_failed_result() -> None:
    def failing_rule(record: AuditRecord) -> str | None:
        return "component must be 'authorized'"

    pipeline = ValidationPipeline([failing_rule])
    result = pipeline.validate(make_record())
    assert result.passed is False
    assert result.errors == ("component must be 'authorized'",)


def test_multiple_errors_preserve_order() -> None:
    def rule1(record: AuditRecord) -> str | None:
        return "error one"

    def rule2(record: AuditRecord) -> str | None:
        return "error two"

    def rule3(record: AuditRecord) -> str | None:
        return "error three"

    pipeline = ValidationPipeline([rule1, rule2, rule3])
    result = pipeline.validate(make_record())
    assert result.passed is False
    assert result.errors == ("error one", "error two", "error three")


def test_rules_execute_deterministically() -> None:
    execution_order: list[int] = []

    def rule1(record: AuditRecord) -> str | None:
        execution_order.append(1)
        return None

    def rule2(record: AuditRecord) -> str | None:
        execution_order.append(2)
        return None

    pipeline = ValidationPipeline([rule1, rule2])
    pipeline.validate(make_record())
    assert execution_order == [1, 2]


def test_audit_record_remains_unchanged() -> None:
    record = make_record()
    original_component = record.component

    pipeline = ValidationPipeline([])
    pipeline.validate(record)

    assert record.component == original_component


def test_rule_exception_propagates() -> None:
    def raising_rule(record: AuditRecord) -> str | None:
        raise ValueError("unexpected error")

    pipeline = ValidationPipeline([raising_rule])
    with pytest.raises(ValueError, match="unexpected error"):
        pipeline.validate(make_record())


def test_constructor_stores_rules_independently() -> None:
    rules_list = [lambda r: None, lambda r: None]
    pipeline = ValidationPipeline(rules_list)

    rules_list.clear()

    assert len(pipeline._rules) == 2
