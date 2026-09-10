from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_plan_display_order_is_free_to_enterprise_in_both_locales() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    names = ['name: "Free"', 'name: "Pro"', 'name: "Business"', 'name: "Power"', 'name: "Enterprise"']
    first = [content.index(name) for name in names]
    assert first == sorted(first)

    second_start = content.index('tr: {')
    tr_content = content[second_start:]
    second = [tr_content.index(name) for name in names]
    assert second == sorted(second)
