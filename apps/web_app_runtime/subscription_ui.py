"""Subscription HTML presentation using the canonical plan catalog."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import cast

from services.subscription_presentation import plan_catalog

_ASSETS = Path(__file__).with_name("subscription_assets")


def subscription_asset(name: str) -> bytes:
    if name not in {"styles.css", "app.js"}:
        raise ValueError("unknown subscription asset")
    return (_ASSETS / name).read_bytes()


def render_subscription(locale: str) -> bytes:
    catalog = plan_catalog(locale)
    tr = locale == "tr"

    def copy(en: str, turkish: str) -> str:
        return turkish if tr else en

    def value(item: object) -> str:
        return escape(str(item)) if item is not None else copy("Contract", "Sözleşmeye özel")

    plans = cast(list[dict[str, object]], catalog["plans"])
    cards: list[str] = []
    rows: list[str] = []
    for plan in plans:
        plan_id = str(plan["plan_id"])
        if plan["price_kind"] == "custom":
            price = copy("Custom quote", "Özel teklif")
        elif plan["monthly_price"] is None:
            price = copy("Price pending", "Fiyat bekleniyor")
        elif plan["monthly_price"] == 0:
            price = copy("Free", "Ücretsiz")
        elif catalog["currency"] == "TRY":
            monthly_price = cast(int, plan["monthly_price"])
            price = f"{monthly_price:,}".replace(",", ".") + " TL / ay"
        else:
            price = f'${plan["monthly_price"]} / month'
        parent = plan["parent"]
        inheritance = (
            copy("Start with included usage", "Dahil kullanımla başlayın")
            if parent is None
            else f'{parent} {copy("features included", "özellikleri dahil")}'
        )
        if plan["free_video_requires_verified_zero_cost"]:
            video = copy(
                "Video when a verified zero-cost option is available.",
                "Video, doğrulanmış sıfır maliyetli seçenek bulunduğunda kullanılabilir.",
            )
        elif plan["enterprise_custom_video_budget"]:
            video = copy("Contract-specific video capacity", "Sözleşmeye özel video kapasitesi")
            video += f' · {value(plan["max_video_resolution"])} '
            video += copy(
                "ceiling, subject to provider and policy support.",
                "üst sınırı; sağlayıcı ve politika desteğine bağlıdır.",
            )
        else:
            video = (
                f'{plan["video_pool_minutes"]} '
                + copy(
                    "min/month Mini 480p-equivalent shared pool",
                    "dk/ay Mini 480p eşdeğeri ortak havuz",
                )
                + f' · {copy("Up to", "En fazla")} {plan["max_video_resolution"]}'
            )
        limits = ""
        if plan_id != "ENTERPRISE":
            limits = (
                '<ul class="plan-facts">'
                f'<li><strong>{value(plan["max_active_projects"])}</strong> {copy("projects", "proje")}</li>'
                f'<li><strong>{value(plan["max_active_automations"])}</strong> {copy("automations", "otomasyon")}</li>'
                f'<li><strong>{value(plan["storage_limit_gb"])}</strong> GB {copy("storage", "depolama")}</li>'
                f'<li><strong>{value(plan["max_concurrent_jobs"])}</strong> {copy("concurrent jobs", "eşzamanlı iş")}</li>'
                "</ul>"
            )
        else:
            limits = f'<p class="enterprise-note">{copy("Capacity and workspace limits are defined by contract.", "Kapasite ve çalışma alanı limitleri sözleşmeyle belirlenir.")}</p>'
        button = (
            f'<a class="button" href="mailto:contact@ilaios.com">{copy("Request a quote", "Teklif iste")}</a>'
            if plan["price_kind"] == "custom"
            else f'<button class="button" type="button" data-plan="{plan_id}" data-price="{escape(price)}">{copy("View plan", "Planı incele")}</button>'
        )
        popular = f'<span class="plan-badge">{copy("Recommended", "Önerilen")}</span>' if plan_id == "POWER" else ""
        cards.append(
            f'<article class="plan plan-{plan_id.lower()}" aria-labelledby="plan-{plan_id}">{popular}'
            f'<h3 id="plan-{plan_id}">{plan_id.title()}</h3><p class="price">{escape(price)}</p>'
            f'<p class="muted">{inheritance}</p><p class="video">{video}</p>{limits}{button}</article>'
        )

    model_cells: list[str] = []
    for plan in plans:
        if plan["free_video_requires_verified_zero_cost"]:
            models = copy("Verified free options only", "Yalnız doğrulanmış ücretsiz seçenekler")
        else:
            names = cast(list[str], plan["video_models"])
            models = ", ".join(
                copy("Contract-approved options", "Sözleşmeyle izinli seçenekler")
                if name == "contract-allowlisted-models"
                else name
                for name in names
            )
        model_cells.append(f"<td>{escape(models)}</td>")
    rows.append(
        f'<tr><th scope="row">{copy("Video models", "Video modelleri")}</th>'
        + "".join(model_cells)
        + "</tr>"
    )
    for key, en, turkish in [
        ("max_active_projects", "Active projects", "Aktif proje"),
        ("max_active_automations", "Active automations", "Aktif otomasyon"),
        ("automation_runs_per_month", "Automation runs / month", "Otomasyon çalıştırma / ay"),
        ("storage_limit_gb", "Storage (GB)", "Depolama (GB)"),
        ("workspace_users", "Workspace users", "Çalışma alanı kullanıcısı"),
        ("max_concurrent_jobs", "Concurrent jobs", "Eşzamanlı iş"),
    ]:
        rows.append(
            f'<tr><th scope="row">{copy(en, turkish)}</th>'
            + "".join(f'<td>{value(p[key])}</td>' for p in plans)
            + "</tr>"
        )

    title = copy("Plans & subscription", "Planlar ve abonelik")
    html = f'''<!doctype html>
<html lang="{locale}" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark">
<title>{escape(title)} | ILAIOS</title><link rel="stylesheet" href="/login/styles.css">
<link rel="stylesheet" href="/subscription/styles.css"></head><body>
<header class="page-header"><a href="/?lang={locale}" aria-label="ILAIOS">
<img class="brand-image-light" src="/login/brand-light.jpg" alt="ILAIOS">
<img class="brand-image-dark" src="/login/brand-dark.jpg" alt="ILAIOS"></a>
<nav class="preferences" aria-label="{copy('Preferences', 'Tercihler')}">
<button class="theme-control" id="subscription-theme" type="button" aria-pressed="false"><span class="theme-icon" aria-hidden="true">◐</span><span id="theme-label">{copy('Theme', 'Tema')}</span></button>
<div class="language-control" aria-label="{copy('Language', 'Dil')}"><a href="?lang=en" lang="en" class="{'active' if not tr else ''}">EN</a><a href="?lang=tr" lang="tr" class="{'active' if tr else ''}">TR</a></div></nav></header>
<main class="subscription-shell"><div class="eyebrow">ILAIOS / {copy('YOUR ACCOUNT', 'HESABINIZ')}</div>
<h1>{escape(title)}</h1><p class="lead">{copy('One account. Included capacity across ILAIOS App and Desktop.', 'Tek hesap. ILAIOS App ve Desktop boyunca planınıza dahil kapasite.')}</p>
<section class="value-strip" aria-label="{copy('Platform value', 'Platform kapsamı')}"><strong>{copy('9 production factories', '9 üretim fabrikası')}</strong><span>{copy('One subscription authority', 'Tek abonelik yetkisi')}</span><span>{copy('No automatic overage charges', 'Otomatik limit aşımı ücreti yok')}</span></section>
<section class="current" aria-labelledby="current-title"><div><h2 id="current-title">{copy('Current plan', 'Mevcut plan')}</h2>
<p id="current-plan" role="status">{copy('Loading subscription…', 'Abonelik bilgisi yükleniyor…')}</p>
<p id="period" class="muted"></p><p id="usage" class="muted">{copy('Remaining usage is not available yet.', 'Kalan kullanım bilgisi henüz alınamıyor.')}</p></div>
<div><a id="sign-in" class="button" href="/?lang={locale}">{copy('Sign in', 'Giriş yap')}</a>
<a href="mailto:support@ilaios.com" class="support-link">{copy('Subscription support', 'Abonelik desteği')}</a></div></section>
<section aria-labelledby="plans-title"><div class="section-heading"><h2 id="plans-title">{copy('Choose your plan', 'Planınızı seçin')}</h2><span>{copy('Monthly plans · USD', 'Aylık planlar · TL')}</span></div>
<div class="plans">{''.join(cards)}</div>
<p class="note">{copy('Model and quality choices use the same video pool at different rates. These are not separate model allowances.', 'Model ve kalite seçimi aynı video havuzunu farklı hızlarda tüketir. Süreler model başına ayrı haklar değildir.')}</p>
<p class="note payment-note">{copy('Payment is not available yet. No charge or automatic plan change will occur.', 'Ödeme henüz kullanılamıyor. Tahsilat veya otomatik plan değişikliği yapılmaz.')}</p></section>
<section aria-labelledby="comparison-title"><h2 id="comparison-title">{copy('Compare included usage', 'Dahil kullanımı karşılaştırın')}</h2>
<div class="table-scroll" role="region" aria-labelledby="comparison-title" tabindex="0"><table><thead><tr><th scope="col">{copy('Feature', 'Özellik')}</th>{''.join('<th scope="col">'+str(p['plan_id']).title()+'</th>' for p in plans)}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="note">{copy('Enterprise limits are contract-specific.', 'Enterprise limitleri sözleşmeye özeldir.')}</p></section>
<section class="management"><h2>{copy('Manage subscription', 'Aboneliği yönet')}</h2><p class="muted">{copy('Renewal, cancellation and plan changes are not available yet. Contact support for assistance.', 'Yenileme, iptal ve plan değişikliği işlemleri henüz kullanılamıyor. Yardım için desteğe ulaşın.')}</p>
<div class="actions"><button disabled>{copy('Upgrade', 'Plan yükselt')}</button><button disabled>{copy('Downgrade', 'Plan düşür')}</button><button disabled>{copy('Cancel subscription', 'Aboneliği iptal et')}</button></div></section>
<footer><p>{copy('Seller', 'Satıcı')}: Ali Turgut</p><a href="mailto:support@ilaios.com">{copy('Support', 'Destek')}</a> · <a href="mailto:privacy@ilaios.com">{copy('Privacy enquiries', 'Gizlilik talepleri')}</a> · <a href="mailto:contact@ilaios.com">{copy('Contact', 'İletişim')}</a></footer></main>
<dialog id="checkout" aria-labelledby="checkout-title"><h2 id="checkout-title">{copy('Plan summary', 'Plan özeti')}</h2><p id="selected-plan"></p><p id="selected-price"></p>
<p>{copy('Final payable amount is not available. Payment cannot begin yet.', 'Ödenecek kesin tutar henüz mevcut değil. Ödeme şu anda başlatılamaz.')}</p>
<p>{copy('Sales terms and cancellation conditions will be provided before payment becomes available.', 'Ödeme açılmadan önce satış sözleşmesi ve iptal koşulları sunulacaktır.')}</p>
<a href="mailto:privacy@ilaios.com">{copy('Privacy enquiries', 'Gizlilik talepleri')}</a>
<div class="actions"><button type="button" disabled>{copy('Proceed to payment', 'Ödemeye devam et')}</button><button type="button" id="close-checkout">{copy('Close', 'Kapat')}</button></div></dialog>
<script src="/subscription/app.js" defer></script></body></html>'''
    return html.encode("utf-8")
