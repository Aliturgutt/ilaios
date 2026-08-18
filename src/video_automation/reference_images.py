"""Provider-neutral reference-image contracts for Video Factory generation.

User uploads form a bounded visual-reference pool. Provider adapters may use a
smaller deterministic subset according to their proven capabilities. Exact
first/last-frame anchors remain a separate contract because video providers
assign different semantics to frame control and reference-to-video guidance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from urllib.parse import urlparse

MAX_USER_REFERENCE_IMAGES = 8
DEFAULT_PROVIDER_REFERENCE_IMAGES = 3
ALLOWED_REFERENCE_MEDIA_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)
MAX_REFERENCE_IMAGE_BYTES = 10 * 1024 * 1024
MAX_REFERENCE_UPLOAD_BYTES = 40 * 1024 * 1024


class ReferenceImageError(ValueError):
    """Raised when a visual-reference contract is unsafe or ambiguous."""


class ReferenceImageRole(str, Enum):
    """Provider-neutral intent used for deterministic outbound selection."""

    SUBJECT_PRIMARY = "subject_primary"
    SUBJECT_SECONDARY = "subject_secondary"
    DETAIL = "detail"
    STYLE = "style"
    ENVIRONMENT = "environment"


_ROLE_PRIORITY = {
    ReferenceImageRole.SUBJECT_PRIMARY: 0,
    ReferenceImageRole.SUBJECT_SECONDARY: 1,
    ReferenceImageRole.DETAIL: 2,
    ReferenceImageRole.STYLE: 3,
    ReferenceImageRole.ENVIRONMENT: 4,
}


@dataclass(frozen=True, slots=True)
class VideoReferenceImage:
    """One already-validated and externally staged reference image.

    ``asset_id`` and ``sha256_digest`` bind the provider URL back to the
    tenant-scoped source asset. ``https_url`` is intentionally required here:
    local paths and loopback URLs are never valid provider-dispatch material.
    """

    asset_id: str
    sha256_digest: str
    https_url: str
    role: ReferenceImageRole = ReferenceImageRole.SUBJECT_PRIMARY

    def __post_init__(self) -> None:
        _text("asset_id", self.asset_id)
        _sha256("sha256_digest", self.sha256_digest)
        _https_url("https_url", self.https_url)
        if not isinstance(self.role, ReferenceImageRole):
            raise ReferenceImageError("role must be a ReferenceImageRole")

    def to_wire(self) -> dict[str, str]:
        return {
            "asset_id": self.asset_id,
            "sha256": self.sha256_digest,
            "url": self.https_url,
            "role": self.role.value,
        }


@dataclass(frozen=True, slots=True)
class ReferenceSelection:
    selected: tuple[VideoReferenceImage, ...]
    omitted_asset_ids: tuple[str, ...]

    @property
    def selected_count(self) -> int:
        return len(self.selected)

    @property
    def omitted_count(self) -> int:
        return len(self.omitted_asset_ids)


def validate_reference_pool(
    references: tuple[VideoReferenceImage, ...],
) -> tuple[VideoReferenceImage, ...]:
    """Validate the user-level pool without silently changing its meaning."""

    if len(references) > MAX_USER_REFERENCE_IMAGES:
        raise ReferenceImageError(
            f"at most {MAX_USER_REFERENCE_IMAGES} reference images are allowed"
        )
    asset_ids: set[str] = set()
    digests: set[str] = set()
    for reference in references:
        if reference.asset_id in asset_ids:
            raise ReferenceImageError("reference asset_id values must be unique")
        if reference.sha256_digest in digests:
            raise ReferenceImageError("duplicate reference image content is not allowed")
        asset_ids.add(reference.asset_id)
        digests.add(reference.sha256_digest)
    return references


def select_provider_references(
    references: tuple[VideoReferenceImage, ...],
    *,
    provider_limit: int = DEFAULT_PROVIDER_REFERENCE_IMAGES,
) -> ReferenceSelection:
    """Select a stable quality-first subset for one provider request.

    The eight-image UI limit is an ingestion limit, not a claim about any
    external model. Until an adapter proves another safe bound, outbound
    reference-to-video requests use at most three images. Subject identity and
    product details outrank style/environment guidance; original order breaks
    equal-role ties deterministically.
    """

    validate_reference_pool(references)
    if provider_limit <= 0 or provider_limit > MAX_USER_REFERENCE_IMAGES:
        raise ReferenceImageError("provider reference limit is outside safe bounds")
    indexed = tuple(enumerate(references))
    ranked = sorted(indexed, key=lambda item: (_ROLE_PRIORITY[item[1].role], item[0]))
    selected_pairs = ranked[:provider_limit]
    selected_indexes = {index for index, _ in selected_pairs}
    selected = tuple(reference for _, reference in selected_pairs)
    omitted = tuple(
        reference.asset_id
        for index, reference in indexed
        if index not in selected_indexes
    )
    return ReferenceSelection(selected=selected, omitted_asset_ids=omitted)


def parse_reference_images(raw: object) -> tuple[VideoReferenceImage, ...]:
    """Parse provider-request JSON into validated typed references."""

    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ReferenceImageError("reference_images must be an array")
    references: list[VideoReferenceImage] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ReferenceImageError("reference image entry must be an object")
        try:
            asset_id = item["asset_id"]
            digest = item["sha256"]
            url = item["url"]
            role = item["role"]
        except KeyError as exc:
            raise ReferenceImageError("reference image entry is incomplete") from exc
        if not all(isinstance(value, str) for value in (asset_id, digest, url, role)):
            raise ReferenceImageError("reference image fields must be strings")
        try:
            normalized_role = ReferenceImageRole(role)
        except ValueError as exc:
            raise ReferenceImageError("unknown reference image role") from exc
        references.append(
            VideoReferenceImage(
                asset_id=asset_id,
                sha256_digest=digest,
                https_url=url,
                role=normalized_role,
            )
        )
    return validate_reference_pool(tuple(references))


def build_openrouter_input_references(
    references: tuple[VideoReferenceImage, ...],
    *,
    provider_limit: int = DEFAULT_PROVIDER_REFERENCE_IMAGES,
) -> tuple[list[dict[str, object]], ReferenceSelection]:
    """Translate selected staged images to OpenRouter reference-to-video shape."""

    selection = select_provider_references(references, provider_limit=provider_limit)
    payload = [
        {
            "type": "image_url",
            "image_url": {"url": reference.https_url},
        }
        for reference in selection.selected
    ]
    return payload, selection


def reference_pool_digest(references: tuple[VideoReferenceImage, ...]) -> str:
    """Return a deterministic identity for idempotency/evidence binding."""

    validate_reference_pool(references)
    material = "\n".join(
        f"{item.asset_id}|{item.sha256_digest}|{item.role.value}|{item.https_url}"
        for item in references
    )
    return sha256(material.encode("utf-8")).hexdigest()


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ReferenceImageError(f"{name} must be normalized non-blank text")


def _sha256(name: str, value: str) -> None:
    if len(value) != 64:
        raise ReferenceImageError(f"{name} must be a SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ReferenceImageError(f"{name} must be hexadecimal") from exc


def _https_url(name: str, value: str) -> None:
    _text(name, value)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ReferenceImageError(f"{name} must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ReferenceImageError(f"{name} must not contain embedded credentials")
