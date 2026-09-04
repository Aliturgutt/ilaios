"""Artifact and provenance integrity tests for PLATFORM.P12."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.evidence import EvidenceError, EvidenceStore


def test_evidence_independently_proves_execution_after_restart(tmp_path: Path) -> None:
    first = EvidenceStore(tmp_path / "evidence")
    artifact = first.put_artifact(b"governed output")
    appended = first.append_provenance("execution-1", artifact, "render.completed")

    verified = EvidenceStore(tmp_path / "evidence").verify()
    assert verified == (appended,)
    assert verified[0].artifact_digest == artifact.digest


def test_artifact_tampering_is_detected(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    artifact = store.put_artifact(b"original")
    store.append_provenance("execution-1", artifact, "created")
    artifact.path.write_bytes(b"tampered")

    with pytest.raises(EvidenceError, match="integrity"):
        store.verify()


def test_provenance_chain_tampering_is_detected(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    artifact = store.put_artifact(b"original")
    store.append_provenance("execution-1", artifact, "created")
    with sqlite3.connect(tmp_path / "evidence" / "provenance.sqlite3") as connection:
        connection.execute("UPDATE provenance SET action = 'forged'")

    with pytest.raises(EvidenceError, match="hash chain"):
        store.verify()


def test_persisted_provenance_record_replay_is_rejected(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    artifact = store.put_artifact(b"original")
    appended = store.append_provenance("execution-1", artifact, "created")

    database = tmp_path / "evidence" / "provenance.sqlite3"
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT execution_id, artifact_digest, action, occurred_at, "
            "previous_hash, record_hash FROM provenance WHERE sequence = ?",
            (appended.sequence,),
        ).fetchone()
        assert row is not None

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO provenance "
                "(execution_id, artifact_digest, action, occurred_at, previous_hash, record_hash) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                row,
            )

    assert store.verify() == (appended,)
