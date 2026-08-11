# ILAIOS Security Policy

## Scope

This policy covers the ILAIOS source repository, control-plane services, runtime components, infrastructure definitions, automation code and repository-managed product clients.

A repository file, test or document is not by itself proof that a capability is production-safe. Security claims require executable evidence appropriate to the risk.

## Reporting a vulnerability

Do not place secrets, credentials, private customer data, exploit material or sensitive infrastructure details in a public issue or pull request.

Report security concerns privately to the repository owner through an authenticated private channel. Include only the minimum information needed to reproduce and assess the issue. Credentials and secret values must never be included unless a deliberately approved secure exchange method is established.

## Security invariants

Changes must preserve the following invariants:

- backend/control-plane authority for authorization, policy, tenant boundaries and governed execution;
- least-privilege credentials and scoped execution grants;
- fail-closed behavior on missing or ambiguous security prerequisites;
- no test weakening to obtain a passing build;
- no dependency or approval bypass;
- no secret material committed to Git;
- no autonomous production promotion;
- no force-push or history rewrite as a routine recovery mechanism;
- independent verification when risk policy requires it;
- evidence and audit records must not be fabricated.

## Secrets

Secrets belong in approved secret stores and must be injected at runtime. Repository code may contain secret references, schemas and test fixtures only when they cannot be used as real credentials.

If a credential is accidentally committed, treat it as compromised: revoke/rotate it first, then remove or remediate repository exposure through a governed recovery process. Merely deleting the current file is not sufficient.

## Dependency and supply-chain changes

New dependencies require a concrete need, maintained upstream source, bounded permissions and compatibility with the project's security model. Build and release artifacts should preserve provenance, integrity checks and dependency evidence where available.

## Production-impacting changes

Production infrastructure, signing identity, DNS, billing, release promotion and external-account actions require explicit authorization. Repository automation must prepare and validate these operations but must not infer permission to execute them.

## Security response lifecycle

1. Record the report privately.
2. Reproduce without broadening exposure.
3. Determine affected components and release states.
4. Create a bounded repair branch/package.
5. Add regression and negative tests.
6. Run required repository quality and security gates.
7. Deploy only through governed release controls.
8. Verify remediation in the affected environment.
9. Preserve evidence and lessons learned without disclosing secrets.

## Certification boundary

Passing repository security tests does not imply external certification, regulatory compliance or third-party security approval. Such claims require the applicable independent process and evidence.
