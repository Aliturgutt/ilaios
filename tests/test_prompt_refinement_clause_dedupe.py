from services.prompt_refinement import PromptRefinementMode, refine_prompt


def test_structure_renders_each_classified_clause_once() -> None:
    result = refine_prompt(
        "Build a website. Never publish. Tests must pass.",
        PromptRefinementMode.STRUCTURE,
    )

    assert result.refined_prompt.count("Never publish.") == 1
    assert result.refined_prompt.count("Tests must pass.") == 1
    assert "Exclusions:\n- Never publish." in result.refined_prompt
    assert "Acceptance conditions:\n- Tests must pass." in result.refined_prompt


def test_improve_does_not_repeat_acceptance_as_constraint() -> None:
    result = refine_prompt(
        "Build a website. Only change src/app.py. Tests must pass.",
        PromptRefinementMode.IMPROVE,
    )

    assert result.refined_prompt.count("Tests must pass.") == 1
    assert "Constraints:\n- Only change src/app.py." in result.refined_prompt
    assert "Acceptance conditions:\n- Tests must pass." in result.refined_prompt
