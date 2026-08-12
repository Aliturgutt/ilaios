import json

import pytest

from services.creative_document_factory import CreativeDocumentError, CreativeDocumentFactory
from services.document_format_adapters import DocumentFormatAdapters


def _approved_factory() -> CreativeDocumentFactory:
    factory = CreativeDocumentFactory()
    factory.register_source(
        "source-1",
        locator="https://example.invalid/evidence",
        content=b"trusted evidence",
        trusted=True,
    )
    factory.compose(
        "artifact-1",
        title="ILAIOS <Report>",
        sections=("First paragraph.", "Second <unsafe> paragraph."),
        source_ids=("source-1",),
    )
    factory.approve("artifact-1")
    return factory


def test_approved_artifact_renders_markdown_json_and_html() -> None:
    adapters = DocumentFormatAdapters(_approved_factory())

    markdown = adapters.markdown("artifact-1")
    assert markdown.extension == ".md"
    assert b"# ILAIOS <Report>" in markdown.content
    assert b"source-1" in markdown.content

    structured = adapters.json("artifact-1")
    parsed = json.loads(structured.content)
    assert parsed["artifact_id"] == "artifact-1"
    assert parsed["sources"][0]["source_id"] == "source-1"

    rendered_html = adapters.html("artifact-1")
    assert rendered_html.extension == ".html"
    assert b"ILAIOS &lt;Report&gt;" in rendered_html.content
    assert b"Second &lt;unsafe&gt; paragraph." in rendered_html.content


def test_unapproved_artifact_cannot_render() -> None:
    factory = CreativeDocumentFactory()
    factory.register_source(
        "source-1", locator="file:///evidence", content=b"evidence", trusted=True
    )
    factory.compose(
        "draft", title="Draft", sections=("body",), source_ids=("source-1",)
    )
    with pytest.raises(CreativeDocumentError, match="approved"):
        DocumentFormatAdapters(factory).markdown("draft")


def test_unknown_format_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        DocumentFormatAdapters(_approved_factory()).render("artifact-1", "pdf")
