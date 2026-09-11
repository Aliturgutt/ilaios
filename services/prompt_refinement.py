"""Deterministic, provider-neutral prompt refinement before governed admission.

This service changes presentation only.  ``compile_prompt`` remains the sole
owner of domain admission, risk classification, and executable ambiguity.
The safe default preserves user intent so existing admission semantics remain
backward-compatible; presentation-changing modes must be selected explicitly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from services.prompt_intent_compiler import PromptCompilation, compile_prompt


class PromptRefinementMode(str, Enum):
    IMPROVE = "improve"
    CLARIFY = "clarify"
    STRUCTURE = "structure"
    PRESERVE_INTENT = "preserve-intent"
    COMPRESS = "compress"
    EVALUATE = "evaluate"


@dataclass(frozen=True, slots=True)
class PromptEvaluation:
    clarity: str
    specificity: str
    structure: str
    readiness: str
    ambiguity_detected: bool
    constraints_detected: bool
    risk_cues: tuple[str, ...]
    risk_cues_preserved: bool | None
    unresolved_critical_information: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PromptRefinement:
    original_prompt: str
    refined_prompt: str
    mode: PromptRefinementMode
    transformed: bool
    detected_issues: tuple[str, ...]
    preserved_constraints: tuple[str, ...]
    unresolved_ambiguities: tuple[str, ...]
    warnings: tuple[str, ...]
    evaluation: PromptEvaluation


_MAX_INPUT_LENGTH = 20_000
_INJECTION_TERMS = (
    "ignore previous rules",
    "disable policy",
    "bypass approval",
    "call provider directly",
    "reveal secrets",
    "ignore tenant boundary",
    "skip validation",
    "mark this verified",
    "pretend tests passed",
)
_NEGATIVE_CUE = re.compile(
    r"\b(?:do not|never|must not|only|yalnızca|sadece|asla|yapma|değiştirme)\b",
    re.IGNORECASE,
)
_ACCEPTANCE_CUE = re.compile(
    r"\b(?:acceptance|success criteria|must pass|test(?:s)? pass|evidence|"
    r"kabul kriter|başarı kriter|test(?:ler)? geç|kanıt)\b",
    re.IGNORECASE,
)
_CONSTRAINT_CUE = re.compile(
    r"\b(?:do not|never|must not|only|must|require(?:ment)?|limit|scope|"
    r"file|branch|budget|cost|language|format|yalnızca|sadece|asla|yapma|"
    r"değiştirme|dosya|dal|bütçe|maliyet|dil|biçim|kapsam)\b",
    re.IGNORECASE,
)
_RISK_CUE = re.compile(
    r"\b(?:publish|production(?:\s+deploy)?|deploy(?:\s+to\s+production)?|"
    r"payment|send(?:\s+email|\s+to\s+customer)?|password|secret|api key|"
    r"token|private(?:\s+data)?|personal(?:\s+data)?|sensitive(?:\s+data)?|"
    r"customer|approval|budget|cost|yayınla|canlıya al|dağıt|ödeme|şifre|gizli|"
    r"api anahtarı|özel|kişisel|hassas|müşteri|onay|bütçe|maliyet)\b",
    re.IGNORECASE,
)
_CLAUSE_BREAK = re.compile(r"(?:\s*[;\n]+\s*|(?<=[.!?])\s+)")


def refine_prompt(
    raw_prompt: str,
    mode: PromptRefinementMode = PromptRefinementMode.PRESERVE_INTENT,
    *,
    explicit_constraints: tuple[str, ...] = (),
) -> PromptRefinement:
    """Return a bounded textual refinement suitable for ``compile_prompt``.

    The service never truncates, supplies context, chooses a route, or changes
    user data into authority.  Explicit constraints are appended only when they
    were not already represented in the text passed to the compiler. The
    default mode preserves normalized user intent; callers that want textual
    restructuring must opt into a presentation-changing mode explicitly.
    """
    if not isinstance(raw_prompt, str):
        raise ValueError("raw prompt must be text")
    if not raw_prompt.strip():
        raise ValueError("raw prompt must be non-blank")
    if len(raw_prompt) > _MAX_INPUT_LENGTH:
        raise ValueError("raw prompt exceeds one-prompt input limit")
    if not isinstance(mode, PromptRefinementMode):
        raise ValueError("refinement mode is invalid")
    if any(not isinstance(item, str) or not item or item != item.strip() for item in explicit_constraints):
        raise ValueError("explicit constraints must be non-blank and trimmed text")

    normalized = _normalize(raw_prompt)
    source = _append_missing_explicit_constraints(normalized, explicit_constraints)
    compilation = compile_prompt(source)
    clauses = _clauses(source)
    constraints = tuple(clause for clause in clauses if _CONSTRAINT_CUE.search(clause))
    exclusions = tuple(clause for clause in clauses if _NEGATIVE_CUE.search(clause))
    acceptance = tuple(clause for clause in clauses if _ACCEPTANCE_CUE.search(clause))
    risk_cues = tuple(match.group(0) for match in _RISK_CUE.finditer(source))
    issues: list[str] = []
    warnings: list[str] = []
    if raw_prompt != normalized:
        issues.append("whitespace normalized")
    if compilation.needs_clarification:
        issues.append("canonical compiler requires clarification")
    contains_injection_text = any(term in source.casefold() for term in _INJECTION_TERMS)
    if contains_injection_text:
        warnings.append("governance-affecting text preserved as untrusted user data")
    if explicit_constraints:
        warnings.append("explicit constraints are represented in the compiler input")

    if contains_injection_text or mode is PromptRefinementMode.PRESERVE_INTENT:
        refined = source
    elif mode is PromptRefinementMode.COMPRESS:
        refined = _compress(source)
        if refined == source:
            issues.append("no lossless deterministic compression available")
    elif mode is PromptRefinementMode.STRUCTURE:
        refined = _structure(clauses, constraints, exclusions, acceptance, compilation)
    elif mode is PromptRefinementMode.IMPROVE:
        refined = _improve(clauses, constraints, acceptance)
    elif mode is PromptRefinementMode.CLARIFY:
        refined = _clarify(source, compilation)
    else:
        refined = source

    preserved_risk = None if not risk_cues else all(cue.casefold() in refined.casefold() for cue in risk_cues)
    evaluation = PromptEvaluation(
        clarity="needs-clarification" if compilation.needs_clarification else "bounded",
        specificity="constrained" if constraints or explicit_constraints else "limited",
        structure="sectioned" if mode is PromptRefinementMode.STRUCTURE else "freeform",
        readiness="advisory-only",
        ambiguity_detected=bool(compilation.ambiguity_reasons),
        constraints_detected=bool(constraints or explicit_constraints),
        risk_cues=risk_cues,
        risk_cues_preserved=preserved_risk,
        unresolved_critical_information=compilation.missing_critical_information,
    )
    return PromptRefinement(
        original_prompt=raw_prompt,
        refined_prompt=refined,
        mode=mode,
        transformed=refined != raw_prompt,
        detected_issues=tuple(issues),
        preserved_constraints=tuple(dict.fromkeys((*constraints, *explicit_constraints))),
        unresolved_ambiguities=compilation.ambiguity_reasons,
        warnings=tuple(warnings),
        evaluation=evaluation,
    )


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _clauses(text: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in _CLAUSE_BREAK.split(text) if item.strip())


def _append_missing_explicit_constraints(text: str, constraints: tuple[str, ...]) -> str:
    missing = tuple(item for item in constraints if item.casefold() not in text.casefold())
    if not missing:
        return text
    return text + "\nExplicit constraints:\n" + "\n".join(f"- {item}" for item in missing)


def _compress(text: str) -> str:
    """Remove only adjacent exact duplicate clauses; otherwise preserve text."""
    clauses = _clauses(text)
    kept: list[str] = []
    for clause in clauses:
        if not kept or clause.casefold() != kept[-1].casefold():
            kept.append(clause)
    return " ".join(kept)


def _improve(
    clauses: tuple[str, ...], constraints: tuple[str, ...], acceptance: tuple[str, ...]
) -> str:
    objective = clauses[0]
    remaining = [item for item in clauses[1:] if item not in constraints and item not in acceptance]
    sections = [f"Objective: {objective}"]
    if remaining:
        sections.extend(("Requirements:", *[f"- {item}" for item in remaining]))
    if constraints:
        sections.extend(("Constraints:", *[f"- {item}" for item in constraints]))
    if acceptance:
        sections.extend(("Acceptance conditions:", *[f"- {item}" for item in acceptance]))
    return "\n".join(sections)


def _structure(
    clauses: tuple[str, ...],
    constraints: tuple[str, ...],
    exclusions: tuple[str, ...],
    acceptance: tuple[str, ...],
    compilation: PromptCompilation,
) -> str:
    objective = clauses[0]
    classified = set(constraints) | set(acceptance)
    requirements = [item for item in clauses[1:] if item not in classified]
    sections = [f"Objective: {objective}"]
    if requirements:
        sections.extend(("Requirements:", *[f"- {item}" for item in requirements]))
    if constraints:
        sections.extend(("Constraints:", *[f"- {item}" for item in constraints]))
    if exclusions:
        sections.extend(("Exclusions:", *[f"- {item}" for item in exclusions]))
    if acceptance:
        sections.extend(("Acceptance conditions:", *[f"- {item}" for item in acceptance]))
    if compilation.needs_clarification:
        sections.extend(("Unresolved ambiguity:", *[f"- {item}" for item in compilation.clarification_questions]))
    return "\n".join(sections)


def _clarify(text: str, compilation: PromptCompilation) -> str:
    if not compilation.needs_clarification:
        return text
    return "\n".join((text, "Unresolved ambiguity:", *[f"- {item}" for item in compilation.clarification_questions]))
