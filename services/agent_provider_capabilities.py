"""Additive canonical capability boundary for governed external text providers.

This module does not route work. It only defines which canonical agent capabilities
may be advertised by the existing governed AI provider adapter as agent teams are
wired into the single runtime.
"""
from __future__ import annotations

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
    if P0_GOVERNED_AI_CAPABILITIES & WEB_GOVERNED_AI_CAPABILITIES:
        raise ValueError("P0 and Web governed AI capabilities must remain distinct")
    if SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES != frozenset(
        {"architecture.propose", "code.review", "test.execute"}
    ):
        raise ValueError("Skill Engineering governed AI capability population drifted")
    if (
        SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES - P0_GOVERNED_AI_CAPABILITIES
        != frozenset({"test.execute"})
    ):
        raise ValueError("Skill Engineering provider capability delta drifted")
    if len(AGENT_GOVERNED_AI_CAPABILITIES) != 22:
        raise ValueError("P0+Web+Skill Engineering governed AI capability population must be 22")
    if "web.verify" in AGENT_GOVERNED_AI_CAPABILITIES:
        raise ValueError("BrowserQA must never be advertised as generic governed AI")


validate_agent_provider_capabilities()
