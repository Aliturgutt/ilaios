"""Durable SQLite evidence store for governed Research/Data records."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from services.research_data_factory import DataAnalysis, ResearchClaim, ResearchSource


class SQLiteResearchDataStore:
    """Persist immutable-style research records without external data fetching."""

    def __init__(self, database: str | Path) -> None:
        self._connection = sqlite3.connect(str(database))
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY,
                    locator TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    trusted INTEGER NOT NULL CHECK (trusted IN (0, 1)),
                    metadata TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    source_ids TEXT NOT NULL,
                    verified INTEGER NOT NULL CHECK (verified IN (0, 1))
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    analysis_id TEXT PRIMARY KEY,
                    values_sha256 TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    minimum REAL NOT NULL,
                    maximum REAL NOT NULL,
                    mean REAL NOT NULL
                )
                """
            )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SQLiteResearchDataStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def save_source(self, source: ResearchSource) -> None:
        metadata = json.dumps(dict(source.metadata), sort_keys=True, separators=(",", ":"))
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO sources(source_id, locator, content_sha256, trusted, metadata)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    locator = excluded.locator,
                    content_sha256 = excluded.content_sha256,
                    trusted = excluded.trusted,
                    metadata = excluded.metadata
                """,
                (source.source_id, source.locator, source.content_sha256, int(source.trusted), metadata),
            )

    def load_source(self, source_id: str) -> ResearchSource | None:
        row = self._connection.execute(
            "SELECT * FROM sources WHERE source_id = ?", (source_id,)
        ).fetchone()
        if row is None:
            return None
        metadata_raw = json.loads(row["metadata"])
        if not isinstance(metadata_raw, dict):
            raise ValueError("persisted research source metadata is invalid")
        metadata = tuple(sorted((str(key), str(value)) for key, value in metadata_raw.items()))
        return ResearchSource(
            row["source_id"], row["locator"], row["content_sha256"], bool(row["trusted"]), metadata
        )

    def save_claim(self, claim: ResearchClaim) -> None:
        source_ids = json.dumps(claim.source_ids, separators=(",", ":"))
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO claims(claim_id, statement, source_ids, verified)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(claim_id) DO UPDATE SET
                    statement = excluded.statement,
                    source_ids = excluded.source_ids,
                    verified = excluded.verified
                """,
                (claim.claim_id, claim.statement, source_ids, int(claim.verified)),
            )

    def load_claim(self, claim_id: str) -> ResearchClaim | None:
        row = self._connection.execute(
            "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        if row is None:
            return None
        raw_source_ids = json.loads(row["source_ids"])
        if not isinstance(raw_source_ids, list) or not all(
            isinstance(item, str) for item in raw_source_ids
        ):
            raise ValueError("persisted research claim sources are invalid")
        return ResearchClaim(
            row["claim_id"], row["statement"], tuple(raw_source_ids), bool(row["verified"])
        )

    def save_analysis(self, analysis: DataAnalysis) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO analyses(analysis_id, values_sha256, count, minimum, maximum, mean)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(analysis_id) DO UPDATE SET
                    values_sha256 = excluded.values_sha256,
                    count = excluded.count,
                    minimum = excluded.minimum,
                    maximum = excluded.maximum,
                    mean = excluded.mean
                """,
                (
                    analysis.analysis_id,
                    analysis.values_sha256,
                    analysis.count,
                    analysis.minimum,
                    analysis.maximum,
                    analysis.mean,
                ),
            )

    def load_analysis(self, analysis_id: str) -> DataAnalysis | None:
        row = self._connection.execute(
            "SELECT * FROM analyses WHERE analysis_id = ?", (analysis_id,)
        ).fetchone()
        if row is None:
            return None
        return DataAnalysis(
            row["analysis_id"],
            row["values_sha256"],
            row["count"],
            row["minimum"],
            row["maximum"],
            row["mean"],
        )
