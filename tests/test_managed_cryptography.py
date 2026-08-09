"""Bounded proofs for CRYPTO.I03 without custom production cryptography."""

from datetime import datetime, timedelta, timezone

import pytest

from services.cryptography import (
    CryptoPolicyError,
    CryptoProfile,
    ManagedSecretStore,
)

NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


class _ManagedProvider:
    provider_id = "kms-adapter"

    def wrap_key(
        self, key_reference: str, plaintext_data_key: bytes, context: bytes
    ) -> bytes:
        return (
            b"wrapped|"
            + key_reference.encode()
            + b"|"
            + context
            + b"|"
            + plaintext_data_key
        )

    def unwrap_key(
        self, key_reference: str, wrapped_data_key: bytes, context: bytes
    ) -> bytes:
        prefix = b"wrapped|" + key_reference.encode() + b"|" + context + b"|"
        if not wrapped_data_key.startswith(prefix):
            raise CryptoPolicyError("key context mismatch")
        return wrapped_data_key[len(prefix) :]


class _ApprovedTestCipher:
    """Test adapter only; proves boundary calls, not a cryptographic primitive."""

    algorithm = "approved-test-adapter"

    def generate_data_key(self) -> bytes:
        return b"test-data-key"

    def encrypt(
        self, plaintext: bytes, data_key: bytes, associated_data: bytes
    ) -> bytes:
        return associated_data + b"|" + data_key + b"|" + plaintext

    def decrypt(
        self, ciphertext: bytes, data_key: bytes, associated_data: bytes
    ) -> bytes:
        prefix = associated_data + b"|" + data_key + b"|"
        if not ciphertext.startswith(prefix):
            raise CryptoPolicyError("cipher context mismatch")
        return ciphertext[len(prefix) :]


def _store() -> ManagedSecretStore:
    return ManagedSecretStore(
        _ManagedProvider(),
        _ApprovedTestCipher(),
        CryptoProfile("profile-1", frozenset({"approved-test-adapter"}), 3600),
    )


def test_envelope_encryption_is_tenant_bound_audited_and_rotatable() -> None:
    store = _store()
    first = store.put(
        "secret-1", "tenant-a", b"value-1", "key-a", NOW, NOW + timedelta(minutes=30)
    )
    assert first.envelope.ciphertext != b"value-1"
    assert store.reveal("secret-1", "tenant-a", NOW) == b"value-1"
    second = store.put(
        "secret-1", "tenant-a", b"value-2", "key-b", NOW, NOW + timedelta(minutes=30)
    )
    assert second.envelope.version == 2
    assert [event.operation for event in store.audit_events()] == [
        "create",
        "reveal",
        "rotate",
    ]
    with pytest.raises(CryptoPolicyError, match="tenant"):
        store.reveal("secret-1", "tenant-b", NOW)


def test_cryptoperiod_revocation_and_destruction_fail_closed() -> None:
    store = _store()
    store.put(
        "secret-1", "tenant-a", b"value", "key-a", NOW, NOW + timedelta(minutes=1)
    )
    with pytest.raises(CryptoPolicyError, match="cryptoperiod"):
        store.reveal("secret-1", "tenant-a", NOW + timedelta(minutes=2))
    with pytest.raises(CryptoPolicyError, match="revoked"):
        store.destroy("secret-1", "tenant-a", NOW)
    store.revoke("secret-1", "tenant-a", NOW)
    with pytest.raises(CryptoPolicyError, match="not active"):
        store.reveal("secret-1", "tenant-a", NOW)
    store.destroy("secret-1", "tenant-a", NOW)
    assert store.audit_events()[-1].operation == "destroy"


def test_crypto_agility_rejects_unapproved_algorithm_and_long_cryptoperiod() -> None:
    with pytest.raises(CryptoPolicyError, match="algorithm"):
        ManagedSecretStore(
            _ManagedProvider(),
            _ApprovedTestCipher(),
            CryptoProfile("profile-1", frozenset({"different"}), 3600),
        )
    with pytest.raises(CryptoPolicyError, match="cryptoperiod"):
        _store().put(
            "secret-1",
            "tenant-a",
            b"value",
            "cmk://tenant-a/key",
            NOW,
            NOW + timedelta(hours=2),
        )
