# Provenance

FIRST-PARTY ILAIOS IMPLEMENTATION
INDEPENDENTLY AUTHORED
CODE/TEXT IMPORTED = NONE
COMMERCIAL COMPATIBILITY = ACCEPTABLE

Reference-only research:
- `microsoft/skills` pinned at `e20084b9d230c6f3b46ce36f011e6c3e50f79f8a`.
- `.github/plugins/microsoft-foundry/skills/foundry-observability` was inspected as a catalog symlink. At the pinned revision it points to `../../azure-skills/skills/foundry-observability`, but that target is absent from the pinned repository tree. No target-skill prose or implementation was assimilated.
- Microsoft first-party public observability/tracing/evaluation documentation was used only to validate generic concepts such as trace correlation, workflow evaluation, latency/error/cost signals, and OpenTelemetry-compatible semantics.

The resulting ILAIOS methodology is independently authored around existing ILAIOS runtime, privacy, tenant, validation, audit, evidence, and cost boundaries.

Excluded: Foundry/Azure-specific configuration, SDKs, exporters, endpoints, prompt text, code, templates, scripts, assets, credentials, dependencies, and control-plane authority.
