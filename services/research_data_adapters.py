"""Governed local ingestion adapters for the bounded Research/Data Factory."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.research_data_factory import ResearchDataError, ResearchDataFactory, ResearchSource


@dataclass(frozen=True, slots=True)
class IngestedTable:
    source: ResearchSource
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


class GovernedLocalIngestion:
    """Ingest caller-supplied local bytes without network or external side effects."""

    def __init__(self, factory: ResearchDataFactory) -> None:
        self._factory = factory

    def ingest_text(
        self,
        source_id: str,
        *,
        locator: str,
        content: bytes,
        trusted: bool,
        encoding: str = "utf-8",
    ) -> tuple[ResearchSource, str]:
        text = self._decode(content, encoding)
        source = self._factory.register_source(
            source_id,
            locator=locator,
            content=content,
            trusted=trusted,
            metadata={"adapter": "text", "encoding": encoding},
        )
        return source, text

    def ingest_json(
        self,
        source_id: str,
        *,
        locator: str,
        content: bytes,
        trusted: bool,
        encoding: str = "utf-8",
    ) -> tuple[ResearchSource, Any]:
        text = self._decode(content, encoding)
        try:
            value: Any = json.loads(text)
        except json.JSONDecodeError as error:
            raise ResearchDataError("JSON source is invalid") from error
        source = self._factory.register_source(
            source_id,
            locator=locator,
            content=content,
            trusted=trusted,
            metadata={"adapter": "json", "encoding": encoding},
        )
        return source, value

    def ingest_csv(
        self,
        source_id: str,
        *,
        locator: str,
        content: bytes,
        trusted: bool,
        encoding: str = "utf-8",
    ) -> IngestedTable:
        text = self._decode(content, encoding)
        reader = csv.reader(io.StringIO(text))
        try:
            header = next(reader)
        except StopIteration as error:
            raise ResearchDataError("CSV source must contain a header") from error
        columns = tuple(item.strip() for item in header)
        if not columns or any(not item for item in columns) or len(columns) != len(set(columns)):
            raise ResearchDataError("CSV header must contain unique non-blank columns")
        rows: list[tuple[str, ...]] = []
        for raw_row in reader:
            if len(raw_row) != len(columns):
                raise ResearchDataError("CSV row width does not match header")
            rows.append(tuple(raw_row))
        source = self._factory.register_source(
            source_id,
            locator=locator,
            content=content,
            trusted=trusted,
            metadata={"adapter": "csv", "encoding": encoding},
        )
        return IngestedTable(source, columns, tuple(rows))

    def ingest_file(
        self, source_id: str, path: Path, *, trusted: bool
    ) -> ResearchSource:
        if not path.is_file():
            raise ResearchDataError("local ingestion path must be a file")
        content = path.read_bytes()
        suffix = path.suffix.lower()
        locator = path.resolve().as_uri()
        if suffix == ".json":
            return self.ingest_json(
                source_id, locator=locator, content=content, trusted=trusted
            )[0]
        if suffix == ".csv":
            return self.ingest_csv(
                source_id, locator=locator, content=content, trusted=trusted
            ).source
        if suffix in {".txt", ".md"}:
            return self.ingest_text(
                source_id, locator=locator, content=content, trusted=trusted
            )[0]
        raise ResearchDataError(f"unsupported local ingestion format: {suffix or '<none>'}")

    @staticmethod
    def _decode(content: bytes, encoding: str) -> str:
        if not content:
            raise ResearchDataError("source content must not be empty")
        try:
            return content.decode(encoding)
        except UnicodeDecodeError as error:
            raise ResearchDataError("source content cannot be decoded") from error
