from __future__ import annotations

import json
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
from src.video_automation.models import ProviderRequest
from src.video_automation.openrouter_video_catalog import (
    ManagedVideoFamily,
    OpenRouterVideoModel,
)


def _identity_database(
    path: Path,
    *,
    tenant_id: str | None = "tenant-1",
    budget_minor: int = 100,
    request_id: str = "request-1",
    requester_id: str = "user-1",
) -> Path:
    proposal_id = f"proposal-{request_id}"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE product_proofs ("
            "request_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, proposal_id TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE product_proof_identity ("
            "request_id TEXT PRIMARY KEY, requester_id TEXT NOT NULL, tenant_id TEXT)"
        )
        connection.execute(
            "INSERT INTO product_proofs VALUES (?, ?, ?)",
            (request_id, f"job-{request_id}", proposal_id),
        )
        connection.execute(
            "INSERT INTO product_proof_identity VALUES (?, ?, ?)",
            (request_id, requester_id, tenant_id),
        )
    with sqlite3.connect(path.parent / "control-plane.sqlite3") as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS proposals ("
            "proposal_id TEXT PRIMARY KEY, proposal_json TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO proposals VALUES (?, ?)",
            (
                proposal_id,
                json.dumps(
                    {
                        "goal": {
                            "budget": {
                                "max_attempts": 2,
                                "max_runtime_seconds": 600,
                                "max_external_spend_minor": budget_minor,
                            }
                        }
                    },
                    sort_keys=True,
                ),
            ),
        )
    return path


def _request(request_id: str = "provider-dispatch-1") -> ProviderRequest:
    return ProviderRequest(
        request_id=request_id,
        job_id="provider-job-1",
        provider_name="openrouter-video-managed",
        operation="video.generate",
        payload={
            "model_id": "bytedance/seedance-2.0-fast",
            "items_json": "[]",
        },
    )


def _seedance_model() -> OpenRouterVideoModel:
    return OpenRouterVideoModel(
        model_id="bytedance/seedance-2.0-fast",
        canonical_slug="bytedance/seedance-2.0-fast",
        name="Seedance 2.0 Fast",
        generate_audio=True,
        supported_aspect_ratios=("16:9",),
        supported_durations=(4,),
        supported_frame_images=(),
        supported_resolutions=("480p",),
        supported_sizes=("854x480",),
        allowed_passthrough_parameters=(),
        pricing_skus={"video_tokens": "0.0000042"},
        family=ManagedVideoFamily.SEEDANCE,
    )


def _managed_session(tmp_path: Path, *, budget_minor: int = 500) -> TenantBoundManagedDesktopVideoSession:
    resolver = DurableProductIdentityResolver(
        _identity_database(tmp_path / "proof.sqlite3", budget_minor=budget_minor)
    )
    return TenantBoundManagedDesktopVideoSession(
        identity_resolver=resolver,
        root=tmp_path / "managed",
        api_key="test-api-key",
        model_id="bytedance/seedance-2.0-fast",
        resolution="480p",
        max_total_cost_usd=Decimal("20.00"),
    )


def _provider_side_effect_count(root: Path) -> int:
    database = root / "managed-credit-ledger" / "managed_media_finops.sqlite3"
    with sqlite3.connect(database) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM provider_side_effects").fetchone()[0])


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
        resolver.resolve("job-request-1")


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


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("budget_minor", "expected_usd"),
    ((50, "0.5"), (100, "1"), (500, "5"), (2000, "20")),
)
def test_approved_product_budget_accepts_user_amounts_above_old_one_dollar_cap(
    tmp_path: Path,
    budget_minor: int,
    expected_usd: str,
) -> None:
    resolver = DurableProductIdentityResolver(
        _identity_database(tmp_path / f"proof-{budget_minor}.sqlite3", budget_minor=budget_minor)
    )

    approved = resolver.approved_budget("request-1", approval_proven=True)

    assert approved.tenant_id == "tenant-1"
    assert approved.requester_id == "user-1"
    assert approved.approval_id == "request-1"
    assert Decimal(approved.approved_budget_microusd) / Decimal(1_000_000) == Decimal(
        expected_usd
    )


def test_approved_product_budget_requires_exact_request_approval(tmp_path: Path) -> None:
    resolver = DurableProductIdentityResolver(
        _identity_database(tmp_path / "proof.sqlite3", budget_minor=500)
    )

    with pytest.raises(VideoRuntimeError, match="requires explicit approval"):
        resolver.approved_budget("request-1", approval_proven=False)


def test_managed_session_requires_explicit_product_request_binding(tmp_path: Path) -> None:
    session = _managed_session(tmp_path)

    with pytest.raises(VideoRuntimeError, match="lacks product request identity binding"):
        session._require_bound_product_request()

    with session.bind_product_request("request-1"):
        assert session._require_bound_product_request() == "request-1"
        with pytest.raises(VideoRuntimeError, match="binding is already active"):
            with session.bind_product_request("request-2"):
                pass

    with pytest.raises(VideoRuntimeError, match="lacks product request identity binding"):
        session._require_bound_product_request()


