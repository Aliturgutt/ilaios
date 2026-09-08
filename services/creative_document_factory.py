"""Bounded Creative/Document Factory with deterministic provenance and approval gates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any, TypedDict


class CreativeDocumentError(ValueError):
    """Creative/document work violates a bounded validation or approval gate."""


class SourceProjection(TypedDict):
    source_id: str
    locator: str
    content_sha256: str


class DocumentProjection(TypedDict):
    artifact_id: str
    title: str
    body: str
    body_sha256: str
    sources: tuple[SourceProjection, ...]


@dataclass(frozen=True, slots=True)
class DocumentSource:
    source_id: str
    locator: str
    content_sha256: str
    trusted: bool


@dataclass(frozen=True, slots=True)
class DocumentArtifact:
    artifact_id: str
    title: str
    body: str
    body_sha256: str
    source_ids: tuple[str, ...]
    approved: bool


@dataclass(frozen=True, slots=True)
class BookMetadata:
    title: str
    author: str
    publisher: str
    language: str
    edition: str
    publication_date: str
    description: str
    keywords: tuple[str, ...]
    subtitle: str | None = None
    isbn: str | None = None


@dataclass(frozen=True, slots=True)
class BookCitation:
    citation_id: str
    claim_id: str
    marker: str


@dataclass(frozen=True, slots=True)
class BookAsset:
    asset_id: str
    body: bytes
    mime_type: str
    provenance_ref: str
    rights_state: str
    alt_text: str
    license_identifier: str | None = None
    attribution: str | None = None

    @property
    def body_sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


@dataclass(frozen=True, slots=True)
class BookChapter:
    chapter_id: str
    title: str
    body: str
    factual: bool
    claim_ids: tuple[str, ...]
    citations: tuple[BookCitation, ...]
    editorial_evidence_ref: str
    originality_evidence_ref: str
    image_asset_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BookClaimProjection:
    claim_id: str
    statement: str
    source_ids: tuple[str, ...]
    verification_mode: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BookManifest:
    book_id: str
    metadata: BookMetadata
    chapters: tuple[BookChapter, ...]
    claims: tuple[BookClaimProjection, ...]
    assets: tuple[BookAsset, ...]
    build_version: str
    content_sha256: str
    approved: bool


@dataclass(frozen=True, slots=True)
class BookExportManifest:
    book_id: str
    title: str
    build_version: str
    book_content_sha256: str
    pdf_sha256: str
    epub_sha256: str
    cover_sha256: str
    provenance_sha256: str
    source_provenance_map: tuple[tuple[str, tuple[str, ...]], ...]


class CreativeDocumentFactory:
    """Build deterministic text artifacts without publishing or external mutation."""

    def __init__(self) -> None:
        self._sources: dict[str, DocumentSource] = {}
        self._artifacts: dict[str, DocumentArtifact] = {}
        self._books: dict[str, BookManifest] = {}

    def register_source(
        self,
        source_id: str,
        *,
        locator: str,
        content: bytes,
        trusted: bool,
    ) -> DocumentSource:
        _require_id(source_id, "source_id")
        _require_text(locator, "locator")
        if not content:
            raise CreativeDocumentError("source content must not be empty")
        if source_id in self._sources:
            raise CreativeDocumentError("source_id already exists")
        source = DocumentSource(
            source_id,
            locator,
            hashlib.sha256(content).hexdigest(),
            trusted,
        )
        self._sources[source_id] = source
        return source

    def compose(
        self,
        artifact_id: str,
        *,
        title: str,
        sections: tuple[str, ...],
        source_ids: tuple[str, ...],
    ) -> DocumentArtifact:
        _require_id(artifact_id, "artifact_id")
        _require_text(title, "title")
        if artifact_id in self._artifacts:
            raise CreativeDocumentError("artifact_id already exists")
        if not sections or any(not section.strip() for section in sections):
            raise CreativeDocumentError("sections must contain non-blank text")
        normalized_sources = _unique_ids(source_ids, "source_ids")
        missing = [item for item in normalized_sources if item not in self._sources]
        if missing:
            raise CreativeDocumentError(f"artifact references unknown sources: {missing}")
        if any(not self._sources[item].trusted for item in normalized_sources):
            raise CreativeDocumentError("artifact sources must be trusted")
        body = "\n\n".join(section.strip() for section in sections)
        artifact = DocumentArtifact(
            artifact_id,
            title.strip(),
            body,
            hashlib.sha256(body.encode("utf-8")).hexdigest(),
            normalized_sources,
            False,
        )
        self._artifacts[artifact_id] = artifact
        return artifact

    def approve(self, artifact_id: str) -> DocumentArtifact:
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            raise CreativeDocumentError("artifact does not exist")
        approved = DocumentArtifact(
            artifact.artifact_id,
            artifact.title,
            artifact.body,
            artifact.body_sha256,
            artifact.source_ids,
            True,
        )
        self._artifacts[artifact_id] = approved
        return approved

    def export_projection(self, artifact_id: str) -> DocumentProjection:
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            raise CreativeDocumentError("artifact does not exist")
        if not artifact.approved:
            raise CreativeDocumentError("only approved artifacts may export")
        return {
            "artifact_id": artifact.artifact_id,
            "title": artifact.title,
            "body": artifact.body,
            "body_sha256": artifact.body_sha256,
            "sources": tuple(
                {
                    "source_id": source_id,
                    "locator": self._sources[source_id].locator,
                    "content_sha256": self._sources[source_id].content_sha256,
                }
                for source_id in artifact.source_ids
            ),
        }

    def compose_book(
        self,
        book_id: str,
        *,
        metadata: BookMetadata,
        chapters: tuple[BookChapter, ...],
        research_projections: tuple[dict[str, Any], ...],
        assets: tuple[BookAsset, ...] = (),
        build_version: str = "1",
    ) -> BookManifest:
        """Create one validated book manifest from strict Research/Data projections."""

        _require_id(book_id, "book_id")
        if book_id in self._books:
            raise CreativeDocumentError("book_id already exists")
        _validate_book_metadata(metadata)
        _require_text(build_version, "build_version")
        if not chapters:
            raise CreativeDocumentError("book requires at least one chapter")
        chapter_ids = [chapter.chapter_id for chapter in chapters]
        if len(chapter_ids) != len(set(chapter_ids)):
            raise CreativeDocumentError("book chapter ids must be unique")
        asset_map = _validate_book_assets(assets)
        claims = _normalize_research_projections(research_projections)
        claim_map = {claim.claim_id: claim for claim in claims}
        for chapter in chapters:
            _validate_book_chapter(chapter, claim_map=claim_map, asset_map=asset_map)

        canonical = {
            "book_id": book_id,
            "metadata": _metadata_projection(metadata),
            "chapters": [
                {
                    "chapter_id": chapter.chapter_id,
                    "title": chapter.title,
                    "body": chapter.body,
                    "factual": chapter.factual,
                    "claim_ids": list(chapter.claim_ids),
                    "citations": [
                        {
                            "citation_id": citation.citation_id,
                            "claim_id": citation.claim_id,
                            "marker": citation.marker,
                        }
                        for citation in chapter.citations
                    ],
                    "editorial_evidence_ref": chapter.editorial_evidence_ref,
                    "originality_evidence_ref": chapter.originality_evidence_ref,
                    "image_asset_ids": list(chapter.image_asset_ids),
                }
                for chapter in chapters
            ],
            "claims": [
                {
                    "claim_id": claim.claim_id,
                    "statement": claim.statement,
                    "source_ids": list(claim.source_ids),
                    "verification_mode": claim.verification_mode,
                    "evidence_refs": list(claim.evidence_refs),
                }
                for claim in claims
            ],
            "assets": [
                {
                    "asset_id": asset.asset_id,
                    "sha256": asset.body_sha256,
                    "mime_type": asset.mime_type,
                    "provenance_ref": asset.provenance_ref,
                    "rights_state": asset.rights_state,
                    "alt_text": asset.alt_text,
                    "license_identifier": asset.license_identifier,
                    "attribution": asset.attribution,
                }
                for asset in assets
            ],
            "build_version": build_version,
        }
        content_sha256 = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest()
        manifest = BookManifest(
            book_id=book_id,
            metadata=metadata,
            chapters=chapters,
            claims=claims,
            assets=assets,
            build_version=build_version.strip(),
            content_sha256=content_sha256,
            approved=False,
        )
        self._books[book_id] = manifest
        return manifest

    def approve_book(self, book_id: str) -> BookManifest:
        manifest = self._books.get(book_id)
        if manifest is None:
            raise CreativeDocumentError("book does not exist")
        approved = replace(manifest, approved=True)
        self._books[book_id] = approved
        return approved

    def book_for_export(self, book_id: str) -> BookManifest:
        manifest = self._books.get(book_id)
        if manifest is None:
            raise CreativeDocumentError("book does not exist")
        if not manifest.approved:
            raise CreativeDocumentError("only approved books may export")
        return manifest


def _metadata_projection(metadata: BookMetadata) -> dict[str, Any]:
    return {
        "title": metadata.title,
        "subtitle": metadata.subtitle,
        "author": metadata.author,
        "publisher": metadata.publisher,
        "language": metadata.language,
        "edition": metadata.edition,
        "publication_date": metadata.publication_date,
        "description": metadata.description,
        "keywords": list(metadata.keywords),
        "isbn": metadata.isbn,
    }


def _validate_book_metadata(metadata: BookMetadata) -> None:
    for field, value in (
        ("title", metadata.title),
        ("author", metadata.author),
        ("publisher", metadata.publisher),
        ("language", metadata.language),
        ("edition", metadata.edition),
        ("publication_date", metadata.publication_date),
        ("description", metadata.description),
    ):
        _require_text(value, field)
        _reject_invalid_unicode(value, field)
    if metadata.subtitle is not None:
        _require_text(metadata.subtitle, "subtitle")
        _reject_invalid_unicode(metadata.subtitle, "subtitle")
    if metadata.isbn is not None:
        _require_text(metadata.isbn, "isbn")
        normalized = metadata.isbn.replace("-", "").replace(" ", "")
        if not normalized.isdigit() or len(normalized) not in {10, 13}:
            raise CreativeDocumentError("isbn must be a provided ISBN-10 or ISBN-13")
    if not metadata.keywords or any(not item.strip() for item in metadata.keywords):
        raise CreativeDocumentError("book keywords must contain non-blank values")


def _validate_book_assets(assets: tuple[BookAsset, ...]) -> dict[str, BookAsset]:
    allowed_mime = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}
    allowed_rights = {"OWNED", "LICENSED", "PUBLIC_DOMAIN", "ILAIOS_GENERATED"}
    asset_map: dict[str, BookAsset] = {}
    for asset in assets:
        _require_id(asset.asset_id, "asset_id")
        if asset.asset_id in asset_map:
            raise CreativeDocumentError("book asset ids must be unique")
        if not asset.body:
            raise CreativeDocumentError("book asset body must not be empty")
        if asset.mime_type not in allowed_mime:
            raise CreativeDocumentError("unsupported book asset mime type")
        _require_text(asset.provenance_ref, "asset provenance_ref")
        _require_text(asset.alt_text, "asset alt_text")
        if asset.rights_state not in allowed_rights:
            raise CreativeDocumentError("book asset publication rights are unknown")
        if asset.rights_state == "LICENSED":
            if not asset.license_identifier or not asset.attribution:
                raise CreativeDocumentError("licensed book assets require license and attribution")
        asset_map[asset.asset_id] = asset
    return asset_map


def _validate_book_chapter(
    chapter: BookChapter,
    *,
    claim_map: dict[str, BookClaimProjection],
    asset_map: dict[str, BookAsset],
) -> None:
    _require_id(chapter.chapter_id, "chapter_id")
    _require_text(chapter.title, "chapter title")
    _require_text(chapter.body, "chapter body")
    _reject_invalid_unicode(chapter.title, "chapter title")
    _reject_invalid_unicode(chapter.body, "chapter body")
    _require_text(chapter.editorial_evidence_ref, "editorial_evidence_ref")
    _require_text(chapter.originality_evidence_ref, "originality_evidence_ref")
    if "TODO" in chapter.body or "PLACEHOLDER" in chapter.body:
        raise CreativeDocumentError("chapter contains accidental placeholder text")
    if chapter.factual and not chapter.claim_ids:
        raise CreativeDocumentError("factual chapter requires verified claim provenance")
    if not chapter.factual and chapter.claim_ids:
        raise CreativeDocumentError("non-factual chapter must not claim factual provenance")
    if len(chapter.claim_ids) != len(set(chapter.claim_ids)):
        raise CreativeDocumentError("chapter claim ids must be unique")
    missing_claims = [claim_id for claim_id in chapter.claim_ids if claim_id not in claim_map]
    if missing_claims:
        raise CreativeDocumentError(f"chapter references unknown claims: {missing_claims}")
    if any(
        claim_map[claim_id].verification_mode != "CONTENT_BOUND_FACTUAL"
        for claim_id in chapter.claim_ids
    ):
        raise CreativeDocumentError("factual chapter requires CONTENT_BOUND_FACTUAL verification")
    citation_ids = [citation.citation_id for citation in chapter.citations]
    if len(citation_ids) != len(set(citation_ids)):
        raise CreativeDocumentError("citation ids must be unique within chapter")
    cited_claims = {citation.claim_id for citation in chapter.citations}
    if chapter.factual and cited_claims != set(chapter.claim_ids):
        raise CreativeDocumentError("every factual claim must have exactly mapped citation coverage")
    for citation in chapter.citations:
        _require_id(citation.citation_id, "citation_id")
        _require_text(citation.marker, "citation marker")
        if citation.claim_id not in chapter.claim_ids:
            raise CreativeDocumentError("citation references claim outside chapter")
    for asset_id in chapter.image_asset_ids:
        if asset_id not in asset_map:
            raise CreativeDocumentError("chapter references missing book asset")


def _normalize_research_projections(
    projections: tuple[dict[str, Any], ...],
) -> tuple[BookClaimProjection, ...]:
    claims: list[BookClaimProjection] = []
    seen: set[str] = set()
    for projection in projections:
        fact = projection.get("fact")
        evidence = projection.get("evidence")
        if not isinstance(fact, dict) or not isinstance(evidence, list):
            raise CreativeDocumentError("research projection is malformed")
        node_id = fact.get("node_id")
        statement = fact.get("statement")
        verified = fact.get("verified")
        verification_mode = fact.get("verification_mode")
        if not isinstance(node_id, str) or not node_id.startswith("fact:"):
            raise CreativeDocumentError("research projection fact id is invalid")
        claim_id = node_id.removeprefix("fact:")
        _require_id(claim_id, "claim_id")
        if claim_id in seen:
            raise CreativeDocumentError("research projection claim ids must be unique")
        seen.add(claim_id)
        if verified is not True or verification_mode != "CONTENT_BOUND_FACTUAL":
            raise CreativeDocumentError("book factual claims require strict Research/Data verification")
        if not isinstance(statement, str):
            raise CreativeDocumentError("research projection statement is invalid")
        _require_text(statement, "claim statement")
        source_ids: list[str] = []
        evidence_refs: list[str] = []
        for item in evidence:
            if not isinstance(item, dict):
                raise CreativeDocumentError("research evidence projection is malformed")
            source_id = item.get("source_id")
            validator_ref = item.get("validator_evidence_ref")
            stance = item.get("stance")
            if not isinstance(source_id, str) or not isinstance(validator_ref, str):
                raise CreativeDocumentError("strict research evidence is incomplete")
            if stance != "SUPPORTS":
                raise CreativeDocumentError("book claim contains non-supporting research evidence")
            _require_id(source_id, "source_id")
            _require_text(validator_ref, "validator_evidence_ref")
            source_ids.append(source_id)
            evidence_refs.append(validator_ref)
        if len(source_ids) < 2 or len(set(source_ids)) != len(source_ids):
            raise CreativeDocumentError("book factual claim requires independent source evidence")
        claims.append(
            BookClaimProjection(
                claim_id=claim_id,
                statement=statement.strip(),
                source_ids=tuple(source_ids),
                verification_mode=verification_mode,
                evidence_refs=tuple(evidence_refs),
            )
        )
    return tuple(claims)


def _reject_invalid_unicode(value: str, field: str) -> None:
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise CreativeDocumentError(f"{field} contains malformed Unicode") from exc


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise CreativeDocumentError(f"{field} must be non-blank and trimmed")


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise CreativeDocumentError(f"{field} must be non-blank")


def _unique_ids(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not values:
        raise CreativeDocumentError(f"{field} must not be empty")
    if any(not item or item != item.strip() for item in values):
        raise CreativeDocumentError(f"{field} must contain trimmed IDs")
    if len(values) != len(set(values)):
        raise CreativeDocumentError(f"{field} must not contain duplicates")
    return values
