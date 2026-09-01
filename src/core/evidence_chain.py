"""Deterministic append-only evidence chain for ILAIOS."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from string import hexdigits


class EvidenceChainValidationError(ValueError):
    """Raised when an evidence record or chain link is invalid."""


def _is_sha256_hex(value: str) -> bool:
    """Return whether value is a lowercase SHA-256 hexadecimal digest."""
    return (
        len(value) == 64
        and value == value.lower()
        and all(character in hexdigits for character in value)
    )


def _calculate_chain_hash(
    timestamp: datetime,
    source: str,
    data_hash: str,
    prev_hash: str | None,
) -> str:
    """Calculate the deterministic hash for an evidence record."""
    payload = (
        timestamp.isoformat()
        + source
        + data_hash
        + (prev_hash if prev_hash is not None else "")
    )
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Immutable representation of one evidence-chain entry."""

    timestamp: datetime
    source: str
    data_hash: str
    prev_hash: str | None = None
    chain_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise EvidenceChainValidationError(
                "Evidence timestamp must be timezone-aware"
            )

        if self.timestamp.utcoffset() != timezone.utc.utcoffset(self.timestamp):
            raise EvidenceChainValidationError(
                "Evidence timestamp must use UTC"
            )

        if not isinstance(self.source, str) or not self.source.strip():
            raise EvidenceChainValidationError(
                "Evidence source must not be empty"
            )

        if not isinstance(self.data_hash, str) or not _is_sha256_hex(
            self.data_hash
        ):
            raise EvidenceChainValidationError(
                "Evidence data_hash must be a lowercase SHA-256 digest"
            )

        if self.prev_hash is not None:
            if not isinstance(self.prev_hash, str):
                raise EvidenceChainValidationError(
                    "Evidence prev_hash must be a string or None"
                )

            if not _is_sha256_hex(self.prev_hash):
                raise EvidenceChainValidationError(
                    "Evidence prev_hash must be a lowercase SHA-256 digest"
                )

        object.__setattr__(
            self,
            "chain_hash",
            _calculate_chain_hash(
                self.timestamp,
                self.source,
                self.data_hash,
                self.prev_hash,
            ),
        )


class EvidenceChain:
    """Append-only in-memory chain of immutable evidence records."""

    def __init__(self) -> None:
        self._records: list[EvidenceRecord] = []

    def add_record(self, record: EvidenceRecord) -> None:
        """Validate and append one evidence record."""
        if not isinstance(record, EvidenceRecord):
            raise EvidenceChainValidationError(
                "Evidence chain accepts only EvidenceRecord instances"
            )

        expected_prev_hash = (
            None if not self._records else self._records[-1].chain_hash
        )

        if record.prev_hash != expected_prev_hash:
            raise EvidenceChainValidationError(
                "Evidence record does not reference the current chain tip"
            )

        expected_chain_hash = _calculate_chain_hash(
            record.timestamp,
            record.source,
            record.data_hash,
            record.prev_hash,
        )

        if record.chain_hash != expected_chain_hash:
            raise EvidenceChainValidationError(
                "Evidence record chain_hash is invalid"
            )

        self._records.append(record)

    def get_root_hash(self) -> str:
        """Return the genesis record hash, or an empty string for no records."""
        if not self._records:
            return ""
        return self._records[0].chain_hash

    def get_records(self) -> tuple[EvidenceRecord, ...]:
        """Return an immutable snapshot of all records in append order."""
        return tuple(self._records)

    def verify_integrity(self) -> bool:
        """Verify every record hash and predecessor link in the chain."""
        expected_prev_hash: str | None = None

        for record in self._records:
            if not isinstance(record, EvidenceRecord):
                return False

            if record.prev_hash != expected_prev_hash:
                return False

            expected_chain_hash = _calculate_chain_hash(
                record.timestamp,
                record.source,
                record.data_hash,
                record.prev_hash,
            )

            if record.chain_hash != expected_chain_hash:
                return False

            expected_prev_hash = record.chain_hash

        return True
