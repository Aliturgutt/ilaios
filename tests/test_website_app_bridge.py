from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHROME = ROOT / "apps" / "website" / "app" / "SiteChrome.tsx"
USE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"
SIGN_IN = ROOT / "apps" / "website" / "app" / "SignInPage.tsx"


def test_public_header_exposes_canonical_app_handoff_without_duplicating_auth() -> None:
    chrome = CHROME.read_text(encoding="utf-8")

    assert 'const APP_ORIGIN = "https://app.ilaios.com"' in chrome
    assert 'href={`${APP_ORIGIN}/?lang=${lang}`}' in chrome
    assert '{isTr ? "Uygulama" : "App"}' in chrome


def test_contact_remains_available_after_app_handoff_uses_existing_header_slot() -> None:
    chrome = CHROME.read_text(encoding="utf-8")

    assert '["Contact", "/contact"]' in chrome
    assert '["İletişim", "/tr/contact"]' in chrome


def test_use_ilaios_hands_product_and_plan_actions_to_canonical_app_surfaces() -> None:
    use_page = USE.read_text(encoding="utf-8")

    assert 'const APP_ORIGIN = "https://app.ilaios.com"' in use_page
    assert 'href={`${APP_ORIGIN}/?lang=${locale}`}' in use_page
    assert 'href={`${APP_ORIGIN}/subscription?lang=${locale}`}' in use_page
    assert 'openApp: "Open ILAIOS App"' in use_page
    assert 'openApp: "ILAIOS Uygulamasını Aç"' in use_page


def test_website_sign_in_delegates_provider_authentication_to_app_runtime() -> None:
    sign_in = SIGN_IN.read_text(encoding="utf-8")

    assert 'const APP_ORIGIN = "https://app.ilaios.com"' in sign_in
    assert '${APP_ORIGIN}/auth/google/start' in sign_in
    assert '${APP_ORIGIN}/auth/microsoft/start' in sign_in
    assert '${APP_ORIGIN}/auth/github/start' in sign_in
