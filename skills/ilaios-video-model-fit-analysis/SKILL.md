---
name: ilaios-video-model-fit-analysis
description: Analyze already-policy-eligible Video Factory provider/model candidate fit through the existing RoutingIntelligenceEngine; final route/model selection remains with canonical routing authority.
---

# ILAIOS Video Model Fit Analysis

Use this skill when an admitted video capability request needs advisory provider/model fit analysis before canonical route selection.

## Canonical execution

This skill delegates candidate evaluation to the existing `RoutingIntelligenceEngine`, using current `ProviderCatalogSnapshot`, `ProviderRuntimeSnapshot`, `RoutingPolicy`, and `RoutingIntelligenceRequest` evidence.

The engine can consider capability, health, quota, cost, latency, reliability, quality, freshness, and policy. This skill exposes ranking evidence only.

Final model selection remains with the canonical `services.ai_governance.route_model` authority through the existing governed routing path. This skill cannot expand policy and does not emit an independent routing decision.

## Boundaries

It does not create a second router, discover providers over the network, use credentials, dispatch generation, authorize spend, or bypass evidence requirements.

See `references/model-capability-guidance.md`.
