from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "apps" / "website" / "app" / "HomePage.tsx"
CHROME = ROOT / "apps" / "website" / "app" / "SiteChrome.tsx"


def test_canonical_homepage_keeps_production_density_bounds() -> None:
    source = HOME.read_text(encoding="utf-8")

    assert 'data-visual-role="homepage-v2-authoritative"' in source
    assert 'style={{ paddingTop: "32px", paddingBottom: "32px" }}' in source
    assert 'style={{ paddingTop: "48px", paddingBottom: "48px" }}' not in source
    assert 'fontSize: "clamp(2.2rem, 3.35vw, 3rem)"' in source


def test_shared_footer_keeps_compact_production_density() -> None:
    source = CHROME.read_text(encoding="utf-8")

    assert '<footer className="site-footer"' in source
    assert 'style={{ paddingTop: "24px", paddingBottom: "24px" }}' in source
    assert 'style={{ paddingTop: 0, paddingBottom: "20px", gap: "28px" }}' in source
