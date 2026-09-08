from __future__ import annotations

from pathlib import Path

import pytest

from services.integrations.desktop_video_composition import (
    _governed_stock_selector_from_environment,
    _official_brand_logo,
)
from src.video_automation.stock_source_adapters import StockProvider


def test_default_free_stock_selector_has_public_no_secret_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ILAIOS_PEXELS_API_KEY", raising=False)
    monkeypatch.delenv("ILAIOS_PIXABAY_API_KEY", raising=False)
    monkeypatch.delenv("ILAIOS_UNSPLASH_ACCESS_KEY", raising=False)

    selector = _governed_stock_selector_from_environment()
    adapters = selector._adapters

    assert StockProvider.WIKIMEDIA in adapters
    assert StockProvider.NASA in adapters
    assert StockProvider.INTERNET_ARCHIVE in adapters
    assert StockProvider.PEXELS not in adapters
    assert StockProvider.PIXABAY not in adapters
    assert StockProvider.UNSPLASH not in adapters


def test_credentialed_stock_sources_are_only_added_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ILAIOS_PEXELS_API_KEY", "pexels-key")
    monkeypatch.setenv("ILAIOS_PIXABAY_API_KEY", "pixabay-key")
    monkeypatch.setenv("ILAIOS_UNSPLASH_ACCESS_KEY", "unsplash-key")

    selector = _governed_stock_selector_from_environment()
    adapters = selector._adapters

    assert StockProvider.PEXELS in adapters
    assert StockProvider.PIXABAY in adapters
    assert StockProvider.UNSPLASH in adapters


def test_verified_free_composition_does_not_reference_seedance_free_alias() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "integrations"
        / "desktop_video_composition.py"
    ).read_text(encoding="utf-8")

    assert "SEEDANCE_FREE_MODEL_ID" not in source
    assert "ILAIOS_VIDEO_MODEL_ID" not in source
    assert "GovernedStockDesktopVideoRuntime(" in source
    assert '_DEFAULT_MANAGED_MODEL_ID = "bytedance/seedance-2.0-fast"' in source
    assert 'managed_model_id.endswith(":free")' in source


def test_verified_free_stock_runtime_reuses_durable_product_tenant_identity() -> None:
    root = Path(__file__).resolve().parents[1]
    composition_source = (
        root / "services" / "integrations" / "desktop_video_composition.py"
    ).read_text(encoding="utf-8")
    runtime_source = (
        root / "services" / "integrations" / "governed_stock_video_runtime.py"
    ).read_text(encoding="utf-8")

    assert "DurableProductIdentityResolver(product_identity_database)" in composition_source
    assert "tenant_id, requester_id = self._identity_resolver.resolve(request_id)" in runtime_source
    assert "tenant_id=tenant_id" in runtime_source
    assert "tenant_id=request_id" not in runtime_source


def test_video_provider_certification_uses_public_stock_for_verified_free() -> None:
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "video-provider-production-certification.yml"
    ).read_text(encoding="utf-8")

    assert "default: verified-free" in workflow
    assert "          - verified-free" in workflow
    assert "free-only" not in workflow
    assert "VIDEO_FREE_PROVIDER_MODELS" not in workflow
    assert "ILAIOS_VIDEO_MODEL_ID: bytedance/seedance" not in workflow
    assert "bytedance/seedance-2.0-fast:free" not in workflow
    assert "python -m scripts.video_public_stock_live_e2e" in workflow
    assert "python -m src.video_automation.free_provider_production_certification" not in workflow
    assert "VIDEO_PROVIDER_MODEL: bytedance/seedance-2.0-fast" in workflow
    assert "ILAIOS_VIDEO_MANAGED_MODEL_ID: bytedance/seedance-2.0-fast" in workflow


def test_canonical_brand_logo_is_reused_without_recolor_or_replacement() -> None:
    logo = _official_brand_logo()
    assert logo.name == "05-ilaios-app-icon.jpg"
    assert logo.is_file()
