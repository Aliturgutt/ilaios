---
name: usage-intelligence
description: Produce privacy-minimized ILAIOS usage statistics from authoritative runtime-route, bounded provider diagnostics, governance, cost, and evidence projections without inventing unavailable or production-wide data.
---

# ILAIOS Native Usage Intelligence

Status: IMPLEMENTED
Owner: ILAIOS
Scope: Read-only operational usage projection

## Purpose

Provide an ILAIOS-owned statistics capability for understanding how the local authenticated ILAIOS control-plane instance is being used. The skill is a projection only: it does not authorize work, meter billing, admit evidence, modify runtime state, or become a second observability authority.

## Authority

1. Existing authoritative runtime-route metadata.
2. Allow-listed bounded provider diagnostics already persisted by the canonical runtime (`model_id`, `input_tokens`, `output_tokens`, `latency_ms`) when present.
3. Existing governance state and explicit-currency cost projection.
4. Existing verified evidence count when supplied by the caller.
5. This skill's deterministic projection rules.

If an upstream source is unavailable or lacks explicit semantics, the corresponding statistic remains unavailable. The skill must not infer or synthesize missing telemetry.

## Output contract

The native projector may emit:

- total governed runtime-route count;
- unique agent, skill, provider, and capability counts;
- UTC activity-by-date histogram;
- active-day count;
- latest observed activity streak and longest observed streak;
- peak execution hour in UTC;
- provider, skill, capability, model, and governance-status distributions;
- aggregate input/output/total tokens for routes with explicit authoritative provider diagnostics;
- bounded latency sample count/average/min/max for routes with explicit authoritative latency diagnostics;
- verified evidence count when authoritatively supplied;
- explicit USD cost totals only when the existing cost projection proves `currency=USD` and `coverage=explicit_currency_only`;
- a machine-readable coverage map that marks unavailable or partial metrics explicitly.

## Current integration

- `services/governance/runtime.py` projects the native usage snapshot under `GovernedRuntimeGateway.state()["usage"]`.
- The existing authenticated `/v1/governance/state` transport therefore carries the projection without creating a second API authority.
- The existing Desktop operational snapshot already consumes the governance-state map, so the usage payload reaches the Desktop data boundary without redesigning the visually frozen Desktop shell.
- Provider diagnostics are read only through an allow-list. Prompt text, provider response text, IDs unrelated to usage, or arbitrary output fields are not emitted by the usage projection.
- The governance-state integration does not fabricate an evidence count; evidence coverage stays `unavailable` until a caller with verified Evidence authority supplies it explicitly.

## Truth boundaries

- Runtime route count is not called a user session count.
- Provider identity is distinct from model identity; model distribution is populated only from explicit persisted `model_id` diagnostics.
- Token, latency, and model coverage may be partial because deterministic/local routes need not expose provider diagnostics.
- Local authenticated control-plane statistics are not labeled platform-global, tenant-global, cloud-global, or production-global.
- Prompt text, runtime response text, requester identifiers, secrets, credentials, and raw evidence payloads are excluded from this projection.

## Fail-closed rules

- malformed route identity or timestamp rejects the projection;
- naive timestamps without a timezone reject the projection;
- malformed or non-object persisted runtime output rejects the projection;
- incomplete/negative/non-integer token diagnostics reject the projection;
- malformed model IDs or latency diagnostics reject the projection;
- malformed governance work status rejects the projection;
- ambiguous/non-USD/non-explicit cost semantics reject monetary projection;
- negative/non-finite monetary values reject the projection;
- negative evidence counts reject the projection.

## Machine contract

- Schema: `ilaios.usage-stats.v1`.
- Scope: `local_authenticated_control_plane`.
- Time zone: UTC.
- Implementation: `services/usage_intelligence.py`.
- Integration: `services/governance/runtime.py`.
- Tests: `tests/test_usage_intelligence.py` and `tests/test_governance_cost_state.py`.
- Runtime dependencies: Python standard library only.
- Third-party runtime dependency: none.
- Copied third-party implementation code/text: NO.

This skill is intentionally outside the fixed Software Factory SF-7 skill registry and does not create a parallel runtime, router, policy engine, evidence store, FinOps ledger, or telemetry authority.
