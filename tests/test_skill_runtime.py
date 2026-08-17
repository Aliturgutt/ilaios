"""Security and routing proofs for the ILAIOS native skill runtime."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from services.runtime.routing import RuntimeError as GovernedRuntimeError
from services.runtime.skill_runtime import (
    NativeSkillRegistry,
    NativeSkillRuntime,
    SkillManifest,
    SkillMatch,
    SkillRequest,
    SkillRuntimeError,
    normalize_prompt,
)


class _EchoSkill:
    manifest = SkillManifest(
        "ilaios.skill.echo",
        "1.0.0",
        "Test-only deterministic echo skill.",
        frozenset(),
    )
    artifact_content = b"echo-v1"

    def match(self, normalized_prompt: str) -> SkillMatch:
        return SkillMatch(0.9, ("echo",)) if "echo" in normalized_prompt else SkillMatch(0.0)

    def execute(self, request: SkillRequest) -> Mapping[str, object]:
        return {"text": request.prompt}


class _SecondEchoSkill:
    manifest = SkillManifest(
        "ilaios.skill.echo-second",
        "1.0.0",
        "Second test-only deterministic echo skill.",
        frozenset(),
    )
    artifact_content = b"echo-v2"

    def match(self, normalized_prompt: str) -> SkillMatch:
        return SkillMatch(0.89, ("echo",)) if "echo" in normalized_prompt else SkillMatch(0.0)

    def execute(self, request: SkillRequest) -> Mapping[str, object]:
        return {"text": request.prompt}


class _MutableSkill:
    manifest = SkillManifest(
        "ilaios.skill.mutable",
        "1.0.0",
        "Test-only mutable artifact skill.",
        frozenset(),
    )

    def __init__(self) -> None:
        self.artifact_content = b"approved"

    def match(self, normalized_prompt: str) -> SkillMatch:
        return SkillMatch(1.0, ("mutable",))

    def execute(self, request: SkillRequest) -> Mapping[str, object]:
        return {"ok": True}


def test_runtime_routes_and_invokes_registered_skill() -> None:
    registry = NativeSkillRegistry()
    registry.register(_EchoSkill())
    invocation = NativeSkillRuntime(registry).invoke("please echo this")

    assert invocation.skill_id == "ilaios.skill.echo"
    assert invocation.output == {"text": "please echo this"}
    assert len(invocation.artifact_sha256) == 64
    assert invocation.route_signals == ("echo",)


def test_runtime_fails_closed_for_unknown_and_ambiguous_routes() -> None:
    registry = NativeSkillRegistry()
    registry.register(_EchoSkill())
    runtime = NativeSkillRuntime(registry)
    with pytest.raises(SkillRuntimeError, match="no native skill matched"):
        runtime.invoke("unrelated request")

    registry.register(_SecondEchoSkill())
    with pytest.raises(SkillRuntimeError, match="ambiguous native skill route"):
        runtime.invoke("echo something")


def test_registry_rejects_duplicate_ids_and_non_ilaios_namespace() -> None:
    registry = NativeSkillRegistry()
    registry.register(_EchoSkill())
    with pytest.raises(SkillRuntimeError, match="duplicate skill id"):
        registry.register(_EchoSkill())

    class InvalidSkill(_EchoSkill):
        manifest = SkillManifest("external.echo", "1.0.0", "Invalid namespace.", frozenset())

    with pytest.raises(SkillRuntimeError, match="ilaios.skill namespace"):
        registry.register(InvalidSkill())


def test_artifact_tampering_is_detected_before_execution() -> None:
    registry = NativeSkillRegistry()
    skill = _MutableSkill()
    registry.register(skill)
    skill.artifact_content = b"tampered"

    with pytest.raises(GovernedRuntimeError, match="digest does not match approval"):
        NativeSkillRuntime(registry).invoke("mutable", skill_id="ilaios.skill.mutable")


def test_prompt_normalization_is_bounded_turkish_aware_and_token_safe() -> None:
    assert normalize_prompt("  SAĞDAN   AYARLAR  ") == "sagdan ayarlar"
    assert normalize_prompt("Drawer, please! Right-side.") == "drawer please right side"
    with pytest.raises(SkillRuntimeError, match="blank"):
        normalize_prompt("   ")
    with pytest.raises(SkillRuntimeError, match="NUL"):
        normalize_prompt("safe\x00unsafe")
    with pytest.raises(SkillRuntimeError, match="4096"):
        normalize_prompt("x" * 4097)
