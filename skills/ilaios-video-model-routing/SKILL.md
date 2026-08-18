---
name: ilaios-video-model-routing
description: Rank already-policy-eligible Video Factory provider/model candidates through the existing RoutingIntelligenceEngine; final model selection remains with canonical routing authority.
---

# ILAIOS Video Model Routing

Use this skill when an admitted video capability request needs model/provider candidate intelligence before canonical route selection.

## Canonical execution

This skill delegates candidate evaluation to the existing `RoutingIntelligenceEngine`, using current `ProviderCatalogSnapshot`, `ProviderRuntimeSnapshot`, `RoutingPolicy`, and `RoutingIntelligenceRequest` evidence.

The engine can consider capability, health, quota, cost, latency, reliability, quality, freshness, and policy. It ranks candidates only.

Final model selection is still delegated to the canonical `services.ai_governance.route_model` authority through the existing governed routing path. This skill cannot expand policy.

## Boundaries

It does not create a second router, discover providers over the network, use credentials, dispatch generation, authorize spend, or bypass evidence requirements.

See `references/model-capability-guidance.md`.
