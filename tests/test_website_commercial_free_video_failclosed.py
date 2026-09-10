from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_free_video_has_no_fixed_paid_video_promise() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "verified $0 provider/model route" in content
    assert "no fixed paid-video minutes or resolution" in content
