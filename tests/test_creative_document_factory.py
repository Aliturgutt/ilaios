"""Tests for bounded Creative/Document Factory provenance and approval gates."""

import pytest

from services.creative_document_factory import CreativeDocumentError, CreativeDocumentFactory


def _factory() -> CreativeDocumentFactory:
    factory = CreativeDocumentFactory()
    factory.register_source(
        "source-a",
        locator="fixture://creative/source-a",
        content=b"approved source material",
        trusted=True,
    )
    return factory


def test_approved_artifact_exports_deterministic_provenance() -> None:
    first = _factory()
    artifact = first.compose(
        "artifact-1",
        title="Bounded document",
        sections=("Section one.", "Section two."),
        source_ids=("source-a",),
    )
    assert artifact.approved is False
    approved = first.approve("artifact-1")
    projection = first.export_projection("artifact-1")

    second = _factory()
    second_artifact = second.compose(
        "artifact-1",
        title="Bounded document",
        sections=("Section one.", "Section two."),
        source_ids=("source-a",),
    )

    assert approved.body_sha256 == second_artifact.body_sha256
    assert projection["body_sha256"] == approved.body_sha256
    assert projection["sources"][0]["source_id"] == "source-a"
    assert len(projection["sources"][0]["content_sha256"]) == 64


def test_unapproved_artifact_fails_closed_on_export() -> None:
    factory = _factory()
    factory.compose(
        "artifact-1",
        title="Draft",
        sections=("Not approved.",),
        source_ids=("source-a",),
    )
    with pytest.raises(CreativeDocumentError, match="only approved artifacts"):
        factory.export_projection("artifact-1")


def test_untrusted_or_unknown_sources_fail_closed() -> None:
    factory = CreativeDocumentFactory()
    factory.register_source(
        "untrusted",
        locator="fixture://untrusted",
        content=b"untrusted material",
        trusted=False,
    )
    with pytest.raises(CreativeDocumentError, match="sources must be trusted"):
        factory.compose(
            "artifact-untrusted",
            title="Unsafe",
            sections=("Content",),
            source_ids=("untrusted",),
        )
    with pytest.raises(CreativeDocumentError, match="unknown sources"):
        factory.compose(
            "artifact-missing",
            title="Missing",
            sections=("Content",),
            source_ids=("missing",),
        )


def test_duplicate_sources_blank_sections_and_duplicate_artifacts_fail_closed() -> None:
    factory = _factory()
    with pytest.raises(CreativeDocumentError, match="duplicates"):
        factory.compose(
            "duplicate-sources",
            title="Duplicate",
            sections=("Content",),
            source_ids=("source-a", "source-a"),
        )
    with pytest.raises(CreativeDocumentError, match="sections"):
        factory.compose(
            "blank-section",
            title="Blank",
            sections=("",),
            source_ids=("source-a",),
        )
    factory.compose(
        "artifact-1",
        title="First",
        sections=("Content",),
        source_ids=("source-a",),
    )
    with pytest.raises(CreativeDocumentError, match="artifact_id already exists"):
        factory.compose(
            "artifact-1",
            title="Second",
            sections=("Content",),
            source_ids=("source-a",),
        )
