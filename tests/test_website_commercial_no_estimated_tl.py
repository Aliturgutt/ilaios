from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_paid_tl_prices_fail_closed_until_canonical_tl_authority_exists() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert '≈ 2.495 TL / ay' not in content
    assert '≈ 5.040 TL / ay' not in content
    assert '≈ 10.130 TL / ay' not in content
    assert content.count('price: "TL fiyatı ödeme öncesinde gösterilir"') == 3
