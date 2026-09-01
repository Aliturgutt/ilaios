"""Canonical validation pipeline primitives for ILAIOS.

The legacy AuditRecord rule runner remains available for existing callers. SF-11
adds an immutable contract-bound pipeline that validates exact subject digests,
fixed rule sets, read-only validator authority, deterministic rule order, and
non-accepting validation evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum

from src.core.audit_engine import AuditRecord

ValidationRule = Callable[[AuditRecord], str | None]
ContractRule = Callable[[Mapping[str, object]], str | None]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Backward-compatible result for the legacy AuditRecord validator."""

    passed: bool
    errors: tuple[str, ...]


class ValidationPipeline:
    """Backward-compatible deterministic AuditRecord validation runner."""

    def __init__(self, rules: Iterable[ValidationRule] = ()) -> None:
        self._rules: tuple[ValidationRule, ...] = tuple(rules)

    def validate(self, record: AuditRecord) -> ValidationResult:
        errors: list[str] = []
        for rule in self._rules:
            error = rule(record)
            if error is not None:
                errors.append(error)
        return ValidationResult(passed=len(errors) == 0, errors=tuple(errors))


class RuleSeverity(str, Enum):
    """Whether a rule failure blocks a passing aggregate result."""

    MANDATORY = "MANDATORY"
    ADVISORY = "ADVISORY"


class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ValidationContract:
    """Versioned, immutable validation contract for one exact subject."""

    pipeline_run_id: str
    contract_version: str
    tenant_id: str
    task_id: str
    correlation_id: str
    subject_id: str
    subject_sha256: str
    producer_id: str
    validator_id: str
    governed_proposal_sha256: str
    policy_reference: str
    rule_set_id: str
    required_rule_ids: tuple[str, ...]
    environment_id: str
    acceptance_criteria: tuple[str, ...]
    read_only_environment: bool = True


