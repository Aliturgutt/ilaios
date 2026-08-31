from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "apps" / "website" / "app" / "SignInPage.tsx"
STYLES = ROOT / "apps" / "website" / "app" / "SignInPage.module.css"
EN_ROUTE = ROOT / "apps" / "website" / "app" / "sign-in" / "page.tsx"
TR_ROUTE = ROOT / "apps" / "website" / "app" / "tr" / "sign-in" / "page.tsx"


def test_signin_surface_is_scoped_and_bilingual() -> None:
    assert COMPONENT.is_file()
    assert STYLES.is_file()
    assert EN_ROUTE.is_file()
    assert TR_ROUTE.is_file()

    component = COMPONENT.read_text(encoding="utf-8")
    assert "SignInPage.module.css" in component
    assert "Continue with Google" in component
    assert "Microsoft ile devam et" in component


def test_signin_surface_uses_existing_production_auth_routes_only() -> None:
    component = COMPONENT.read_text(encoding="utf-8")

    assert 'const APP_ORIGIN = "https://app.ilaios.com";' in component
    assert "/auth/google/start" in component
    assert "/auth/microsoft/start" in component
    assert "/auth/github/start" in component
    assert "/auth/link/" not in component


def test_signin_routes_are_not_indexed_while_auth_closure_is_in_progress() -> None:
    for route in (EN_ROUTE, TR_ROUTE):
        source = route.read_text(encoding="utf-8")
        assert "robots: { index: false, follow: false }" in source
