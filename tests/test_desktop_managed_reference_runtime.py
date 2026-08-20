from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from services.integrations.desktop_video_composition import _managed_budget
from services.integrations.reference_aware_managed_provider_video_runtime import (
    DurableProductIdentityResolver,
    TenantBoundManagedDesktopVideoSession,
)
from services.integrations.video_runtime import VideoRuntimeError


def _identity_database(path: Path, *, tenant_id: str | None = "tenant-1") -> Path:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE product_proofs (request_id TEXT PRIMARY KEY, job_id TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE product_proof_identity ("
            "request_id TEXT PRIMARY KEY, requester_id TEXT NOT NULL, tenant_id TEXT)"
        )
        connection.execute(
            "INSERT INTO product_proofs VALUES ('request-1', 'job-1')"
        )
        connection.execute(
            "INSERT INTO product_proof_identity VALUES ('request-1', 'user-1', ?)",
            (tenant_id,),
        )
    return path


def test_managed_identity_resolver_uses_durable_product_request_identity(
    tmp_path: Path,
) -> None:
    resolver = DurableProductIdentityResolver(_identity_database(tmp_path / "proof.sqlite3"))

    assert resolver.resolve("request-1") == ("tenant-1", "user-1")


def test_managed_identity_resolver_does_not_treat_control_plane_job_as_product_request(
    tmp_path: Path,
) -> None:
    resolver = DurableProductIdentityResolver(_identity_database(tmp_path / "proof.sqlite3"))

    with pytest.raises(VideoRuntimeError, match="product request lacks one durable"):
        resolver.resolve("job-1")


def test_managed_identity_resolver_fails_closed_without_tenant(tmp_path: Path) -> None:
    resolver = DurableProductIdentityResolver(
        _identity_database(tmp_path / "proof.sqlite3", tenant_id=None)
    )

    with pytest.raises(VideoRuntimeError, match="tenant identity is unavailable"):
        resolver.resolve("request-1")


def test_managed_identity_resolver_fails_closed_for_unknown_request(tmp_path: Path) -> None:
    resolver = DurableProductIdentityResolver(_identity_database(tmp_path / "proof.sqlite3"))

    with pytest.raises(VideoRuntimeError, match="product request lacks one durable"):
        resolver.resolve("request-missing")


def test_managed_session_requires_explicit_product_request_binding(tmp_path: Path) -> None:
    resolver = DurableProductIdentityResolver(_identity_database(tmp_path / "proof.sqlite3"))
    session = TenantBoundManagedDesktopVideoSession(
        identity_resolver=resolver,
        root=tmp_path / "managed",
        api_key="test-api-key",
        model_id="bytedance/seedance-2.0-fast",
        resolution="480p",
        max_total_cost_usd=Decimal("1.00"),
    )

    with pytest.raises(VideoRuntimeError, match="lacks product request identity binding"):
        session._require_bound_product_request()

    with session.bind_product_request("request-1"):
        assert session._require_bound_product_request() == "request-1"
        with pytest.raises(VideoRuntimeError, match="binding is already active"):
            with session.bind_product_request("request-2"):
                pass

    with pytest.raises(VideoRuntimeError, match="lacks product request identity binding"):
        session._require_bound_product_request()


def test_managed_budget_requires_explicit_bounded_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", raising=False)
    with pytest.raises(VideoRuntimeError, match="requires ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD"):
        _managed_budget()

    monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "1.01")
    with pytest.raises(VideoRuntimeError, match="<= 1.00 USD"):
        _managed_budget()

    monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "1.00")
    assert str(_managed_budget()) == "1.00"


def test_reference_analyzer_is_pinned_to_supported_free_multimodal_route() -> None:
    runtime = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "integrations"
        / "reference_aware_managed_provider_video_runtime.py"
    ).read_text(encoding="utf-8")

    assert (
        '_DEFAULT_REFERENCE_ANALYZER_MODEL_ID = "google/gemma-4-26b-a4b-it:free"'
        in runtime
    )
    assert "_DEFAULT_REFERENCE_ANALYZER_MODEL_ID" in runtime.split(
        "OpenRouterReferenceImageAnalyzer(", 1
    )[1]


def test_desktop_sidecar_managed_mode_is_explicit_and_truthful() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "apps"
        / "desktop"
        / "sidecar"
        / "ilaios_control_plane_sidecar.py"
    ).read_text(encoding="utf-8")
    composition = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "integrations"
        / "desktop_video_composition.py"
    ).read_text(encoding="utf-8")

    assert '"ILAIOS_VIDEO_PROVIDER_MODE", "verified-free"' in source
    assert '"video_provider_mode": video_provider_mode' in source
    assert '"video_managed_budget_usd": video_managed_budget_usd' in source
    assert 'os.environ.get("ILAIOS_VIDEO_PROVIDER_MODE", _VERIFIED_FREE)' in composition
    assert "if mode == _VERIFIED_FREE:" in composition
    assert "ManagedReferenceAwareProviderBackedDesktopVideoRuntime(" in composition
    assert "unknown Desktop Video provider mode" in composition
    assert "automatic" in composition and "fallback" in composition
