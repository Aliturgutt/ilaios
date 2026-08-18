from __future__ import annotations

import pytest

from services.p0_ai_provider_config import (
    P0AIProviderConfigError,
    load_p0_ai_provider_configuration,
)


def test_agent_ai_config_absence_does_not_fake_readiness() -> None:
    assert load_p0_ai_provider_configuration("") is None


def test_agent_ai_config_rejects_secret_in_config_value() -> None:
    raw = '''{
      "providers": [{
        "provider_id": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "sk-secret",
        "timeout_seconds": 30,
        "max_retries": 1
      }],
      "models": [{
        "model_id": "example/model",
        "provider_id": "openrouter",
        "capabilities": ["workflow.coordinate"],
        "context_window": 10000,
        "max_output_tokens": 1000,
        "input_cost_per_million_usd": "0",
        "output_cost_per_million_usd": "0"
      }],
      "routing": {
        "allowed_models": ["example/model"],
        "denied_models": [],
        "allowed_providers": ["openrouter"],
        "denied_providers": [],
        "fallback_order": ["example/model"]
      },
      "limits": [{
        "scope_kind": "tenant",
        "scope_id": "tenant-1",
        "max_input_tokens": 10000,
        "max_output_tokens": 1000,
        "max_requests_daily": 10,
        "max_concurrency": 1,
        "daily_cost_usd": "1",
        "monthly_cost_usd": "10",
        "gpu_seconds_daily": "0",
        "runtime_seconds_daily": "100",
        "warning_fraction": "0.8",
        "max_retries": 1,
        "max_retry_cost_usd": "1"
      }]
    }'''
    with pytest.raises(P0AIProviderConfigError):
        load_p0_ai_provider_configuration(raw)