@dataclass(frozen=True, slots=True)
class ValidationRuleSpec:
    """Stable rule identity, order and evaluator binding."""

    rule_id: str
    version: str
    severity: RuleSeverity
    evaluator: ContractRule
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RuleResult:
    rule_id: str
    version: str
    severity: RuleSeverity
    status: RuleStatus
    message: str | None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Content-addressed validation evidence with no acceptance authority."""

    pipeline_run_id: str
    contract_sha256: str
    subject_sha256: str
    status: ValidationStatus
    rule_results: tuple[RuleResult, ...]
    errors: tuple[str, ...]
    acceptance_authorized: bool
    subject_mutated: bool
    report_sha256: str

    @property
    def passed(self) -> bool:
        return self.status is ValidationStatus.PASS


class ContractValidationPipeline:
    """Fail-closed, fixed-rule validation over immutable canonical JSON subjects."""

    def __init__(self, rules: Iterable[ValidationRuleSpec]) -> None:
        self._rules = tuple(rules)
        if not self._rules:
            raise ValueError("contract validation pipeline requires at least one rule")
        seen: set[str] = set()
        for rule in self._rules:
            if not _trimmed(rule.rule_id) or not _trimmed(rule.version):
                raise ValueError("validation rule identity and version are required")
            if rule.rule_id in seen:
                raise ValueError("validation rule IDs must be unique")
            if any(dependency not in seen for dependency in rule.depends_on):
                raise ValueError("validation rule dependency must resolve earlier in order")
            seen.add(rule.rule_id)

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self._rules)

    def run(
        self,
        contract: ValidationContract,
        subject: Mapping[str, object],
    ) -> ValidationReport:
        try:
            subject_before = canonical_sha256(subject)
        except (TypeError, ValueError):
            return self._report(
                contract,
                ValidationStatus.BLOCKED,
                (),
                ("validation subject is not canonical JSON",),
                subject_mutated=False,
            )

        intake_errors = self._intake_errors(contract, subject_before)
        if intake_errors:
            return self._report(
                contract,
                ValidationStatus.BLOCKED,
                (),
                tuple(intake_errors),
                subject_mutated=False,
            )

        results: list[RuleResult] = []
        errors: list[str] = []
        subject_mutated = False
        for rule in self._rules:
            try:
                message = rule.evaluator(subject)
            except Exception as exc:
                message = f"validator exception: {type(exc).__name__}"
                result = RuleResult(
                    rule.rule_id,
                    rule.version,
                    rule.severity,
                    RuleStatus.BLOCKED,
                    message,
                )
                results.append(result)
                errors.append(f"{rule.rule_id}: {message}")
                break

            try:
                current_digest = canonical_sha256(subject)
            except (TypeError, ValueError):
                current_digest = ""
            if current_digest != subject_before:
                subject_mutated = True
                message = "validator mutated the validation subject"
                results.append(
                    RuleResult(
                        rule.rule_id,
                        rule.version,
                        rule.severity,
                        RuleStatus.BLOCKED,
                        message,
                    )
                )
                errors.append(f"{rule.rule_id}: {message}")
                break

            status = RuleStatus.PASS if message is None else RuleStatus.FAIL
            results.append(
                RuleResult(rule.rule_id, rule.version, rule.severity, status, message)
            )
            if message is not None:
                errors.append(f"{rule.rule_id}: {message}")

        aggregate = ValidationStatus.PASS
        if any(result.status is RuleStatus.BLOCKED for result in results):
            aggregate = ValidationStatus.BLOCKED
        elif any(
            result.status is RuleStatus.FAIL
            and result.severity is RuleSeverity.MANDATORY
            for result in results
        ):
            aggregate = ValidationStatus.FAIL

        return self._report(
            contract,
            aggregate,
            tuple(results),
            tuple(errors),
            subject_mutated=subject_mutated,
        )

    def _intake_errors(
        self, contract: ValidationContract, subject_sha256: str
    ) -> list[str]:
        errors: list[str] = []
        required_text = {
            "pipeline_run_id": contract.pipeline_run_id,
            "contract_version": contract.contract_version,
            "tenant_id": contract.tenant_id,
            "task_id": contract.task_id,
            "correlation_id": contract.correlation_id,
            "subject_id": contract.subject_id,
            "producer_id": contract.producer_id,
            "validator_id": contract.validator_id,
            "policy_reference": contract.policy_reference,
            "rule_set_id": contract.rule_set_id,
            "environment_id": contract.environment_id,
        }
        for field, value in required_text.items():
            if not _trimmed(value):
                errors.append(f"{field} must be non-blank and trimmed")
        if _SHA256.fullmatch(contract.subject_sha256) is None:
            errors.append("subject_sha256 must be lowercase SHA-256")
        elif contract.subject_sha256 != subject_sha256:
            errors.append("validation subject digest mismatch")
        if _SHA256.fullmatch(contract.governed_proposal_sha256) is None:
            errors.append("governed_proposal_sha256 must be lowercase SHA-256")
        if contract.producer_id == contract.validator_id:
            errors.append("producer cannot validate its own material result")
        if contract.required_rule_ids != self.rule_ids:
            errors.append("validation contract cannot weaken or reorder the rule set")
        if not contract.acceptance_criteria or any(
            not _trimmed(item) for item in contract.acceptance_criteria
        ):
            errors.append("validation contract requires explicit acceptance criteria")
        if not contract.read_only_environment:
            errors.append("validation environment must be read-only")
        return errors

    def _report(
        self,
        contract: ValidationContract,
        status: ValidationStatus,
        rule_results: tuple[RuleResult, ...],
        errors: tuple[str, ...],
        *,
        subject_mutated: bool,
    ) -> ValidationReport:
        contract_sha256 = canonical_sha256(_contract_material(contract))
        material = {
            "pipeline_run_id": contract.pipeline_run_id,
            "contract_sha256": contract_sha256,
            "subject_sha256": contract.subject_sha256,
            "status": status.value,
            "rule_results": [
                {
                    "rule_id": result.rule_id,
                    "version": result.version,
                    "severity": result.severity.value,
                    "status": result.status.value,
                    "message": result.message,
                }
                for result in rule_results
            ],
            "errors": list(errors),
            "acceptance_authorized": False,
            "subject_mutated": subject_mutated,
        }
        return ValidationReport(
            pipeline_run_id=contract.pipeline_run_id,
            contract_sha256=contract_sha256,
            subject_sha256=contract.subject_sha256,
            status=status,
            rule_results=rule_results,
            errors=errors,
            acceptance_authorized=False,
            subject_mutated=subject_mutated,
            report_sha256=canonical_sha256(material),
        )


def canonical_sha256(value: object) -> str:
    """Return a deterministic SHA-256 for JSON-compatible validation material."""

    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _contract_material(contract: ValidationContract) -> dict[str, object]:
    return {
        "pipeline_run_id": contract.pipeline_run_id,
        "contract_version": contract.contract_version,
        "tenant_id": contract.tenant_id,
        "task_id": contract.task_id,
        "correlation_id": contract.correlation_id,
        "subject_id": contract.subject_id,
        "subject_sha256": contract.subject_sha256,
        "producer_id": contract.producer_id,
        "validator_id": contract.validator_id,
        "governed_proposal_sha256": contract.governed_proposal_sha256,
        "policy_reference": contract.policy_reference,
        "rule_set_id": contract.rule_set_id,
        "required_rule_ids": list(contract.required_rule_ids),
        "environment_id": contract.environment_id,
        "acceptance_criteria": list(contract.acceptance_criteria),
        "read_only_environment": contract.read_only_environment,
    }


def _trimmed(value: str) -> bool:
    return bool(value) and value == value.strip()
