from services.prompt_intent_compiler import (
    PromptDomain,
    PromptRisk,
    compile_prompt,
)


def test_amateur_web_prompt_routes_to_web_with_canonical_hint() -> None:
    compiled = compile_prompt("bana modern bir diş kliniği sitesi yap")

    assert compiled.domain is PromptDomain.WEB
    assert compiled.domains == (PromptDomain.WEB,)
    assert compiled.intent == "build_finished_product"
    assert compiled.output_type == "website"
    assert compiled.needs_clarification is False
    assert compiled.suggested_capabilities == ("ilaios.capability.web-factory",)
    assert compiled.success_criteria[-1] == "finished-product evidence is available"
    assert compiled.canonical_objective.startswith("website task:")


def test_amateur_video_prompt_routes_to_video_and_extracts_duration() -> None:
    compiled = compile_prompt("ürünüm için 20 saniye profesyonel video yap")

    assert compiled.domain is PromptDomain.VIDEO
    assert compiled.output_type == "video"
    assert "duration_seconds=20" in compiled.constraints
    assert compiled.suggested_capabilities == (
        "ilaios.capability.video-media-factory",
    )
    assert compiled.canonical_objective == compiled.normalized_objective


def test_software_prompt_routes_to_software() -> None:
    compiled = compile_prompt("müşteri taleplerini takip eden basit bir yazılım yap")

    assert compiled.domain is PromptDomain.SOFTWARE
    assert compiled.output_type == "software"
    assert compiled.suggested_capabilities == (
        "ilaios.capability.software-factory",
    )


def test_web_app_prompt_preserves_existing_desktop_web_route() -> None:
    compiled = compile_prompt("müşteriler için giriş ekranlı bir web app yap")

    assert compiled.domain is PromptDomain.WEB
    assert compiled.output_type == "website"
    assert compiled.canonical_objective.startswith("website task:")


def test_mobile_and_desktop_app_prompts_route_to_app_capability() -> None:
    mobile = compile_prompt("müşteriler için bir mobile app yap")
    desktop = compile_prompt("Windows için bir desktop app yap")

    assert mobile.domain is PromptDomain.APP
    assert desktop.domain is PromptDomain.APP
    assert mobile.suggested_capabilities == ("ilaios.capability.app-factory",)


def test_research_document_commerce_personal_and_security_match_canonical_routes() -> None:
    research = compile_prompt("bu dataset üzerinde research yap")
    document = compile_prompt("sonuçlardan bir pdf document oluştur")
    commerce = compile_prompt("yeni ürün için marketing campaign hazırla")
    personal = compile_prompt("yarın için calendar checklist oluştur")
    security = compile_prompt("security review ve threat model yap")

    assert research.domain is PromptDomain.RESEARCH
    assert document.domain is PromptDomain.DOCUMENT
    assert commerce.domain is PromptDomain.COMMERCE
    assert personal.domain is PromptDomain.PERSONAL
    assert security.domain is PromptDomain.SECURITY


def test_explicit_multi_capability_request_is_not_mistaken_for_ambiguity() -> None:
    compiled = compile_prompt("bir web sitesi ve video yap")

    assert compiled.domain is PromptDomain.GENERAL
    assert compiled.domains == (PromptDomain.VIDEO, PromptDomain.WEB)
    assert compiled.is_multi_domain is True
    assert compiled.intent == "multi_capability_goal"
    assert compiled.needs_clarification is False
    assert compiled.suggested_capabilities == (
        "ilaios.capability.video-media-factory",
        "ilaios.capability.web-factory",
    )
    assert "video website task:" in compiled.canonical_objective


def test_true_alternative_cross_domain_prompt_requests_one_clarification() -> None:
    compiled = compile_prompt("web sitesi veya video yap")

    assert compiled.domain is PromptDomain.GENERAL
    assert compiled.needs_clarification is True
    assert compiled.missing_critical_information == ("target execution domain",)
    assert len(compiled.clarification_questions) == 1


def test_business_only_prompt_stays_advisory_without_inventing_core_capability() -> None:
    compiled = compile_prompt("şirket operasyon stratejisini değerlendir")

    assert compiled.domain is PromptDomain.BUSINESS
    assert compiled.suggested_capabilities == ()
    assert compiled.canonical_objective.startswith("business workflow task:")


def test_general_prompt_remains_backward_compatible() -> None:
    objective = "yarınki toplantı için bana kısa bir hazırlık listesi çıkar"
    compiled = compile_prompt(objective)

    assert compiled.domain is PromptDomain.GENERAL
    assert compiled.domains == ()
    assert compiled.canonical_objective == objective
    assert compiled.needs_clarification is False


def test_professional_existing_route_hint_is_not_duplicated() -> None:
    objective = "Website build task: Build a responsive website for Acme"
    compiled = compile_prompt(objective)

    assert compiled.domain is PromptDomain.WEB
    assert compiled.canonical_objective == objective


def test_long_messy_prompt_is_normalized_without_losing_user_content() -> None:
    objective = (
        "bana   responsive   bir web sitesi yap,  Türkçe olsun,   modern olsun "
        "ve iletişim sayfası da olsun"
    )
    compiled = compile_prompt(objective)

    assert compiled.domain is PromptDomain.WEB
    assert "  " not in compiled.normalized_objective
    assert "iletişim sayfası" in compiled.canonical_objective
    assert "locale=tr" in compiled.constraints
    assert "responsive=true" in compiled.constraints


def test_high_risk_side_effect_is_signaled_not_authorized() -> None:
    compiled = compile_prompt("siteyi production deploy et ve yayınla")

    assert compiled.domain is PromptDomain.WEB
    assert compiled.risk is PromptRisk.HIGH
    assert compiled.intent == "build_finished_product"


def test_locale_and_responsive_constraints_are_detected() -> None:
    compiled = compile_prompt("Türkçe ve English responsive bir website yap")

    assert compiled.domain is PromptDomain.WEB
    assert "locale=tr" in compiled.constraints
    assert "locale=en" in compiled.constraints
    assert "responsive=true" in compiled.constraints


def test_rejects_untrimmed_and_overlong_input() -> None:
    try:
        compile_prompt(" web sitesi yap ")
    except ValueError as error:
        assert "trimmed" in str(error)
    else:
        raise AssertionError("untrimmed prompt must be rejected")

    try:
        compile_prompt("x" * 20_001)
    except ValueError as error:
        assert "limit" in str(error)
    else:
        raise AssertionError("overlong prompt must be rejected")
