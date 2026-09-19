from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.integrations.web_factory import GovernedWebFactory, derive_website_spec
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy

_WEB3D_FEATURES = {
    "3d-hero",
    "scroll-camera",
    "product-rotation",
    "parallax",
    "particles",
    "webgl-background",
    "3d-typography",
    "pointer-interaction",
}


def _grant(now: datetime, site_id: str) -> ExecutionGrant:
    return ExecutionGrant(
        "web3d-factory-grant",
        "web-worker",
        frozenset({"web.build"}),
        frozenset({site_id}),
        now + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def test_governed_web_factory_wires_explicit_3d_request(tmp_path: Path) -> None:
    objective = (
        "Build a premium website with a 3D hero, scroll-driven camera motion, "
        "interactive product model rotation, parallax, particles, a WebGL background, "
        "3D typography, and touch interaction."
    )
    spec = derive_website_spec("web3d-factory", objective)
    assert _WEB3D_FEATURES <= set(spec.features)

    now = datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc)
    acceptance = GovernedWebFactory(
        GrantPolicy(), tmp_path / "artifacts"
    ).build_generated_site(
        spec,
        grant=_grant(now, spec.site_id),
        now=now,
    )

    bundle = Path(acceptance.bundle_path)
    assert acceptance.accepted is True
    assert (bundle / "assets/3d/index.html").is_file()
    home = (bundle / "en/index.html").read_text(encoding="utf-8")
    assert 'class="ilaios-web3d-frame"' in home
    assert 'sandbox="allow-scripts"' in home
    assert 'referrerpolicy="no-referrer"' in home

    manifest = json.loads((bundle / "acceptance.json").read_text(encoding="utf-8"))
    qa = manifest["qa"]
    assert isinstance(qa, dict)
    web3d = qa["web3d"]
    assert isinstance(web3d, dict)
    assert web3d["status"] == "SOURCE_INTEGRATED_NOT_BROWSER_CERTIFIED"
    assert web3d["runtime_path"] == "assets/3d/index.html"
    assert len(web3d["plan_sha256"]) == 64
    assert set(web3d["features"]) == _WEB3D_FEATURES


def test_governed_web_factory_keeps_ordinary_site_without_3d(tmp_path: Path) -> None:
    spec = derive_website_spec(
        "ordinary-factory",
        "Build a premium website for a corporate law firm.",
    )
    assert not _WEB3D_FEATURES.intersection(spec.features)

    now = datetime(2026, 8, 30, 0, 1, tzinfo=timezone.utc)
    acceptance = GovernedWebFactory(
        GrantPolicy(), tmp_path / "ordinary-artifacts"
    ).build_generated_site(
        spec,
        grant=_grant(now, spec.site_id),
        now=now,
    )

    bundle = Path(acceptance.bundle_path)
    assert acceptance.accepted is True
    assert not (bundle / "assets/3d/index.html").exists()
    manifest = json.loads((bundle / "acceptance.json").read_text(encoding="utf-8"))
    qa = manifest["qa"]
    assert isinstance(qa, dict)
    assert "web3d" not in qa
