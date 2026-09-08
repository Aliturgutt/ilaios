from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfReader

from services.book_renderers import render_book_package, validate_epub_structure
from services.creative_document_factory import (
    BookAsset,
    BookChapter,
    BookCitation,
    BookMetadata,
    CreativeDocumentError,
    CreativeDocumentFactory,
)
from services.research_data_factory import ResearchDataFactory


def _strict_projection(claim_id: str = "claim-ai") -> dict[str, object]:
    research = ResearchDataFactory()
    research.register_source(
        "source-a",
        locator="fixture://source-a",
        content=b"Independent source A states that AI infrastructure demand increased.",
        trusted=True,
        metadata={"publisher": "publisher-a"},
    )
    research.register_source(
        "source-b",
        locator="fixture://source-b",
        content=b"Independent source B confirms that AI infrastructure demand increased.",
        trusted=True,
        metadata={"publisher": "publisher-b"},
    )
    research.propose_claim(
        claim_id,
        statement="AI infrastructure demand increased.",
        source_ids=("source-a", "source-b"),
    )
    research.register_claim_evidence(
        claim_id,
        source_id="source-a",
        excerpt=b"AI infrastructure demand increased",
        stance="SUPPORTS",
        validator_evidence_ref="validator://claim-a",
        published_on="2026-08-01",
    )
    research.register_claim_evidence(
        claim_id,
        source_id="source-b",
        excerpt=b"AI infrastructure demand increased",
        stance="SUPPORTS",
        validator_evidence_ref="validator://claim-b",
        published_on="2026-08-02",
    )
    research.verify_factual_claim(
        claim_id,
        as_of="2026-09-08",
        max_source_age_days=90,
    )
    return research.knowledge_projection(claim_id)


def _metadata() -> BookMetadata:
    return BookMetadata(
        title="The AI Economy Brief",
        subtitle="Infrastructure, companies and capital",
        author="ILAIOS Editorial",
        publisher="ILAIOS",
        language="en",
        edition="1",
        publication_date="2026-09-08",
        description="A governed sample book for professional document production validation.",
        keywords=("AI", "technology", "economy"),
    )


def _chapters() -> tuple[BookChapter, ...]:
    return (
        BookChapter(
            chapter_id="chapter-1",
            title="Infrastructure",
            body="AI infrastructure demand increased as companies expanded compute capacity. [1]",
            factual=True,
            claim_ids=("claim-ai",),
            citations=(BookCitation("citation-1", "claim-ai", "[1]"),),
            editorial_evidence_ref="editorial://sample/chapter-1",
            originality_evidence_ref="originality://sample/chapter-1",
        ),
        BookChapter(
            chapter_id="chapter-2",
            title="What changes next",
            body="This editorial chapter explains how readers can evaluate future infrastructure signals.",
            factual=False,
            claim_ids=(),
            citations=(),
            editorial_evidence_ref="editorial://sample/chapter-2",
            originality_evidence_ref="originality://sample/chapter-2",
        ),
    )


def _approved_book() -> tuple[CreativeDocumentFactory, object]:
    factory = CreativeDocumentFactory()
    manifest = factory.compose_book(
        "sample-ai-economy",
        metadata=_metadata(),
        chapters=_chapters(),
        research_projections=(_strict_projection(),),
        build_version="1",
    )
    assert manifest.approved is False
    approved = factory.approve_book("sample-ai-economy")
    return factory, approved


def test_professional_book_renders_parseable_pdf_epub_and_manifest() -> None:
    factory, _ = _approved_book()
    package = render_book_package(factory.book_for_export("sample-ai-economy"))

    reader = PdfReader(BytesIO(package.pdf))
    assert len(reader.pages) >= 6
    names = validate_epub_structure(package.epub)
    assert "EPUB/chapter-1.xhtml" in names
    assert "EPUB/chapter-2.xhtml" in names
    assert "EPUB/bibliography.xhtml" in names
    assert package.cover_svg.startswith(b"<svg")
    assert len(package.export_manifest.pdf_sha256) == 64
    assert len(package.export_manifest.epub_sha256) == 64
    assert package.export_manifest.source_provenance_map == (
        ("claim-ai", ("source-a", "source-b")),
    )
    assert b"CONTENT_BOUND_FACTUAL" in package.provenance_json


