"""Canonical provider-independent Web Factory native skill family."""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast


@dataclass(frozen=True, slots=True)
class WebFactorySkill:
    skill_id: str
    capability: str
    stage: str


WEB_FACTORY_NATIVE_SKILLS: tuple[WebFactorySkill, ...] = (
    WebFactorySkill("ilaios-web-architecture", "web.architecture", "architecture"),
    WebFactorySkill("ilaios-web-design", "web.design", "design"),
    WebFactorySkill("ilaios-web-accessibility", "web.accessibility", "accessibility"),
    WebFactorySkill("ilaios-web-performance", "web.performance", "performance"),
    WebFactorySkill("ilaios-web-validation", "web.validate", "validation"),
    WebFactorySkill("ilaios-web-production-qa", "web.production-qa", "production-qa"),
)

WEB_FACTORY_NATIVE_SKILL_IDS: tuple[str, ...] = tuple(
    skill.skill_id for skill in WEB_FACTORY_NATIVE_SKILLS
)


def validate_web_factory_native_skills() -> None:
    ids = WEB_FACTORY_NATIVE_SKILL_IDS
    if len(ids) != 6 or len(set(ids)) != 6:
        raise ValueError("Web Factory native skill family must contain six unique skills")
    if ids[0] != "ilaios-web-architecture" or ids[-1] != "ilaios-web-production-qa":
        raise ValueError("Web Factory native skill order drifted")
    for skill in WEB_FACTORY_NATIVE_SKILLS:
        if not skill.skill_id.startswith("ilaios-web-"):
            raise ValueError("Web Factory native skill identity drifted")
        if not skill.capability.startswith("web."):
            raise ValueError("Web Factory native capability drifted")


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


def bind_web_factory_native_skill_evidence(
    manifest: dict[str, object],
) -> dict[str, object]:
    """Bind native skill stages to real Web runtime evidence without widening claims.

    Local artifact evidence can bind architecture/design/accessibility/performance/
    validation stages. Production QA remains explicitly blocked until a deployment
    receipt exists; local CI or artifact acceptance can never promote it.
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
    if not isinstance(manifest.get("design_strategy"), dict):
        raise ValueError("Web design evidence is incomplete")
    qa = manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("passed") is not True:
        raise ValueError("Web local quality evidence is incomplete")
    if not manifest.get("artifact_digest") or not manifest.get("source_project_digest"):
        raise ValueError("Web validation evidence is incomplete")

    deployment_state = str(manifest.get("deployment_state", ""))
    local_statuses = (
        "EVIDENCE_BOUND",
        "EVIDENCE_BOUND",
        "LOCAL_QA_BOUND",
        "LOCAL_QA_BOUND",
        "LOCAL_VERIFIED",
    )
    execution: list[dict[str, object]] = []
    for skill, status in zip(WEB_FACTORY_NATIVE_SKILLS[:-1], local_statuses, strict=True):
        execution.append(
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
            "PRODUCTION_VERIFIED"
            if deployment_state == "PRODUCTION_VERIFIED"
            else "DEPLOYED_NOT_LIVE_VERIFIED"
        )
    else:
        raise ValueError("unknown Web deployment state")
    execution.append(
        {
            "skill_id": production_skill.skill_id,
            "capability": production_skill.capability,
            "stage": production_skill.stage,
            "status": production_status,
        }
    )

    bound = dict(manifest)
    bound["native_skill_plan"] = cast(tuple[dict[str, str], ...], web_factory_native_skill_plan())
    bound["native_skill_execution"] = execution
    return bound


validate_web_factory_native_skills()
