# ILAIOS Usage Intelligence — Provenance

Status: CONTROLLED FIRST-PARTY IMPLEMENTATION RECORD
Date: 2026-08-18

## External reference

The product idea was informed by a user-provided screenshot showing a command-line usage-statistics experience. The external visual was treated only as a non-authoritative product/UX reference.

- External source code imported: NONE.
- External prompt/skill text imported: NONE.
- External runtime dependency: NONE.
- External telemetry authority: NONE.
- External product API dependency: NONE.

## ILAIOS source authorities

The implementation is independently authored from existing ILAIOS contracts:

- `services/runtime/execution.py` — persisted governed route metadata and explicit provider diagnostic output fields;
- `services/runtime/ai_provider_adapter.py` — bounded authoritative `model_id`, token and latency diagnostics for provider-backed routes;
- `services/governance/runtime.py` — governed work and explicit cost projection;
- `services/governance/cost_projection.py` — fail-closed explicit-currency semantics;
- `services/evidence/` — verified evidence authority when a count is supplied by an authenticated caller;
- `services/observability.py` — existing telemetry boundary and the rule that telemetry does not become authorization/evidence authority.

## Independent implementation evidence

- Native projector: `services/usage_intelligence.py`.
- Native skill contract: `tools/usage-intelligence/SKILL.md`.
- Regression tests: `tests/test_usage_intelligence.py` and `tests/test_governance_cost_state.py`.
- Schema: `ilaios.usage-stats.v1`.
- Dependencies: Python standard library only.

The projector deliberately excludes raw prompt/provider-response contents and requester identifiers. Only allow-listed model/token/latency diagnostics are aggregated when explicitly present; coverage remains unavailable or partial otherwise. It does not reinterpret opaque ledger units as money and does not claim local statistics are platform-global or production-global.
