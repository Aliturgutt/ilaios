"""Tests for the ILAIOS evidence chain."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from src.core.evidence_chain import (
    EvidenceChain,
    EvidenceChainValidationError,
    EvidenceRecord,
)

TIMESTAMP = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


def _data_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _record(
    *,
    timestamp: datetime = TIMESTAMP,
    source: str = "audit_engine",
    data: str = "payload",
    prev_hash: str | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        timestamp=timestamp,
        source=source,
        data_hash=_data_hash(data),
        prev_hash=prev_hash,
    )


def test_evidence_record_computes_expected_chain_hash() -> None:
    record = _record()

    expected = sha256(
        (
            TIMESTAMP.isoformat()
            + "audit_engine"
            + _data_hash("payload")
            + ""
        ).encode("utf-8")
    ).hexdigest()

    assert record.chain_hash == expected
    assert record.prev_hash is None


def test_evidence_record_is_immutable() -> None:
    record = _record()

    with pytest.raises(FrozenInstanceError):
        record.source = "modified"  # type: ignore[misc]


def test_evidence_record_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(
        EvidenceChainValidationError,
        match="timezone-aware",
    ):
        _record(timestamp=datetime(2026, 7, 27, 12, 0, 0))  # noqa: DTZ001


def test_evidence_record_requires_utc_timestamp() -> None:
    non_utc = timezone(timedelta(hours=3))

    with pytest.raises(
        EvidenceChainValidationError,
        match="must use UTC",
    ):
        _record(timestamp=datetime(2026, 7, 27, 12, 0, 0, tzinfo=non_utc))


def test_evidence_record_rejects_empty_source() -> None:
    with pytest.raises(
        EvidenceChainValidationError,
        match="source must not be empty",
    ):
        _record(source="   ")


@pytest.mark.parametrize(  # type: ignore[misc, unused-ignore]
    "invalid_hash",
    [
        "",
        "abc",
        "A" * 64,
        "g" * 64,
        "0" * 63,
        "0" * 65,
    ],
)
def test_evidence_record_rejects_invalid_data_hash(
    invalid_hash: str,
) -> None:
    with pytest.raises(
        EvidenceChainValidationError,
        match="data_hash",
    ):
        EvidenceRecord(
            timestamp=TIMESTAMP,
            source="audit_engine",
            data_hash=invalid_hash,
        )


def test_evidence_record_rejects_non_string_prev_hash() -> None:
    with pytest.raises(
        EvidenceChainValidationError,
        match="string or None",
    ):
        EvidenceRecord(
            timestamp=TIMESTAMP,
            source="audit_engine",
            data_hash=_data_hash("payload"),
            prev_hash=123,  # type: ignore[arg-type]
        )


def test_evidence_record_rejects_invalid_prev_hash_digest() -> None:
    with pytest.raises(
        EvidenceChainValidationError,
        match="prev_hash must be",
    ):
        _record(prev_hash="invalid")


def test_empty_evidence_chain_is_valid() -> None:
    chain = EvidenceChain()

    assert chain.get_root_hash() == ""
    assert chain.get_records() == ()
    assert chain.verify_integrity() is True


def test_genesis_record_is_added_with_none_prev_hash() -> None:
    chain = EvidenceChain()
    genesis = _record()

    chain.add_record(genesis)

    assert chain.get_records() == (genesis,)
    assert chain.get_root_hash() == genesis.chain_hash
    assert chain.verify_integrity() is True


def test_second_record_links_to_current_chain_tip() -> None:
    chain = EvidenceChain()
    genesis = _record(data="genesis")
    second = _record(
        timestamp=TIMESTAMP + timedelta(seconds=1),
        source="validation_pipeline",
        data="second",
        prev_hash=genesis.chain_hash,
    )

    chain.add_record(genesis)
    chain.add_record(second)

    assert chain.get_records() == (genesis, second)
    assert chain.get_root_hash() == genesis.chain_hash
    assert chain.verify_integrity() is True


def test_genesis_record_with_non_none_prev_hash_is_rejected() -> None:
    chain = EvidenceChain()
    invalid_genesis = _record(prev_hash="0" * 64)

    with pytest.raises(
        EvidenceChainValidationError,
        match="current chain tip",
    ):
        chain.add_record(invalid_genesis)

    assert chain.get_records() == ()


def test_record_with_incorrect_previous_hash_is_rejected() -> None:
    chain = EvidenceChain()
    genesis = _record(data="genesis")
    invalid_second = _record(
        timestamp=TIMESTAMP + timedelta(seconds=1),
        data="second",
        prev_hash="0" * 64,
    )

    chain.add_record(genesis)

    with pytest.raises(
        EvidenceChainValidationError,
        match="current chain tip",
    ):
        chain.add_record(invalid_second)

    assert chain.get_records() == (genesis,)


def test_record_with_tampered_chain_hash_is_rejected() -> None:
    chain = EvidenceChain()
    record = _record()

    object.__setattr__(record, "chain_hash", "0" * 64)

    with pytest.raises(
        EvidenceChainValidationError,
        match="chain_hash is invalid",
    ):
        chain.add_record(record)

    assert chain.get_records() == ()


def test_verify_integrity_detects_tampered_record_data() -> None:
    chain = EvidenceChain()
    genesis = _record(data="genesis")
    second = _record(
        timestamp=TIMESTAMP + timedelta(seconds=1),
        data="second",
        prev_hash=genesis.chain_hash,
    )

    chain.add_record(genesis)
    chain.add_record(second)

    object.__setattr__(genesis, "data_hash", _data_hash("tampered"))

    assert chain.verify_integrity() is False


def test_verify_integrity_detects_tampered_link() -> None:
    chain = EvidenceChain()
    genesis = _record(data="genesis")
    second = _record(
        timestamp=TIMESTAMP + timedelta(seconds=1),
        data="second",
        prev_hash=genesis.chain_hash,
    )

    chain.add_record(genesis)
    chain.add_record(second)

    object.__setattr__(second, "prev_hash", "0" * 64)

    assert chain.verify_integrity() is False


def test_get_records_returns_immutable_snapshot() -> None:
    chain = EvidenceChain()
    genesis = _record()

    chain.add_record(genesis)
    snapshot = chain.get_records()

    assert snapshot == (genesis,)
    assert isinstance(snapshot, tuple)


def test_root_hash_remains_genesis_hash_after_chain_growth() -> None:
    chain = EvidenceChain()
    genesis = _record(data="genesis")
    second = _record(
        timestamp=TIMESTAMP + timedelta(seconds=1),
        data="second",
        prev_hash=genesis.chain_hash,
    )

    chain.add_record(genesis)
    chain.add_record(second)

    assert chain.get_root_hash() == genesis.chain_hash


def test_chain_rejects_non_evidence_record() -> None:
    chain = EvidenceChain()

    with pytest.raises(
        EvidenceChainValidationError,
        match="only EvidenceRecord",
    ):
        chain.add_record("invalid")  # type: ignore[arg-type]
