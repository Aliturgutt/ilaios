from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_no_hidden_automatic_overage_language() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "no hidden automatic overage" in content
    assert "gizli otomatik aşım ücreti yoktur" in content
