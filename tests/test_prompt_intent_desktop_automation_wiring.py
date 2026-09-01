import inspect

from services.desktop_execution_coordinator import (
    DesktopExecutionCoordinator,
    normalize_desktop_execution_objective,
)
from services.execution_coordinator import classify_execution_plan
from services.prompt_intent_compiler import compile_prompt


def test_desktop_automation_compiles_before_canonical_prepare() -> None:
    source = inspect.getsource(DesktopExecutionCoordinator.prepare)

    assert source.index("compile_prompt(normalized)") < source.index("super().prepare")
    assert "compilation.canonical_objective" in source
    assert "compilation.needs_clarification" in source


def test_amateur_desktop_prompt_reaches_existing_web_route_before_execution() -> None:
    raw = "bana modern bir diş kliniği sitesi yap"
    normalized = normalize_desktop_execution_objective(raw)
    compiled = compile_prompt(normalized)
    plan = classify_execution_plan(compiled.canonical_objective)

    assert compiled.needs_clarification is False
    assert plan.capability_ids == ("ilaios.capability.web-factory",)


def test_true_alternative_is_detected_before_desktop_route_execution() -> None:
    compiled = compile_prompt(
        normalize_desktop_execution_objective("web sitesi veya video yap")
    )

    assert compiled.needs_clarification is True
    assert len(compiled.clarification_questions) == 1
