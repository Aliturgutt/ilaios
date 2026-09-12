from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_site_does_not_claim_checkout_is_already_active() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "when paid checkout is available" in content
    assert "Ücretli checkout kullanıma açıldığında" in content
    assert "PayTR ile şimdi öde" not in content
    assert "ödeme sistemi aktif" not in content
