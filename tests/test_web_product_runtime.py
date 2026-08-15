"""Finished-product Web Factory tests including real headless-browser rendering in CI."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.integrations import GovernedWebFactory, derive_website_spec
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy


def _grant(site_id: str, now: datetime) -> ExecutionGrant:
    return ExecutionGrant(
        "web-generated-grant",
        "web-worker",
        frozenset({"web.build"}),
        frozenset({site_id}),
        now + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def test_generated_site_is_context_derived_bilingual_and_tamper_evident(tmp_path: Path) -> None:
    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)
    objective = (
        "Create a premium bilingual Turkish/English website for a professional "
        "law firm focused on corporate clients, with contact conversion, strong "
        "trust presentation and responsive mobile design."
    )
    spec = derive_website_spec("web-e2e-law", objective)
    assert spec.business_category == "law firm"
    assert spec.locales == ("en", "tr")
    assert spec.pages == ("home", "expertise", "about", "contact")

    factory = GovernedWebFactory(GrantPolicy(), tmp_path / "artifacts")
    result = factory.build_generated_site(spec, grant=_grant(spec.site_id, now), now=now)
    assert result.accepted is True
    assert result.spec_hash
    assert result.qa is not None
    assert result.qa["passed"] is True
    assert result.qa["deployment_state"] == "NOT_DEPLOYED"
    assert result.design_strategy is not None
    assert result.design_strategy["primary_composition"] == "minimal-institutional"
    assert len(result.routes) == 8

    bundle = Path(result.bundle_path)
    home = (bundle / "en" / "index.html").read_text(encoding="utf-8")
    assert "Lorem ipsum" not in home
    assert "Content-Security-Policy" in home
    assert 'class="skip-link"' in home
    assert "Counsel for decisions" in home

    (bundle / "en" / "index.html").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="tampered"):
        GovernedWebFactory(GrantPolicy(), tmp_path / "artifacts").build_generated_site(
            spec,
            grant=_grant(spec.site_id, now),
            now=now,
        )


def test_design_strategy_differs_for_visual_business_context(tmp_path: Path) -> None:
    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)
    spec = derive_website_spec(
        "web-e2e-furniture",
        "Build a premium website for a furniture company with a visual collection.",
    )
    result = GovernedWebFactory(GrantPolicy(), tmp_path / "artifacts").build_generated_site(
        spec,
        grant=_grant(spec.site_id, now),
        now=now,
    )
    assert result.design_strategy is not None
    assert result.design_strategy["primary_composition"] == "editorial-split"
    assert "collection" in result.required_pages
    assert "assets/site.css" in {row.relative_path for row in result.files}


@pytest.mark.parametrize(
    ("request_id", "objective"),
    (
        ("web-e2e-saas", "Build a website for a SaaS software company serving enterprise teams."),
        ("web-e2e-restaurant", "Build a visual website for a premium restaurant."),
        ("web-e2e-health", "Build a trusted website for a healthcare clinic."),
    ),
)
def test_generated_site_accepts_multiple_context_specific_compositions(
    tmp_path: Path,
    request_id: str,
    objective: str,
) -> None:
    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)
    spec = derive_website_spec(request_id, objective)
    result = GovernedWebFactory(GrantPolicy(), tmp_path / request_id).build_generated_site(
        spec,
        grant=_grant(spec.site_id, now),
        now=now,
    )
    assert result.accepted is True
    assert result.design_strategy is not None
    assert result.qa is not None and result.qa["passed"] is True


def test_generated_site_renders_in_real_headless_browser_at_required_viewports(tmp_path: Path) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome is None:
        if os.environ.get("CI"):
            pytest.fail("CI must provide Chromium/Chrome for Web Factory browser evidence")
        pytest.skip("local Chrome/Chromium is unavailable")

    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)
    spec = derive_website_spec(
        "web-browser-e2e",
        "Create a bilingual Turkish/English website for a corporate security company.",
    )
    result = GovernedWebFactory(GrantPolicy(), tmp_path / "artifacts").build_generated_site(
        spec,
        grant=_grant(spec.site_id, now),
        now=now,
    )
    page = (Path(result.bundle_path) / "en" / "index.html").resolve().as_uri()
    for width in (320, 360, 390, 412, 430, 768, 1024, 1440):
        screenshot = tmp_path / f"web-{width}.png"
        completed = subprocess.run(
            [
                chrome,
                "--headless=new",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                f"--window-size={width},900",
                f"--screenshot={screenshot}",
                page,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr
        assert screenshot.is_file()
        assert screenshot.stat().st_size > 1000
