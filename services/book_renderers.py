"""Deterministic PDF/EPUB3 render adapters for approved Creative/Document books."""

from __future__ import annotations

import hashlib
import html
import io
import json
import textwrap
import zipfile
from dataclasses import dataclass
from typing import Iterable

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from services.creative_document_factory import (
    BookExportManifest,
    BookManifest,
    CreativeDocumentError,
)


@dataclass(frozen=True, slots=True)
class RenderedBookPackage:
    pdf: bytes
    epub: bytes
    cover_svg: bytes
    provenance_json: bytes
    export_manifest: BookExportManifest


def render_book_package(manifest: BookManifest) -> RenderedBookPackage:
    """Render one approved book without gaining approval or publication authority."""

    if not manifest.approved:
        raise CreativeDocumentError("only approved books may render final exports")
    cover = _render_cover_svg(manifest)
    pdf = _render_pdf(manifest)
    epub = _render_epub(manifest, cover)
    provenance = _render_provenance(manifest)
    source_map = tuple(
        sorted((claim.claim_id, claim.source_ids) for claim in manifest.claims)
    )
    export = BookExportManifest(
        book_id=manifest.book_id,
        title=manifest.metadata.title,
        build_version=manifest.build_version,
        book_content_sha256=manifest.content_sha256,
        pdf_sha256=hashlib.sha256(pdf).hexdigest(),
        epub_sha256=hashlib.sha256(epub).hexdigest(),
        cover_sha256=hashlib.sha256(cover).hexdigest(),
        provenance_sha256=hashlib.sha256(provenance).hexdigest(),
        source_provenance_map=source_map,
    )
    return RenderedBookPackage(pdf, epub, cover, provenance, export)


def validate_epub_structure(epub: bytes) -> tuple[str, ...]:
    """Return EPUB3 entries after structural validation; fail closed on defects."""

    required = {
        "mimetype",
        "META-INF/container.xml",
        "EPUB/package.opf",
        "EPUB/nav.xhtml",
        "EPUB/cover.svg",
    }
    try:
        with zipfile.ZipFile(io.BytesIO(epub), "r") as archive:
            names = tuple(archive.namelist())
            if archive.read("mimetype") != b"application/epub+zip":
                raise CreativeDocumentError("EPUB mimetype is invalid")
            missing = required - set(names)
            if missing:
                raise CreativeDocumentError(f"EPUB is missing required entries: {sorted(missing)}")
            if len(archive.read("EPUB/package.opf")) == 0 or len(archive.read("EPUB/nav.xhtml")) == 0:
                raise CreativeDocumentError("EPUB package/navigation is empty")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise CreativeDocumentError("EPUB is not a valid ZIP/EPUB container") from exc
    return names


