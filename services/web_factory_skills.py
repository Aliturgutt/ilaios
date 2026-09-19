"""Canonical provider-independent Web Factory native skill families."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WebFactorySkill:
    skill_id: str
    capability: str
    stage: str


WEB_FACTORY_NATIVE_SKILLS: tuple[WebFactorySkill, ...] = (
    WebFactorySkill("ilaios-web-architecture", "web.architecture", "architecture"),
    WebFactorySkill("ilaios-web-design", "web.design", "design"),
    WebFactorySkill("ilaios-web-motion-design", "web.motion-design", "motion-design"),
    WebFactorySkill("ilaios-web-interaction-design", "web.interaction-design", "interaction-design"),
    WebFactorySkill("ilaios-web-scroll-composition", "web.scroll-composition", "scroll-composition"),
    WebFactorySkill("ilaios-web-interactive-showcase", "web.interactive-showcase", "interactive-showcase"),
    WebFactorySkill("ilaios-web-motion-accessibility", "web.motion-accessibility", "motion-accessibility"),
    WebFactorySkill("ilaios-web-motion-qa", "web.motion-qa", "motion-qa"),
    WebFactorySkill("ilaios-web-accessibility", "web.accessibility", "accessibility"),
    WebFactorySkill("ilaios-web-performance", "web.performance", "performance"),
    WebFactorySkill("ilaios-web-validation", "web.validate", "validation"),
    WebFactorySkill("ilaios-web-production-qa", "web.production-qa", "production-qa"),
)

WEB_FACTORY_NATIVE_SKILL_IDS: tuple[str, ...] = tuple(
    skill.skill_id for skill in WEB_FACTORY_NATIVE_SKILLS
)

# Browser support skills are not a second Web Factory pipeline. They are bounded
# BrowserQA capabilities consumed by validation/production-QA through Tool Gateway.
WEB_FACTORY_BROWSER_SKILLS: tuple[WebFactorySkill, ...] = (
    WebFactorySkill("ilaios-browser", "web.verify", "browser"),
    WebFactorySkill("ilaios-browser-automate", "web.verify", "browser-automate"),
    WebFactorySkill("ilaios-web-e2e", "web.verify", "web-e2e"),
    WebFactorySkill("ilaios-visual-qa", "web.verify", "visual-qa"),
    WebFactorySkill(
        "ilaios-production-verification", "web.verify", "production-verification"
    ),
)

WEB_FACTORY_BROWSER_SKILL_IDS: tuple[str, ...] = tuple(
    skill.skill_id for skill in WEB_FACTORY_BROWSER_SKILLS
)


def validate_web_factory_native_skills() -> None:
    ids = WEB_FACTORY_NATIVE_SKILL_IDS
    if len(ids) != 12 or len(set(ids)) != 12:
        raise ValueError("Web Factory native skill family must contain twelve unique skills")
    if ids[0] != "ilaios-web-architecture" or ids[-1] != "ilaios-web-production-qa":
        raise ValueError("Web Factory native skill order drifted")
    for skill in WEB_FACTORY_NATIVE_SKILLS:
        if not skill.skill_id.startswith("ilaios-web-"):
            raise ValueError("Web Factory native skill identity drifted")
        if not skill.capability.startswith("web."):
            raise ValueError("Web Factory native capability drifted")


def validate_web_factory_browser_skills() -> None:
    expected = (
        "ilaios-browser",
        "ilaios-browser-automate",
        "ilaios-web-e2e",
        "ilaios-visual-qa",
        "ilaios-production-verification",
    )
    if WEB_FACTORY_BROWSER_SKILL_IDS != expected:
        raise ValueError("Web Factory browser skill identity/order drifted")
    if set(WEB_FACTORY_BROWSER_SKILL_IDS) & set(WEB_FACTORY_NATIVE_SKILL_IDS):
        raise ValueError("browser support skills must not replace native pipeline stages")
    for skill in WEB_FACTORY_BROWSER_SKILLS:
        if skill.capability != "web.verify":
            raise ValueError("browser support skills may not widen BrowserQA capability")


def web_factory_native_skill_plan() -> tuple[dict[str, str], ...]:
    """Return the immutable ordered native skill plan exposed to Web runtime callers."""
    validate_web_factory_native_skills()
    return tuple(
        {
            "skill_id": skill.skill_id,
            "capability": skill.capability,
            "stage": skill.stage,
        }
        for skill in WEB_FACTORY_NATIVE_SKILLS
    )


def web_factory_browser_skill_plan() -> tuple[dict[str, str], ...]:
    """Return BrowserQA support skills without granting execution authority."""
    validate_web_factory_browser_skills()
    return tuple(
        {
            "skill_id": skill.skill_id,
            "capability": skill.capability,
            "stage": skill.stage,
        }
        for skill in WEB_FACTORY_BROWSER_SKILLS
    )


def bind_web_factory_native_skill_evidence(
    manifest: dict[str, object],
) -> dict[str, object]:
    """Project canonical Web runtime evidence onto native skill coverage.

    This function does not dispatch or execute the native skills. It only binds
    already-observed canonical Web runtime evidence to the skill stages whose
    contracts are covered by that evidence. Therefore the returned field is named
    ``native_skill_evidence_binding`` rather than ``native_skill_execution``.

    Production QA remains explicitly blocked until a deployment receipt exists;
    local CI or artifact acceptance can never be presented as live-production proof.
    """
    validate_web_factory_native_skills()
    if manifest.get("adapter_id") != "web.product-runtime.v1":
        raise ValueError("native Web skills require the canonical Web runtime adapter")
    if manifest.get("accepted") is not True:
        raise ValueError("native Web skill evidence requires accepted runtime evidence")
    if manifest.get("job_state_proven") is not True:
        raise ValueError("native Web skill evidence requires proven terminal job state")
    if not manifest.get("site_id") or not manifest.get("spec_hash"):
        raise ValueError("Web architecture evidence is incomplete")
    design_strategy = manifest.get("design_strategy")
    if not isinstance(design_strategy, dict):
        raise ValueError("Web design evidence is incomplete")
    motion_evidence_complete = all(
        key in design_strategy
        for key in (
            "motion_intensity",
            "interaction_density",
            "scroll_behavior",
            "showcase_behavior",
            "motion_accessibility",
        )
    )
    qa = manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("passed") is not True:
        raise ValueError("Web local quality evidence is incomplete")
    if not manifest.get("artifact_digest") or not manifest.get("source_project_digest"):
        raise ValueError("Web validation evidence is incomplete")

    deployment_state = str(manifest.get("deployment_state", ""))
    motion_status = (
        "DESIGN_CONTRACT_EVIDENCE_BOUND"
        if motion_evidence_complete
        else "NOT_EVIDENCE_BOUND"
    )
    local_status_by_id = {
        "ilaios-web-architecture": "EVIDENCE_BOUND",
        "ilaios-web-design": "EVIDENCE_BOUND",
        "ilaios-web-motion-design": motion_status,
        "ilaios-web-interaction-design": motion_status,
        "ilaios-web-scroll-composition": motion_status,
        "ilaios-web-interactive-showcase": motion_status,
        "ilaios-web-motion-accessibility": (
            "QA_EVIDENCE_BOUND" if motion_evidence_complete else "NOT_EVIDENCE_BOUND"
        ),
        "ilaios-web-motion-qa": (
            "QA_EVIDENCE_BOUND" if motion_evidence_complete else "NOT_EVIDENCE_BOUND"
        ),
        "ilaios-web-accessibility": "QA_EVIDENCE_BOUND",
        "ilaios-web-performance": "QA_EVIDENCE_BOUND",
        "ilaios-web-validation": "VALIDATION_EVIDENCE_BOUND",
    }
    bindings: list[dict[str, object]] = []
    local_skills = WEB_FACTORY_NATIVE_SKILLS[:-1]
    for skill in local_skills:
        status = local_status_by_id[skill.skill_id]
        bindings.append(
            {
                "skill_id": skill.skill_id,
                "capability": skill.capability,
                "stage": skill.stage,
                "status": status,
            }
        )

    production_skill = WEB_FACTORY_NATIVE_SKILLS[-1]
    if deployment_state == "NOT_DEPLOYED":
        production_status = "BLOCKED_DEPLOYMENT"
    elif deployment_state in {"DEPLOYED", "PRODUCTION_VERIFIED"}:
        receipt = manifest.get("deployment_receipt")
        if not isinstance(receipt, dict) or not receipt:
            raise ValueError("production Web skill evidence requires deployment receipt")
        production_status = (
            "PRODUCTION_VERIFICATION_EVIDENCE_BOUND"
            if deployment_state == "PRODUCTION_VERIFIED"
            else "DEPLOYMENT_EVIDENCE_BOUND_NOT_LIVE_VERIFIED"
        )
    else:
        raise ValueError("unknown Web deployment state")
    bindings.append(
        {
            "skill_id": production_skill.skill_id,
            "capability": production_skill.capability,
            "stage": production_skill.stage,
            "status": production_status,
        }
    )

    bound = dict(manifest)
    bound["native_skill_plan"] = web_factory_native_skill_plan()
    bound["native_skill_evidence_binding"] = bindings
    return bound


validate_web_factory_native_skills()
validate_web_factory_browser_skills()
