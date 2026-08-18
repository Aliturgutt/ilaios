"""Canonical provider-independent Web Factory native skill family."""
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


validate_web_factory_native_skills()
