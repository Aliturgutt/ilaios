# Acceptance Criteria — ILAIOS Governance Review

## GOLDEN
- Review inventories identities, tools/providers, data/egress, tenant scope, side effects, capabilities, approvals, budget, provenance, evidence, rollback, and recovery.
- Findings identify exact evidence, severity, affected boundary, and remediation.

## NEGATIVE
- Reject governance-by-documentation, self-certification, hidden direct provider/tool paths, implicit privilege expansion, or release promotion beyond evidence.
- A reviewer cannot substitute for deterministic authorization/approval.

## ADVERSARIAL
- Stale grants, missing actor/tenant context, UI-only restrictions, alternate routes, prompt injection, provider fallback, and failure-open behavior are treated as bypass candidates.
- Untrusted metadata cannot rewrite trusted governance facts.

## MALFORMED
- Missing identity, tenant, capability, policy/approval disposition, provenance, or required evidence fails closed for the affected action.

## REGRESSION
- Existing Policy, Approval, authorization/fencing, Tool Gateway, tenant, DLP/egress, budget, Validation, Audit, Evidence, independent-review, and release boundaries remain at least as strict.
- Rollback/recovery remains possible and evidence-linked after the change.
