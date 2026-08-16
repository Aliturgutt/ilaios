# ILAIOS — Repository Project Status

Status snapshot: 16 August 2026
Baseline branch: `master`
Baseline commit at this truth-sync: `c1883342816011dd1c359f90cce104d6384dfe1a`

## Authority rule

This file is a human-readable status projection. It is not a canonical architecture or release authority. If this file conflicts with repository code, tests, CI, runtime evidence, deployment evidence, or canonical implementation authorities, the lower proven lifecycle state wins until the conflict is reconciled.

## Current verified state

- Master commercial/product identity: ILAIOS.
- Canonical v1 execution chain is completed through `RELEASE.R03`.
- `RELEASE.R01`: CANARY deployment evidence exists and is healthy.
- `RELEASE.R02`: LIMITED deployment evidence exists and is healthy.
- `RELEASE.R03`: PRODUCTION deployment evidence records `PRODUCTION_DEPLOYED_HEALTHY` for the governed platform release chain.
- Production release evidence records TLS, OIDC, target health and rollback availability for that platform release scope.
- Repository includes Core, Code Intelligence, Knowledge Graph, Project Manager, Video Automation, Control Plane, governance, evidence, privacy, observability, operations and deployment implementations.
- The one canonical Execution Coordinator is merged with durable lifecycle, fail-closed routing, recovery/cancellation, evidence and bounded multi-capability DAG execution.
- Verified bounded finished-product execution is now wired for Video plus registered Web, Software and Windows-first App product runtimes. Wider arbitrary-product, external-provider and commercial-production claims remain evidence-gated.
- Web Factory PR #248 is merged. Its bounded closure includes generated-source assurance, bounded repair, real Next.js production build/start, Chromium responsive E2E, accessibility/SEO/security checks, first-party contact/content/newsletter/search features and content-addressed local deployment/rollback evidence. It does not prove a current public Vercel production deployment.
- Software Factory remains verified for its bounded local finished-product scope with real Windows evidence; arbitrary software generation and commercial external delivery are not implied.
- App Factory PR #250 is merged. A bounded Windows task/checklist Flutter application is generated through the canonical Coordinator, formatted, analyzed, tested, built as a real Windows release, packaged, smoke-tested and persisted with exact-head content-addressed evidence. The exact pre-merge head `ddf6ca4e4a79c4dfb024788a4513bfa5f7eec6f4` passed Required CI, Desktop CI, MSIX Packaging, Windows Gate, Web Factory Browser E2E and Software Factory Final Evidence. Issue #97 is closed for this bounded Windows-first scope.
- The exact App Windows evidence artifact for that head was `app-windows-finished-product-ddf6ca4e4a79c4dfb024788a4513bfa5f7eec6f4-31971331229`, size `113078073` bytes, digest `sha256:a6660940d445cb9067d6b1cdacf8300c801df48cad3177cd17723e29c172aff7`.
- Desktop repository readiness advanced through PR #249: EN/TR product surfaces, MSIX language resources, package identity regression coverage, responsive/scaling coverage and truthful Store-listing material are present. Real Microsoft App Registration/client ID, Microsoft external login acceptance, Partner Center identity, production signing, certification and Store publication remain separate external gates.
- Website and Desktop remain active product surfaces with their own live/external acceptance boundaries.

## Canonical v1 completion

The canonical implementation namespace remains:

1. `PRE.S00`
2. `VIDEO.V01` through `VIDEO.V30`
3. `PRE.S01`
4. `PLATFORM.P00` through `PLATFORM.P20`
5. `RELEASE.R00` through `RELEASE.R03`

No new milestone ID is canonical merely because it appears in a planning document. Post-v1 work remains dependency-ordered, bounded and additive to the existing governance model.

## Current repository governance state

### Verified live controls

- `ILAIOS Master Protection` repository ruleset is active on the default branch.
- Non-fast-forward updates and branch deletion are blocked.
- Pull requests are required.
- Review-thread resolution is required.
- `Required CI Gate` is a required status check.
- No bypass actor is configured and the connected owner cannot bypass the ruleset.
- `.github/CODEOWNERS` covers repository default, canonical documentation, governance/security/operations/ADR areas, workflows, infrastructure and release-sensitive automation files.

### Completed truth/hygiene work

