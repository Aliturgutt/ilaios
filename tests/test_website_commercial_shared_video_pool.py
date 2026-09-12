from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_video_minutes_are_presented_as_shared_equivalent_pools() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "one shared pool" in content
    assert "tek ortak havuz" in content
    assert "50 minutes at 1080p" not in content
    assert "50 dakika 1080p vaadi değildir" in content
