# Model capability fit guidance

Video model-fit analysis must use current canonical provider/model evidence, not brand preference or static documentation, and must never become routing authority.

Relevant evidence belongs in existing ILAIOS structures such as:

- `ProviderCatalogSnapshot` for provider/model identity and declared capabilities,
- `ProviderRuntimeSnapshot` for bounded health/quota state,
- `RoutingPolicy` for allow/deny constraints,
- `RoutingIntelligenceEngine` for deterministic ranking evidence,
- canonical `route_model` for final selection authority.

Public model families may expose text-to-video, image-to-video, reference conditioning, first/last-frame, edit/extend, native audio, or other capabilities. Those facts are replaceable catalog data and can become stale; this skill must not encode them as permanent routing truth.

The skill analyzes only already-policy-eligible candidates and cannot expand the caller's policy, emit an independent routing decision, or authorize provider execution.
