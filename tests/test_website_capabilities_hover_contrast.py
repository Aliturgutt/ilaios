from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES = ROOT / "apps" / "website" / "app" / "CapabilitiesPage.tsx"
TUNING = ROOT / "apps" / "website" / "app" / "website-v2-tuning.css"
VISUAL_FIXES = ROOT / "apps" / "website" / "app" / "visual-audit-fixes.css"


def test_light_capability_cards_do_not_inherit_white_text_from_legacy_dark_surface_rule() -> None:
    capabilities = CAPABILITIES.read_text(encoding="utf-8")
    tuning = TUNING.read_text(encoding="utf-8")
    visual_fixes = VISUAL_FIXES.read_text(encoding="utf-8")

    assert 'className="card dark-surface"' in capabilities
    assert 'html[data-theme="light"] :where(.dark-surface, a.dark-surface, .card.dark-surface)' in visual_fixes
    assert 'background: #FFFFFF !important;' in visual_fixes

    legacy_selector = 'html[data-theme="light"] main :where(.evidence-control.is-active,.dark-surface,[data-surface="dark"])'
    fixed_selector = 'html[data-theme="light"] main :where(.evidence-control.is-active,[data-surface="dark"])'
    assert legacy_selector not in tuning
    assert fixed_selector in tuning
