from __future__ import annotations

import json
from pathlib import Path

EXPECTED = {
    "ilaios-video-script": "IMPLEMENTED",
    "ilaios-video-storyboard": "IMPLEMENTED",
    "ilaios-video-stock-search": "SPECIFIED",
    "ilaios-video-motion-design": "IMPLEMENTED",
    "ilaios-video-visual-explainer": "IMPLEMENTED",
    "ilaios-video-caption": "IMPLEMENTED",
    "ilaios-video-sfx-design": "IMPLEMENTED",
    "ilaios-video-audio-mix": "IMPLEMENTED",
    "ilaios-video-quality-review": "IMPLEMENTED",
    "ilaios-video-delivery": "IMPLEMENTED",
}

def test_video_editorial_skill_packages_have_fail_closed_manifests() -> None:
    root = Path("skills")
    for name, maturity in EXPECTED.items():
        skill = root / name / "SKILL.md"
        manifest_path = root / name / "manifest.json"
        assert skill.is_file()
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["name"] == name
        assert manifest["maturity"] == maturity
        assert manifest["runtime"]["capability"] == "ilaios.capability.video-media-factory"
        assert manifest["permissions"]["network"] is False
        assert manifest["permissions"]["shell"] is False
        assert manifest["permissions"]["secrets"] is False
        assert "canonical routing authority remains authoritative" in manifest["authority_boundary"]["provider_selection"]

def test_stock_search_does_not_claim_runtime_integration() -> None:
    manifest = json.loads((Path("skills") / "ilaios-video-stock-search" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["maturity"] == "SPECIFIED"
    assert manifest["runtime"]["python_module"] is None
    assert manifest["runtime"]["adapter_kind"] == "not-runtime-wired"
