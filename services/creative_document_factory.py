"""Bounded Creative/Document Factory with deterministic provenance and approval gates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TypedDict


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


class CreativeDocumentFactory:
    """Build deterministic text artifacts without publishing or external mutation."""

    def __init__(self) -> None:
        self._sources: dict[str, DocumentSource] = {}
        self._artifacts: dict[str, DocumentArtifact] = {}

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
