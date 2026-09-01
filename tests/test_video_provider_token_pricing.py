from __future__ import annotations

from decimal import Decimal

import pytest

from src.video_automation.openrouter_video_catalog import (
    ManagedVideoFamily,
    OpenRouterVideoModel,
)
from src.video_automation.provider_production_certification import (
    CertificationShape,
    ProviderProductionCertificationError,
    certification_price,
)


def _token_model(*, pricing_skus: dict[str, str]) -> OpenRouterVideoModel:
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
        pricing_skus=pricing_skus,
        family=ManagedVideoFamily.SEEDANCE,
    )


def test_live_no_audio_video_token_sku_produces_bounded_exact_quote() -> None:
    price = certification_price(
        _token_model(
            pricing_skus={
                "video_tokens": "0.0000042",
                "video_tokens_without_audio": "0.0000042",
                "video_tokens_with_video_input": "0.000002475",
            }
        ),
        CertificationShape(),
    )

    assert price.sku == "video_tokens_without_audio"
    assert price.unit_price_usd == Decimal("0.0000042")
    assert price.estimated_units == Decimal("38430")
    assert price.estimated_total_usd == Decimal("0.1614060")
    assert price.estimated_total_microusd == 161_406


def test_token_pricing_falls_back_to_generic_video_tokens() -> None:
    price = certification_price(
        _token_model(pricing_skus={"video_tokens": "0.0000042"}),
        CertificationShape(),
    )

    assert price.sku == "video_tokens"
    assert price.estimated_units == Decimal("38430")


def test_audio_certification_never_uses_no_audio_sku() -> None:
    price = certification_price(
        _token_model(
            pricing_skus={
                "video_tokens": "0.0000043",
                "video_tokens_without_audio": "0.0000010",
            }
        ),
        CertificationShape(generate_audio=True),
    )

    assert price.sku == "video_tokens"
    assert price.unit_price_usd == Decimal("0.0000043")


def test_token_pricing_blocks_unproven_pixel_mapping() -> None:
    with pytest.raises(
        ProviderProductionCertificationError,
        match="approved pixel mapping",
    ):
        certification_price(
            _token_model(pricing_skus={"video_tokens_without_audio": "0.0000042"}),
            CertificationShape(aspect_ratio="9:16"),
        )


def test_token_pricing_enforces_effective_per_second_ceiling() -> None:
    with pytest.raises(
        ProviderProductionCertificationError,
        match="effective per-second price exceeds",
    ):
        certification_price(
            _token_model(pricing_skus={"video_tokens_without_audio": "0.0000200"}),
            CertificationShape(),
        )
