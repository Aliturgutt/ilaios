"""Physical SF-7 package contract test."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_package_contract() -> None:
    manifest = json.loads((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    evals = json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))
    provenance = (ROOT / "PROVENANCE.md").read_text(encoding="utf-8")
    assert manifest["skill_id"] == ROOT.name
    assert {case["kind"] for case in evals["cases"]} == {"GOLDEN", "NEGATIVE", "ADVERSARIAL", "MALFORMED", "REGRESSION"}
    assert "FIRST-PARTY ILAIOS IMPLEMENTATION" in provenance
    assert "CODE/TEXT IMPORTED = NONE" in provenance
