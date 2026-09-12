from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_public_commercial_surface_lists_launch_plan_family_and_prices() -> None:
    content = SURFACE.read_text(encoding="utf-8")

    for value in (
        'name: "Free"',
        'name: "Pro"',
        'name: "Business"',
        'name: "Power"',
        'name: "Enterprise"',
        '$49 / month',
        '$99 / month',
        '$199 / month',
        '0 TL/ay',
        '2.401 TL/ay',
        '4.851 TL/ay',
        '9.751 TL/ay',
        'Sözleşmeye özel',
        'Proje, otomasyon ve eşzamanlı iş: sözleşmeye özel',
    ):
        assert value in content


def test_public_commercial_surface_explains_subscription_and_verified_payment_flow() -> None:
    content = SURFACE.read_text(encoding="utf-8")

    assert 'id="plans"' in content
    assert 'paymentEyebrow: "How payment works"' in content
    assert 'paymentEyebrow: "Ödeme nasıl çalışır?"' in content
    assert 'Verified payment activates access' in content
    assert 'Doğrulanmış ödeme erişimi açar' in content
    assert 'Exceptional one-off work' in content
    assert 'Olağanüstü tek seferlik iş' in content


def test_public_commercial_surface_does_not_expose_payment_provider_or_internal_accounting() -> None:
    content = SURFACE.read_text(encoding="utf-8")

    for forbidden in (
        "PayTR",
        "microusd",
        "provider ledger",
        "kâr marjı",
        "profit margin",
        "CPU maliyeti",
        "internal provider budget",
    ):
        assert forbidden not in content
