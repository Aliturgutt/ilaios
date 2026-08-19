from __future__ import annotations

import sqlite3
import threading
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


def test_managed_identity_resolver_uses_durable_product_identity(tmp_path: Path) -> None:
    resolver = DurableProductIdentityResolver(_identity_database(tmp_path / "proof.sqlite3"))

    assert resolver.resolve("job-1") == ("tenant-1", "user-1")


def test_managed_identity_resolver_fails_closed_without_tenant(tmp_path: Path) -> None:
    resolver = DurableProductIdentityResolver(
        _identity_database(tmp_path / "proof.sqlite3", tenant_id=None)
    )

    with pytest.raises(VideoRuntimeError, match="tenant identity is unavailable"):
        resolver.resolve("job-1")


def test_managed_identity_resolver_fails_closed_for_unknown_job(tmp_path: Path) -> None:
    resolver = DurableProductIdentityResolver(_identity_database(tmp_path / "proof.sqlite3"))

    with pytest.raises(VideoRuntimeError, match="one durable product identity"):
        resolver.resolve("job-missing")


def test_managed_session_binds_product_job_per_execution_thread() -> None:
    session = object.__new__(TenantBoundManagedDesktopVideoSession)
    session._product_job_context = threading.local()

    with pytest.raises(VideoRuntimeError, match="product job identity is not bound"):
        session._bound_product_job_id()

    with session.bind_product_job("job-1"):
        assert session._bound_product_job_id() == "job-1"
        with pytest.raises(VideoRuntimeError, match="already bound"):
            with session.bind_product_job("job-2"):
                pass

    with pytest.raises(VideoRuntimeError, match="product job identity is not bound"):
        session._bound_product_job_id()


def test_managed_reference_runtime_resolves_admitted_product_job_not_dispatch_job() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (
        root
        / "services"
        / "integrations"
        / "reference_aware_managed_provider_video_runtime.py"
    ).read_text(encoding="utf-8")

    assert "self._identity_resolver.resolve(\n            self._bound_product_job_id()\n        )" in source
    assert "with self._tenant_bound_session.bind_product_job(job_id):" in source
    assert "self._identity_resolver.resolve(request.job_id)" not in source


def test_managed_budget_requires_explicit_bounded_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", raising=False)
    with pytest.raises(VideoRuntimeError, match="requires ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD"):
        _managed_budget()

    monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "1.01")
    with pytest.raises(VideoRuntimeError, match="<= 1.00 USD"):
        _managed_budget()

    monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "1.00")
    assert str(_managed_budget()) == "1.00"


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
