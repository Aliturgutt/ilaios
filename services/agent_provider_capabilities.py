"""Additive canonical capability boundary for governed external text providers.

This module does not route work. It only defines which canonical agent capabilities
may be advertised by the existing governed AI provider adapter as agent teams are
wired into the single runtime.
"""
# Final current-master Agent closure recertification trigger; no capability behavior change.
from __future__ import annotations

from services.media_intelligence_agent_execution import (
    MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES,
)
from services.operations_meta_agent_execution import (
    OPERATIONS_META_GOVERNED_AI_CAPABILITIES,
)
from services.p0_agent_execution import P0_AGENT_BINDINGS
from services.skill_engineering_runtime import SKILL_ENGINEERING_RUNTIME_BINDINGS
from services.web_agent_execution import WEB_GOVERNED_AI_CAPABILITIES


P0_GOVERNED_AI_CAPABILITIES = frozenset(
    binding.capability
    for binding in P0_AGENT_BINDINGS
    if binding.execution_mode == "governed-ai"
)

SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES = frozenset(
    binding.capability for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS
)

AGENT_GOVERNED_AI_CAPABILITIES = frozenset(
    set(P0_GOVERNED_AI_CAPABILITIES)
    | set(WEB_GOVERNED_AI_CAPABILITIES)
    | set(MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES)
    | set(OPERATIONS_META_GOVERNED_AI_CAPABILITIES)
    | set(SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES)
)

# IndependentVerifier remains deterministic/local in the canonical runtime. The
# explicit config loader historically accepts evidence.verify, so retain that
# compatibility without treating it as a provider-backed producer role.
ALLOWED_AGENT_AI_CAPABILITIES = frozenset(
    set(AGENT_GOVERNED_AI_CAPABILITIES) | {"evidence.verify"}
)


def validate_agent_provider_capabilities() -> None:
    if len(P0_GOVERNED_AI_CAPABILITIES) != 16:
        raise ValueError("P0 governed AI capability population drifted")
    if len(WEB_GOVERNED_AI_CAPABILITIES) != 5:
        raise ValueError("Web governed AI capability population drifted")
    if len(MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES) != 12:
        raise ValueError("Media/Intelligence governed AI capability population drifted")
    if len(OPERATIONS_META_GOVERNED_AI_CAPABILITIES) != 7:
        raise ValueError("Operations/Meta governed AI capability population drifted")
    teams = (
        P0_GOVERNED_AI_CAPABILITIES,
        WEB_GOVERNED_AI_CAPABILITIES,
        MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES,
        OPERATIONS_META_GOVERNED_AI_CAPABILITIES,
    )
    for index, left in enumerate(teams):
        for right in teams[index + 1 :]:
            if left & right:
                raise ValueError("agent team governed AI capabilities must remain distinct")
    if SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES != frozenset(
        {"architecture.propose", "code.review", "test.execute"}
    ):
        raise ValueError("Skill Engineering governed AI capability population drifted")
    if (
        SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES - P0_GOVERNED_AI_CAPABILITIES
        != frozenset({"test.execute"})
    ):
        raise ValueError("Skill Engineering provider capability delta drifted")
    if len(AGENT_GOVERNED_AI_CAPABILITIES) != 41:
        raise ValueError(
            "P0+P1+Operations/Meta+Skill Engineering governed AI capability population must be 41"
        )
    forbidden = {
        "web.verify",
        "evidence.verify",
        "provider.request",
        "media.write",
        "social.publish",
    }
    if forbidden & AGENT_GOVERNED_AI_CAPABILITIES:
        raise ValueError("external text provider boundary contains side-effect authority")


validate_agent_provider_capabilities()
