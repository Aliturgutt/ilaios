"""Canonical M22 semantic and composition validation.

M22 validates content evidence after rendering and technical validation but
before platform adaptation or publishing. It does not render, repair, publish,
or mutate media.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


class ContentValidationError(ValueError):
    """Raised when M22 validation input or policy is invalid."""


@dataclass(frozen=True, slots=True)
class ContentValidationPolicy:
    """Explicit semantic/composition acceptance requirements."""

    expected_scene_ids: tuple[str, ...]
    required_asset_ids: tuple[str, ...]
    required_platforms: tuple[str, ...]
    minimum_duration_seconds: float
    maximum_duration_seconds: float
    require_narration_consistency: bool = True
    require_captions: bool = True
    require_cta: bool = True
    required_brand_terms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_unique_texts("expected_scene_ids", self.expected_scene_ids)
        _validate_unique_texts("required_asset_ids", self.required_asset_ids)
        _validate_unique_texts("required_platforms", self.required_platforms)
        _validate_unique_texts(
            "required_brand_terms",
            self.required_brand_terms,
        )

        if self.minimum_duration_seconds <= 0:
            raise ContentValidationError(
                "minimum_duration_seconds must be greater than zero"
            )

        if self.maximum_duration_seconds < self.minimum_duration_seconds:
            raise ContentValidationError(
                "maximum_duration_seconds must be >= minimum_duration_seconds"
            )


@dataclass(frozen=True, slots=True)
class ContentValidationEvidence:
    """Normalized evidence consumed by M22."""

    job_id: str
    scene_ids: tuple[str, ...]
    narrated_scene_ids: tuple[str, ...]
    asset_ids: tuple[str, ...]
    caption_count: int
    duration_seconds: float
    target_platforms: tuple[str, ...]
    cta_text: str | None
    brand_text: str

    def __post_init__(self) -> None:
        _require_non_blank("job_id", self.job_id)
        _validate_unique_texts("scene_ids", self.scene_ids)
        _validate_unique_texts(
            "narrated_scene_ids",
            self.narrated_scene_ids,
        )
        _validate_unique_texts("asset_ids", self.asset_ids)
        _validate_unique_texts(
            "target_platforms",
            self.target_platforms,
        )

        if self.caption_count < 0:
            raise ContentValidationError(
                "caption_count must be greater than or equal to zero"
            )

        if self.duration_seconds <= 0:
            raise ContentValidationError(
                "duration_seconds must be greater than zero"
            )

        if self.cta_text is not None:
            _require_non_blank("cta_text", self.cta_text)

        if self.brand_text and self.brand_text != self.brand_text.strip():
            raise ContentValidationError(
                "brand_text must not contain surrounding whitespace"
            )


@dataclass(frozen=True, slots=True)
class ContentValidationIssue:
    """One deterministic M22 semantic/composition mismatch."""

    code: str
    message: str

    def __post_init__(self) -> None:
        _require_non_blank("code", self.code)
        _require_non_blank("message", self.message)


@dataclass(frozen=True, slots=True)
class ContentValidationResult:
    """Immutable M22 decision evidence."""

    validation_id: str
    job_id: str
    passed: bool
    issues: tuple[ContentValidationIssue, ...]

    def __post_init__(self) -> None:
        _require_non_blank("validation_id", self.validation_id)
        _require_non_blank("job_id", self.job_id)

        if self.passed and self.issues:
            raise ContentValidationError(
                "passed validation must not contain issues"
            )

        if not self.passed and not self.issues:
            raise ContentValidationError(
                "failed validation must contain at least one issue"
            )


class ContentValidationCoordinator:
    """Validate M22 content evidence against explicit policy."""

    def __init__(
        self,
        policy: ContentValidationPolicy,
    ) -> None:
        self._policy = policy

    def validate(
        self,
        evidence: ContentValidationEvidence,
    ) -> ContentValidationResult:
        issues: list[ContentValidationIssue] = []

        scene_ids = set(evidence.scene_ids)
        narrated_scene_ids = set(evidence.narrated_scene_ids)
        asset_ids = set(evidence.asset_ids)
        target_platforms = set(evidence.target_platforms)

        for scene_id in self._policy.expected_scene_ids:
            if scene_id not in scene_ids:
                issues.append(
                    ContentValidationIssue(
                        code="expected_scene_missing",
                        message=f"expected scene is missing: {scene_id}",
                    )
                )

        if self._policy.require_narration_consistency:
            for scene_id in evidence.scene_ids:
                if scene_id not in narrated_scene_ids:
                    issues.append(
                        ContentValidationIssue(
                            code="narration_scene_missing",
                            message=(
                                "narration is missing for scene: "
                                f"{scene_id}"
                            ),
                        )
                    )

            for scene_id in evidence.narrated_scene_ids:
                if scene_id not in scene_ids:
                    issues.append(
                        ContentValidationIssue(
                            code="narration_scene_unknown",
                            message=(
                                "narration references unknown scene: "
                                f"{scene_id}"
                            ),
                        )
                    )

        if self._policy.require_captions and evidence.caption_count == 0:
            issues.append(
                ContentValidationIssue(
                    code="captions_missing",
                    message="required captions are missing",
                )
            )

        for asset_id in self._policy.required_asset_ids:
            if asset_id not in asset_ids:
                issues.append(
                    ContentValidationIssue(
                        code="required_asset_missing",
                        message=f"required asset is missing: {asset_id}",
                    )
                )

        if (
            evidence.duration_seconds
            < self._policy.minimum_duration_seconds
        ):
            issues.append(
                ContentValidationIssue(
                    code="duration_too_short",
                    message=(
                        f"duration {evidence.duration_seconds} is below "
                        f"{self._policy.minimum_duration_seconds}"
                    ),
                )
            )

        if (
            evidence.duration_seconds
            > self._policy.maximum_duration_seconds
        ):
            issues.append(
                ContentValidationIssue(
                    code="duration_too_long",
                    message=(
                        f"duration {evidence.duration_seconds} exceeds "
                        f"{self._policy.maximum_duration_seconds}"
                    ),
                )
            )

        for platform in self._policy.required_platforms:
            if platform not in target_platforms:
                issues.append(
                    ContentValidationIssue(
                        code="required_platform_missing",
                        message=(
                            "required target platform is missing: "
                            f"{platform}"
                        ),
                    )
                )

        if self._policy.require_cta and evidence.cta_text is None:
            issues.append(
                ContentValidationIssue(
                    code="cta_missing",
                    message="required CTA is missing",
                )
            )

        normalized_brand_text = evidence.brand_text.casefold()

        for term in self._policy.required_brand_terms:
            if term.casefold() not in normalized_brand_text:
                issues.append(
                    ContentValidationIssue(
                        code="branding_term_missing",
                        message=f"required branding term is missing: {term}",
                    )
                )

        canonical_material = "|".join(
            (
                evidence.job_id,
                ",".join(evidence.scene_ids),
                ",".join(evidence.narrated_scene_ids),
                ",".join(evidence.asset_ids),
                str(evidence.caption_count),
                _number(evidence.duration_seconds),
                ",".join(evidence.target_platforms),
                evidence.cta_text or "none",
                evidence.brand_text,
                ",".join(issue.code for issue in issues),
                ",".join(issue.message for issue in issues),
            )
        )

        validation_id = (
            "content-validation-"
            + sha256(
                canonical_material.encode("utf-8")
            ).hexdigest()[:24]
        )

        return ContentValidationResult(
            validation_id=validation_id,
            job_id=evidence.job_id,
            passed=not issues,
            issues=tuple(issues),
        )


def _validate_unique_texts(
    name: str,
    values: tuple[str, ...],
) -> None:
    seen: set[str] = set()

    for value in values:
        _require_non_blank(name, value)

        if value in seen:
            raise ContentValidationError(
                f"{name} must contain unique values"
            )

        seen.add(value)


def _number(value: float) -> str:
    return format(value, ".9g")


def _require_non_blank(
    name: str,
    value: str,
) -> None:
    if not value or not value.strip():
        raise ContentValidationError(
            f"{name} must not be blank"
        )

    if value != value.strip():
        raise ContentValidationError(
            f"{name} must not contain surrounding whitespace"
        )
