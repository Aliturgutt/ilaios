from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "apps" / "website" / "app" / "layout.tsx"
TOGGLE = ROOT / "apps" / "website" / "app" / "ThemeToggle.tsx"


def test_website_defaults_to_light_without_overriding_explicit_choice() -> None:
    layout = LAYOUT.read_text(encoding="utf-8")
    toggle = TOGGLE.read_text(encoding="utf-8")

    assert 'const theme = stored === "light" || stored === "dark" ? stored : "light";' in layout
    assert 'document.documentElement.dataset.theme = "light"' in layout
    assert 'document.documentElement.style.colorScheme = "light"' in layout
    assert 'localStorage.setItem(STORAGE_KEY, next)' in toggle


def test_website_default_theme_does_not_follow_system_dark_mode() -> None:
    layout = LAYOUT.read_text(encoding="utf-8")

    assert "prefers-color-scheme" not in layout