def test_paid_seedance_without_approval_never_reaches_provider(tmp_path: Path) -> None:
    session = _managed_session(tmp_path)
    session.configure_approval_checker(lambda _request_id: False)

    with session.bind_product_request("request-1"):
        result = session.execute(_request())

    assert result.success is False
    assert result.error_code == "approval_required"
    assert result.metadata["reapproval_required"] == "true"
    assert _provider_side_effect_count(tmp_path / "managed") == 0


def test_tenant_a_approval_cannot_authorize_tenant_b_request(tmp_path: Path) -> None:
    database = _identity_database(
        tmp_path / "proof.sqlite3",
        tenant_id="tenant-a",
        budget_minor=500,
        request_id="request-a",
        requester_id="user-a",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO product_proofs VALUES ('request-b', 'job-b', 'proposal-request-b')"
        )
        connection.execute(
            "INSERT INTO product_proof_identity VALUES ('request-b', 'user-b', 'tenant-b')"
        )
    with sqlite3.connect(tmp_path / "control-plane.sqlite3") as connection:
        connection.execute(
            "INSERT INTO proposals VALUES (?, ?)",
            (
                "proposal-request-b",
                json.dumps(
                    {"goal": {"budget": {"max_external_spend_minor": 500}}},
                    sort_keys=True,
                ),
            ),
        )
    resolver = DurableProductIdentityResolver(database)
    session = TenantBoundManagedDesktopVideoSession(
        identity_resolver=resolver,
        root=tmp_path / "managed",
        api_key="test-api-key",
        model_id="bytedance/seedance-2.0-fast",
        resolution="480p",
        max_total_cost_usd=Decimal("20.00"),
    )
    session.configure_approval_checker(lambda request_id: request_id == "request-a")

    with session.bind_product_request("request-b"):
        result = session.execute(_request("provider-dispatch-b"))

    assert result.success is False
    assert result.error_code == "approval_required"
    assert _provider_side_effect_count(tmp_path / "managed") == 0


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "approved_budget_usd", ("0.50", "1.00", "5.00", "20.00")
)
def test_preflight_accepts_user_budget_without_old_one_dollar_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approved_budget_usd: str,
) -> None:
    session = _managed_session(tmp_path)
    monkeypatch.setattr(session._catalog, "paid_eligible_models", lambda: (_seedance_model(),))

    estimate = session.preflight_estimate(
        objective="Create an 8 second cinematic video",
        approved_budget_microusd=int(Decimal(approved_budget_usd) * 1_000_000),
    )

    assert estimate.provider == "openrouter-video-managed"
    assert estimate.model == "bytedance/seedance-2.0-fast"
    assert estimate.planned_generation_count == 2
    assert estimate.estimated_cost_microusd > 0
    assert estimate.reserved_ceiling_microusd <= int(
        Decimal(approved_budget_usd) * 1_000_000
    )


def test_preflight_blocks_when_estimate_exceeds_user_budget_before_provider_post(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _managed_session(tmp_path)
    monkeypatch.setattr(session._catalog, "paid_eligible_models", lambda: (_seedance_model(),))

    with pytest.raises(VideoRuntimeError, match="reapproval required"):
        session.preflight_estimate(
            objective="Create an 8 second cinematic video",
            approved_budget_microusd=200_000,
        )

    assert _provider_side_effect_count(tmp_path / "managed") == 0


def test_managed_budget_requires_explicit_positive_deployment_ceiling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", raising=False)
    with pytest.raises(VideoRuntimeError, match="requires ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD"):
        _managed_budget()

    for value in ("0.50", "1.00", "5.00", "20.00"):
        monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", value)
        assert str(_managed_budget()) == value

    monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "0")
    with pytest.raises(VideoRuntimeError, match="finite positive"):
        _managed_budget()

    monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "NaN")
    with pytest.raises(VideoRuntimeError, match="finite positive"):
        _managed_budget()

    monkeypatch.setenv("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "1.0000001")
    with pytest.raises(VideoRuntimeError, match="microUSD precision"):
        _managed_budget()


def test_certification_caps_remain_one_dollar_and_separate_from_production() -> None:
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "video-provider-production-certification.yml"
    ).read_text(encoding="utf-8")

    assert 'VIDEO_PROVIDER_MAX_TOTAL_COST_USD: "1.00"' in workflow
    assert 'ILAIOS_VIDEO_MANAGED_E2E_MAX_TOTAL_USD: "1.00"' in workflow
    assert "_MAX_MANAGED_DESKTOP_BUDGET_USD" not in (
        Path(__file__).resolve().parents[1]
        / "services"
        / "integrations"
        / "desktop_video_composition.py"
    ).read_text(encoding="utf-8")


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
    assert "_MAX_MANAGED_DESKTOP_BUDGET_USD" not in composition
