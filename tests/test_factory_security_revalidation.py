"""Cross-capability revalidation for bounded ILAIOS factory/security foundations."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.cryptography import CryptoPolicyError, CryptoProfile, ManagedSecretStore
from services.integrations import GovernedWebFactory
from services.privacy import DataRecord, PrivacyError, TenantDataPolicy, TenantDataStore
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy


class _ManagedProvider:
    provider_id = "revalidation-kms-adapter"

    def wrap_key(
        self, key_reference: str, plaintext_data_key: bytes, context: bytes
    ) -> bytes:
        return b"wrapped|" + key_reference.encode() + b"|" + context + b"|" + plaintext_data_key

    def unwrap_key(
        self, key_reference: str, wrapped_data_key: bytes, context: bytes
    ) -> bytes:
        prefix = b"wrapped|" + key_reference.encode() + b"|" + context + b"|"
        if not wrapped_data_key.startswith(prefix):
            raise CryptoPolicyError("key context mismatch")
        return wrapped_data_key[len(prefix) :]


class _ApprovedTestCipher:
    """Boundary adapter for tests only; not a production cryptographic primitive."""

    algorithm = "approved-revalidation-adapter"

    def generate_data_key(self) -> bytes:
        return b"revalidation-data-key"

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


def _web_grant(now: datetime) -> ExecutionGrant:
    return ExecutionGrant(
        "revalidation-web-grant",
        "web-worker",
        frozenset({"web.build"}),
        frozenset({"ilaios-official"}),
        now + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def test_web_artifact_flows_through_tenant_privacy_and_crypto_boundaries(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 8, 11, tzinfo=timezone.utc)
    acceptance = GovernedWebFactory(
        GrantPolicy(), tmp_path / "artifacts"
    ).build_official_site(
        "ilaios-official",
        ("home", "product", "security", "contact"),
        grant=_web_grant(now),
        now=now,
    )
    assert acceptance.accepted is True

    privacy = TenantDataStore()
    privacy.register_policy(
        TenantDataPolicy(
            tenant_id="tenant-a",
            allowed_regions=frozenset({"eu"}),
            retention=timedelta(days=30),
            allowed_purposes=frozenset({"artifact-audit"}),
            allowed_fields=frozenset({"site_id", "artifact_hash", "bundle_id"}),
            dlp_blocked_classes=frozenset({"secret"}),
        )
    )
    privacy.create(
        DataRecord(
            record_id="web-acceptance-1",
            tenant_id="tenant-a",
            region="eu",
            purpose="artifact-audit",
            fields=(
                ("site_id", acceptance.site_id),
                ("artifact_hash", acceptance.artifact_hash),
                ("bundle_id", acceptance.bundle_id),
            ),
            classifications=frozenset({"internal"}),
            created_at=now,
        ),
        actor_id="web-worker",
    )
    stored = privacy.read("web-acceptance-1", "tenant-a", "auditor-1", now)
    assert dict(stored.fields)["artifact_hash"] == acceptance.artifact_hash
    with pytest.raises(PrivacyError, match="tenant"):
        privacy.read("web-acceptance-1", "tenant-b", "auditor-1", now)

    secrets = ManagedSecretStore(
        _ManagedProvider(),
        _ApprovedTestCipher(),
        CryptoProfile(
            "revalidation-profile",
            frozenset({"approved-revalidation-adapter"}),
            3600,
        ),
    )
    plaintext = acceptance.artifact_hash.encode()
    secret = secrets.put(
        "web-artifact-integrity",
        "tenant-a",
        plaintext,
        "key://tenant-a/revalidation",
        now,
        now + timedelta(minutes=30),
    )
    assert secret.envelope.ciphertext != plaintext
    assert secrets.reveal("web-artifact-integrity", "tenant-a", now) == plaintext
    with pytest.raises(CryptoPolicyError, match="tenant"):
        secrets.reveal("web-artifact-integrity", "tenant-b", now)
