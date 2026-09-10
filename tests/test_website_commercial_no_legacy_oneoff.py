from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_website_has_no_legacy_one_off_customer_billing_language() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    for forbidden in (
        "Exceptional one-off work",
        "Olağanüstü tek seferlik iş",
        "separate high-cost job",
        "specific quote",
        "ayrı yüksek maliyetli bir iş",
        "token pack",
        "kredi paketi",
    ):
        assert forbidden not in content
