# Incident Response Runbook

Status: CONTROLLED

## Severity
SEV-1: active compromise, cross-tenant exposure, signing/production credential compromise, or major production outage. SEV-2: material security degradation or contained exposure. SEV-3: limited issue with no confirmed sensitive-data/production impact. SEV-4: low-risk observation.

## Workflow
1. Detect and open a private incident record.
2. Establish severity, affected assets, start time, and incident owner.
3. Preserve volatile evidence before destructive cleanup where safe.
4. Contain: revoke/rotate compromised credentials, isolate affected workloads, block abusive access, or halt promotion as appropriate.
5. Eradicate root cause with a bounded repair.
6. Recover through governed deployment and restore procedures.
7. Verify service, authorization, tenant boundaries, data integrity, observability and security regression tests.
8. Close only after residual risk and follow-up actions are recorded.

## Communications
Do not disclose secrets or unverified attribution. Legal/regulatory/customer notification decisions require applicable human/legal review.

## Evidence
Retain timeline, indicators, affected versions/environments, actions, approvals, CI/deployment IDs, rotated credential identifiers (not values), and verification results.

## Postmortem
SEV-1/2 require a blameless technical postmortem covering root cause, detection gap, control failure, impact, corrective actions, owner and due date. Incident closure does not waive incomplete corrective actions.
