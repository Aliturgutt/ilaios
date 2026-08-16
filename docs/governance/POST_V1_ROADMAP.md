# ILAIOS Post-v1 Roadmap

Status: **SUPERSEDED PLANNING SNAPSHOT / NON-CANONICAL**
Truth-sync date: 16 August 2026

This file previously proposed a post-v1 selection sequence from an earlier repository audit. That proposal is no longer a reliable current-state plan: master protection is now active, Knowledge/RAG has a merged bounded implementation plus RAG.14 production-readiness machinery, and product integration has advanced through the canonical Execution Coordinator plus bounded Video/Web/Software finished-product paths.

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

The correct near-term strategy is **product-integration and production-evidence closure on the existing architecture**, not selection of a new Core, router, orchestrator or parallel factory generation.

Dependency order is:

1. preserve the single canonical Execution Coordinator and adapter registry;
2. preserve the merged bounded Video/Web/Software finished-product paths and close only their remaining real external/deployment evidence gaps;
3. complete Desktop real Windows OIDC/package acceptance, then signing/Partner Center/Store evidence through the separate governed release boundary;
4. execute the guarded RAG.14 live canary/evidence path only with explicit bounded external-spend authority and exact release evidence;
5. close App finished-product issue `#97` only when a real Windows-first Flutter implementation/build/package artifact can pass the existing platform gates;
6. keep Research/Data, Creative/Document and Security capabilities bounded until their required input/scope bindings and executable finished-product evidence exist;
7. keep Commerce/Growth and Personal Operations review-only until governed external channel/account mutations and reconciliation are implemented;
8. implement Mobile only after higher-priority product closure and platform-specific build/sign/store gates are available;
9. implement the commercial plan/entitlement/usage/billing layer before public SaaS monetization requires it;
10. create the first formal SemVer tag/GitHub Release only from an exact release-ready SHA after release-specific licensing/redistribution and required CI gates are satisfied.

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
- signing certificates and signing secrets;
- Partner Center / Store identity and final submissions;
- paid channel spend;
- legal terms and release-specific redistribution/licensing decisions.

Repository code, tests or CI must not fabricate completion of those external proofs.

## Definition of done

This roadmap is only a dependency guide. A capability closes only through the canonical maturity chain:

`DESIGNED -> SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> DEPLOYED / PRODUCTION`

`PRODUCTION` requires real runtime/external evidence where the capability has external effects. Current state remains governed by live evidence, not this file.
