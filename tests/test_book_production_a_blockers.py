from __future__ import annotations

import base64
import zipfile
from dataclasses import replace
from io import BytesIO

import pytest
from pypdf import PdfReader

from services.book_renderers import render_book_package
from services.creative_document_factory import (
    BookAsset,
    BookChapter,
    BookCitation,
    BookMetadata,
    CreativeDocumentError,
    CreativeDocumentFactory,
)
from services.research_data_factory import ResearchDataFactory


_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl9sAAAAASUVORK5CYII="
)


def _projection() -> dict[str, object]:
    research = ResearchDataFactory()
    research.register_source(
        "source-tr-a",
        locator="fixture://source-tr-a",
        content=b"Source A confirms the governed claim.",
        trusted=True,
        metadata={"publisher": "publisher-a"},
    )
    research.register_source(
        "source-tr-b",
        locator="fixture://source-tr-b",
        content=b"Source B confirms the governed claim.",
        trusted=True,
        metadata={"publisher": "publisher-b"},
    )
    research.propose_claim(
        "claim-tr",
        statement="Governed publishing requires traceable evidence.",
        source_ids=("source-tr-a", "source-tr-b"),
    )
    for source_id, evidence_ref in (
        ("source-tr-a", "validator://tr-a"),
        ("source-tr-b", "validator://tr-b"),
    ):
        research.register_claim_evidence(
            "claim-tr",
            source_id=source_id,
            excerpt=b"confirms the governed claim",
            stance="SUPPORTS",
            validator_evidence_ref=evidence_ref,
            published_on="2026-08-01",
        )
    research.verify_factual_claim(
        "claim-tr",
        as_of="2026-09-09",
        max_source_age_days=90,
    )
    return research.knowledge_projection("claim-tr")


def _approved_book():
    metadata = BookMetadata(
        title="Türkçe Üretim Doğrulaması",
        subtitle="İçindekiler ve görsel testi",
        author="Şule Işık",
        publisher="ILAIOS",
        language="tr",
        edition="1",
        publication_date="2026-09-09",
        description="Türkçe karakterler: ğüşiöç İĞÜŞÖÇ",
        keywords=("kitap", "Türkçe", "kanıt"),
    )
    image = BookAsset(
        asset_id="chapter-image",
        body=_PNG_1X1,
        mime_type="image/png",
        provenance_ref="asset://chapter-image",
        rights_state="OWNED",
        alt_text="Bölüm görseli",
    )
    chapter = BookChapter(
        chapter_id="chapter-tr",
        title="Giriş ve Ölçüm",
        body="Türkçe metin: ğüşiöç İĞÜŞÖÇ. Governed publishing requires traceable evidence. [1]",
        factual=True,
        claim_ids=("claim-tr",),
        citations=(BookCitation("citation-tr", "claim-tr", "[1]"),),
        editorial_evidence_ref="editorial://chapter-tr",
        originality_evidence_ref="originality://chapter-tr",
        image_asset_ids=("chapter-image",),
    )
    factory = CreativeDocumentFactory()
    factory.compose_book(
        "book-tr",
        metadata=metadata,
        chapters=(chapter,),
        research_projections=(_projection(),),
        assets=(image,),
    )
    return factory.approve_book("book-tr")


def test_epub_has_required_metadata_images_and_citation_links() -> None:
    package = render_book_package(_approved_book())
    with zipfile.ZipFile(BytesIO(package.epub), "r") as archive:
        opf = archive.read("EPUB/package.opf").decode("utf-8")
        chapter = archive.read("EPUB/chapter-1.xhtml").decode("utf-8")
        bibliography = archive.read("EPUB/bibliography.xhtml").decode("utf-8")
        assert '<meta property="dcterms:modified">2026-09-09T00:00:00Z</meta>' in opf
        assert "<dc:publisher>ILAIOS</dc:publisher>" in opf
        assert "<dc:description>" in opf
        assert 'src="assets/chapter-image.png"' in chapter
        assert 'href="bibliography.xhtml#claim-claim-tr"' in chapter
        assert 'id="claim-claim-tr"' in bibliography
        assert archive.read("EPUB/assets/chapter-image.png") == _PNG_1X1


def test_pdf_preserves_turkish_embeds_image_and_has_internal_links() -> None:
    package = render_book_package(_approved_book())
    reader = PdfReader(BytesIO(package.pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Türkçe Üretim Doğrulaması" in text
    assert "Şule Işık" in text
    assert "ğüşiöç İĞÜŞÖÇ" in text
    assert "Bölüm görseli" in text
    assert any(page.images for page in reader.pages)
    annotations = [
        annotation
        for page in reader.pages
        for annotation in (page.get("/Annots") or [])
    ]
    assert len(annotations) >= 3


def test_post_approval_content_change_requires_new_approval() -> None:
    approved = _approved_book()
    changed_chapter = replace(
        approved.chapters[0],
        body=approved.chapters[0].body + " Changed after approval.",
    )
    tampered = replace(approved, chapters=(changed_chapter,))
    with pytest.raises(CreativeDocumentError, match="changed after approval"):
        render_book_package(tampered)
