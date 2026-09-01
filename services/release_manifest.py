"""Deterministic ILAIOS product-release manifest primitives.

The manifest binds one exact source revision to content-addressed release
artifacts and release evidence. It records Microsoft distribution as an external
excluded dependency; it does not claim deployment, signing, or Store approval.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime


class ReleaseManifestError(ValueError):
    """Raised when immutable release metadata is malformed."""


_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    name: str
    kind: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        _text("name", self.name)
        _text("kind", self.kind)
        if _SHA256.fullmatch(self.sha256) is None:
            raise ReleaseManifestError("artifact sha256 must be lowercase hexadecimal")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
            raise ReleaseManifestError("artifact size_bytes must be an integer")
        if self.size_bytes <= 0:
            raise ReleaseManifestError("artifact size_bytes must be positive")


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    version: str
    source_sha: str
    created_at: datetime
    artifacts: tuple[ReleaseArtifact, ...]
    sbom_sha256: str
    third_party_notices_sha256: str
    evidence_ids: tuple[str, ...]
    microsoft_distribution_excluded: bool = True

    def __post_init__(self) -> None:
        _text("version", self.version)
        if _SHA1.fullmatch(self.source_sha) is None:
            raise ReleaseManifestError("source_sha must be an exact lowercase SHA-1")
        if self.created_at.tzinfo is None:
            raise ReleaseManifestError("created_at must be timezone-aware")
        if not self.artifacts:
            raise ReleaseManifestError("release manifest requires at least one artifact")
        names = tuple(artifact.name for artifact in self.artifacts)
        if len(set(names)) != len(names):
            raise ReleaseManifestError("release artifact names must be unique")
        for name, value in (
            ("sbom_sha256", self.sbom_sha256),
            ("third_party_notices_sha256", self.third_party_notices_sha256),
        ):
            if _SHA256.fullmatch(value) is None:
                raise ReleaseManifestError(f"{name} must be lowercase hexadecimal")
        if not self.evidence_ids:
            raise ReleaseManifestError("release manifest requires evidence identities")
        for evidence_id in self.evidence_ids:
            _text("evidence_id", evidence_id)
        if self.microsoft_distribution_excluded is not True:
            raise ReleaseManifestError(
                "non-Microsoft manifest must preserve the Microsoft exclusion"
            )

    def canonical_json(self) -> str:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["artifacts"] = [
            asdict(artifact) for artifact in sorted(self.artifacts, key=lambda item: item.name)
        ]
        payload["evidence_ids"] = sorted(self.evidence_ids)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ReleaseManifestError(f"{name} must be non-blank and trimmed")


__all__ = [
    "ReleaseArtifact",
    "ReleaseManifest",
    "ReleaseManifestError",
]
