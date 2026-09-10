from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_commercial_surface_states_digital_delivery_channels() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "app.ilaios.com" in content
    assert "ILAIOS Desktop" in content
    assert "physical goods" in content
    assert "fiziksel ürün" in content.lower()
