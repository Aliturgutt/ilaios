from pathlib import Path
from typing import cast

import pytest

from services.web_factory_skills import (
    WEB_FACTORY_NATIVE_SKILL_IDS,
    WEB_FACTORY_NATIVE_SKILLS,
    bind_web_factory_native_skill_evidence,
    validate_web_factory_native_skills,
    web_factory_native_skill_plan,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _accepted_local_manifest() -> dict[str, object]:
    return {
        "adapter_id": "web.product-runtime.v1",
        "accepted": True,
        "job_state_proven": True,
        "site_id": "site-test",
        "spec_hash": "spec-sha",
        "design_strategy": {
            "primary_composition": "editorial",
            "motion_intensity": "restrained",
            "interaction_density": "moderate",
            "scroll_behavior": "section-linked",
            "showcase_behavior": "contextual-interactive",
            "motion_accessibility": "reduced-motion-static-equivalent",
        },
        "qa": {"passed": True},
        "artifact_digest": "artifact-sha",
        "source_project_digest": "source-sha",
        "deployment_state": "NOT_DEPLOYED",
    }


def test_web_factory_native_skill_registry_is_ordered_and_unique() -> None:
    validate_web_factory_native_skills()
    assert WEB_FACTORY_NATIVE_SKILL_IDS == (
        "ilaios-web-architecture",
        "ilaios-web-design",
        "ilaios-web-motion-design",
        "ilaios-web-interaction-design",
        "ilaios-web-scroll-composition",
        "ilaios-web-interactive-showcase",
        "ilaios-web-motion-accessibility",
        "ilaios-web-motion-qa",
        "ilaios-web-accessibility",
        "ilaios-web-performance",
        "ilaios-web-validation",
        "ilaios-web-production-qa",
    )
    assert len({item.capability for item in WEB_FACTORY_NATIVE_SKILLS}) == 12
    assert tuple(item["skill_id"] for item in web_factory_native_skill_plan()) == (
        WEB_FACTORY_NATIVE_SKILL_IDS
    )


def test_web_factory_native_skill_packages_exist_and_are_first_party() -> None:
    root = _repo_root() / "tools" / "web-factory" / "skills"
    provenance = (root / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "CODE/TEXT IMPORTED = NONE" in provenance
    assert "PROMPT/SKILL TEXT IMPORTED = NONE" in provenance
    assert "REFERENCE IMPLEMENTATION IMPORTED = NONE" in provenance
    assert "RUNTIME DEPENDENCY ON THIRD-PARTY SKILL REPOSITORIES = NONE" in provenance
    for skill_id in WEB_FACTORY_NATIVE_SKILL_IDS:
        skill = root / skill_id / "SKILL.md"
        assert skill.is_file(), skill_id
        text = skill.read_text(encoding="utf-8")
        assert f"name: {skill_id}" in text
        assert "Owner: ILAIOS" in text
        assert "Status: IMPLEMENTED" in text


def test_web_factory_native_skill_contract_is_provider_independent() -> None:
    root = _repo_root() / "tools" / "web-factory" / "skills"
    forbidden_identity_markers = (
        "vercel-labs/agent-skills",
        "react-best-practices",
        "web-design-guidelines",
        "composition-patterns",
        "vercel-optimize",
        "claude skill",
        "codex skill",
    )
    for skill_id in WEB_FACTORY_NATIVE_SKILL_IDS:
        text = (root / skill_id / "SKILL.md").read_text(encoding="utf-8").casefold()
        assert (
            "provider-independent" in text
            or "provider/framework" in text
            or "hosting-specific" in text
        )
        assert all(marker not in text for marker in forbidden_identity_markers)


def test_web_factory_native_skills_do_not_import_external_skill_assets() -> None:
    root = _repo_root() / "tools" / "web-factory" / "skills"
    allowed_top_level = {"PROVENANCE.md", *WEB_FACTORY_NATIVE_SKILL_IDS}
    assert {path.name for path in root.iterdir()} == allowed_top_level
    for skill_id in WEB_FACTORY_NATIVE_SKILL_IDS:
        package = root / skill_id
        assert {path.name for path in package.iterdir()} == {"SKILL.md"}


def test_native_web_skill_evidence_binding_is_not_execution_claim() -> None:
    bound = bind_web_factory_native_skill_evidence(_accepted_local_manifest())
    assert "native_skill_execution" not in bound
    bindings = cast(
        list[dict[str, object]], bound["native_skill_evidence_binding"]
    )
    assert tuple(item["skill_id"] for item in bindings) == WEB_FACTORY_NATIVE_SKILL_IDS
    assert bindings[0]["status"] == "EVIDENCE_BOUND"
    assert bindings[2]["status"] == "DESIGN_CONTRACT_EVIDENCE_BOUND"
    assert bindings[6]["status"] == "QA_EVIDENCE_BOUND"
    assert bindings[10]["status"] == "VALIDATION_EVIDENCE_BOUND"
    assert bindings[11]["status"] == "BLOCKED_DEPLOYMENT"


def test_native_web_skill_evidence_binding_cannot_fake_production_verification() -> None:
    manifest = _accepted_local_manifest()
    manifest["deployment_state"] = "PRODUCTION_VERIFIED"
    with pytest.raises(ValueError, match="deployment receipt"):
        bind_web_factory_native_skill_evidence(manifest)


def test_native_web_skill_production_binding_names_evidence_not_execution() -> None:
    manifest = _accepted_local_manifest()
    manifest["deployment_state"] = "PRODUCTION_VERIFIED"
    manifest["deployment_receipt"] = {"deployment_id": "deployment-test"}
    bound = bind_web_factory_native_skill_evidence(manifest)
    bindings = cast(
        list[dict[str, object]], bound["native_skill_evidence_binding"]
    )
    assert bindings[-1]["status"] == "PRODUCTION_VERIFICATION_EVIDENCE_BOUND"
    assert "native_skill_execution" not in bound


def test_web_execution_adapter_is_wired_to_native_skill_evidence_binding() -> None:
    source = (
        _repo_root() / "services" / "execution_adapters.py"
    ).read_text(encoding="utf-8")
    assert "from services.web_factory_skills import" in source
    assert source.count("bind_web_factory_native_skill_evidence(") >= 3
