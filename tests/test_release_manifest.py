"""Deterministic product-release manifest evidence."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services.release_manifest import (
    ReleaseArtifact,
    ReleaseManifest,
    ReleaseManifestError,
)


def _artifact(name: str, marker: str) -> ReleaseArtifact:
    return ReleaseArtifact(
        name=name,
        kind="desktop-package",
        sha256=marker * 64,
        size_bytes=128,
    )


def test_release_manifest_is_canonical_and_content_addressed() -> None:
    created_at = datetime(2026, 8, 17, 18, 0, tzinfo=timezone.utc)
    first = ReleaseManifest(
        version="1.0.0-rc.1",
        source_sha="a" * 40,
        created_at=created_at,
        artifacts=(_artifact("z.zip", "b"), _artifact("a.zip", "c")),
        sbom_sha256="d" * 64,
        third_party_notices_sha256="e" * 64,
        evidence_ids=("ci-run-2", "ci-run-1"),
    )
    reordered = ReleaseManifest(
        version="1.0.0-rc.1",
        source_sha="a" * 40,
        created_at=created_at,
        artifacts=(_artifact("a.zip", "c"), _artifact("z.zip", "b")),
        sbom_sha256="d" * 64,
        third_party_notices_sha256="e" * 64,
        evidence_ids=("ci-run-1", "ci-run-2"),
    )

    assert first.canonical_json() == reordered.canonical_json()
    assert first.sha256 == reordered.sha256
    assert len(first.sha256) == 64


def test_release_manifest_rejects_duplicate_artifact_names() -> None:
    with pytest.raises(ReleaseManifestError, match="unique"):
        ReleaseManifest(
            version="1.0.0",
            source_sha="a" * 40,
            created_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
            artifacts=(_artifact("desktop.zip", "b"), _artifact("desktop.zip", "c")),
            sbom_sha256="d" * 64,
            third_party_notices_sha256="e" * 64,
            evidence_ids=("ci-run-1",),
        )


def test_release_manifest_requires_exact_source_and_dependency_digests() -> None:
    with pytest.raises(ReleaseManifestError, match="source_sha"):
        ReleaseManifest(
            version="1.0.0",
            source_sha="bad",
            created_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
            artifacts=(_artifact("desktop.zip", "b"),),
            sbom_sha256="d" * 64,
            third_party_notices_sha256="e" * 64,
            evidence_ids=("ci-run-1",),
        )

    with pytest.raises(ReleaseManifestError, match="sbom_sha256"):
        ReleaseManifest(
            version="1.0.0",
            source_sha="a" * 40,
            created_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
            artifacts=(_artifact("desktop.zip", "b"),),
            sbom_sha256="bad",
            third_party_notices_sha256="e" * 64,
            evidence_ids=("ci-run-1",),
        )


def test_non_microsoft_manifest_cannot_claim_microsoft_distribution() -> None:
    with pytest.raises(ReleaseManifestError, match="Microsoft exclusion"):
        ReleaseManifest(
            version="1.0.0",
            source_sha="a" * 40,
            created_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
            artifacts=(_artifact("desktop.zip", "b"),),
            sbom_sha256="d" * 64,
            third_party_notices_sha256="e" * 64,
            evidence_ids=("ci-run-1",),
            microsoft_distribution_excluded=False,
        )
