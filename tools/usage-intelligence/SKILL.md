---
name: usage-intelligence
description: Produce privacy-minimized ILAIOS usage statistics from authoritative runtime-route, governance, cost, and evidence projections without inventing unavailable token, latency, model, or production-wide data.
---

# ILAIOS Native Usage Intelligence

Status: IMPLEMENTED
Owner: ILAIOS
Scope: Read-only operational usage projection

## Purpose

Provide an ILAIOS-owned statistics capability for understanding how the local authenticated ILAIOS control-plane instance is being used. The skill is a projection only: it does not authorize work, meter billing, admit evidence, modify runtime state, or become a second observability authority.

## Authority

1. Existing authoritative runtime-route metadata.
2. Existing governance state and explicit-currency cost projection.
3. Existing verified evidence count when supplied by the caller.
4. This skill's deterministic projection rules.

If an upstream source is unavailable or lacks explicit semantics, the corresponding statistic remains unavailable. The skill must not infer or synthesize missing telemetry.

## Output contract

The native projector may emit:

- total governed runtime-route count;
- unique agent, skill, provider, and capability counts;
- UTC activity-by-date histogram;
- active-day count;
- latest observed activity streak and longest observed streak;
- peak execution hour in UTC;
- provider, skill, capability, and governance-status distributions;
- verified evidence count when authoritatively supplied;
- explicit USD cost totals only when the existing cost projection proves `currency=USD` and `coverage=explicit_currency_only`;
- a machine-readable coverage map that marks unavailable metrics explicitly.

## Truth boundaries

- Runtime route count is not called a user session count.
- Provider identity is not automatically a model identity.
- Token usage is unavailable until authoritative token telemetry is integrated.
- Latency statistics are unavailable until authoritative latency telemetry is integrated.
- Model statistics are unavailable until canonical runtime data identifies models explicitly.
- Local authenticated control-plane statistics are not labeled platform-global, tenant-global, cloud-global, or production-global.
- Prompt text, runtime output payloads, requester identifiers, secrets, credentials, and raw evidence payloads are excluded from this projection.

## Fail-closed rules

- malformed route identity or timestamp rejects the projection;
- naive timestamps without a timezone reject the projection;
- malformed governance work status rejects the projection;
- ambiguous/non-USD/non-explicit cost semantics reject monetary projection;
- negative/non-finite monetary values reject the projection;
- negative evidence counts reject the projection.

## Machine contract

- Schema: `ilaios.usage-stats.v1`.
- Scope: `local_authenticated_control_plane`.
- Time zone: UTC.
- Implementation: `services/usage_intelligence.py`.
- Tests: `tests/test_usage_intelligence.py`.
- Runtime dependencies: Python standard library only.
- Third-party runtime dependency: none.
- Copied third-party implementation code/text: NO.

This skill is intentionally outside the fixed Software Factory SF-7 skill registry and does not create a parallel runtime, router, policy engine, evidence store, FinOps ledger, or telemetry authority.
