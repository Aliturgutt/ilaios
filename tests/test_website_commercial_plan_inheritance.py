from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_plan_inheritance_is_visible() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "Includes the Free plan scope" in content
    assert "Includes Pro + Free scope" in content
    assert "Includes Business + Pro + Free scope" in content
    assert "Includes the Power plan foundation" in content
