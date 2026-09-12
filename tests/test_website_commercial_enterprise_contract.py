from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_enterprise_is_contract_specific() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    assert "Custom contract" in content
    assert "Özel sözleşme" in content
    assert "contract-allowlisted models" not in content
