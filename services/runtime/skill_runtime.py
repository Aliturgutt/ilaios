"""Governed, deterministic runtime for ILAIOS-native skills.

The runtime is intentionally dependency-free. Skills are explicit in-process
objects, registered through an allow-list, fingerprinted as immutable artifacts,
and validated through the existing runtime supply-chain guard before execution.
User text is data only: it cannot dynamically import modules, request new
runtime authority, or execute arbitrary tools.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from services.runtime.routing import AgentProfile, SkillArtifact, SkillRegistry

MAX_PROMPT_CHARS = 4096
DEFAULT_ROUTE_THRESHOLD = 0.45
DEFAULT_AMBIGUITY_MARGIN = 0.05
ILAIOS_SKILL_OWNER = "ILAIOS"
ILAIOS_SKILL_LICENSE = "LicenseRef-ILAIOS-Proprietary"
ILAIOS_SKILL_PROVENANCE = "ILAIOS-native"


class SkillRuntimeError(ValueError):
    """Raised when a native skill request cannot be executed safely."""


@dataclass(frozen=True, slots=True)
class SkillManifest:
    """Stable identity and authority contract for one native skill."""

    skill_id: str
    version: str
    description: str
    authorities: frozenset[str]


@dataclass(frozen=True, slots=True)
class SkillRequest:
    """Bounded request delivered to a selected skill."""

    prompt: str
    normalized_prompt: str
    context: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SkillMatch:
    """Deterministic routing score produced by a skill."""

    score: float
    signals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SkillRoute:
    """Chosen skill plus inspectable routing evidence."""

    skill_id: str
    score: float
    signals: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SkillInvocation:
    """Serializable execution envelope returned by the runtime."""

    skill_id: str
    version: str
    artifact_sha256: str
    route_score: float
    route_signals: tuple[str, ...]
    output: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "artifact_sha256": self.artifact_sha256,
            "route_score": self.route_score,
            "route_signals": list(self.route_signals),
            "output": dict(self.output),
        }


class NativeSkill(Protocol):
    """Executable contract implemented by every ILAIOS-native skill."""

    @property
    def manifest(self) -> SkillManifest: ...

    @property
    def artifact_content(self) -> bytes: ...

    def match(self, normalized_prompt: str) -> SkillMatch: ...

    def execute(self, request: SkillRequest) -> Mapping[str, object]: ...


class NativeSkillRegistry:
    """Allow-list and immutable artifact registry for native skill objects."""

    def __init__(self) -> None:
        self._skills: dict[str, NativeSkill] = {}
        self._supply_chain = SkillRegistry()

    def register(self, skill: NativeSkill) -> None:
        manifest = skill.manifest
        _validate_manifest(manifest)
        if manifest.skill_id in self._skills:
            raise SkillRuntimeError(f"duplicate skill id: {manifest.skill_id}")
        if not skill.artifact_content:
            raise SkillRuntimeError("skill artifact content must not be empty")

        artifact = _artifact(skill)
        self._supply_chain.approve(
            manifest.skill_id,
            artifact.digest,
            manifest.authorities,
            owner=ILAIOS_SKILL_OWNER,
            license_id=ILAIOS_SKILL_LICENSE,
            source_provenance=ILAIOS_SKILL_PROVENANCE,
        )
        self._skills[manifest.skill_id] = skill

    def get(self, skill_id: str) -> NativeSkill:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise SkillRuntimeError(f"unknown skill: {skill_id}") from exc

    def items(self) -> tuple[tuple[str, NativeSkill], ...]:
        return tuple(sorted(self._skills.items(), key=lambda item: item[0]))

    def validate(self, skill: NativeSkill, agent_authorities: frozenset[str]) -> str:
        artifact = _artifact(skill)
        self._supply_chain.validate(
            artifact,
            AgentProfile("ilaios.skill-runtime", agent_authorities),
        )
        return artifact.digest


class NativeSkillRuntime:
    """Route and execute bounded native skills without dynamic code loading."""

    def __init__(
        self,
        registry: NativeSkillRegistry,
        *,
        route_threshold: float = DEFAULT_ROUTE_THRESHOLD,
        ambiguity_margin: float = DEFAULT_AMBIGUITY_MARGIN,
    ) -> None:
        if not 0.0 <= route_threshold <= 1.0:
            raise SkillRuntimeError("route_threshold must be between 0 and 1")
        if not 0.0 <= ambiguity_margin <= 1.0:
            raise SkillRuntimeError("ambiguity_margin must be between 0 and 1")
        self._registry = registry
        self._route_threshold = route_threshold
        self._ambiguity_margin = ambiguity_margin

    def route(self, prompt: str) -> SkillRoute:
        normalized = normalize_prompt(prompt)
        candidates: list[SkillRoute] = []
        for skill_id, skill in self._registry.items():
            match = skill.match(normalized)
            if not 0.0 <= match.score <= 1.0:
                raise SkillRuntimeError(f"invalid route score from {skill_id}")
            if match.score >= self._route_threshold:
                candidates.append(SkillRoute(skill_id, match.score, match.signals))

        candidates.sort(key=lambda item: (-item.score, item.skill_id))
        if not candidates:
            raise SkillRuntimeError("no native skill matched the request")
        if (
            len(candidates) > 1
            and candidates[0].score - candidates[1].score <= self._ambiguity_margin
        ):
            raise SkillRuntimeError(
                "ambiguous native skill route: "
                f"{candidates[0].skill_id}, {candidates[1].skill_id}"
            )
        return candidates[0]

    def invoke(
        self,
        prompt: str,
        *,
        skill_id: str | None = None,
        context: Mapping[str, object] | None = None,
        agent_authorities: frozenset[str] = frozenset(),
    ) -> SkillInvocation:
        normalized = normalize_prompt(prompt)
        if skill_id is None:
            route = self.route(prompt)
        else:
            skill = self._registry.get(skill_id)
            match = skill.match(normalized)
            route = SkillRoute(skill_id, match.score, match.signals)

        selected = self._registry.get(route.skill_id)
        digest = self._registry.validate(selected, agent_authorities)
        request = SkillRequest(prompt, normalized, dict(context or {}))
        output = selected.execute(request)
        if not isinstance(output, Mapping):
            raise SkillRuntimeError("skill output must be a mapping")
        return SkillInvocation(
            selected.manifest.skill_id,
            selected.manifest.version,
            digest,
            route.score,
            route.signals,
            dict(output),
        )


def normalize_prompt(prompt: str) -> str:
    """Normalize multilingual prompts for bounded deterministic matching."""
    if not isinstance(prompt, str):
        raise SkillRuntimeError("prompt must be text")
    if "\x00" in prompt:
        raise SkillRuntimeError("prompt contains a NUL character")
    stripped = prompt.strip()
    if not stripped:
        raise SkillRuntimeError("prompt must not be blank")
    if len(stripped) > MAX_PROMPT_CHARS:
        raise SkillRuntimeError(
            f"prompt exceeds {MAX_PROMPT_CHARS} characters"
        )
    decomposed = unicodedata.normalize("NFKD", stripped.casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(without_marks.replace("ı", "i").split())


def _artifact(skill: NativeSkill) -> SkillArtifact:
    return SkillArtifact(
        skill.manifest.skill_id,
        skill.artifact_content,
        skill.manifest.authorities,
        owner=ILAIOS_SKILL_OWNER,
        license_id=ILAIOS_SKILL_LICENSE,
        source_provenance=ILAIOS_SKILL_PROVENANCE,
    )


def _validate_manifest(manifest: SkillManifest) -> None:
    if not manifest.skill_id.startswith("ilaios.skill."):
        raise SkillRuntimeError("skill id must use the ilaios.skill namespace")
    for value, field_name in (
        (manifest.skill_id, "skill_id"),
        (manifest.version, "version"),
        (manifest.description, "description"),
    ):
        if not value or value != value.strip():
            raise SkillRuntimeError(f"{field_name} must be non-blank and trimmed")
    if any(
        not authority or authority != authority.strip()
        for authority in manifest.authorities
    ):
        raise SkillRuntimeError("skill authorities must be non-blank and trimmed")
