from __future__ import annotations

from pathlib import Path

from services.reference_relay_access import ReferenceRelayAccessLedger


def test_relay_access_ledger_records_fetches_without_signed_url_or_identity(tmp_path: Path) -> None:
    ledger = ReferenceRelayAccessLedger(tmp_path / "access.sqlite3")
    digest = "a" * 64

    assert ledger.evidence(digest) is None
    ledger.record_fetch(digest, now_epoch_s=100)
    ledger.record_fetch(digest, now_epoch_s=125)

    evidence = ledger.evidence(digest)
    assert evidence is not None
    assert evidence.sha256 == digest
    assert evidence.fetch_count == 2
    assert evidence.first_fetched_at_epoch_s == 100
    assert evidence.last_fetched_at_epoch_s == 125
    assert "tenant" not in evidence.__dataclass_fields__
    assert "principal" not in evidence.__dataclass_fields__
    assert "url" not in evidence.__dataclass_fields__
