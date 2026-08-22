from __future__ import annotations

import pytest

from services.web_3d_integration import (
    Web3DIntegrationError,
    integrate_web_3d_into_generated_content,
)
from services.web_3d_runtime import Web3DRuntimePlan, compile_web_3d_runtime_plan


def _content() -> dict[str, bytes]:
    return {
        "en/index.html": (
            '<!doctype html><html><body><main id="main">'
            "<h1>Product</h1></main></body></html>"
        ).encode(),
        "en/contact.html": b"<!doctype html><html><body>Contact</body></html>",
        "assets/site.css": b":root{--muted:#475467}\nbody{margin:0}\n",
    }


def _plan() -> Web3DRuntimePlan:
    return compile_web_3d_runtime_plan(
        "Build a premium website with a 3D hero, scroll camera motion, "
        "interactive product rotation, and WebGL."
    )


def test_integration_adds_sandboxed_same_origin_runtime() -> None:
    original = _content()
    result = integrate_web_3d_into_generated_content(
        original,
        _plan(),
        home_routes=("en/index.html",),
    )

    assert result.runtime_path == "assets/3d/index.html"
    assert result.plan_sha256 == _plan().plan_sha256
    assert len(result.runtime_source_sha256) == 64
    assert len(result.bundle_sha256) == 64
    assert original["en/index.html"] != result.content["en/index.html"]
    assert original["en/contact.html"] == result.content["en/contact.html"]

    home = result.content["en/index.html"].decode()
    runtime = result.content["assets/3d/index.html"].decode()
    assert 'src="../assets/3d/index.html"' in home
    assert 'sandbox="allow-scripts"' in home
    assert 'referrerpolicy="no-referrer"' in home
    assert "equivalent page content remains available" in home
    assert "https://" not in runtime
    assert "<script src=" not in runtime


def test_integration_is_deterministic_and_binds_plan_hash() -> None:
    first = integrate_web_3d_into_generated_content(
        _content(),
        _plan(),
        home_routes=("en/index.html",),
    )
    second = integrate_web_3d_into_generated_content(
        _content(),
        _plan(),
        home_routes=("en/index.html",),
    )

    assert first == second
    assert first.bundle_sha256 == second.bundle_sha256
    assert f'data-plan-sha="{_plan().plan_sha256}"' in first.content[
        "en/index.html"
    ].decode()


def test_integration_fails_closed_for_missing_home_route() -> None:
    with pytest.raises(Web3DIntegrationError, match="home route is missing"):
        integrate_web_3d_into_generated_content(
            _content(),
            _plan(),
            home_routes=("tr/index.html",),
        )


def test_integration_fails_closed_for_non_home_target() -> None:
    with pytest.raises(Web3DIntegrationError, match="home index routes"):
        integrate_web_3d_into_generated_content(
            _content(),
            _plan(),
            home_routes=("en/contact.html",),
        )


def test_integration_fails_closed_for_runtime_path_collision() -> None:
    content = _content()
    content["assets/3d/index.html"] = b"tampered"
    with pytest.raises(Web3DIntegrationError, match="conflicting content"):
        integrate_web_3d_into_generated_content(
            content,
            _plan(),
            home_routes=("en/index.html",),
        )


def test_integration_requires_canonical_main_marker() -> None:
    content = _content()
    content["en/index.html"] = b"<!doctype html><html><body>No main marker</body></html>"
    with pytest.raises(Web3DIntegrationError, match="canonical main marker"):
        integrate_web_3d_into_generated_content(
            content,
            _plan(),
            home_routes=("en/index.html",),
        )


def test_stylesheet_gets_responsive_and_reduced_motion_rules() -> None:
    result = integrate_web_3d_into_generated_content(
        _content(),
        _plan(),
        home_routes=("en/index.html",),
    )
    css = result.content["assets/site.css"].decode()

    assert ".ilaios-web3d-frame" in css
    assert "@media (max-width:720px)" in css
    assert "@media (prefers-reduced-motion:reduce)" in css
