from pathlib import Path

import pytest

from services.research_data_adapters import GovernedLocalIngestion
from services.research_data_factory import ResearchDataError, ResearchDataFactory


def test_json_csv_and_text_ingestion_preserve_provenance() -> None:
    factory = ResearchDataFactory()
    adapter = GovernedLocalIngestion(factory)

    json_source, value = adapter.ingest_json(
        "json-1",
        locator="file:///evidence.json",
        content=b'{"verified": true}',
        trusted=True,
    )
    table = adapter.ingest_csv(
        "csv-1",
        locator="file:///metrics.csv",
        content=b"metric,value\nlatency,10\n",
        trusted=True,
    )
    text_source, text = adapter.ingest_text(
        "text-1",
        locator="file:///notes.md",
        content=b"# Evidence",
        trusted=False,
    )

    assert value == {"verified": True}
    assert dict(json_source.metadata)["adapter"] == "json"
    assert table.columns == ("metric", "value")
    assert table.rows == (("latency", "10"),)
    assert text == "# Evidence"
    assert text_source.trusted is False


def test_local_file_adapter_is_bounded_to_supported_formats(tmp_path: Path) -> None:
    adapter = GovernedLocalIngestion(ResearchDataFactory())
    source_path = tmp_path / "source.json"
    source_path.write_text('{"ok": 1}', encoding="utf-8")
    source = adapter.ingest_file("local", source_path, trusted=True)
    assert source.locator == source_path.resolve().as_uri()

    unsupported = tmp_path / "source.bin"
    unsupported.write_bytes(b"binary")
    with pytest.raises(ResearchDataError, match="unsupported"):
        adapter.ingest_file("binary", unsupported, trusted=True)


def test_invalid_csv_fails_closed() -> None:
    adapter = GovernedLocalIngestion(ResearchDataFactory())
    with pytest.raises(ResearchDataError, match="row width"):
        adapter.ingest_csv(
            "bad",
            locator="file:///bad.csv",
            content=b"a,b\n1\n",
            trusted=True,
        )
