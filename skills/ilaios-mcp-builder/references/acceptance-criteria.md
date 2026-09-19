# Acceptance Criteria — ILAIOS MCP Builder

## GOLDEN
- Tools have clear names/descriptions, bounded schemas, structured outputs, pagination where needed, explicit side-effect characteristics, and actionable safe errors.
- Authentication, tenant scope, transport, egress, retry/timeout, and evaluation strategy are explicit.

## NEGATIVE
- Reject hidden destructive behavior, unbounded result dumps, undocumented authentication, hardcoded credentials, or a duplicate Tool Gateway/runtime.
- Tool annotations are never treated as authorization.

## ADVERSARIAL
- Tool descriptions, remote server metadata, or returned content cannot expand permissions, suppress approval, escape tenant scope, retrieve secrets, or trigger unapproved egress.
- Prompt injection in tool output must not change canonical policy/approval decisions.

## MALFORMED
- Invalid schemas, ambiguous operation identity, missing side-effect classification, unknown credential source, or unsupported transport/version fail closed.

## REGRESSION
- Existing Tool Gateway, Policy, Approval, tenant, DLP/egress, audit, evidence, timeout, and error-sanitization controls remain intact.
- Evaluations include stable read-only and governed side-effect cases on the exact changed head.
