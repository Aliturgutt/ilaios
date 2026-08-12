# ILAIOS Threat Model

Status: CONTROLLED

## Assets
Primary assets include identities, tenant/customer data, secrets, policy/approval state, audit/evidence records, source and release artifacts, provider credentials, signing identities, billing authority, and production infrastructure.

## Trust boundaries
Key boundaries are: user/client to control plane; control plane to execution workers; tenant to tenant; service to provider; CI to cloud; repository to release pipeline; runtime to secret store; public website to internal systems; desktop client to backend authority.

## Principal threats
- authorization or tenant-boundary bypass;
- prompt/tool injection causing unauthorized actions;
- credential theft or exfiltration;
- malicious or compromised dependency/action;
- forged audit/release evidence;
- CI/CD compromise or artifact substitution;
- SSRF/data exfiltration through tools/providers;
- insecure desktop update/signing path;
- destructive or cross-tenant data operations;
- availability exhaustion and cost abuse.

## Mandatory mitigations
Server-side authorization; least privilege; deny-by-default tool grants; tenant-scoped identifiers and queries; secret-store injection; output/log redaction; immutable release evidence; dependency pinning; protected branches; explicit production approvals; negative authorization tests; rate/quota controls; monitored privileged actions; rollback/recovery capability.

## Residual risk
Third-party provider compromise, zero-days, operator-account compromise, and external cloud/service outages cannot be eliminated. They must be reduced through isolation, limited credentials, provider failover where designed, backups, monitoring, and incident response.

## Review
Update after architecture boundary changes, new factories/providers, authentication changes, material incidents, or production topology changes.
