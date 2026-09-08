from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from services.governance import GovernedRuntimeGateway
from services.integrations.desktop_video_composition import _managed_budget
from services.integrations.reference_aware_managed_provider_video_runtime import (
    DurableProductIdentityResolver,
    TenantBoundManagedDesktopVideoSession,
)
from services.integrations.video_runtime import VideoRuntimeError
from services.runtime import GovernedRuntime


def _identity_database(
    path: Path,
    *,
    tenant_id: str | None = "tenant-1",
    budget_minor: int = 100,
) -> Path:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE product_proofs (request_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, proposal_id TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE product_proof_identity ("
            "request_id TEXT PRIMARY KEY, requester_id TEXT NOT NULL, tenant_id TEXT)"
        )
        connection.execute(
            "INSERT INTO product_proofs VALUES ('request-1', 'job-1', 'proposal-1')"
        )
        connection.execute(
            "INSERT INTO product_proof_identity VALUES ('request-1', 'user-1', ?)",
            (tenant_id,),
        )
    control = path.parent / "control-plane.sqlite3"
    proposal = {
        "proposal_id": "proposal-1",
        "goal": {
            "budget": {
                "max_attempts": 2,
                "max_runtime_seconds": 600,
                "max_external_spend_minor": budget_minor,
            }
        },
    }
    with sqlite3.connect(control) as connection:
        connection.execute(
            "CREATE TABLE proposals (proposal_id TEXT PRIMARY KEY, proposal_json TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO proposals VALUES (?, ?)",
            ("proposal-1", json.dumps(proposal, sort_keys=True)),
        )
    return path


def _gateway(tmp_path: Path) -> GovernedRuntimeGateway:
    return GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(tmp_path / "governed-runtime.sqlite3"),
        hard_cap_minor=10_000,
    )


def _approve(gateway: GovernedRuntimeGateway, request_id: str = "request-1") -> None:
    gateway.submit(
        request_id,
        "user-1",
        "video-agent",
        "video-skill",
        "video",
        {"goal_id": "goal-1", "job_id": "job-1", "tenant_id": "tenant-1"},
        (),
        risk="high",
    )
    gateway.decide(request_id, "independent-approver", "approved")


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


@pytest.mark.parametrize(
    ("budget_minor", "expected_microusd"),
    ((50, 500_000), (100, 1_000_000), (500, 5_000_000), (2_000, 20_000_000)),
)
def test_product_budget_resolver_accepts_user_budget_above_one_dollar(
    tmp_path: Path,
    budget_minor: int,
    expected_microusd: int,
) -> None:
    resolver = DurableProductIdentityResolver(
        _identity_database(tmp_path / "proof.sqlite3", budget_minor=budget_minor)
    )

    assert resolver.approved_budget_microusd("request-1") == expected_microusd


def test_managed_session_requires_explicit_product_request_binding(tmp_path: Path) -> None:
    resolver = DurableProductIdentityResolver(_identity_database(tmp_path / "proof.sqlite3"))
    gateway = _gateway(tmp_path)
    session = TenantBoundManagedDesktopVideoSession(
        identity_resolver=resolver,
        governance=gateway,
        root=tmp_path / "managed",
        api_key="test-api-key",
        model_id="bytedance/seedance-2.0-fast",
        resolution="480p",
        max_total_cost_usd=Decimal("1.00"),
    )

    with pytest.raises(VideoRuntimeError, match="lacks product request identity binding"):
        session._require_bound_product_request()

    with pytest.raises(VideoRuntimeError, match="explicit human approval"):
        with session.bind_product_request("request-1"):
            pass

    _approve(gateway)
    with session.bind_product_request("request-1"):
        assert session._require_bound_product_request() == "request-1"
        assert session.max_total_cost_microusd == 1_000_000
        with pytest.raises(VideoRuntimeError, match="binding is already active"):
            with session.bind_product_request("request-1"):
                pass

    with pytest.raises(VideoRuntimeError, match="lacks product request identity binding"):
        session._require_bound_product_request()


def test_managed_session_uses_approved_five_dollar_budget_not_configured_one_dollar(
    tmp_path: Path,
) -> None:
    resolver = DurableProductIdentityResolver(
        _identity_database(tmp_path / "proof.sqlite3", budget_minor=500)
    )
    gateway = _gateway(tmp_path)
    _approve(gateway)
    session = TenantBoundManagedDesktopVideoSession(
        identity_resolver=resolver,
        governance=gateway,
        root=tmp_path / "managed",
        api_key="test-api-key",
        model_id="bytedance/seedance-2.0-fast",
        resolution="480p",
        max_total_cost_usd=Decimal("1.00"),
    )

    with session.bind_product_request("request-1"):
        assert session.max_total_cost_microusd == 5_000_000
        assert session._active_approval_id() == "request-1"


def test_managed_budget_requires_explicit_positive_finite_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", raising=False)
    with pytest.raises(VideoRuntimeError, match="requires ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD"):
        _managed_budget()

    for value in ("0.50", "1.00", "5.00", "20.00"):
        monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", value)
        assert str(_managed_budget()) == value

    for value in ("0", "-1", "NaN", "Infinity"):
        monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", value)
        with pytest.raises(VideoRuntimeError, match="finite and > 0"):
            _managed_budget()

    monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "1.0000001")
    with pytest.raises(VideoRuntimeError, match="microUSD precision"):
        _managed_budget()


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
    assert "_MAX_MANAGED_DESKTOP_BUDGET_USD" not in composition
    assert "unknown Desktop Video provider mode" in composition
    assert "automatic" in composition and "fallback" in composition
