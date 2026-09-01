"""Governed company-document ingestion adapters for the canonical Knowledge/RAG plane.

This module is deliberately not a second memory authority. It validates and extracts
supported document bytes, then delegates durable knowledge semantics to the existing
``KnowledgeRAG`` capability. Binary storage remains owned by the existing governed
files/object-storage boundary.
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from typing import Protocol

from services.knowledge_rag import KnowledgeRAG, KnowledgeSource


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
        text = xml.decode("utf-8", errors="strict")
        text = re.sub(r"</w:p\s*>", "\n", text)
        text = re.sub(r"<w:tab\s*/>", "\t", text)
        text = re.sub(r"<[^>]+>", "", text)
        return _normalize(text)


class CompanyKnowledgeIngestor:
    """Format adapter boundary that delegates memory semantics to ``KnowledgeRAG``."""

    _MAX_BYTES = 25 * 1024 * 1024

    def __init__(
        self,
        knowledge: KnowledgeRAG,
        *,
        extractors: tuple[DocumentTextExtractor, ...] | None = None,
    ) -> None:
        self._knowledge = knowledge
        selected = extractors or (PlainTextExtractor(), DocxTextExtractor())
        self._extractors = {
            mime_type: extractor
            for extractor in selected
            for mime_type in extractor.mime_types
        }

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


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