def _render_cover_svg(manifest: BookManifest) -> bytes:
    title = html.escape(manifest.metadata.title)
    subtitle = html.escape(manifest.metadata.subtitle or "")
    author = html.escape(manifest.metadata.author)
    subtitle_block = (
        f'<text x="600" y="850" text-anchor="middle" font-size="42">{subtitle}</text>'
        if subtitle
        else ""
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1800" viewBox="0 0 1200 1800">
<rect width="1200" height="1800" fill="#ffffff"/>
<rect x="80" y="80" width="1040" height="1640" fill="none" stroke="#111111" stroke-width="8"/>
<text x="600" y="650" text-anchor="middle" font-family="sans-serif" font-weight="700" font-size="72">{title}</text>
{subtitle_block}
<text x="600" y="1450" text-anchor="middle" font-family="sans-serif" font-size="42">{author}</text>
</svg>"""
    return svg.encode("utf-8")


def _render_pdf(manifest: BookManifest) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, invariant=1, pageCompression=1)
    width, height = A4
    pdf.setTitle(manifest.metadata.title)
    pdf.setAuthor(manifest.metadata.author)
    pdf.setSubject(manifest.metadata.description)

    _pdf_cover(pdf, manifest, width, height)
    _pdf_front_matter(pdf, manifest, width, height)
    _pdf_toc(pdf, manifest, width, height)
    for index, chapter in enumerate(manifest.chapters, start=1):
        pdf.bookmarkPage(f"chapter-{chapter.chapter_id}")
        pdf.addOutlineEntry(chapter.title, f"chapter-{chapter.chapter_id}", level=0)
        _pdf_chapter(pdf, manifest, index, chapter.title, chapter.body, chapter.citations, width, height)
    _pdf_bibliography(pdf, manifest, width, height)
    pdf.save()
    result = buffer.getvalue()
    if not result.startswith(b"%PDF-"):
        raise CreativeDocumentError("PDF renderer did not produce a PDF artifact")
    return result


def _pdf_cover(pdf: canvas.Canvas, manifest: BookManifest, width: float, height: float) -> None:
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, height * 0.68, _pdf_safe(manifest.metadata.title))
    if manifest.metadata.subtitle:
        pdf.setFont("Helvetica", 16)
        pdf.drawCentredString(width / 2, height * 0.60, _pdf_safe(manifest.metadata.subtitle))
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, height * 0.18, _pdf_safe(manifest.metadata.author))
    pdf.showPage()


def _pdf_front_matter(pdf: canvas.Canvas, manifest: BookManifest, width: float, height: float) -> None:
    y = height - 72
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(72, y, "Publication information")
    y -= 36
    pdf.setFont("Helvetica", 10)
    lines = (
        f"Title: {manifest.metadata.title}",
        f"Author: {manifest.metadata.author}",
        f"Publisher: {manifest.metadata.publisher}",
        f"Language: {manifest.metadata.language}",
        f"Edition: {manifest.metadata.edition}",
        f"Publication date: {manifest.metadata.publication_date}",
        *( (f"ISBN: {manifest.metadata.isbn}",) if manifest.metadata.isbn else () ),
        "Copyright and publication rights remain with the declared rights holders.",
    )
    for line in lines:
        pdf.drawString(72, y, _pdf_safe(line))
        y -= 16
    pdf.showPage()


def _pdf_toc(pdf: canvas.Canvas, manifest: BookManifest, width: float, height: float) -> None:
    y = height - 72
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(72, y, "Table of Contents")
    y -= 32
    pdf.setFont("Helvetica", 11)
    for index, chapter in enumerate(manifest.chapters, start=1):
        pdf.drawString(84, y, _pdf_safe(f"{index}. {chapter.title}"))
        y -= 18
    pdf.drawString(84, y, "Bibliography")
    pdf.showPage()


def _pdf_chapter(
    pdf: canvas.Canvas,
    manifest: BookManifest,
    index: int,
    title: str,
    body: str,
    citations: Iterable[object],
    width: float,
    height: float,
) -> None:
    del manifest, citations, width
    y = height - 72
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(72, y, _pdf_safe(f"Chapter {index}: {title}"))
    y -= 34
    pdf.setFont("Helvetica", 10)
    for paragraph in body.split("\n"):
        if not paragraph.strip():
            y -= 10
            continue
        for line in textwrap.wrap(paragraph, width=92, replace_whitespace=False):
            if y < 72:
                pdf.showPage()
                y = height - 72
                pdf.setFont("Helvetica", 10)
            pdf.drawString(72, y, _pdf_safe(line))
            y -= 14
    pdf.showPage()


def _pdf_bibliography(pdf: canvas.Canvas, manifest: BookManifest, width: float, height: float) -> None:
    del width
    y = height - 72
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(72, y, "Bibliography / Provenance")
    y -= 30
    pdf.setFont("Helvetica", 9)
    for claim in manifest.claims:
        line = f"{claim.claim_id}: {claim.statement} | sources: {', '.join(claim.source_ids)}"
        for wrapped in textwrap.wrap(line, width=100):
            if y < 72:
                pdf.showPage()
                y = height - 72
                pdf.setFont("Helvetica", 9)
            pdf.drawString(72, y, _pdf_safe(wrapped))
            y -= 13
    pdf.showPage()


def _pdf_safe(value: str) -> str:
    # ReportLab's standard Helvetica uses WinAnsi. Preserve deterministic rendering
    # while refusing malformed Unicode earlier in the Document Factory.
    return value.encode("cp1252", "replace").decode("cp1252")


def _render_epub(manifest: BookManifest, cover: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        _zip_write(archive, "mimetype", b"application/epub+zip", compress=False)
        _zip_write(archive, "META-INF/container.xml", _container_xml())
        _zip_write(archive, "EPUB/cover.svg", cover)
        chapter_entries: list[tuple[str, bytes]] = []
        for index, chapter in enumerate(manifest.chapters, start=1):
            chapter_entries.append(
                (f"EPUB/chapter-{index}.xhtml", _chapter_xhtml(manifest, index))
            )
        for name, data in chapter_entries:
            _zip_write(archive, name, data)
        _zip_write(archive, "EPUB/nav.xhtml", _nav_xhtml(manifest))
        _zip_write(archive, "EPUB/bibliography.xhtml", _bibliography_xhtml(manifest))
        _zip_write(archive, "EPUB/package.opf", _package_opf(manifest))
        for asset in manifest.assets:
            extension = {
                "image/png": "png",
                "image/jpeg": "jpg",
                "image/webp": "webp",
                "image/svg+xml": "svg",
            }[asset.mime_type]
            _zip_write(archive, f"EPUB/assets/{asset.asset_id}.{extension}", asset.body)
    result = output.getvalue()
    validate_epub_structure(result)
    return result


def _zip_write(archive: zipfile.ZipFile, name: str, data: bytes, *, compress: bool = True) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    archive.writestr(info, data)


def _container_xml() -> bytes:
    return b'''<?xml version="1.0" encoding="UTF-8"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''


def _chapter_xhtml(manifest: BookManifest, index: int) -> bytes:
    chapter = manifest.chapters[index - 1]
    paragraphs = "".join(f"<p>{html.escape(part)}</p>" for part in chapter.body.split("\n") if part.strip())
    citations = "".join(
        f'<li id="{html.escape(citation.citation_id)}">{html.escape(citation.marker)} — {html.escape(citation.claim_id)}</li>'
        for citation in chapter.citations
    )
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{html.escape(manifest.metadata.language)}"><head><title>{html.escape(chapter.title)}</title></head><body><h1>Chapter {index}: {html.escape(chapter.title)}</h1>{paragraphs}<section><h2>Citations</h2><ol>{citations}</ol></section></body></html>'''
    return content.encode("utf-8")


def _nav_xhtml(manifest: BookManifest) -> bytes:
    items = "".join(
        f'<li><a href="chapter-{index}.xhtml">{index}. {html.escape(chapter.title)}</a></li>'
        for index, chapter in enumerate(manifest.chapters, start=1)
    )
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head><body><nav epub:type="toc"><h1>Contents</h1><ol>{items}<li><a href="bibliography.xhtml">Bibliography</a></li></ol></nav></body></html>'''
    return content.encode("utf-8")


def _bibliography_xhtml(manifest: BookManifest) -> bytes:
    items = "".join(
        f"<li>{html.escape(claim.claim_id)} — {html.escape(claim.statement)} — sources: {html.escape(', '.join(claim.source_ids))}</li>"
        for claim in manifest.claims
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Bibliography</title></head><body><h1>Bibliography / Provenance</h1><ol>{items}</ol></body></html>'''.encode("utf-8")


def _package_opf(manifest: BookManifest) -> bytes:
    chapter_manifest = "".join(
        f'<item id="chapter-{index}" href="chapter-{index}.xhtml" media-type="application/xhtml+xml"/>'
        for index in range(1, len(manifest.chapters) + 1)
    )
    chapter_spine = "".join(
        f'<itemref idref="chapter-{index}"/>' for index in range(1, len(manifest.chapters) + 1)
    )
    asset_items = []
    for asset in manifest.assets:
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg"}[asset.mime_type]
        asset_items.append(
            f'<item id="asset-{html.escape(asset.asset_id)}" href="assets/{html.escape(asset.asset_id)}.{extension}" media-type="{asset.mime_type}"/>'
        )
    title = html.escape(manifest.metadata.title)
    author = html.escape(manifest.metadata.author)
    language = html.escape(manifest.metadata.language)
    identifier = html.escape(manifest.metadata.isbn or manifest.book_id)
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">{identifier}</dc:identifier><dc:title>{title}</dc:title><dc:creator>{author}</dc:creator><dc:language>{language}</dc:language></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="cover" href="cover.svg" media-type="image/svg+xml" properties="cover-image"/><item id="bibliography" href="bibliography.xhtml" media-type="application/xhtml+xml"/>{chapter_manifest}{''.join(asset_items)}</manifest><spine>{chapter_spine}<itemref idref="bibliography"/></spine></package>'''
    return content.encode("utf-8")


def _render_provenance(manifest: BookManifest) -> bytes:
    payload = {
        "book_id": manifest.book_id,
        "book_content_sha256": manifest.content_sha256,
        "claims": [
            {
                "claim_id": claim.claim_id,
                "verification_mode": claim.verification_mode,
                "source_ids": list(claim.source_ids),
                "evidence_refs": list(claim.evidence_refs),
            }
            for claim in manifest.claims
        ],
        "assets": [
            {
                "asset_id": asset.asset_id,
                "sha256": asset.body_sha256,
                "provenance_ref": asset.provenance_ref,
                "rights_state": asset.rights_state,
                "license_identifier": asset.license_identifier,
                "attribution": asset.attribution,
            }
            for asset in manifest.assets
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
