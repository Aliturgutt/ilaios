"""Provider-neutral managed cryptography and secret lifecycle boundaries."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Protocol


class CryptoPolicyError(PermissionError):
    """A cryptographic or secret lifecycle operation failed closed."""


class ManagedKeyProvider(Protocol):
    """Replaceable KMS/HSM or customer-managed-key adapter."""

    @property
    def provider_id(self) -> str: ...

    def wrap_key(
        self, key_reference: str, plaintext_data_key: bytes, context: bytes
    ) -> bytes: ...

    def unwrap_key(
        self, key_reference: str, wrapped_data_key: bytes, context: bytes
    ) -> bytes: ...


class EnvelopeCipher(Protocol):
    """Approved library/provider cipher; ILAIOS defines no primitive."""

    @property
    def algorithm(self) -> str: ...

    def generate_data_key(self) -> bytes: ...

    def encrypt(
        self, plaintext: bytes, data_key: bytes, associated_data: bytes
    ) -> bytes: ...

    def decrypt(
        self, ciphertext: bytes, data_key: bytes, associated_data: bytes
    ) -> bytes: ...


@dataclass(frozen=True, slots=True)
class CryptoProfile:
    profile_id: str
    allowed_algorithms: frozenset[str]
    maximum_cryptoperiod_seconds: int

    def __post_init__(self) -> None:
        if not self.profile_id or not self.allowed_algorithms:
            raise ValueError("crypto profile identity and algorithms are required")
        if self.maximum_cryptoperiod_seconds <= 0:
            raise ValueError("cryptoperiod must be positive")


@dataclass(frozen=True, slots=True)
class Envelope:
    secret_id: str
    tenant_id: str
    version: int
    provider_id: str
    key_reference: str
    algorithm: str
    ciphertext: bytes
    wrapped_data_key: bytes
    created_at: datetime
    rotate_after: datetime


class SecretStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    DESTROYED = "destroyed"


@dataclass(frozen=True, slots=True)
class SecretRecord:
    envelope: Envelope
    status: SecretStatus = SecretStatus.ACTIVE
    revoked_at: datetime | None = None
    destroyed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CryptoAuditEvent:
    operation: str
    secret_id: str
    tenant_id: str
    version: int
    provider_id: str
    key_reference: str
    occurred_at: datetime


class ManagedSecretStore:
    """Tenant-bound envelope storage with rotation, revocation, and destruction."""

    def __init__(
        self,
        provider: ManagedKeyProvider,
        cipher: EnvelopeCipher,
        profile: CryptoProfile,
    ) -> None:
        if cipher.algorithm not in profile.allowed_algorithms:
            raise CryptoPolicyError("algorithm is not admitted by crypto profile")
        self._provider = provider
        self._cipher = cipher
        self._profile = profile
        self._records: dict[str, list[SecretRecord]] = {}
        self._audit: list[CryptoAuditEvent] = []

    @staticmethod
    def _context(secret_id: str, tenant_id: str, version: int) -> bytes:
        return f"ilaios|{tenant_id}|{secret_id}|{version}".encode()

    def put(
        self,
        secret_id: str,
        tenant_id: str,
        plaintext: bytes,
        key_reference: str,
        now: datetime,
        rotate_after: datetime,
    ) -> SecretRecord:
        if not secret_id or not tenant_id or not plaintext or not key_reference:
            raise CryptoPolicyError(
                "secret, tenant, plaintext, and key reference are required"
            )
        seconds = (rotate_after - now).total_seconds()
        if seconds <= 0 or seconds > self._profile.maximum_cryptoperiod_seconds:
            raise CryptoPolicyError("rotation exceeds cryptoperiod policy")
        versions = self._records.setdefault(secret_id, [])
        if versions and versions[-1].envelope.tenant_id != tenant_id:
            raise CryptoPolicyError("secret identifier belongs to another tenant")
        version = len(versions) + 1
        context = self._context(secret_id, tenant_id, version)
        data_key = self._cipher.generate_data_key()
        record = SecretRecord(
            Envelope(
                secret_id,
                tenant_id,
                version,
                self._provider.provider_id,
                key_reference,
                self._cipher.algorithm,
                self._cipher.encrypt(plaintext, data_key, context),
                self._provider.wrap_key(key_reference, data_key, context),
                now,
                rotate_after,
            )
        )
        versions.append(record)
        self._event("create" if version == 1 else "rotate", record, now)
        return record

    def reveal(self, secret_id: str, tenant_id: str, now: datetime) -> bytes:
        record = self._active(secret_id, tenant_id)
        if now >= record.envelope.rotate_after:
            raise CryptoPolicyError("secret cryptoperiod expired")
        envelope = record.envelope
        context = self._context(secret_id, tenant_id, envelope.version)
        key = self._provider.unwrap_key(
            envelope.key_reference, envelope.wrapped_data_key, context
        )
        plaintext = self._cipher.decrypt(envelope.ciphertext, key, context)
        self._event("reveal", record, now)
        return plaintext

    def revoke(self, secret_id: str, tenant_id: str, now: datetime) -> None:
        record = self._active(secret_id, tenant_id)
        updated = replace(record, status=SecretStatus.REVOKED, revoked_at=now)
        self._records[secret_id][-1] = updated
        self._event("revoke", updated, now)

    def destroy(self, secret_id: str, tenant_id: str, now: datetime) -> None:
        records = self._records.get(secret_id)
        if not records or records[-1].envelope.tenant_id != tenant_id:
            raise CryptoPolicyError("secret not found for tenant")
        record = records[-1]
        if record.status is not SecretStatus.REVOKED:
            raise CryptoPolicyError("secret must be revoked before destruction")
        destroyed_envelope = replace(
            record.envelope, ciphertext=b"", wrapped_data_key=b""
        )
        updated = replace(
            record,
            envelope=destroyed_envelope,
            status=SecretStatus.DESTROYED,
            destroyed_at=now,
        )
        records[-1] = updated
        self._event("destroy", updated, now)

    def audit_events(self) -> tuple[CryptoAuditEvent, ...]:
        return tuple(self._audit)

    def _active(self, secret_id: str, tenant_id: str) -> SecretRecord:
        records = self._records.get(secret_id)
        if not records or records[-1].envelope.tenant_id != tenant_id:
            raise CryptoPolicyError("secret not found for tenant")
        record = records[-1]
        if record.status is not SecretStatus.ACTIVE:
            raise CryptoPolicyError("secret is not active")
        return record

    def _event(self, operation: str, record: SecretRecord, now: datetime) -> None:
        envelope = record.envelope
        self._audit.append(
            CryptoAuditEvent(
                operation,
                envelope.secret_id,
                envelope.tenant_id,
                envelope.version,
                envelope.provider_id,
                envelope.key_reference,
                now,
            )
        )
