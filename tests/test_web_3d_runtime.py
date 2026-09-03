from __future__ import annotations

import pytest

from services.web_3d_runtime import (
    Web3DAssetRef,
    Web3DRuntimeError,
    compile_web_3d_runtime_plan,
    render_native_webgl_artifact,
)


def test_compile_detects_explicit_premium_product_launch_features() -> None:
    plan = compile_web_3d_runtime_plan(
        "Build a dark website with a 3D hero, scroll-driven camera motion, "
        "interactive product model rotation, parallax, particles, and a WebGL background."
    )

    assert plan.features == (
        "3d-hero",
        "scroll-camera",
        "product-rotation",
        "parallax",
        "particles",
        "webgl-background",
        "pointer-interaction",
    )
    assert plan.renderer == "native-webgl-bounded-v1"
    assert plan.fallback_mode == "static-2d"
    assert plan.reduced_motion_mode == "static-2d-no-continuous-animation"
    assert len(plan.plan_sha256) == 64


def test_compile_fails_closed_for_ordinary_web_app_without_explicit_3d() -> None:
    with pytest.raises(Web3DRuntimeError, match="does not explicitly require"):
        compile_web_3d_runtime_plan(
            "Build a Web App dashboard with login, tables, and analytics charts."
        )


def test_compile_fails_closed_when_surface_is_not_explicitly_web() -> None:
    with pytest.raises(Web3DRuntimeError, match="does not explicitly target a Web surface"):
        compile_web_3d_runtime_plan("Build an interactive 3D product presentation.")


def test_asset_metadata_is_bounded_and_immutable() -> None:
    asset = Web3DAssetRef(
        sha256="a" * 64,
        media_type="model/gltf-binary",
        byte_size=2_000_000,
        role="model",
    )
    plan = compile_web_3d_runtime_plan(
        "Build a website with a 3D product hero.",
        assets=(asset,),
    )

    assert plan.assets == (asset,)
    assert plan.assets[0].sha256 == "a" * 64

    with pytest.raises(Web3DRuntimeError, match="lowercase hexadecimal"):
        Web3DAssetRef(
            sha256="Z" * 64,
            media_type="model/gltf-binary",
            byte_size=2_000_000,
            role="model",
        )


def test_total_asset_budget_fails_closed() -> None:
    assets = tuple(
        Web3DAssetRef(
            sha256=f"{index:064x}",
            media_type="image/webp",
            byte_size=3 * 1024 * 1024,
            role="texture",
        )
        for index in range(12)
    )

    with pytest.raises(Web3DRuntimeError, match="32 MiB total budget"):
        compile_web_3d_runtime_plan(
            "Build a website with a 3D WebGL hero.",
            assets=assets,
        )


def test_native_webgl_artifact_is_deterministic_and_dependency_free() -> None:
    plan = compile_web_3d_runtime_plan(
        "Build a website with a 3D hero, scroll camera motion, and interactive mouse control."
    )
    first = render_native_webgl_artifact(plan)
    second = render_native_webgl_artifact(plan)

    assert first == second
    assert first.filename == "index.html"
    assert first.plan_sha256 == plan.plan_sha256
    assert len(first.source_sha256) == 64
    assert first.bundle_bytes <= plan.performance.max_bundle_bytes
    assert "getContext('webgl2'" in first.source
    assert "getContext('webgl'" in first.source
    assert "prefers-reduced-motion: reduce" in first.source
    assert "data-fallback" in first.source
    assert "requestAnimationFrame" in first.source
    assert "pointermove" in first.source
    assert "https://" not in first.source
    assert "<script src=" not in first.source
    assert "eval(" not in first.source


def test_native_webgl_artifact_uses_canonical_neutral_palette_only() -> None:
    plan = compile_web_3d_runtime_plan("Build a website with a 3D WebGL hero.")
    artifact = render_native_webgl_artifact(plan)
    source = artifact.source.lower()

    for canonical in ("#0a0a0a", "#141414", "#2a2a2a", "#b3b3b3", "#ffffff"):
        assert canonical in source

    for retired in (
        "#0b0f14",
        "#111827",
        "#334155",
        "#b8c2cc",
        "#00c2d1",
        "#146bff",
        "vec4(.0,.76,.82,1.0)",
    ):
        assert retired not in source


def test_turkish_explicit_3d_request_activates_optional_pack() -> None:
    plan = compile_web_3d_runtime_plan(
        "Koyu temalı bir web sitesi yap: 3D tanıtım alanı, scroll ile kamera hareketi, "
        "paralaks ve mouse etkileşimi olsun."
    )

    assert "3d-hero" in plan.features
    assert "scroll-camera" in plan.features
    assert "parallax" in plan.features
    assert "pointer-interaction" in plan.features
