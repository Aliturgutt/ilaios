# sf-recovery

Identity: `sf-recovery` v1.0.0, IMPLEMENTED, build-release-operations, critical risk.

Purpose: recommend idempotent governed recovery for failed jobs, interrupted validation, worker failure, stale workspace, failed build or failed promotion proposal. Inputs: `intent`, `failure_evidence`. Outputs: failure classification, cleanup, retry eligibility, resume recommendation, escalation.

Recovery recommendations cannot bypass governance, mutate production, or self-approve promotion. Independent review is required for critical recovery decisions.

The common `../CONTRACT.md` applies.
