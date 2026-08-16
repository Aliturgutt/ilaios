# ILAIOS Post-v1 Roadmap

Status: **SUPERSEDED PLANNING SNAPSHOT / NON-CANONICAL**
Truth-sync date: 17 August 2026

This file previously proposed a post-v1 selection sequence from an earlier repository audit. That proposal is no longer a reliable current-state plan: master protection is active, Knowledge/RAG has a merged bounded implementation plus RAG.14 repository-side production-readiness machinery, Web Factory closure and accepted-assurance hardening are merged, Windows-first App finished-product closure is merged, and the canonical Execution Coordinator now has verified bounded finished-product paths for Video, Web, Software and Windows-first App generation.

The historical proposal remains recoverable in Git history. It must not be used as current execution authority.

## Current authority

For current reality, use evidence in this order:

1. current `master` code and exact commit lineage;
2. tests and Required CI;
3. runtime/deployment/external evidence;
4. `PROJECT_STATUS.md` and `docs/governance/CAPABILITY_MATRIX.md` as mutable projections;
5. canonical architecture/specification documents for target truth.

No roadmap prose may promote a capability beyond its observed evidence.

## Current post-v1 direction

The correct strategy is **product-integration, production-hardening and external-evidence closure on the existing architecture**, not selection of a new Core, router, orchestrator or parallel factory generation.

Dependency order is:

1. preserve the single canonical Execution Coordinator, adapter registry, governance and evidence authorities;
2. preserve the merged verified bounded Video/Web/Software/App Windows finished-product paths, the Desktop interactive closure and Web accepted-evidence fail-closed semantics; close only their remaining breadth/external-production gaps;
3. when the Vercel daily quota/account-project blocker clears, produce exact-green-master public Web deployment evidence: deployment identity, canonical-domain linkage, live browser/health certification and rollback proof;
4. complete Desktop external Microsoft App Registration/client ID and real login persistence acceptance, then Partner Center publisher/package identity, production signing, certification and Store publication through the separate governed release boundary;
5. execute guarded RAG.14 live canary/evidence only with explicit bounded external credentials/spend authority and exact production embedding/index, tenant/auth/DLP/leakage, SLO/recovery and deploy/rollback evidence;
6. strengthen production tenant isolation, managed cryptography/KMS, provider-specific routing/fallback/cost evidence, SLO/alert operations and recurring recovery drills;
7. broaden Research/Data, Creative/Document and Security capabilities only when their required input/scope bindings and executable finished-product/external evidence exist;
8. keep Commerce/Growth and Personal Operations externally fail-closed until governed channel/account mutations, approvals and reconciliation exist;
9. implement Android/iOS only after platform-specific architecture, build, signing, test and store gates are available; the verified Windows App adapter is not evidence for mobile readiness;
10. implement commercial plan/entitlement/usage/billing capability before monetized public SaaS launch;
11. create the first formal SemVer tag/GitHub Release only from an exact release-ready SHA after release-specific licensing/redistribution clearance, artifact/SBOM/notices preparation and required CI.

## Completed near-term closures

- Web Factory source/runtime closure is merged through PR #248 with exact-head Required CI and certified Next.js/Chromium evidence. Public Vercel production proof remains separate.
- Windows-first App Factory P0 issue #97 is closed through merged PR #250 after exact-head Required CI and a real generated Flutter Windows build/package artifact passed the platform gates.
- The App closure remains intentionally bounded; it does not imply arbitrary application generation, production signing, Store publication, Android/iOS or commercial deployment.
- Desktop interactive/current-master closure is merged through PR #253 after exact-head Required CI, Desktop CI, Windows Gate, MSIX Packaging and Software evidence passed. It preserves truthful operational rendering and does not invent Microsoft external acceptance.
- Web durable accepted-state fail-closed hardening is merged through PR #255 after exact-head Required CI, Web Browser E2E, Windows Gate and Software evidence passed. Accepted Web state now requires source-assurance and certified gate receipts rather than trusting legacy/tampered accepted rows.
- At the 17 August truth-sync snapshot there are no open GitHub issues in `Aliturgutt/ilaios`.

## Existing architecture invariants

Post-v1 work must not create:

- `Core 2`;
- a second global router;
- a second orchestration authority;
- a second policy engine;
- a second capability registry;
- a factory-local parallel RAG authority;
- an evidence-free `PLATFORM.P21` or `RELEASE.R04` merely to continue numbering.

Existing components evolve in place through bounded, tested and evidence-backed changes.

## External-action boundary

The following remain separate governed/external actions when applicable:

- credentials, OAuth/provider registration and 2FA/CAPTCHA;
- cloud/provider spend authorization;
- production DNS/deployment mutation not already authorized by a release workflow;
- Vercel billing/plan changes or account ownership changes;
- signing certificates and signing secrets;
- Partner Center / Store identity and final submissions;
- paid channel spend;
- legal terms and release-specific redistribution/licensing decisions.

Repository code, tests or CI must not fabricate completion of those external proofs.

## Definition of done

This roadmap is only a dependency guide. A capability closes only through the canonical maturity chain:

`DESIGNED -> SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> DEPLOYED / PRODUCTION`

`PRODUCTION` requires real runtime/external evidence where the capability has external effects. Current state remains governed by live evidence, not this file.
