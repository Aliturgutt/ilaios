from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.control_plane.migrations import migrate_database
from services.runtime import GovernedRuntime, GrantPolicy
from services.runtime.browser_evidence_adapter import (
    BROWSER_EVIDENCE_ADAPTER_KIND,
    BROWSER_EVIDENCE_PROVIDER_ID,
    BrowserEvidenceAdapterError,
    BrowserEvidenceRuntimeAdapter,
)
from services.web_agent_execution import WEB_AGENT_BINDINGS, validate_web_agent_bindings
from services.web_agent_provider_config import (
    WEB_GOVERNED_AI_CAPABILITIES,
    build_zero_cost_web_openrouter_configuration,
)
from services.web_agent_runtime_composition import compose_web_agent_runtime
from services.web_agent_skill_catalog import (
    WEB_AGENT_PROPOSAL_SKILLS,
    validate_web_agent_skill_catalog,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _browser_document(source_sha: str) -> dict[str, object]:
    return {
        "schema": "ilaios.web.finished-product-browser-evidence.v2",
        "source_head_sha": source_sha,
        "adapter_id": "web.product-runtime.v1",
        "local_acceptance": True,
        "browser_runtime_evidence": "PASS",
        "verification_scope": "LOCAL_CERTIFIED_NEXT_BUILD_BROWSER_AND_ROLLBACK",
        "public_production_proven": False,
        "browser": {
            "engine": "playwright-chromium-next-production",
            "check_count": 8,
            "console_errors": 0,
            "page_errors": 0,
            "responsive": "PASS",
            "navigation": "PASS",
            "en_tr_content_parity": "PASS",
            "accessibility": "PASS",
            "seo": "PASS",
            "security_headers": "PASS",
            "functional_modules": "PASS",
            "runtime": "PASS",
        },
    }


def test_web_bindings_cover_exact_six_canonical_agents() -> None:
    validate_web_agent_bindings()
    assert len(WEB_AGENT_BINDINGS) == 6
    assert len({binding.agent_id for binding in WEB_AGENT_BINDINGS}) == 6
    assert [binding.execution_mode for binding in WEB_AGENT_BINDINGS].count("governed-ai") == 5
    assert [binding.execution_mode for binding in WEB_AGENT_BINDINGS].count("browser-evidence") == 1


def test_web_proposal_skills_are_first_party_and_exact() -> None:
    validate_web_agent_skill_catalog()
    assert len(WEB_AGENT_PROPOSAL_SKILLS) == 5
    assert {item.capability for item in WEB_AGENT_PROPOSAL_SKILLS} == WEB_GOVERNED_AI_CAPABILITIES
    assert all(item.content().strip() for item in WEB_AGENT_PROPOSAL_SKILLS)


def test_web_provider_configuration_is_zero_cost_free_router_only() -> None:
    configuration = build_zero_cost_web_openrouter_configuration()
    for capability in WEB_GOVERNED_AI_CAPABILITIES:
        selection = configuration.adapter.select(capability)
        assert selection.provider_id == "openrouter"
        assert selection.model_id == "openrouter/free"
    assert configuration.provider_capabilities == {
        "openrouter": WEB_GOVERNED_AI_CAPABILITIES
    }


def test_browser_evidence_adapter_requires_exact_local_real_browser_receipt(
    tmp_path: Path,
) -> None:
    source_sha = "a" * 40
    path = tmp_path / "browser-evidence.json"
    path.write_text(json.dumps(_browser_document(source_sha)), encoding="utf-8")
    adapter = BrowserEvidenceRuntimeAdapter(tmp_path)
    result = adapter.execute(
        {"evidence_path": str(path), "source_sha": source_sha}
    )
    assert result["browser_runtime_evidence"] == "PASS"
    assert result["public_production_proven"] is False
    assert isinstance(result["browser_evidence_sha256"], str)


def test_browser_evidence_adapter_rejects_production_overclaim(tmp_path: Path) -> None:
    source_sha = "b" * 40
    document = _browser_document(source_sha)
    document["public_production_proven"] = True
    path = tmp_path / "browser-evidence.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(BrowserEvidenceAdapterError, match="must not claim public production"):
        BrowserEvidenceRuntimeAdapter(tmp_path).execute(
            {"evidence_path": str(path), "source_sha": source_sha}
        )


def test_web_composition_reuses_single_governed_runtime(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    migrate_database(database)
    configuration = build_zero_cost_web_openrouter_configuration()
    browser_adapter = BrowserEvidenceRuntimeAdapter(tmp_path / "browser")
    external = dict(configuration.adapter.runtime_adapters())
    external.update(browser_adapter.runtime_adapters())
    runtime = GovernedRuntime(database, external_adapters=external)
    composition = compose_web_agent_runtime(
        runtime,
        GrantPolicy(),
        repository_root=_root(),
        browser_evidence_adapter=browser_adapter,
        ai_adapter=configuration.adapter,
        ai_provider_capabilities=configuration.provider_capabilities,
    )
    assert composition.target_agent_count == 6
    assert composition.skill_count == 9
    assert composition.ai_provider_count == 1
    assert composition.local_provider_count == 2
    providers = {item["provider_id"] for item in runtime.providers()}
    assert "openrouter" in providers
    assert BROWSER_EVIDENCE_PROVIDER_ID in providers
    assert BROWSER_EVIDENCE_ADAPTER_KIND in {
        item["adapter_kind"] for item in runtime.providers()
    }
