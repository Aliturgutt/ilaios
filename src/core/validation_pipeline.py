"""Validation Pipeline for Hermes Enterprise OS core modules."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from src.core.audit_engine import AuditRecord

ValidationRule = Callable[[AuditRecord], str | None]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    passed: bool
    errors: tuple[str, ...]


class ValidationPipeline:
    def __init__(self, rules: Iterable[ValidationRule] = ()) -> None:
        self._rules: tuple[ValidationRule, ...] = tuple(rules)

    def validate(self, record: AuditRecord) -> ValidationResult:
        errors: list[str] = []
        for rule in self._rules:
            error = rule(record)
            if error is not None:
                errors.append(error)
        return ValidationResult(passed=len(errors) == 0, errors=tuple(errors))
