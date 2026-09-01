"""Fail-closed golden delivery evidence for the canonical Video Factory.

This module does not manufacture media, provider results, QA outcomes, or policy
state. It only binds already-produced evidence into one immutable delivery
receipt after the required documentary/reels proof dimensions are present.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


class GoldenDeliveryEvidenceError(ValueError):
    """Raised when finished-product evidence is incomplete or inconsistent."""


_REQUIRED_VISUAL_FEATURES = frozenset(
    {"stock_footage", "visual_explainer", "chart", "kinetic_text", "transition"}
)
_REQUIRED_QA_DOMAINS = frozenset({"technical", "visual", "audio", "brand"})
_REQUIRED_SHA256_LENGTH = 64


@dataclass(frozen=True, slots=True)
class GoldenDeliveryReceipt:
    """Evidence binding for one finished documentary/reels artifact."""

    job_id: str
    final_mp4_path: str
    final_mp4_sha256: str
    stock_provider: str
    stock_source_url: str
    stock_license_name: str
    visual_features: frozenset[str]
    narration_present: bool
    sound_effects_present: bool
    music_present: bool
    ducked_music_frames: int
    word_synced_captions_present: bool
    qa_domains_passed: frozenset[str]

    def __post_init__(self) -> None:
        _require_non_blank("job_id", self.job_id)
        _require_non_blank("final_mp4_path", self.final_mp4_path)
        _require_sha256("final_mp4_sha256", self.final_mp4_sha256)
        _require_non_blank("stock_provider", self.stock_provider)
        _require_https("stock_source_url", self.stock_source_url)
        _require_non_blank("stock_license_name", self.stock_license_name)

        missing_visuals = _REQUIRED_VISUAL_FEATURES - self.visual_features
        if missing_visuals:
            raise GoldenDeliveryEvidenceError(
                "golden delivery is missing visual evidence: "
                + ", ".join(sorted(missing_visuals))
            )

        if not self.narration_present:
            raise GoldenDeliveryEvidenceError("golden delivery requires narration evidence")
        if not self.sound_effects_present:
            raise GoldenDeliveryEvidenceError("golden delivery requires SFX evidence")
        if not self.music_present:
            raise GoldenDeliveryEvidenceError("golden delivery requires music evidence")
        if self.ducked_music_frames <= 0:
            raise GoldenDeliveryEvidenceError(
                "golden delivery requires positive music-ducking evidence"
            )
        if not self.word_synced_captions_present:
            raise GoldenDeliveryEvidenceError(
                "golden delivery requires word-synced caption evidence"
            )

        missing_qa = _REQUIRED_QA_DOMAINS - self.qa_domains_passed
        if missing_qa:
            raise GoldenDeliveryEvidenceError(
                "golden delivery is missing QA evidence: "
                + ", ".join(sorted(missing_qa))
            )

        artifact = Path(self.final_mp4_path)
        if not artifact.is_file() or artifact.stat().st_size <= 0:
            raise GoldenDeliveryEvidenceError(
                "final_mp4_path must reference a non-empty finished artifact"
            )
        try:
            digest = sha256(artifact.read_bytes()).hexdigest()
        except OSError as exc:
            raise GoldenDeliveryEvidenceError("final MP4 artifact is unreadable") from exc
        if digest != self.final_mp4_sha256:
            raise GoldenDeliveryEvidenceError("final MP4 checksum does not match artifact bytes")


def _require_non_blank(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise GoldenDeliveryEvidenceError(f"{name} must be non-blank and trimmed")


def _require_https(name: str, value: str) -> None:
    _require_non_blank(name, value)
    if not value.startswith("https://"):
        raise GoldenDeliveryEvidenceError(f"{name} must use https")


def _require_sha256(name: str, value: str) -> None:
    if len(value) != _REQUIRED_SHA256_LENGTH:
        raise GoldenDeliveryEvidenceError(f"{name} must be a SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise GoldenDeliveryEvidenceError(f"{name} must be hexadecimal") from exc
