from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_payment_provider_name_is_not_public_copy() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "PayTR" not in content