- Stale Desktop PR chains were consolidated and superseded branches/PRs were identified rather than treated as parallel authorities.
- Generic Web finished-product issue #96 and Software finished-product issue #98 were closed after exact-head finished-product/CI evidence.
- Web closure PR #248 was merged after exact-head Required CI and Web Factory Browser E2E passed; older parallel Web closure PR #238 was closed as superseded.
- App closure PR #250 was rebuilt on the current post-Web master rather than merging stale PR #233. Exact-head Required CI and real Windows packaged-app evidence passed; #250 was squash-merged and #233 was closed as superseded.
- App finished-product issue #97 is closed with exact artifact evidence for the bounded Windows-first scope.

### Remaining governance/repository gaps

- Required approving review count is currently `0`; CODEOWNER approval and last-push approval are not enforced by the active ruleset. Required CI is therefore the current independent automated verifier, not a human-review guarantee.
- Repository metadata still requires owner-level cleanup if the GitHub connector does not expose repository-description/homepage/topic mutation: the public description is stale, the homepage is stale relative to the canonical domain, and topics are empty.
- `docs/governance/LICENSE_DECISION.md` records publicly visible source with a proprietary-by-default/no-open-source-grant posture. A release-specific legal/redistribution package, dependency notices and exact commercial distribution terms still require governed release review; no root OSI license is implied or invented.
- GitHub Releases and immutable version tags remain empty even though platform production deployment evidence exists. The first formal product release must not be created until an exact release-ready SHA and release/licensing gates are satisfied.

## External/public deployment truth

- The connected Vercel API context does not currently resolve the `ilaios` project even though the GitHub Vercel integration has historical ILAIOS deployment records.
- On 16 August 2026 the Vercel Git integration also reported the Free-plan daily deployment limit (`api-deployments-free-per-day`) for new ILAIOS deployments. That is an external quota/account condition, not a repository code failure.
- Therefore current Web Factory evidence must remain `VERIFIED bounded/local finished-product` rather than `public production deployed` until an exact master SHA is publicly deployed, domain-linked, health-checked and rollback-proven.
- An external quota/project-access watch may observe when a safe public deployment becomes possible; it must not change billing, plans, credentials or DNS automatically.

## Post-v1 product integration status

Product integration has advanced on `master` without creating a second Core, router, scheduler, policy engine or Coordinator.

Current dependency-ordered direction:

1. preserve the single canonical Coordinator and adapter registry;
2. preserve the verified bounded Video/Web/Software/App Windows finished-product paths and close only their remaining real external/deployment breadth gaps;
3. complete exact-SHA public Web deployment evidence when the Vercel quota/account-project blocker is resolved without inventing production state;
4. complete Desktop external Microsoft App Registration/login acceptance, Partner Center identity, production signing, certification and Store publication through the separate governed release boundary;
5. execute guarded RAG.14 live canary/evidence only with explicit approved external credentials/spend and exact deploy/rollback evidence;
6. strengthen production tenant isolation, managed cryptography, observability/SLOs, recovery drills and provider-specific runtime evidence without weakening fail-closed controls;
7. broaden Research/Data, Creative/Document, Security, Commerce/Growth and Personal Operations only with capability-specific executable/external evidence;
8. implement Android/iOS only after platform-specific architecture/build/sign/store gates are available;
9. implement commercial plan/entitlement/usage/billing capability before monetized public SaaS launch requires it;
10. create the first formal SemVer tag/GitHub Release only from an exact release-ready SHA after licensing/redistribution clearance and required CI.

See:

- `docs/governance/CAPABILITY_MATRIX.md`
- `docs/governance/CI_WORKFLOW_AUDIT.md`
- `docs/governance/POST_V1_ROADMAP.md`
- `docs/governance/RELEASE_VERSION_POLICY.md`
- `docs/governance/LICENSE_DECISION.md`
- `.github/CODEOWNERS`

## Safety boundary

Repository automation must not autonomously:

- create or rotate secrets/credentials;
- change billing/spend or authorize paid external effects;
- accept legal terms or make an unresolved licensing decision;
- submit Microsoft Store releases or bypass Store identity/signing controls;
- force-push or rewrite Git history;
- weaken tests, branch rules or required CI;
- redefine canonical architecture by prose;
- label mock, fixture, synthetic, bounded-local or preview evidence as external production proof.

Production AWS/DNS/deployment mutations remain governed by their explicit release/deployment authority and evidence requirements; repository source changes alone do not authorize them.

## Current decision

The platform v1 build/release chain has production deployment evidence and the canonical Coordinator now has verified bounded finished-product paths for Video, Web, Software and Windows-first App generation. The remaining work is primarily external/public proof, production hardening, capability breadth, mobile/commercial layers and governed release closure on the existing architecture—not `Core 2`, a parallel Coordinator, an invented `PLATFORM.P21`, or an evidence-free `RELEASE.R04`.
