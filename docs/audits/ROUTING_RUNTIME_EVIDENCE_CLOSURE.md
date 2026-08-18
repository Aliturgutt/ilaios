# Routing Runtime Evidence Closure

Date: 2026-08-18
Base master: `89becbde081d6b6637cc6d92037f0742cb67c853`

## Scope

This closes the repository/runtime gaps left after the OmniRoute + UI/UX Pro Max
clean-room audit without installing either third-party project and without
creating a second routing authority.

## Closed runtime gaps

`services/routing_runtime.py` adds one bounded runtime binding around the
existing routing truth:

1. obtain a fresh `ProviderCatalogSnapshot` from a replaceable provider catalog
   source;
2. obtain a fresh `ProviderRuntimeSnapshot` from a replaceable health/quota
   source;
3. evaluate the existing `RoutingPolicy` with
   `RoutingIntelligenceEngine`;
4. narrow policy only to evidenced candidates;
5. delegate final model selection to the existing
   `services.ai_governance.route_model` authority;
6. persist the complete route evidence into the canonical content-addressed
   `EvidenceStore` before returning a resolution.

The runtime re-observes catalog and provider state for every resolution. Source
adapters own retrieval/caching semantics; the routing runtime does not silently
reuse stale state.

## Persisted evidence

Each successful resolution persists `ilaios.routing-evidence.v1`, binding:

- execution identity;
- selected provider/model;
- caller allow/deny/fallback policy;
- capability and token estimates;
- complete provider/model/pricing/quality catalog snapshot;
- complete health/circuit/quota runtime snapshot;
- candidate scores, costs, eligibility and exclusion reasons;
- catalog/runtime versions and observation/evaluation timestamps.

The artifact is SHA-256 content-addressed and appended to the existing
tamper-evident provenance chain with action `routing.resolve`.

A selection is not returned if source observation, routing evaluation, canonical
selection, or evidence persistence fails.

## Red-team invariants

The closure is rejected if any of the following becomes true:

- a new `RoutingDecision` or final-selection authority is introduced;
- external/provider evidence can widen a caller policy;
- routing proceeds after stale or missing required evidence;
- catalog/runtime source failure is converted into an optimistic default;
- a provider adapter chooses fallback independently;
- route evidence is optional after successful selection;
- secrets or provider credentials are written into routing evidence;
- Core, Video Factory, OpenRouter provider authority, or the fixed SF-7 registry
  is rewritten for this closure.

## Verification

`tests/test_routing_runtime.py` proves:

- dynamic source observation on each route;
- state changes alter the ranked candidate set without changing routing
  authority;
- final selection still comes through the canonical router;
- full route evidence is durably persisted and hash-chain verifiable;
- provider-source failures fail closed before evidence/selection;
- stale runtime evidence fails closed;
- intelligence cannot widen the existing policy.

Repository Required CI remains the acceptance gate.

## External production boundary

This closure makes provider telemetry/catalog sources pluggable and mandatory
for the governed runtime; it does not fabricate live third-party observations.
A production deployment still needs its configured provider adapters and
credentials to supply real catalog, health and quota snapshots. No production
or external-provider claim may be made without that observed evidence.
