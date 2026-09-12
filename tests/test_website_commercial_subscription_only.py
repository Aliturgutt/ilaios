from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_customer_model_is_subscription_with_upgrade_path() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "monthly subscription model" in content
    assert "aylık aboneliktir" in content
    assert "upgrade" in content
    assert "üst plana" in content
