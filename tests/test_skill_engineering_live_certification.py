from __future__ import annotations

# Final Agent closure exact-master recertification trigger; no test behavior change.
# Agent closure exact-master co-certification trigger; no test behavior change.
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from services.ai_governance import (
    ModelProviderRegistry,
    ModelRecord,
    ProviderRecord,
    RoutingPolicy,
    Scope,
    ScopeKind,
    UsageGovernor,
    UsageLimits,
)
from services.p0_ai_provider_config import (
    P0AIProviderConfiguration,
    load_p0_ai_provider_configuration,
)
from services.runtime.ai_provider_adapter import (
    GovernedAIProviderAdapter,
    ProviderEndpoint,
    ProviderTransportResult,
)
from services.skill_engineering_live_certification import (
    run_skill_engineering_live_certification,
)
from services.skill_engineering_runtime import SKILL_ENGINEERING_RUNTIME_BINDINGS

ROOT = Path(__file__).resolve().parents[1]


class _Transport:
    def complete(
        self,
        endpoint: ProviderEndpoint,
        *,
        api_key: str,
        model_id: str,
        system_instructions: str,
        prompt: str,
        max_output_tokens: int,
    ) -> ProviderTransportResult:
        assert endpoint.provider_id == "local-test"
        assert model_id == "local-test/model"
        assert system_instructions.strip()
        assert prompt.strip()
        assert max_output_tokens == 1024
        return ProviderTransportResult(
            text="bounded certification proposal",
            input_tokens=64,
            output_tokens=16,
            response_id=f"response-{len(system_instructions)}",
        )


def _configuration() -> P0AIProviderConfiguration:
    capabilities = frozenset(
        binding.capability for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS
    )
    registry = ModelProviderRegistry()
    registry.register_provider(ProviderRecord("local-test", "openai-compatible"))
    registry.register_model(
        ModelRecord(
            "local-test/model",
            "local-test",
            capabilities,
            context_window=8192,
            max_output_tokens=1024,
            input_cost_per_million=Decimal(0),
            output_cost_per_million=Decimal(0),
        )
    )
    policy = RoutingPolicy(
        allowed_models=frozenset({"local-test/model"}),
        allowed_providers=frozenset({"local-test"}),
        fallback_order=("local-test/model",),
    )
    tenant_scope = Scope(ScopeKind.TENANT, "ilaios-skill-engineering-live-certification")
    governor = UsageGovernor(
        registry,
        {
            tenant_scope: UsageLimits(
                max_input_tokens=32768,
                max_output_tokens=4096,
                max_requests_daily=20,
                max_concurrency=2,
                daily_cost=Decimal(0),
                monthly_cost=Decimal(0),
                gpu_seconds_daily=Decimal(0),
                runtime_seconds_daily=Decimal("600"),
                warning_fraction=Decimal("0.8"),
                max_retries=0,
                max_retry_cost=Decimal(0),
            )
        },
    )
    adapter = GovernedAIProviderAdapter(
        registry,
        policy,
        governor,
        (
            ProviderEndpoint(
                "local-test",
                "http://127.0.0.1:9999/v1",
                "LOCAL_TEST_KEY",
                max_retries=0,
                requires_api_key=False,
            ),
        ),
        transport=_Transport(),
    )
    return P0AIProviderConfiguration(
        adapter=adapter,
        provider_capabilities={"local-test": capabilities},
        configured_scopes=(tenant_scope,),
    )


def test_five_skill_certification_persists_verified_receipt(tmp_path: Path) -> None:
    revision = "a" * 40
    receipt = run_skill_engineering_live_certification(
        repository_root=ROOT,
        output_dir=tmp_path,
        revision_sha=revision,
        configuration=_configuration(),
        now=datetime(2026, 8, 19, tzinfo=timezone.utc),
    )
    assert receipt["status"] == "VERIFIED"
    assert receipt["revision_sha"] == revision
    assert receipt["verified_skill_count"] == 5
    assert receipt["target_skill_count"] == 5
    skills = receipt["skills"]
    assert isinstance(skills, list)
    assert [item["skill_id"] for item in skills] == [
        binding.skill_id for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS
    ]
    assert all(item["actual_cost_usd"] == "0" for item in skills)
    persisted = json.loads(
        (tmp_path / "skill-engineering-live-receipt.json").read_text(encoding="utf-8")
    )
    assert persisted == receipt


def test_explicit_local_provider_config_accepts_admitted_test_execute_capability() -> None:
    raw = json.dumps(
        {
            "providers": [
                {
                    "provider_id": "local",
                    "base_url": "http://127.0.0.1:8080/v1",
                    "api_key_env": "ILAIOS_LOCAL_PROVIDER_KEY",
                    "timeout_seconds": 30,
                    "max_retries": 0,
                }
            ],
            "models": [
                {
                    "model_id": "local/model",
                    "provider_id": "local",
                    "capabilities": ["test.execute"],
                    "context_window": 8192,
                    "max_output_tokens": 512,
                    "input_cost_per_million_usd": "0",
                    "output_cost_per_million_usd": "0",
                }
            ],
            "routing": {
                "allowed_models": ["local/model"],
                "denied_models": [],
                "allowed_providers": ["local"],
                "denied_providers": [],
                "fallback_order": ["local/model"],
            },
            "limits": [
                {
                    "scope_kind": "tenant",
                    "scope_id": "tenant-1",
                    "max_input_tokens": 8192,
                    "max_output_tokens": 512,
                    "max_requests_daily": 10,
                    "max_concurrency": 1,
                    "daily_cost_usd": "0",
                    "monthly_cost_usd": "0",
                    "gpu_seconds_daily": "0",
                    "runtime_seconds_daily": "600",
                    "warning_fraction": "0.8",
                    "max_retries": 0,
                    "max_retry_cost_usd": "0",
                }
            ],
        }
    )
    configuration = load_p0_ai_provider_configuration(raw)
    assert configuration is not None
    assert configuration.adapter.select("test.execute").provider_id == "local"
