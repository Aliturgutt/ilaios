"""Deterministic final episode acceptance gate.

This module combines immutable assembled-output technical validation evidence
with explicit, externally supplied quality checks and produces the final
publishability decision for one episode.

It does not inspect media, call AI models, render, repair, publish, infer
subjective quality, or override failed evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from types import MappingProxyType

from .assembled_output_technical_validation import (
    AssembledOutputTechnicalValidation,
    AssembledOutputTechnicalValidationStatus,
)
from .episode_assembly_execution import EpisodeAssemblyArtifact


class FinalEpisodeAcceptanceError(ValueError):
    """Raised when final episode acceptance cannot be evaluated safely."""


class FinalEpisodeAcceptanceStatus(str, Enum):
    """Normalized final episode disposition."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class FinalEpisodeQualityCheck:
    """One externally established quality-control result."""

    check_code: str
    passed: bool
    evidence_id: str
    detail: str

    def __post_init__(self) -> None:
        _require_non_blank("check_code", self.check_code)
        _require_non_blank("evidence_id", self.evidence_id)
        _require_non_blank("detail", self.detail)


@dataclass(frozen=True, slots=True)
class FinalEpisodeAcceptancePolicy:
    """Explicit deterministic requirements for final episode acceptance."""

    required_quality_checks: tuple[str, ...]
    min_duration_seconds: float
    max_duration_seconds: float
    require_audio_stream: bool = True
    min_source_asset_count: int = 1

    def __post_init__(self) -> None:
        if not self.required_quality_checks:
            raise FinalEpisodeAcceptanceError(
                "required_quality_checks must not be empty"
            )
        normalized = tuple(
            _normalize_code(value) for value in self.required_quality_checks
        )
        if len(normalized) != len(set(normalized)):
            raise FinalEpisodeAcceptanceError(
                "required_quality_checks must be unique"
            )
        if self.min_duration_seconds <= 0:
            raise FinalEpisodeAcceptanceError(
                "min_duration_seconds must be greater than zero"
            )
        if self.max_duration_seconds <= 0:
            raise FinalEpisodeAcceptanceError(
                "max_duration_seconds must be greater than zero"
            )
        if self.min_duration_seconds > self.max_duration_seconds:
            raise FinalEpisodeAcceptanceError(
                "min_duration_seconds must not exceed max_duration_seconds"
            )
        if self.min_source_asset_count <= 0:
            raise FinalEpisodeAcceptanceError(
                "min_source_asset_count must be greater than zero"
            )
        object.__setattr__(self, "required_quality_checks", normalized)


@dataclass(frozen=True, slots=True)
class FinalEpisodeAcceptanceIssue:
    """One deterministic reason an episode was rejected."""

    code: str
    message: str

    def __post_init__(self) -> None:
        _require_non_blank("code", self.code)
        _require_non_blank("message", self.message)


