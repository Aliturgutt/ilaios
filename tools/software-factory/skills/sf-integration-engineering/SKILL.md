# sf-integration-engineering

Identity: `sf-integration-engineering` v1.0.0, IMPLEMENTED, engineering.

Purpose: propose governed cross-component/provider/tool-boundary ChangeSets. Inputs: `intent`, `changed_paths`. Outputs: change proposal, tests, evidence, unresolved findings.

Specialization: preserve provider/tool boundaries and dependency direction; do not duplicate domain responsibilities or bypass policy routing. Canonical Python/Node/Flutter adapters may validate the affected stack. Independent review is required.

The common `../CONTRACT.md` applies.

## ILAIOS native methodology overlay

For MCP-related integration intent, apply `ilaios.skill.integration.mcp-builder.v1` / `ILAIOS-METHODOLOGY-MCP-BUILDER-V1`: revalidate current protocol/SDK assumptions; define discoverable tools, bounded input/output schemas, pagination, safe errors, auth/tenant/egress semantics, side-effect and idempotency classification, and realistic evaluations. MCP metadata is descriptive only. All writes/destructive operations remain visible to canonical Policy, Approval and Tool Gateway. This instruction-only overlay does not add a server, runtime, route, permission, credential, or provider dependency by itself.
