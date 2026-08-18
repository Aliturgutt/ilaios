# ilaios-routing-intelligence

Identity: `ilaios-routing-intelligence` v1.0.0, IMPLEMENTED.

## Purpose

Rank provider/model candidates with bounded, inspectable health, quota, catalog,
cost, latency, reliability, and quality evidence while preserving the existing
ILAIOS canonical routing authority.

This skill is **routing intelligence, not a router**.

## Canonical authority boundary

The only final model selection function remains
`services.ai_governance.route_model`.

This skill may:

- validate versioned provider/model catalog evidence;
- validate bounded provider health and quota evidence;
- estimate request cost from catalog pricing metadata;
- deterministically score eligible candidates;
- produce an ordered candidate set plus reasons/evidence;
- narrow an existing `RoutingPolicy` to evidenced candidates;
- delegate final selection to `route_model`.

This skill may **not**:

- emit an independent `RoutingDecision`;
- bypass tenant/privacy/security/budget policy;
- widen an allowed model/provider set;
- call providers directly;
- fetch secrets;
- create a second router, policy engine, scheduler, Core, or evidence authority;
- silently use stale, exhausted, unhealthy, or missing required provider state.

## Runtime modules

- `services/provider_catalog.py`
- `services/provider_state.py`
- `services/routing_intelligence.py`
- existing authority: `services/ai_governance.py`

## Deterministic ranking inputs

Eligible candidates are evaluated from:

1. capability match;
2. existing allow/deny policy;
3. catalog freshness;
4. provider health and circuit state;
5. quota availability;
6. estimated input/output cost;
7. latency;
8. historical reliability;
9. bounded model quality score;
10. deterministic tie break.

Unknown required health/quota evidence fails closed for that candidate. Stale
catalog or runtime snapshots fail closed for the evaluation.

## Evidence contract

`RoutingIntelligenceEvidence` records capability, catalog version, runtime-state
version, evaluated timestamp, ranked model IDs, every candidate's
provider/model identity, eligibility, deterministic score, estimated cost, and
exclusion/selection reasons. The evidence does not authorize execution.

## Canonical path

```text
CapabilityRequirement
  -> existing ILAIOS Policy
  -> ProviderCatalogSnapshot + ProviderRuntimeSnapshot
  -> ilaios-routing-intelligence
  -> ranked candidate evidence
  -> narrowed RoutingPolicy
  -> services.ai_governance.route_model
  -> ONE canonical route truth
  -> approved provider adapter
```

## Dependency / IP boundary

Runtime dependency on OmniRoute: **NONE**.
Copied OmniRoute code/text: **NONE**.
OmniRoute is a non-authoritative research reference only.
