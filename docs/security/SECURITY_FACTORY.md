# ILAIOS Security Factory v1

Status: bounded defensive repository implementation.

## Purpose

Security Factory consolidates the defensive security concepts inherited from historical Hermes, ILAKOS and ILATEN designs behind the single active ILAIOS capability `ilaios.capability.security-factory`.

It does not create a parallel security authority. Platform policy, execution grants, tenant boundaries, evidence requirements and independent verification remain authoritative.

## v1 capabilities

`services/security_factory.py` provides deterministic, repository-local controls for:

- source-pattern security analysis for high-risk dynamic execution constructs;
- credential-pattern detection for selected high-confidence secret material;
- dependency pinning review for Python requirements and project dependencies;
- infrastructure configuration checks for selected world-open and wildcard-permission patterns;
- non-destructive HTTP security-header observation analysis;
- blocking-finding remediation/retest comparison;
- independent producer/verifier separation.

## Authorization boundary

A `SecurityScope` is mandatory. Security Factory v1 fails closed when:

- the scope ID is missing;
- the repository root does not exist;
- external-network testing is requested;
- DAST observations reference a host outside the configured localhost/test allowlist.

The v1 DAST path does not initiate network traffic. It evaluates supplied observations for explicitly authorized local/test targets. This avoids silently converting a repository security capability into an external scanner.

## Explicit non-goals

Security Factory v1 does not:

- exploit vulnerabilities;
- scan arbitrary Internet targets;
- bypass authentication or authorization;
- mutate production infrastructure;
- rotate credentials;
- claim third-party penetration-test coverage;
- claim regulatory certification;
- independently promote a release.

External penetration testing, independent certification and provider-specific security assessment remain separate evidence requirements.

## Agent organization

The canonical security roles are registered in `services/agent_registry.py`:

- SecurityCoordinator
- CodeSec
- WebAPISec
- SupplyChainSec
- InfrastructureSec
- SecurityVerifier

Registry membership proves stable ILAIOS identity and governance metadata. It does not by itself prove a specialized autonomous executor. Executor maturity remains evidence-driven.

## Release blocking

A repository report fails when one or more findings have severity `HIGH` or `CRITICAL`. Medium findings remain visible but do not automatically become release-blocking in this primitive; the governing workflow may impose a stricter policy.

A producer may not independently verify its own report. Verification requires a distinct verifier identity.

## Evidence and maturity

The implementation is `IMPLEMENTED` when merged with passing repository gates. It should not be promoted to broad `VERIFIED` or `PRODUCTION` security capability without bounded E2E evidence appropriate to each scanner class and, where required, independent external assessment.
