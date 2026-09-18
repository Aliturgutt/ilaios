from dataclasses import replace

from services.prompt_intent_compiler import compile_prompt
from services.prompt_refinement import (
    PromptRefinementMode,
    _factory_hints,
    refine_prompt,
)


def test_known_factory_hint_uses_canonical_registry_identity() -> None:
    result = refine_prompt("build a responsive website")
    assert result.evaluation.factory_metadata_complete is True
    assert result.evaluation.factory_hints == (
        "Web Factory (ilaios.capability.web-factory)",
    )


def test_multi_domain_factory_hints_preserve_compiler_order() -> None:
    result = refine_prompt("build a website and video")
    assert result.evaluation.factory_metadata_complete is True
    assert result.evaluation.factory_hints == (
        "Video and Media Factory (ilaios.capability.video-media-factory)",
        "Web Factory (ilaios.capability.web-factory)",
    )
    assert compile_prompt(result.refined_prompt).is_multi_domain is True


def test_ambiguous_alternatives_remain_compiler_owned() -> None:
    prompt = "build a website or video"
    result = refine_prompt(prompt, PromptRefinementMode.CLARIFY)
    compiled = compile_prompt(result.refined_prompt)
    assert result.evaluation.ambiguity_detected is True
    assert compiled.needs_clarification is True
    assert result.evaluation.factory_hints


def test_general_and_business_without_factory_capability_do_not_invent_one() -> None:
    for prompt in ("general helpful task", "assess business strategy"):
        result = refine_prompt(prompt)
        assert result.evaluation.factory_hints == ()
        assert result.evaluation.factory_metadata_complete is True


def test_unknown_capability_metadata_fails_closed() -> None:
    compiled = replace(
        compile_prompt("build a website"),
        suggested_capabilities=("ilaios.capability.unknown-factory",),
    )
    hints, complete = _factory_hints(compiled)
    assert hints == ()
    assert complete is False


def test_non_factory_capability_metadata_fails_closed() -> None:
    compiled = replace(
        compile_prompt("build a website"),
        suggested_capabilities=("ilaios.capability.core",),
    )
    hints, complete = _factory_hints(compiled)
    assert hints == ()
    assert complete is False


def test_factory_awareness_is_deterministic_for_turkish_and_english() -> None:
    prompts = (
        "mobil uyumlu bir web sitesi yap",
        "build a mobile friendly website",
    )
    for prompt in prompts:
        first = refine_prompt(prompt)
        second = refine_prompt(prompt)
        assert first == second
        assert first.evaluation.factory_hints == (
            "Web Factory (ilaios.capability.web-factory)",
        )


def test_factory_awareness_does_not_change_default_admission_semantics() -> None:
    prompt = "build a website. only change src/app.py. never deploy production"
    before = compile_prompt(prompt)
    result = refine_prompt(prompt)
    after = compile_prompt(result.refined_prompt)
    assert result.refined_prompt == prompt
    assert after.domain == before.domain
    assert after.domains == before.domains
    assert after.risk == before.risk
    assert after.constraints == before.constraints
    assert after.ambiguity_reasons == before.ambiguity_reasons
    assert result.evaluation.risk_cues_preserved is True
    assert result.evaluation.constraints_detected is True


def test_explicit_presentation_refinement_still_passes_through_compiler() -> None:
    prompt = "build a website. only change src/app.py"
    result = refine_prompt(prompt, PromptRefinementMode.STRUCTURE)
    compiled = compile_prompt(result.refined_prompt)
    assert result.transformed is True
    assert compiled.suggested_capabilities == (
        "ilaios.capability.web-factory",
    )
    assert result.evaluation.readiness == "advisory-only"