def test_book_render_is_deterministic() -> None:
    factory, _ = _approved_book()
    manifest = factory.book_for_export("sample-ai-economy")
    first = render_book_package(manifest)
    second = render_book_package(manifest)
    assert first.pdf == second.pdf
    assert first.epub == second.epub
    assert first.cover_svg == second.cover_svg
    assert first.provenance_json == second.provenance_json
    assert first.export_manifest == second.export_manifest


def test_unapproved_book_cannot_render() -> None:
    factory = CreativeDocumentFactory()
    manifest = factory.compose_book(
        "sample-ai-economy",
        metadata=_metadata(),
        chapters=_chapters(),
        research_projections=(_strict_projection(),),
    )
    with pytest.raises(CreativeDocumentError, match="approved books"):
        render_book_package(manifest)
    with pytest.raises(CreativeDocumentError, match="approved books"):
        factory.book_for_export("sample-ai-economy")


def test_factual_book_rejects_non_strict_research_projection() -> None:
    projection = _strict_projection()
    assert isinstance(projection["fact"], dict)
    projection["fact"]["verification_mode"] = "TRUST_THRESHOLD"
    factory = CreativeDocumentFactory()
    with pytest.raises(CreativeDocumentError, match="strict Research/Data verification"):
        factory.compose_book(
            "sample-ai-economy",
            metadata=_metadata(),
            chapters=_chapters(),
            research_projections=(projection,),
        )


def test_unknown_asset_rights_and_missing_asset_fail_closed() -> None:
    unknown = BookAsset(
        asset_id="chart-1",
        body=b"not-empty",
        mime_type="image/png",
        provenance_ref="asset://chart-1",
        rights_state="UNKNOWN",
        alt_text="Sample chart",
    )
    factory = CreativeDocumentFactory()
    with pytest.raises(CreativeDocumentError, match="publication rights are unknown"):
        factory.compose_book(
            "sample-ai-economy",
            metadata=_metadata(),
            chapters=_chapters(),
            research_projections=(_strict_projection(),),
            assets=(unknown,),
        )

    chapter = BookChapter(
        chapter_id="chapter-asset",
        title="Asset chapter",
        body="A factual chapter with an absent image asset. [1]",
        factual=True,
        claim_ids=("claim-ai",),
        citations=(BookCitation("citation-asset", "claim-ai", "[1]"),),
        editorial_evidence_ref="editorial://asset",
        originality_evidence_ref="originality://asset",
        image_asset_ids=("missing-image",),
    )
    with pytest.raises(CreativeDocumentError, match="missing book asset"):
        CreativeDocumentFactory().compose_book(
            "sample-with-missing-asset",
            metadata=_metadata(),
            chapters=(chapter,),
            research_projections=(_strict_projection(),),
        )


def test_duplicate_chapter_placeholder_and_bad_isbn_fail_closed() -> None:
    factory = CreativeDocumentFactory()
    with pytest.raises(CreativeDocumentError, match="chapter ids must be unique"):
        factory.compose_book(
            "duplicate-chapter-book",
            metadata=_metadata(),
            chapters=(_chapters()[0], _chapters()[0]),
            research_projections=(_strict_projection(),),
        )

    placeholder = BookChapter(
        chapter_id="placeholder",
        title="Placeholder",
        body="TODO replace this text",
        factual=False,
        claim_ids=(),
        citations=(),
        editorial_evidence_ref="editorial://placeholder",
        originality_evidence_ref="originality://placeholder",
    )
    with pytest.raises(CreativeDocumentError, match="placeholder"):
        CreativeDocumentFactory().compose_book(
            "placeholder-book",
            metadata=_metadata(),
            chapters=(placeholder,),
            research_projections=(),
        )

    bad = BookMetadata(
        title="Book",
        author="Author",
        publisher="Publisher",
        language="en",
        edition="1",
        publication_date="2026-09-08",
        description="Description",
        keywords=("book",),
        isbn="1234",
    )
    with pytest.raises(CreativeDocumentError, match="ISBN-10 or ISBN-13"):
        CreativeDocumentFactory().compose_book(
            "bad-isbn",
            metadata=bad,
            chapters=(placeholder,),
            research_projections=(),
        )
