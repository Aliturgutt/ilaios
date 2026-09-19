from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from src.video_automation.openrouter_managed_video_provider import (
    OPENROUTER_MANAGED_PROVIDER_NAME,
)
from src.video_automation.openrouter_video_catalog import (
    ManagedVideoFamily,
    OpenRouterVideoModel,
)
from src.video_automation.provider_production_certification import (
    CertificationPrice,
    CertificationShape,
    ProviderProductionCertificationError,
    build_certification_request,
    certification_price,
    certification_provider_cost_ceiling,
    run_certification,
    select_certification_model,
)


def _model(
    *,
    model_id: str = "bytedance/seedance-2.0-fast",
    pricing_skus: dict[str, str] | None = None,
) -> OpenRouterVideoModel:
    return OpenRouterVideoModel(
        model_id=model_id,
        canonical_slug=model_id,
        name="Seedance certification model",
        generate_audio=True,
        supported_aspect_ratios=("16:9", "9:16"),
        supported_durations=(4, 8),
        supported_frame_images=(),
        supported_resolutions=("480p", "720p"),
        supported_sizes=(),
        allowed_passthrough_parameters=(),
        pricing_skus=(
            {"per-video-second": "0.05"}
            if pricing_skus is None
            else pricing_skus
        ),
        family=ManagedVideoFamily.SEEDANCE,
    )


def test_selects_only_configured_model_with_exact_capability() -> None:
    shape = CertificationShape()

    selected = select_certification_model(
        (_model(model_id="kwaivgi/kling-v3.0-pro"), _model()),
        shape,
    )

    assert selected.model_id == shape.model_id


def test_missing_or_incompatible_certification_model_fails_closed() -> None:
    shape = CertificationShape()
    with pytest.raises(
        ProviderProductionCertificationError,
        match="not currently paid-eligible",
    ):
        select_certification_model(
            (_model(model_id="kwaivgi/kling-v3.0-pro"),),
            shape,
        )

    incompatible = OpenRouterVideoModel(
        model_id=shape.model_id,
        canonical_slug=shape.model_id,
        name="incompatible",
        generate_audio=False,
        supported_aspect_ratios=("9:16",),
        supported_durations=(8,),
        supported_frame_images=(),
        supported_resolutions=("720p",),
        supported_sizes=(),
        allowed_passthrough_parameters=(),
        pricing_skus={"per-video-second": "0.05"},
        family=ManagedVideoFamily.SEEDANCE,
    )
    with pytest.raises(
        ProviderProductionCertificationError,
        match="duration",
    ):
        select_certification_model((incompatible,), shape)


def test_live_catalog_price_becomes_bounded_microusd_quote() -> None:
    price = certification_price(_model(), CertificationShape())

    assert price.sku == "per-video-second"
    assert price.unit_price_usd == Decimal("0.05")
    assert price.estimated_total_usd == Decimal("0.20")
    assert price.estimated_total_microusd == 200_000


def test_resolution_specific_price_is_preferred() -> None:
    model = _model(
        pricing_skus={
            "per-video-second": "0.06",
            "per-video-second-480p": "0.04",
            "generate": "0.05",
        }
    )

    price = certification_price(model, CertificationShape())

    assert price.sku == "per-video-second-480p"
    assert price.estimated_total_usd == Decimal("0.16")


def test_unknown_or_over_budget_price_blocks_before_dispatch() -> None:
    with pytest.raises(
        ProviderProductionCertificationError,
        match="recognized bounded video price SKU",
    ):
        certification_price(
            _model(pricing_skus={"other": "0.01"}),
            CertificationShape(),
        )

    with pytest.raises(
        ProviderProductionCertificationError,
        match="unit price exceeds",
    ):
        certification_price(
            _model(pricing_skus={"per-video-second": "0.16"}),
            CertificationShape(),
        )

    with pytest.raises(
        ProviderProductionCertificationError,
        match="total price exceeds",
    ):
        certification_price(
            _model(pricing_skus={"per-video-second": "0.11"}),
            CertificationShape(
                duration_seconds=6,
                max_unit_price_usd=Decimal("0.15"),
            ),
        )


def test_provider_reservation_buffers_variance_inside_hard_spend_cap() -> None:
    price = CertificationPrice(
        sku="video_tokens_without_audio",
        unit_price_usd=Decimal("0.0000042"),
        estimated_units=Decimal("38430"),
        estimated_total_usd=Decimal("0.161406"),
        estimated_total_microusd=161_406,
    )
    shape = CertificationShape(max_total_cost_usd=Decimal("1.00"))

    ceiling = certification_provider_cost_ceiling(
        price,
        shape,
        contingency_bps=1_000,
    )

    assert ceiling == 177_547
    assert 170_495 <= ceiling
    assert ceiling <= 1_000_000


def test_provider_reservation_never_exceeds_authorized_hard_cap() -> None:
    price = CertificationPrice(
        sku="per-video-second",
        unit_price_usd=Decimal("0.10"),
        estimated_units=Decimal("4"),
        estimated_total_usd=Decimal("0.40"),
        estimated_total_microusd=400_000,
    )
    shape = CertificationShape(max_total_cost_usd=Decimal("0.42"))

    assert certification_provider_cost_ceiling(
        price,
        shape,
        contingency_bps=1_000,
    ) == 420_000


def test_request_is_single_item_and_bound_to_managed_provider() -> None:
    request = build_certification_request(
        shape=CertificationShape(),
        run_id="31879000000",
        run_attempt="2",
    )

    assert request.provider_name == OPENROUTER_MANAGED_PROVIDER_NAME
    assert request.operation == "video.generate"
    assert request.payload["request_count"] == 1
    assert request.payload["model_id"] == "bytedance/seedance-2.0-fast"
    items = json.loads(str(request.payload["items_json"]))
    assert len(items) == 1
    assert items[0]["duration_seconds"] == 4
    assert items[0]["resolution"] == "480p"
    assert items[0]["aspect_ratio"] == "16:9"
    assert items[0]["generate_audio"] is False


def test_paid_rerun_is_blocked_before_network(tmp_path: Path) -> None:
    proof_dir = tmp_path / "proof"

    with pytest.raises(
        ProviderProductionCertificationError,
        match="re-runs are forbidden",
    ):
        run_certification(
            api_key="would-not-be-used",
            proof_dir=proof_dir,
            revision_sha="a" * 40,
            run_id="31879000000",
            run_attempt="2",
        )

    receipt = json.loads((proof_dir / "provider-receipt.json").read_text())
    assert receipt["status"] == "BLOCKED_REPEAT_PAID_ATTEMPT"
    assert "external_job_id" not in receipt
    assert not (proof_dir / "provider-proof.mp4").exists()


def test_missing_secret_writes_blocker_receipt_without_network(tmp_path: Path) -> None:
    proof_dir = tmp_path / "proof"

    with pytest.raises(
        ProviderProductionCertificationError,
        match="OPENROUTER_API_KEY is unavailable",
    ):
        run_certification(
            api_key="",
            proof_dir=proof_dir,
            revision_sha="a" * 40,
            run_id="31879000000",
            run_attempt="1",
        )

    receipt = json.loads((proof_dir / "provider-receipt.json").read_text())
    assert receipt["status"] == "BLOCKED_MISSING_SECRET"
    assert receipt["credential_reference"].endswith("/OPENROUTER_API_KEY")
    assert "external_job_id" not in receipt
    assert not (proof_dir / "provider-proof.mp4").exists()
