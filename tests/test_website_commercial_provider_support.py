from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_enterprise_keeps_provider_policy_caveat() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "Provider support and commercial policy still apply" in content
    assert "Provider desteği ve commercial policy şarttır" in content
