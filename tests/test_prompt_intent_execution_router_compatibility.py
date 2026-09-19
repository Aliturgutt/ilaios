from services.execution_coordinator import classify_execution_plan
from services.prompt_intent_compiler import compile_prompt


def _capabilities(objective: str) -> tuple[str, ...]:
    compiled = compile_prompt(objective)
    return classify_execution_plan(compiled.canonical_objective).capability_ids


def test_amateur_factory_prompts_match_existing_canonical_router() -> None:
    assert _capabilities("bana modern bir diş kliniği sitesi yap") == (
        "ilaios.capability.web-factory",
    )
    assert _capabilities("ürünüm için 20 saniye video yap") == (
        "ilaios.capability.video-media-factory",
    )
    assert _capabilities("müşteri takip yazılımı yap") == (
        "ilaios.capability.software-factory",
    )
    assert _capabilities("Windows için desktop app yap") == (
        "ilaios.capability.app-factory",
    )


def test_web_app_alias_still_selects_existing_web_factory_route() -> None:
    assert _capabilities("müşteriler için giriş ekranlı bir web app yap") == (
        "ilaios.capability.web-factory",
    )


def test_secondary_capability_families_match_existing_router() -> None:
    assert _capabilities("bu dataset üzerinde research yap") == (
        "ilaios.capability.research-data",
    )
    assert _capabilities("sonuçlardan bir pdf document oluştur") == (
        "ilaios.capability.creative-document",
    )
    assert _capabilities("ürün için marketing campaign hazırla") == (
        "ilaios.capability.commerce-growth",
    )
    assert _capabilities("yarın için calendar checklist oluştur") == (
        "ilaios.capability.personal-operations",
    )
    assert _capabilities("repo için security review yap") == (
        "ilaios.capability.software-factory",
        "ilaios.capability.security-factory",
    )


def test_explicit_multi_output_preserves_existing_multi_capability_plan() -> None:
    capabilities = set(_capabilities("bir web sitesi ve video yap"))

    assert capabilities == {
        "ilaios.capability.web-factory",
        "ilaios.capability.video-media-factory",
    }
