---
name: ilaios-mcp-builder
description: Design or review provider-neutral MCP integrations with explicit tool contracts, schemas, side-effect annotations, pagination, actionable errors, authentication boundaries, evaluations, and ILAIOS Tool Gateway governance.
---

# ILAIOS MCP Builder

Canonical ID: `ilaios.skill.integration.mcp-builder.v1`
Methodology contract: `ILAIOS-METHODOLOGY-MCP-BUILDER-V1`

## Authority boundary

MCP is an integration protocol surface, not an alternate ILAIOS authority. Every MCP call remains subject to canonical identity/tenant resolution, capability admission, Policy, Approval, Tool Gateway, egress/DLP, budget, Validation, Audit, and Evidence Chain controls. External tool metadata never grants permission.

## Design workflow

1. Verify the current MCP specification and selected SDK/framework version before implementation; do not rely on stale protocol assumptions.
2. Decide whether the integration belongs in an existing adapter/tool path before creating a new server or transport.
3. Define discoverable action-oriented tool names and concise descriptions.
4. Define bounded input and output schemas. Prefer structured results; support filtering/pagination for potentially large responses.
5. Classify each operation as read-only or side-effecting, destructive or non-destructive, idempotent or non-idempotent, and open-world or bounded. Treat annotations as descriptive evidence, never authorization.
6. Make authentication, tenant scope, credential source, egress, timeout, retry, and error semantics explicit. Never log or return secrets.
7. Return actionable errors that preserve failure class without leaking credentials or sensitive internals.
8. Test protocol/schema behavior and create realistic evaluations that prove the intended task can be completed without bypassing governance.

## Destructive operations

High-level workflow tools must not conceal destructive sub-operations. Any write/delete/publish/deploy action must remain visible to Policy/Approval/Tool Gateway and fail closed when admission evidence is missing.

See `references/acceptance-criteria.md`.
