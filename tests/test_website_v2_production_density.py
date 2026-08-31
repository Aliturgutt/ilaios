from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "apps" / "website" / "app" / "HomePage.tsx"
CHROME = ROOT / "apps" / "website" / "app" / "SiteChrome.tsx"
V2_CSS = ROOT / "apps" / "website" / "app" / "website-v2.css"
CERT_CSS = ROOT / "apps" / "website" / "app" / "production-density-cert.css"


def test_canonical_homepage_keeps_production_density_bounds() -> None:
    source = HOME.read_text(encoding="utf-8")
    v2_css = V2_CSS.read_text(encoding="utf-8")
    cert_css = CERT_CSS.read_text(encoding="utf-8")

    assert 'data-visual-role="homepage-v2-authoritative"' in source
    assert ".home-hero {" in v2_css
    assert "main section[class] {" in cert_css
    assert "padding-top: 48px !important;" in cert_css
    assert "padding-bottom: 48px !important;" in cert_css
    assert "@media (max-width: 899px)" in cert_css
    assert "padding-top: 32px !important;" in cert_css
    assert "padding-bottom: 32px !important;" in cert_css
    assert "font-size: clamp(2.2rem, 3.35vw, 3rem) !important;" in cert_css


def test_shared_footer_keeps_compact_production_density() -> None:
    source = CHROME.read_text(encoding="utf-8")
    v2_css = V2_CSS.read_text(encoding="utf-8")

    assert '<footer className="site-footer"' in source
    assert '<div className="shell footer-main">' in source
    assert '<div className="shell footer-row">' in source
    assert ".site-footer {" in v2_css
    assert "padding-top: 52px !important;" in v2_css
    assert ".footer-main { gap: 58px !important; padding-bottom: 42px !important; }" in v2_css
    assert ".footer-row { padding-top: 20px !important;" in v2_css
