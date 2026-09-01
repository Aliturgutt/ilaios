# Non-Microsoft Release Closeout

Status: CONTROLLED

## Purpose

This document defines the release boundary that can be completed while Microsoft external approval remains pending. It does not weaken `docs/release/RELEASE_EVIDENCE_STANDARD.md` and it does not convert repository evidence into a production claim.

## Explicit Microsoft exclusion

The following dependencies are outside this closeout and remain external blockers for Microsoft distribution:

- Microsoft Desktop OIDC application approval / final public Application (client) ID acceptance;
- trusted Microsoft-compatible publisher identity and signed MSIX proof;
- Partner Center submission, Store certification, declarations, and publication.

These exclusions do not authorize bypasses. They simply prevent Microsoft-owned external work from blocking verification of the rest of the product.

## Repository implementation boundary

The non-Microsoft repository closeout requires all of the following to be verified against one exact source SHA:

- packaged Google Desktop OIDC public registration and the existing PKCE/JWKS identity boundary;
- Desktop Windows build/runtime gate and unsigned internal package validation;
- verified Web Factory and Software Factory adapters through the canonical `ExecutionCoordinator`;
- provider-backed Video Factory remaining fail-closed unless a real provider is configured and terminal evidence proves the allowed cost policy;
- full repository CI;
- deterministic release manifest bound to artifact SHA-256 digests;
- SBOM and third-party notices evidence;
- artifact checksums/provenance;
- commercial entitlement admission composed with the existing managed-credit ledger.

`services.commercial_access` owns entitlement state only. It does not create a second pricing, routing, balance, settlement, or duplicate-spend authority. Paid-provider reservation and settlement delegate to `ManagedCreditLedgerStore`.

`services.release_manifest` binds an exact source SHA to immutable artifacts, SBOM/notices digests, and evidence identities. It never claims that those artifacts were deployed or signed.

`services.non_microsoft_release_readiness` aggregates explicit evidence and returns only the highest state actually proven:

- `REPOSITORY_INCOMPLETE`
- `EXTERNAL_PROOF_PENDING`
- `PRODUCTION_READY`

Microsoft dependencies are recorded as excluded external dependencies and are not silently treated as passed.

## External proof still required for PRODUCTION_READY

Repository completion alone is insufficient. The non-Microsoft release gate remains `EXTERNAL_PROOF_PENDING` until all of the following have exact evidence:

1. the declared public website domain serves the exact verified source revision and passes the live-domain browser certification;
2. at least the required real provider route passes its production certification, including cost evidence and finished-product artifact evidence;
3. the selected merchant/payment path passes a real checkout/settlement proof and only then emits a durable entitlement event into the provider-neutral entitlement boundary.

A missing Vercel project, provider credential, merchant account, deployment identity, or real external receipt cannot be replaced by a mock, local test, screenshot, or manually asserted boolean.

## Current Desktop composition

The packaged Desktop sidecar composes the canonical Control Plane, governance, grants, evidence, and `DesktopExecutionCoordinator`. Web and Software runtimes are registered into that coordinator. Video becomes provider-backed only when an approved OpenRouter credential is supplied; otherwise it reports the provider route as unavailable. The bundled Google OIDC public registration remains the default non-Microsoft human sign-in provider.

The App Factory has a separately verified bounded Windows task/checklist runtime, but it is not promoted into the packaged Desktop composition until the host supplies the required enforceable `SecureCommandBoundary`. This closeout must not substitute the fail-closed boundary with unrestricted subprocess execution merely to make the capability appear available.

## Commercial safety

Commercial access does not imply unlimited provider spend. An active entitlement may authorize paid providers, but every paid provider request still requires:

- the canonical routing decision;
- a bounded `ProviderCostQuote`;
- sufficient managed credits;
- durable reservation before the side effect;
- duplicate-side-effect protection;
- settlement against actual provider cost, or release/reconciliation on failure.

If any of these conditions is missing, paid execution remains blocked.

## Release rule

The release may be called `PRODUCTION_READY` only when the exact-source repository evidence and every non-Microsoft external proof above are green together. Until then the correct state is the highest state emitted by the readiness gate. Microsoft distribution remains a separate later gate.
