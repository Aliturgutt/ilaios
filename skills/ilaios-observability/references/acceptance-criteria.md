# Acceptance Criteria — ILAIOS Observability

## GOLDEN
- Required workflows correlate runtime traces/metrics/logs/evaluations with exact request/version evidence and useful latency/error/retry/cost signals.
- Sensitive fields have explicit redaction/retention rules and provider/exporter choices are replaceable.

## NEGATIVE
- Missing telemetry cannot be interpreted as success.
- Reject secret logging, unrestricted raw sensitive payload capture, cross-tenant leakage, or a telemetry vendor becoming correctness authority.

## ADVERSARIAL
- User/tool/provider content cannot inject trace attributes that override trusted tenant, actor, policy, cost, or evidence identity.
- High-cardinality or attacker-controlled fields are bounded to avoid observability cost/availability attacks.

## MALFORMED
- Missing correlation identity, invalid timestamps, contradictory tenant/version fields, or required signal gaps are surfaced explicitly.

## REGRESSION
- Critical workflow telemetry, evaluation correlation, redaction, retention, and error classification remain observable after changes.
- Telemetry overhead and failure behavior must not bypass runtime/policy gates or silently break the user flow.
