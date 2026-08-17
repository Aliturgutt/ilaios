# ILAIOS Post-v1 Roadmap

Status: **SUPERSEDED PLANNING SNAPSHOT / NON-CANONICAL**
Truth-sync date: 17 August 2026
Observed implementation baseline before this truth sync: `1489183e6f5e19a50ba1d35f1c21955a63420f8d`

This file is a dependency guide only. It is not architecture authority and cannot promote capability maturity. Current reality is determined by current `master`, tests/Required CI, runtime/deployment/external evidence, then the mutable status projections.

## Current authority

Use evidence in this order:

1. current `master` code and exact commit lineage;
2. tests and Required CI;
3. runtime, provider, deployment and external evidence;
4. `PROJECT_STATUS.md` and `docs/governance/CAPABILITY_MATRIX.md` as mutable projections;
5. canonical architecture/specification documents for target truth.

No roadmap prose may override a lower observed lifecycle state.

## Completed near-term repository closures

- Web Factory bounded source/runtime closure is merged through #248; public Vercel production proof remains separate.
- Web accepted-state assurance hardening is merged through #255 and fails closed on incomplete/tampered accepted evidence.
- Governed Vercel delivery adapter #258 is merged with preview-first, authorization/budget-before-effects, exact provenance, health, promotion and rollback controls; it does not prove current public canonical-domain production.
- Windows-first App Factory P0 #97 is closed through #250 with real generated Flutter Windows build/package evidence; mobile/signing/Store remain separate.
- Desktop repository work progressed beyond #253 through the approved reference Home composition, canonical runtime brand packaging and Windows DPI/reference-shell regression coverage.
- Video Factory false-acceptance P0 #259 is closed by merged #267 at `1489183e6f5e19a50ba1d35f1c21955a63420f8d`. Stale #260 was not merged.
- #267 exact combined head `214720c5bd7ebff35e25ebaf71d4b3a15668d65d` passed Required CI, Desktop CI, Windows Gate, MSIX Packaging and Software Factory Final Evidence before merge.
- The Desktop path now fails closed rather than treating a deterministic placeholder MP4 as fulfillment of requested generated content.

## Critical Video provider boundary

The P0 code defect is closed, but live zero-cost provider availability is **NOT_VERIFIED**.

The free-only policy must remain fail-closed:

1. validate the explicit request and free-only model policy;
2. before any generation POST, query authoritative provider catalog data for the exact model;
3. require non-empty pricing data and every pricing SKU to parse to exactly zero;
4. reject missing, malformed, negative, unknown or non-zero pricing before generation spend;
5. require terminal provider accounting to resolve to exactly zero as a second independent gate;
6. require generated media retrieval/assembly, technical QA and independent semantic/perceptual acceptance before `*.finished_product` delivery.

A live attempt for `bytedance/seedance-2.0-fast:free` reported `USD 0.1704948`; therefore that route is not accepted as a proven zero-cost provider. No paid/unpriced fallback should be introduced to make the workflow appear available.

## Current dependency order

1. Preserve the single canonical Core, Execution Coordinator, capability registry, governance and evidence authorities.
2. Preserve the merged Video P0 fail-closed contract and finished-product-only delivery semantics.
3. Prove a live zero-cost Video provider/model only when authoritative pre-spend catalog data and terminal accounting both prove exact zero cost. Otherwise keep the provider route unavailable.
4. When Vercel project/team access and quota permit, produce exact-green-master public Web proof: deployment identity, canonical-domain linkage, browser/health certification and rollback evidence. Do not change billing/plans/DNS just to manufacture proof.
5. Complete Desktop external Microsoft App Registration/client ID and real login acceptance, then Partner Center package/publisher identity, production signing, certification and Store publication through the governed release boundary.
6. Execute RAG.14 live canary/evidence only with explicit bounded external credentials/spend authority and exact production embedding/index, tenant/auth/DLP/leakage, SLO/recovery and deploy/rollback evidence.
7. Strengthen production tenant isolation, managed cryptography/KMS, provider routing/fallback/cost evidence, SLO/alert operations and recurring recovery drills.
8. Broaden Research/Data, Creative/Document and Security workloads only with capability-specific executable evidence; keep Commerce/Growth and Personal Operations externally fail-closed without governed account/channel authority.
9. Implement Android/iOS only after platform architecture, build, signing, test and store gates exist; Windows App evidence is not mobile proof.
10. Implement commercial plan/entitlement/usage/billing capability before monetized public SaaS launch.
11. Create the first formal SemVer tag/GitHub Release only from an exact release-ready SHA after release-specific licensing/redistribution clearance, SBOM/notices/artifact preparation and required CI.

## Architecture invariants

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
- Vercel billing/plan or account-ownership changes;
- signing certificates and signing secrets;
- Partner Center / Store identity and final submissions;
- paid channel spend;
- legal terms and release-specific redistribution/licensing decisions.

Repository code, tests or CI must not fabricate completion of those external proofs.

## Definition of done

A capability closes only through the canonical maturity chain:

`DESIGNED -> SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> DEPLOYED / PRODUCTION`

`PRODUCTION` requires real runtime/external evidence wherever the capability has external effects. Current state remains governed by observed evidence, not this roadmap.
