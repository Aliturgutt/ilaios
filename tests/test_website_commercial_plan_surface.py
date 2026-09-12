from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_public_commercial_surface_lists_canonical_plan_family_and_usd_prices() -> None:
    content = SURFACE.read_text(encoding="utf-8")

    ordered = [
        'name: "Free"',
        'name: "Pro"',
        'name: "Business"',
        'name: "Power"',
        'name: "Enterprise"',
    ]
    positions = [content.index(value) for value in ordered]
    assert positions == sorted(positions)

    for value in (
        '$49 / month',
        '$99 / month',
        '$199 / month',
        '0 TL',
        'Özel sözleşme',
    ):
        assert value in content

    for stale_tl_price in (
        '≈ 2.495 TL / ay',
        '≈ 5.040 TL / ay',
        '≈ 10.130 TL / ay',
        'başlangıç ticari referansı',
    ):
        assert stale_tl_price not in content


def test_public_commercial_surface_matches_canonical_video_hierarchy() -> None:
    content = SURFACE.read_text(encoding="utf-8")

    for value in (
        'Seedance 2.0 Mini',
        '20 min/month shared Mini 480p-equivalent video pool',
        'Maximum plan video quality: 480p',
        '30 min/month shared Mini 480p-equivalent video pool',
        'Maximum plan video quality: 720p',
        '50 min/month shared Mini 480p-equivalent video pool',
        'Maximum plan video quality: 1080p',
        'Maximum plan video quality: 4K',
        'Ayda 20 dk ortak Mini 480p-eşdeğer video havuzu',
        'Maksimum plan video kalitesi: 480p',
        'Ayda 30 dk ortak Mini 480p-eşdeğer video havuzu',
        'Maksimum plan video kalitesi: 720p',
        'Ayda 50 dk ortak Mini 480p-eşdeğer video havuzu',
        'Maksimum plan video kalitesi: 1080p',
        'Maksimum plan video kalitesi: 4K',
        'one shared pool',
        'tek ortak havuz',
    ):
        assert value in content

    assert '50 minutes at 1080p' not in content
    assert '50 dakika 1080p vaadi değildir' in content


def test_public_commercial_surface_explains_subscription_without_legacy_job_billing() -> None:
    content = SURFACE.read_text(encoding="utf-8")

    assert 'id="plans"' in content
    assert 'paymentEyebrow: "Subscription model"' in content
    assert 'paymentEyebrow: "Abonelik modeli"' in content
    assert 'monthly subscription model' in content
    assert 'aylık aboneliktir' in content
    assert 'upgrade rather than receive automatic extra charges' in content
    assert 'otomatik ek ücret yerine normal yol üst plana geçmektir' in content
    assert 'physical goods' in content
    assert 'Fiziksel ürün yok' in content
    assert 'app.ilaios.com' in content
    assert 'ILAIOS Desktop' in content

    for forbidden in (
        'Exceptional one-off work',
        'Olağanüstü tek seferlik iş',
        'separate high-cost job',
        'ayrı yüksek maliyetli bir iş',
        'specific quote',
        'token pack',
        'kredi paketi',
        'routine per-job',
        'rutin işlem başına',
    ):
        assert forbidden not in content


def test_public_commercial_surface_fails_closed_for_unknown_paid_tl_prices() -> None:
    content = SURFACE.read_text(encoding="utf-8")

    assert content.count('price: "TL fiyatı ödeme öncesinde gösterilir"') == 3
    assert 'canonical TL price is configured' in content
    assert 'canonical authority henüz yapılandırılmadığından tahmini TL tutarı gösterilmez' in content


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
