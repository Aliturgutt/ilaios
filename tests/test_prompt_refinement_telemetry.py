import json

import pytest

from services.observability import (
    ObservabilityError,
    PromptRefinementTelemetry,
    TelemetryStore,
)
from services.prompt_refinement import (
    PromptRefinementMode,
    prompt_refinement_metrics_snapshot,
    refine_prompt,
)


def test_prompt_refinement_metrics_are_aggregate_and_content_free() -> None:
    secret_prompt = (
        "build a website; password hunter2; API key sk-example-secret; "
        "never deploy production"
    )
    before = prompt_refinement_metrics_snapshot()
    refine_prompt(secret_prompt, PromptRefinementMode.STRUCTURE)
    after = prompt_refinement_metrics_snapshot()

    assert int(after["requests"]) == int(before["requests"]) + 1
    assert "structure" in after["by_mode"]
    serialized = json.dumps(after, sort_keys=True)
    assert secret_prompt not in serialized
    assert "hunter2" not in serialized
    assert "sk-example-secret" not in serialized


def test_canonical_prompt_telemetry_signal_has_only_bounded_non_content_fields() -> None:
    store = TelemetryStore()
    telemetry = PromptRefinementTelemetry(
        store,
        source_sha="a" * 40,
    )
    telemetry.record(
        mode="improve",
        transformed=True,
        issue_count=2,
        ambiguity_detected=False,
        constraints_detected=True,
        risk_cues_preserved=True,
        factory_metadata_complete=True,
        latency_ms=7,
        status="success",
    )

    signals = store.named(PromptRefinementTelemetry.signal_name, None)
    assert len(signals) == 1
    signal = signals[0]
    assert signal.value == "1"
    attributes = dict(signal.attributes)
    assert set(attributes) == {
        "mode",
        "transformed",
        "issue_count",
        "ambiguity_detected",
        "constraints_detected",
        "risk_cues_preserved",
        "factory_metadata_complete",
        "latency_ms",
        "status",
        "contract_version",
        "source_sha",
    }
    assert "prompt" not in " ".join(attributes).casefold()
    assert signal.tenant_id is None


def test_prompt_telemetry_rejects_unbounded_or_unknown_dimensions() -> None:
    store = TelemetryStore()
    telemetry = PromptRefinementTelemetry(store)
    with pytest.raises(ObservabilityError, match="mode"):
        telemetry.record(
            mode="route-for-me",
            transformed=False,
            issue_count=0,
            ambiguity_detected=False,
            constraints_detected=False,
            risk_cues_preserved=None,
            factory_metadata_complete=True,
            latency_ms=1,
            status="success",
        )
    with pytest.raises(ObservabilityError, match="source SHA"):
        PromptRefinementTelemetry(store, source_sha="not-a-sha")


def test_prompt_telemetry_snapshot_does_not_expose_signal_or_correlation_ids() -> None:
    store = TelemetryStore()
    telemetry = PromptRefinementTelemetry(store)
    telemetry.record(
        mode="evaluate",
        transformed=False,
        issue_count=0,
        ambiguity_detected=False,
        constraints_detected=False,
        risk_cues_preserved=None,
        factory_metadata_complete=True,
        latency_ms=0,
        status="success",
    )
    snapshot = telemetry.snapshot()
    assert snapshot == {
        "contract_version": "1",
        "source_sha": "unbound",
        "requests": 1,
        "transformed": 0,
        "failures": 0,
        "by_mode": {
            "clarify": 0,
            "compress": 0,
            "evaluate": 1,
            "improve": 0,
            "preserve-intent": 0,
            "structure": 0,
        },
    }
