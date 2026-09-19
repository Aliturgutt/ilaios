from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.reference_brief_cache import (
    ReferenceBriefCache,
    ReferenceBriefCacheError,
)


def _digest(character: str) -> str:
    return character * 64


def test_reference_brief_cache_round_trips_exact_conditioning(tmp_path: Path) -> None:
    cache = ReferenceBriefCache(tmp_path / "reference-briefs.sqlite3")
    stored = cache.put(
        request_id="exec-123",
        text="Preserve the same red product shell and white logo placement.",
        reference_sha256s=(_digest("a"), _digest("b")),
        analyzer_id="openrouter-reference-analysis:openrouter/free",
    )

    loaded = cache.get("exec-123")

    assert loaded == stored
    assert loaded is not None
    assert loaded.reference_sha256s == (_digest("a"), _digest("b"))


def test_reference_brief_cache_is_idempotent_for_identical_retry(tmp_path: Path) -> None:
    cache = ReferenceBriefCache(tmp_path / "reference-briefs.sqlite3")
    first = cache.put(
        request_id="exec-123",
        text="Keep the same subject silhouette.",
        reference_sha256s=(_digest("a"),),
        analyzer_id="analyzer-v1",
    )
    second = cache.put(
        request_id="exec-123",
        text="Keep the same subject silhouette.",
        reference_sha256s=(_digest("a"),),
        analyzer_id="analyzer-v1",
    )

    assert second == first


def test_reference_brief_cache_rejects_retry_drift(tmp_path: Path) -> None:
    cache = ReferenceBriefCache(tmp_path / "reference-briefs.sqlite3")
    cache.put(
        request_id="exec-123",
        text="Keep the same subject silhouette.",
        reference_sha256s=(_digest("a"),),
        analyzer_id="analyzer-v1",
    )

    with pytest.raises(ReferenceBriefCacheError, match="already frozen"):
        cache.put(
            request_id="exec-123",
            text="Change the subject silhouette.",
            reference_sha256s=(_digest("a"),),
            analyzer_id="analyzer-v2",
        )


def test_reference_brief_cache_fails_closed_on_tampered_digest_metadata(
    tmp_path: Path,
) -> None:
    database = tmp_path / "reference-briefs.sqlite3"
    cache = ReferenceBriefCache(database)
    cache.put(
        request_id="exec-123",
        text="Keep the same subject silhouette.",
        reference_sha256s=(_digest("a"),),
        analyzer_id="analyzer-v1",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE reference_visual_briefs SET reference_sha256s_json = ? "
            "WHERE request_id = ?",
            ('["not-a-digest"]', "exec-123"),
        )

    with pytest.raises(ReferenceBriefCacheError, match="digest is invalid"):
        cache.get("exec-123")
