"""Strict external provider/model/cost configuration tests for P0 agents."""

import json

import pytest

from services.ai_governance import ScopeKind
from services.p0_ai_provider_config import (
    P0AIProviderConfigError,
    load_p0_ai_provider_configuration,
)


def _document() -> dict[str, object]:
    return {
        "providers": [
            {
                "provider_id": "provider-a",
                "base_url": "https://provider-a.invalid/v1",
                "api_key_env": "PROVIDER_A_KEY",
                "timeout_seconds": 30,
                "max_retries": 1,
            }
        ],
        "models": [
            {
                "model_id": "model-a",
                "provider_id": "provider-a",
                "capabilities": ["workflow.plan", "code.propose", "evidence.verify"],
                "context_window": 8192,
                "max_output_tokens": 1024,
                "input_cost_per_million_usd": "1.25",
                "output_cost_per_million_usd": "2.50",
            }
        ],
        "routing": {
            "allowed_models": [],
            "denied_models": [],
            "allowed_providers": [],
            "denied_providers": [],
            "fallback_order": ["model-a"],
        },
        "limits": [
            {
                "scope_kind": "tenant",
                "scope_id": "tenant-test",
                "max_input_tokens": 4096,
                "max_output_tokens": 512,
                "max_requests_daily": 100,
                "max_concurrency": 4,
                "daily_cost_usd": "10",
                "monthly_cost_usd": "100",
                "gpu_seconds_daily": "0",
                "runtime_seconds_daily": "3600",
                "warning_fraction": "0.8",
                "max_retries": 2,
                "max_retry_cost_usd": "1",
            }
        ],
    }


def test_absent_config_keeps_provider_backed_agents_unavailable() -> None:
    assert load_p0_ai_provider_configuration("") is None


def test_explicit_config_builds_provider_pool_without_embedding_secret() -> None:
    config = load_p0_ai_provider_configuration(json.dumps(_document()))
    assert config is not None
    assert config.provider_capabilities == {
        "provider-a": frozenset({"workflow.plan", "code.propose", "evidence.verify"})
    }
    assert len(config.configured_scopes) == 1
    assert config.configured_scopes[0].kind is ScopeKind.TENANT
    assert config.configured_scopes[0].scope_id == "tenant-test"
    assert config.adapter.adapter_kind("provider-a").startswith("ilaios.runtime.ai.")


def test_secret_value_cannot_be_mistaken_for_secret_environment_name() -> None:
    document = _document()
    providers = document["providers"]
    assert isinstance(providers, list)
    providers[0]["api_key_env"] = "sk-secret-value"  # type: ignore[index]
    with pytest.raises(P0AIProviderConfigError, match="not contain a secret"):
        load_p0_ai_provider_configuration(json.dumps(document))


def test_unknown_model_capability_is_rejected() -> None:
    document = _document()
    models = document["models"]
    assert isinstance(models, list)
    models[0]["capabilities"] = ["shell.root"]  # type: ignore[index]
    with pytest.raises(P0AIProviderConfigError, match="exceeds P0"):
        load_p0_ai_provider_configuration(json.dumps(document))


def test_routing_cannot_reference_unknown_model() -> None:
    document = _document()
    routing = document["routing"]
    assert isinstance(routing, dict)
    routing["fallback_order"] = ["model-does-not-exist"]
    with pytest.raises(P0AIProviderConfigError, match="unknown model"):
        load_p0_ai_provider_configuration(json.dumps(document))


def test_tenant_limit_is_mandatory() -> None:
    document = _document()
    limits = document["limits"]
    assert isinstance(limits, list)
    limits[0]["scope_kind"] = "job"  # type: ignore[index]
    with pytest.raises(P0AIProviderConfigError, match="tenant limit"):
        load_p0_ai_provider_configuration(json.dumps(document))
