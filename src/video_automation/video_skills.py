"""ILAIOS-native Video Factory skill contracts and governed evaluation primitives.

Skills are immutable capabilities executed by M30 composition roots.  They are
not agents, provider registries, policy authorities, or evidence stores.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType


class VideoSkillError(ValueError):
    """A video skill contract or governed decision is invalid."""


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise VideoSkillError(f"{name} must be non-blank and trimmed")


def _sha256(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise VideoSkillError("artifact identity must be lowercase SHA-256")


class SkillRisk(str, Enum):
    READ_ONLY = "read_only"
    MEDIA_MUTATION = "media_mutation"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


@dataclass(frozen=True, slots=True)
class VideoSkillManifest:
    skill_id: str
    version: str
    capability_id: str
    implementation: str
    risk: SkillRisk
    permissions: tuple[str, ...]
    owner: str = "ILAIOS"
    license_id: str = "LicenseRef-ILAIOS-Proprietary"
    source_provenance: str = "ILAIOS-native"

    def __post_init__(self) -> None:
        for name in ("skill_id", "version", "capability_id", "implementation"):
            _text(name, getattr(self, name))
        if not self.skill_id.startswith("ilaios.skill.video."):
            raise VideoSkillError("video skills require the canonical ILAIOS namespace")
        if self.capability_id != "ilaios.capability.video-media-factory":
            raise VideoSkillError(
                "video skills must bind to the canonical factory capability"
            )
        if self.owner != "ILAIOS" or self.source_provenance != "ILAIOS-native":
            raise VideoSkillError(
                "proprietary video skills must be ILAIOS-native and ownable"
            )
        if self.license_id != "LicenseRef-ILAIOS-Proprietary":
            raise VideoSkillError("video skill license must preserve ILAIOS ownership")
        if len(self.permissions) != len(set(self.permissions)):
            raise VideoSkillError("skill permissions must be unique")
        for permission in self.permissions:
            _text("permission", permission)

    @property
    def digest(self) -> str:
        material = "|".join(
            (
                self.skill_id,
                self.version,
                self.capability_id,
                self.implementation,
                self.risk.value,
                *self.permissions,
                self.owner,
                self.license_id,
                self.source_provenance,
            )
        )
        return sha256(material.encode()).hexdigest()


VIDEO_SKILLS: tuple[VideoSkillManifest, ...] = (
    VideoSkillManifest(
        "ilaios.skill.video.edit.trim",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:EditOperation",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.edit.concatenate",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:EditOperation",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.edit.overlay",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:EditOperation",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.edit.crop",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:EditOperation",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.edit.scale",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:EditOperation",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.edit.audio-mix",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:EditOperation",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.direction.cinematography",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:CreativeDirection",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.qa.evaluate",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:IndependentVideoEvaluator",
        SkillRisk.READ_ONLY,
        ("media.read",),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.repair.selective",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:SelectiveRepairController",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.thumbnail.generate",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_skills:ThumbnailRequest",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.publish.social",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.publishing_execution:PlatformPublisher",
        SkillRisk.EXTERNAL_SIDE_EFFECT,
        ("media.read", "social.publish"),
    ),
)


def validate_video_skills(skills: Sequence[VideoSkillManifest] = VIDEO_SKILLS) -> None:
    ids = [skill.skill_id for skill in skills]
    if len(ids) != len(set(ids)):
        raise VideoSkillError("video skill IDs must be unique")
    digests = [skill.digest for skill in skills]
    if len(digests) != len(set(digests)):
        raise VideoSkillError("video skill manifests must have unique digests")


class EditKind(str, Enum):
    TRIM = "trim"
    CONCATENATE = "concatenate"
    OVERLAY = "overlay"
    CROP = "crop"
    SCALE = "scale"
    AUDIO_MIX = "audio_mix"


@dataclass(frozen=True, slots=True)
class EditOperation:
    operation_id: str
    kind: EditKind
    input_asset_ids: tuple[str, ...]
    output_asset_id: str
    parameters: Mapping[str, str | int | float | bool]

    def __post_init__(self) -> None:
        _text("operation_id", self.operation_id)
        _text("output_asset_id", self.output_asset_id)
        if not self.input_asset_ids:
            raise VideoSkillError("edit operation requires registered input assets")
        if len(self.input_asset_ids) != len(set(self.input_asset_ids)):
            raise VideoSkillError("edit input assets must be unique")
        if self.output_asset_id in self.input_asset_ids:
            raise VideoSkillError("editing cannot overwrite a registered input asset")
        object.__setattr__(
            self, "parameters", MappingProxyType(dict(sorted(self.parameters.items())))
        )


@dataclass(frozen=True, slots=True)
class CreativeDirection:
    direction_id: str
    visual_intent: str
    shot_scale: str
    camera_angle: str
    camera_movement: str
    lighting: str
    palette: tuple[str, ...]
    pacing: str
    continuity_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "direction_id",
            "visual_intent",
            "shot_scale",
            "camera_angle",
            "camera_movement",
            "lighting",
            "pacing",
        ):
            _text(name, getattr(self, name))
        if not self.palette or not self.continuity_keys:
            raise VideoSkillError(
                "creative direction requires palette and continuity keys"
            )


class QaDomain(str, Enum):
    VISUAL = "visual"
    AUDIO = "audio"
    BRAND = "brand"
    TECHNICAL = "technical"


@dataclass(frozen=True, slots=True)
class QaFinding:
    finding_id: str
    domain: QaDomain
    passed: bool
    score: float
    threshold: float
    evidence_reference: str
    repair_target: str | None = None

    def __post_init__(self) -> None:
        _text("finding_id", self.finding_id)
        _text("evidence_reference", self.evidence_reference)
        if not 0 <= self.score <= 1 or not 0 <= self.threshold <= 1:
            raise VideoSkillError("QA score and threshold must be normalized")
        if self.passed != (self.score >= self.threshold):
            raise VideoSkillError("QA decision must follow its declared threshold")
        if not self.passed and self.repair_target is None:
            raise VideoSkillError("failed QA requires a bounded repair target")


@dataclass(frozen=True, slots=True)
class FinalVideoEvaluation:
    evaluator_id: str
    artifact_sha256: str
    findings: tuple[QaFinding, ...]
    passed: bool


class IndependentVideoEvaluator:
    """Aggregate externally-produced observations; never self-generate evidence."""

    def evaluate(
        self, artifact_sha256: str, findings: Sequence[QaFinding], *, evaluator_id: str
    ) -> FinalVideoEvaluation:
        _sha256(artifact_sha256)
        _text("evaluator_id", evaluator_id)
        items = tuple(findings)
        if len(items) != len(QaDomain) or {item.domain for item in items} != set(
            QaDomain
        ):
            raise VideoSkillError(
                "final evaluation requires visual, audio, brand, and technical findings"
            )
        return FinalVideoEvaluation(
            evaluator_id, artifact_sha256, items, all(item.passed for item in items)
        )


@dataclass(frozen=True, slots=True)
class RepairRequest:
    repair_id: str
    finding_id: str
    target: str
    attempt: int


class SelectiveRepairController:
    def __init__(self, max_attempts: int = 2) -> None:
        if max_attempts < 1:
            raise VideoSkillError("repair attempts must be positive")
        self._max_attempts = max_attempts

    def plan(
        self, evaluation: FinalVideoEvaluation, prior_attempts: Mapping[str, int]
    ) -> tuple[RepairRequest, ...]:
        repairs: list[RepairRequest] = []
        for finding in evaluation.findings:
            if finding.passed:
                continue
            prior_attempt = prior_attempts.get(finding.finding_id, 0)
            if prior_attempt < 0:
                raise VideoSkillError("prior repair attempts must not be negative")
            attempt = prior_attempt + 1
            if attempt > self._max_attempts:
                raise VideoSkillError(f"repair limit exhausted: {finding.finding_id}")
            assert finding.repair_target is not None
            repairs.append(
                RepairRequest(
                    f"repair:{finding.finding_id}:{attempt}",
                    finding.finding_id,
                    finding.repair_target,
                    attempt,
                )
            )
        return tuple(repairs)


@dataclass(frozen=True, slots=True)
class MediaSecurityPolicy:
    workspace_root: Path
    allowed_extensions: frozenset[str]
    max_input_bytes: int
    require_provenance: bool = True

    def admit(
        self, path: Path, *, byte_length: int, provenance_reference: str | None
    ) -> Path:
        root = self.workspace_root.resolve()
        if path.is_symlink():
            raise VideoSkillError("symbolic-link media inputs are prohibited")
        candidate = path.resolve()
        if root != candidate and root not in candidate.parents:
            raise VideoSkillError("media path escapes the configured sandbox")
        if not candidate.is_file():
            raise VideoSkillError("media input must be an existing regular file")
        if candidate.suffix.lower() not in self.allowed_extensions:
            raise VideoSkillError("media extension is not allowed")
        if byte_length < 1 or byte_length > self.max_input_bytes:
            raise VideoSkillError("media byte length violates policy")
        if candidate.stat().st_size != byte_length:
            raise VideoSkillError("declared media byte length does not match the file")
        if self.require_provenance and not provenance_reference:
            raise VideoSkillError("media provenance is required")
        return candidate


@dataclass(frozen=True, slots=True)
class ThumbnailRequest:
    request_id: str
    artifact_sha256: str
    timestamp_ms: int
    width: int
    height: int
    safe_text: str

    def __post_init__(self) -> None:
        _text("request_id", self.request_id)
        _sha256(self.artifact_sha256)
        if self.timestamp_ms < 0 or self.width < 1 or self.height < 1:
            raise VideoSkillError("thumbnail dimensions and timestamp must be valid")
        if len(self.safe_text) > 120:
            raise VideoSkillError("thumbnail text exceeds the safety bound")


validate_video_skills()
