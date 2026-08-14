"""Finished-product certification over existing editing/caption/thumbnail engines."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from src.media_quality import MediaAcceptanceEvidence, MediaKind

from .caption_subtitle import CaptionExportManifest
from .thumbnail_generation import ThumbnailArtifact


class FinishedProductError(ValueError):
    """Raised when a raw/intermediate artifact is presented as a finished product."""


@dataclass(frozen=True, slots=True)
class FinishedVideoProduct:
    product_id: str
    job_id: str
    final_path: str
    final_sha256: str
    byte_length: int
    acceptance_id: str
    encoding_evidence_ref: str
    audio_mix_evidence_ref: str
    caption_manifest_sha256: str | None
    thumbnail_sha256: str | None
    title: str
    description: str

    def __post_init__(self) -> None:
        for name, value in (
            ("product_id", self.product_id),
            ("job_id", self.job_id),
            ("final_path", self.final_path),
            ("acceptance_id", self.acceptance_id),
            ("encoding_evidence_ref", self.encoding_evidence_ref),
            ("audio_mix_evidence_ref", self.audio_mix_evidence_ref),
            ("title", self.title),
            ("description", self.description),
        ):
            _text(name, value)
        _sha256("final_sha256", self.final_sha256)
        if self.caption_manifest_sha256 is not None:
            _sha256("caption_manifest_sha256", self.caption_manifest_sha256)
        if self.thumbnail_sha256 is not None:
            _sha256("thumbnail_sha256", self.thumbnail_sha256)
        if self.byte_length <= 0:
            raise FinishedProductError("finished product byte_length must be positive")


class FinishedProductCertifier:
    """Certify only the exact final encoded artifact accepted by media QA."""

    def certify(
        self,
        *,
        job_id: str,
        final_path: str | Path,
        acceptance: MediaAcceptanceEvidence,
        encoding_evidence_ref: str,
        audio_mix_evidence_ref: str,
        title: str,
        description: str,
        captions: CaptionExportManifest | None = None,
        thumbnail: ThumbnailArtifact | None = None,
        captions_required: bool = False,
        thumbnail_required: bool = False,
    ) -> FinishedVideoProduct:
        for name, value in (
            ("job_id", job_id),
            ("encoding_evidence_ref", encoding_evidence_ref),
            ("audio_mix_evidence_ref", audio_mix_evidence_ref),
            ("title", title),
            ("description", description),
        ):
            _text(name, value)
        if acceptance.media_kind is not MediaKind.VIDEO:
            raise FinishedProductError("finished video requires VIDEO acceptance evidence")
        if not acceptance.accepted:
            raise FinishedProductError("raw or failed-QA artifact cannot be a finished product")
        path = Path(final_path)
        if path.is_symlink() or not path.is_file():
            raise FinishedProductError("finished video must be an existing regular file")
        body = path.read_bytes()
        if not body:
            raise FinishedProductError("finished video must not be empty")
        final_sha = sha256(body).hexdigest()
        if acceptance.artifact_sha256 != final_sha:
            raise FinishedProductError(
                "final encoded artifact SHA does not match acceptance evidence"
            )
        if captions_required and captions is None:
            raise FinishedProductError("finished-product policy requires captions")
        if thumbnail_required and thumbnail is None:
            raise FinishedProductError("finished-product policy requires thumbnail")

        caption_digest = None
        if captions is not None:
            caption_digest = _verify_caption_manifest(captions)
        thumbnail_digest = None
        if thumbnail is not None:
            if thumbnail.source_artifact_sha256 != final_sha:
                raise FinishedProductError("thumbnail is not bound to final video SHA")
            _verify_file_sha(Path(thumbnail.output_path), thumbnail.sha256_hex, "thumbnail")
            thumbnail_digest = thumbnail.sha256_hex

        product_material = "\n".join(
            (
                f"job={job_id}",
                f"final_sha={final_sha}",
                f"acceptance={acceptance.acceptance_id}",
                f"encoding={encoding_evidence_ref}",
                f"audio={audio_mix_evidence_ref}",
                f"captions={caption_digest or ''}",
                f"thumbnail={thumbnail_digest or ''}",
                f"title={title}",
                f"description={description}",
            )
        )
        product_id = "finished-video-" + sha256(product_material.encode()).hexdigest()[:24]
        return FinishedVideoProduct(
            product_id=product_id,
            job_id=job_id,
            final_path=str(path.resolve()),
            final_sha256=final_sha,
            byte_length=len(body),
            acceptance_id=acceptance.acceptance_id,
            encoding_evidence_ref=encoding_evidence_ref,
            audio_mix_evidence_ref=audio_mix_evidence_ref,
            caption_manifest_sha256=caption_digest,
            thumbnail_sha256=thumbnail_digest,
            title=title,
            description=description,
        )


def _verify_caption_manifest(manifest: CaptionExportManifest) -> str:
    artifacts = (
        (Path(manifest.structured_json_path), manifest.structured_json_sha256, "caption JSON"),
        (Path(manifest.srt_path), manifest.srt_sha256, "caption SRT"),
        (Path(manifest.vtt_path), manifest.vtt_sha256, "caption VTT"),
    )
    material: list[str] = []
    for path, expected, label in artifacts:
        _verify_file_sha(path, expected, label)
        material.append(f"{label}:{expected}")
    return sha256("\n".join(material).encode()).hexdigest()


def _verify_file_sha(path: Path, expected: str, label: str) -> None:
    _sha256(f"{label} sha256", expected)
    if path.is_symlink() or not path.is_file():
        raise FinishedProductError(f"{label} must be an existing regular file")
    body = path.read_bytes()
    if not body or sha256(body).hexdigest() != expected:
        raise FinishedProductError(f"{label} content does not match evidence SHA")


def _text(name: str, value: str) -> None:
    if not value or not value.strip() or value != value.strip():
        raise FinishedProductError(f"{name} must be non-blank normalized text")


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise FinishedProductError(f"{name} must be lowercase SHA-256")
