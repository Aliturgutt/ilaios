"""Governed company-document ingestion adapters for the canonical Knowledge/RAG plane.

This module is deliberately not a second memory authority. It validates and extracts
supported document bytes, then delegates memory semantics to the existing Knowledge/RAG
service or its canonical durable runtime. Binary storage remains owned by the existing
governed files/object-storage boundary.
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from typing import Protocol

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from services.knowledge_rag import KnowledgeRAG, KnowledgeSource
from services.knowledge_runtime import DurableKnowledgeRuntime


class CompanyKnowledgeIngestionError(ValueError):
    """A company document failed the bounded ingestion contract."""


@dataclass(frozen=True, slots=True)
class ExtractedCompanyDocument:
    filename: str
    mime_type: str
    text: str
    content_sha256: str


class DocumentTextExtractor(Protocol):
    mime_types: frozenset[str]

    def extract(self, *, filename: str, content: bytes) -> str: ...


class PlainTextExtractor:
    mime_types = frozenset({"text/plain", "text/csv"})

    def extract(self, *, filename: str, content: bytes) -> str:
        del filename
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CompanyKnowledgeIngestionError("text source must be UTF-8") from exc


class PdfTextExtractor:
    mime_types = frozenset({"application/pdf"})
    _MAX_PAGES = 1000
    _MAX_EXTRACTED_CHARS = 5_000_000

    def extract(self, *, filename: str, content: bytes) -> str:
        del filename
        if not content.startswith(b"%PDF-"):
            raise CompanyKnowledgeIngestionError("invalid PDF signature")
        try:
            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise CompanyKnowledgeIngestionError("encrypted PDF is not ingestible")
            if len(reader.pages) > self._MAX_PAGES:
                raise CompanyKnowledgeIngestionError("PDF page count exceeds bounded limit")
            pages: list[str] = []
            extracted_chars = 0
            for page_number, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    continue
                rendered = f"[page {page_number}]\n{page_text}"
                extracted_chars += len(rendered)
                if extracted_chars > self._MAX_EXTRACTED_CHARS:
                    raise CompanyKnowledgeIngestionError(
                        "PDF extracted text exceeds bounded limit"
                    )
                pages.append(rendered)
        except CompanyKnowledgeIngestionError:
            raise
        except (PdfReadError, FileNotDecryptedError, OSError, ValueError) as exc:
            raise CompanyKnowledgeIngestionError("invalid PDF document") from exc
        return _normalize("\n".join(pages))


class DocxTextExtractor:
    mime_types = frozenset(
        {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    )
    _MAX_ENTRIES = 4096
    _MAX_UNCOMPRESSED_BYTES = 64 * 1024 * 1024

    def extract(self, *, filename: str, content: bytes) -> str:
        del filename
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except (zipfile.BadZipFile, OSError) as exc:
            raise CompanyKnowledgeIngestionError("invalid DOCX container") from exc
        with archive:
            infos = archive.infolist()
            if len(infos) > self._MAX_ENTRIES:
                raise CompanyKnowledgeIngestionError("DOCX contains too many archive entries")
            if sum(item.file_size for item in infos) > self._MAX_UNCOMPRESSED_BYTES:
                raise CompanyKnowledgeIngestionError("DOCX expanded size exceeds bounded limit")
            names = {item.filename for item in infos}
            if "word/document.xml" not in names:
                raise CompanyKnowledgeIngestionError("DOCX is missing word/document.xml")
            xml = archive.read("word/document.xml")
        try:
            text = xml.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise CompanyKnowledgeIngestionError("DOCX document.xml must be UTF-8") from exc
        text = re.sub(r"</w:p\s*>", "\n", text)
        text = re.sub(r"<w:tab\s*/>", "\t", text)
        text = re.sub(r"<[^>]+>", "", text)
        return _normalize(text)


class CompanyDocumentExtractor:
    """Bounded format adapter set shared by transient and durable Knowledge ingestion."""

    _MAX_BYTES = 25 * 1024 * 1024

    def __init__(
        self, *, extractors: tuple[DocumentTextExtractor, ...] | None = None
    ) -> None:
        selected = extractors or (
            PlainTextExtractor(),
            PdfTextExtractor(),
            DocxTextExtractor(),
        )
        self._extractors = {
            mime_type: extractor
            for extractor in selected
            for mime_type in extractor.mime_types
        }

    def extract(
        self, *, filename: str, mime_type: str, content: bytes
    ) -> ExtractedCompanyDocument:
        if not filename or "/" in filename or "\\" in filename or "\x00" in filename:
            raise CompanyKnowledgeIngestionError("unsafe filename")
        if not content:
            raise CompanyKnowledgeIngestionError("empty document")
        if len(content) > self._MAX_BYTES:
            raise CompanyKnowledgeIngestionError("document exceeds bounded size")
        extractor = self._extractors.get(mime_type)
        if extractor is None:
            raise CompanyKnowledgeIngestionError("unsupported company-document MIME type")
        text = _normalize(extractor.extract(filename=filename, content=content))
        if not text:
            raise CompanyKnowledgeIngestionError("document produced no ingestible text")
        return ExtractedCompanyDocument(
            filename=filename,
            mime_type=mime_type,
            text=text,
            content_sha256=hashlib.sha256(content).hexdigest(),
        )


class CompanyKnowledgeIngestor:
    """Verification adapter that delegates source semantics to canonical ``KnowledgeRAG``."""

    def __init__(
        self,
        knowledge: KnowledgeRAG,
        *,
        extractors: tuple[DocumentTextExtractor, ...] | None = None,
    ) -> None:
        self._knowledge = knowledge
        self._documents = CompanyDocumentExtractor(extractors=extractors)

    def ingest(
        self,
        source_id: str,
        *,
        tenant_id: str,
        project_id: str,
        filename: str,
        mime_type: str,
        content: bytes,
        locator: str,
        trusted: bool = False,
        classifications: frozenset[str] = frozenset(),
        purposes: frozenset[str] = frozenset(),
        residency: str = "global",
    ) -> KnowledgeSource:
        extracted = self.extract(filename=filename, mime_type=mime_type, content=content)
        return self._knowledge.ingest_source(
            source_id,
            tenant_id=tenant_id,
            project_id=project_id,
            locator=locator,
            content=extracted.text,
            trusted=trusted,
            classifications=classifications,
            purposes=purposes,
            residency=residency,
        )

    def extract(
        self, *, filename: str, mime_type: str, content: bytes
    ) -> ExtractedCompanyDocument:
        return self._documents.extract(
            filename=filename, mime_type=mime_type, content=content
        )


class DurableCompanyKnowledgeIngestor:
    """Company-document adapter for the existing durable governed Knowledge runtime."""

    def __init__(
        self,
        runtime: DurableKnowledgeRuntime,
        *,
        extractors: tuple[DocumentTextExtractor, ...] | None = None,
    ) -> None:
        self._runtime = runtime
        self._documents = CompanyDocumentExtractor(extractors=extractors)

    def ingest(
        self,
        source_id: str,
        *,
        filename: str,
        mime_type: str,
        content: bytes,
        locator: str,
        trusted: bool,
        classifications: frozenset[str],
        purposes: frozenset[str],
        residency: str,
    ) -> dict[str, object]:
        extracted = self._documents.extract(
            filename=filename, mime_type=mime_type, content=content
        )
        return self._runtime.ingest_source(
            source_id=source_id,
            locator=locator,
            content=extracted.text,
            trusted=trusted,
            classifications=classifications,
            purposes=purposes,
            residency=residency,
        )

    def extract(
        self, *, filename: str, mime_type: str, content: bytes
    ) -> ExtractedCompanyDocument:
        return self._documents.extract(
            filename=filename, mime_type=mime_type, content=content
        )


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
