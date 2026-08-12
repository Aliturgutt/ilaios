"""Deterministic export adapters for approved Creative/Document artifacts."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass

from services.creative_document_factory import CreativeDocumentFactory, DocumentProjection


@dataclass(frozen=True, slots=True)
class RenderedDocument:
    media_type: str
    extension: str
    content: bytes


class DocumentFormatAdapters:
    """Render approved projections without publishing or external mutation."""

    def __init__(self, factory: CreativeDocumentFactory) -> None:
        self._factory = factory

    def markdown(self, artifact_id: str) -> RenderedDocument:
        projection = self._factory.export_projection(artifact_id)
        sources = "\n".join(
            f"- {source['source_id']}: {source['locator']} ({source['content_sha256']})"
            for source in projection["sources"]
        )
        text = f"# {projection['title']}\n\n{projection['body']}\n\n## Sources\n\n{sources}\n"
        return RenderedDocument("text/markdown; charset=utf-8", ".md", text.encode())

    def json(self, artifact_id: str) -> RenderedDocument:
        projection = self._factory.export_projection(artifact_id)
        payload = json.dumps(
            projection, ensure_ascii=False, sort_keys=True, indent=2
        ) + "\n"
        return RenderedDocument("application/json", ".json", payload.encode())

    def html(self, artifact_id: str) -> RenderedDocument:
        projection = self._factory.export_projection(artifact_id)
        body = "".join(
            f"<p>{html.escape(paragraph)}</p>"
            for paragraph in projection["body"].split("\n\n")
        )
        source_items = "".join(
            "<li>"
            + html.escape(source["source_id"])
            + ": "
            + html.escape(source["locator"])
            + " ("
            + html.escape(source["content_sha256"])
            + ")</li>"
            for source in projection["sources"]
        )
        page = (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(projection['title'])}</title></head><body>"
            f"<h1>{html.escape(projection['title'])}</h1>{body}"
            f"<h2>Sources</h2><ul>{source_items}</ul></body></html>"
        )
        return RenderedDocument("text/html; charset=utf-8", ".html", page.encode())

    def render(self, artifact_id: str, format_name: str) -> RenderedDocument:
        normalized = format_name.strip().lower()
        adapters = {
            "markdown": self.markdown,
            "md": self.markdown,
            "json": self.json,
            "html": self.html,
        }
        try:
            adapter = adapters[normalized]
        except KeyError as error:
            raise ValueError(f"unsupported document export format: {format_name}") from error
        return adapter(artifact_id)