@dataclass(frozen=True, slots=True)
class FinalEpisodeAcceptanceDecision:
    """Immutable final acceptance evidence for one assembled episode."""

    decision_id: str
    artifact_id: str
    technical_validation_id: str
    request_id: str
    episode_id: str
    status: FinalEpisodeAcceptanceStatus
    quality_checks: tuple[FinalEpisodeQualityCheck, ...]
    issues: tuple[FinalEpisodeAcceptanceIssue, ...]
    policy_id: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "decision_id",
            "artifact_id",
            "technical_validation_id",
            "request_id",
            "episode_id",
            "policy_id",
        ):
            _require_non_blank(name, getattr(self, name))
        if self.status is FinalEpisodeAcceptanceStatus.ACCEPTED and self.issues:
            raise FinalEpisodeAcceptanceError(
                "accepted decision must not contain issues"
            )
        if self.status is FinalEpisodeAcceptanceStatus.REJECTED and not self.issues:
            raise FinalEpisodeAcceptanceError(
                "rejected decision must contain at least one issue"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class FinalEpisodeAcceptanceCoordinator:
    """Produce the final deterministic acceptance decision for one episode."""

    def __init__(self, policy: FinalEpisodeAcceptancePolicy) -> None:
        self._policy = policy

    def evaluate(
        self,
        artifact: EpisodeAssemblyArtifact,
        technical_validation: AssembledOutputTechnicalValidation,
        quality_checks: Sequence[FinalEpisodeQualityCheck],
    ) -> FinalEpisodeAcceptanceDecision:
        _validate_identity(artifact, technical_validation)
        normalized_checks = _normalize_quality_checks(quality_checks)
        issues = _evaluate_acceptance(
            artifact,
            technical_validation,
            normalized_checks,
            self._policy,
        )
        status = (
            FinalEpisodeAcceptanceStatus.ACCEPTED
            if not issues
            else FinalEpisodeAcceptanceStatus.REJECTED
        )
        policy_id = _policy_id(self._policy)
        material = _canonical_decision_material(
            artifact,
            technical_validation,
            normalized_checks,
            issues,
            policy_id,
        )
        decision_id = (
            "final-episode-acceptance-"
            f"{sha256(material.encode('utf-8')).hexdigest()[:16]}"
        )
        return FinalEpisodeAcceptanceDecision(
            decision_id=decision_id,
            artifact_id=artifact.artifact_id,
            technical_validation_id=technical_validation.validation_id,
            request_id=artifact.request_id,
            episode_id=artifact.episode_id,
            status=status,
            quality_checks=normalized_checks,
            issues=issues,
            policy_id=policy_id,
            metadata={
                "executor_id": artifact.executor_id,
                "source_asset_count": str(len(artifact.source_asset_ids)),
            },
        )


def _validate_identity(
    artifact: EpisodeAssemblyArtifact,
    technical_validation: AssembledOutputTechnicalValidation,
) -> None:
    if technical_validation.artifact_id != artifact.artifact_id:
        raise FinalEpisodeAcceptanceError(
            "technical validation artifact_id does not match assembly artifact"
        )
    if technical_validation.request_id != artifact.request_id:
        raise FinalEpisodeAcceptanceError(
            "technical validation request_id does not match assembly artifact"
        )
    if technical_validation.episode_id != artifact.episode_id:
        raise FinalEpisodeAcceptanceError(
            "technical validation episode_id does not match assembly artifact"
        )
    if technical_validation.sha256_hex != artifact.sha256_hex:
        raise FinalEpisodeAcceptanceError(
            "technical validation SHA-256 does not match assembly artifact"
        )
    if technical_validation.byte_length != artifact.byte_length:
        raise FinalEpisodeAcceptanceError(
            "technical validation byte_length does not match assembly artifact"
        )


def _normalize_quality_checks(
    quality_checks: Sequence[FinalEpisodeQualityCheck],
) -> tuple[FinalEpisodeQualityCheck, ...]:
    normalized = tuple(
        FinalEpisodeQualityCheck(
            check_code=_normalize_code(check.check_code),
            passed=check.passed,
            evidence_id=check.evidence_id.strip(),
            detail=check.detail.strip(),
        )
        for check in quality_checks
    )
    codes = tuple(check.check_code for check in normalized)
    if len(codes) != len(set(codes)):
        raise FinalEpisodeAcceptanceError("quality check codes must be unique")
    return tuple(sorted(normalized, key=lambda check: check.check_code))


def _evaluate_acceptance(
    artifact: EpisodeAssemblyArtifact,
    technical_validation: AssembledOutputTechnicalValidation,
    quality_checks: tuple[FinalEpisodeQualityCheck, ...],
    policy: FinalEpisodeAcceptancePolicy,
) -> tuple[FinalEpisodeAcceptanceIssue, ...]:
    issues: list[FinalEpisodeAcceptanceIssue] = []

    if (
        technical_validation.status
        is not AssembledOutputTechnicalValidationStatus.PASSED
    ):
        issues.append(
            FinalEpisodeAcceptanceIssue(
                "technical_validation_failed",
                "assembled output technical validation must pass",
            )
        )

    duration = technical_validation.observation.duration_seconds
    if duration < policy.min_duration_seconds:
        issues.append(
            FinalEpisodeAcceptanceIssue(
                "duration_below_minimum",
                (
                    f"minimum duration is {policy.min_duration_seconds}, "
                    f"observed {duration}"
                ),
            )
        )
    if duration > policy.max_duration_seconds:
        issues.append(
            FinalEpisodeAcceptanceIssue(
                "duration_above_maximum",
                (
                    f"maximum duration is {policy.max_duration_seconds}, "
                    f"observed {duration}"
                ),
            )
        )

    if (
        policy.require_audio_stream
        and technical_validation.observation.audio_stream_count < 1
    ):
        issues.append(
            FinalEpisodeAcceptanceIssue(
                "audio_stream_required",
                "final episode must contain at least one audio stream",
            )
        )

    if len(artifact.source_asset_ids) < policy.min_source_asset_count:
        issues.append(
            FinalEpisodeAcceptanceIssue(
                "source_asset_count_below_minimum",
                (
                    f"minimum source asset count is {policy.min_source_asset_count}, "
                    f"observed {len(artifact.source_asset_ids)}"
                ),
            )
        )

    checks_by_code = {check.check_code: check for check in quality_checks}
    for required_code in policy.required_quality_checks:
        check = checks_by_code.get(required_code)
        if check is None:
            issues.append(
                FinalEpisodeAcceptanceIssue(
                    f"quality_check_missing:{required_code}",
                    f"required quality check is missing: {required_code}",
                )
            )
        elif not check.passed:
            issues.append(
                FinalEpisodeAcceptanceIssue(
                    f"quality_check_failed:{required_code}",
                    f"required quality check failed: {required_code}",
                )
            )

    return tuple(sorted(issues, key=lambda issue: issue.code))


def _policy_id(policy: FinalEpisodeAcceptancePolicy) -> str:
    material = "|".join(
        (
            ",".join(policy.required_quality_checks),
            _canonical_float(policy.min_duration_seconds),
            _canonical_float(policy.max_duration_seconds),
            str(policy.require_audio_stream),
            str(policy.min_source_asset_count),
        )
    )
    return f"final-episode-policy-{sha256(material.encode('utf-8')).hexdigest()[:16]}"


def _canonical_decision_material(
    artifact: EpisodeAssemblyArtifact,
    technical_validation: AssembledOutputTechnicalValidation,
    quality_checks: tuple[FinalEpisodeQualityCheck, ...],
    issues: tuple[FinalEpisodeAcceptanceIssue, ...],
    policy_id: str,
) -> str:
    lines = [
        f"artifact_id={artifact.artifact_id}",
        f"technical_validation_id={technical_validation.validation_id}",
        f"episode_id={artifact.episode_id}",
        f"sha256={artifact.sha256_hex}",
        f"policy_id={policy_id}",
    ]
    lines.extend(
        f"quality={check.check_code}|passed={check.passed}|evidence={check.evidence_id}"
        for check in quality_checks
    )
    lines.extend(f"issue={issue.code}" for issue in issues)
    return "\n".join(lines)


def _normalize_code(value: str) -> str:
    _require_non_blank("quality check code", value)
    normalized = value.strip().lower()
    if any(character.isspace() for character in normalized):
        raise FinalEpisodeAcceptanceError(
            "quality check code must not contain whitespace"
        )
    return normalized


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _canonical_float(value: float) -> str:
    return format(value, ".12g")


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise FinalEpisodeAcceptanceError(f"{name} must not be blank")
