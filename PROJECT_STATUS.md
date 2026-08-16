# ILAIOS — Repository Project Status

Status snapshot: 17 August 2026
Baseline branch: `master`
Observed implementation baseline before this truth-only sync: `26885fa4b1c585dbf24d446e6858caf7ab6de500`

## Authority rule

This file is a human-readable mutable status projection. It is not a canonical architecture or release authority. If this file conflicts with repository code, tests, CI, runtime evidence, deployment evidence, or canonical implementation authorities, the lower proven lifecycle state wins until the conflict is reconciled.

## Current verified state

- Master commercial/product identity: ILAIOS.
- Canonical v1 execution chain is completed through `RELEASE.R03`.
- `RELEASE.R01`: CANARY deployment evidence exists and is healthy.
- `RELEASE.R02`: LIMITED deployment evidence exists and is healthy.
- `RELEASE.R03`: PRODUCTION deployment evidence records `PRODUCTION_DEPLOYED_HEALTHY` for the governed platform release-chain scope.
- Production release evidence records TLS, OIDC, target health and rollback availability for that platform release scope.
- Repository includes Core, Code Intelligence, Knowledge Graph, Project Manager, Video Automation, Control Plane, governance, evidence, privacy, observability, operations and deployment implementations.
- The one canonical Execution Coordinator is merged with durable lifecycle, fail-closed routing, recovery/cancellation, evidence and bounded multi-capability DAG execution.
- Verified bounded finished-product execution is wired for Video plus registered Web, Software and Windows-first App product runtimes. Wider arbitrary-product, external-provider and commercial-production claims remain evidence-gated.
- Web Factory PR #248 is merged. Its bounded closure includes generated-source assurance, bounded repair, real Next.js production build/start, Chromium responsive E2E, accessibility/SEO/security checks, first-party contact/content/newsletter/search features and content-addressed local deployment/rollback evidence. It does not prove a current public Vercel production deployment.
- Web durable-acceptance hardening PR #255 is merged at `4d49a432659002a6c8ed8a759cf61f5d0d2f39f1`. Its exact pre-merge head `37d8c6560aeeae32d1abae0f443217d7feb94f87` passed Required CI, Web Factory Browser E2E, Desktop Windows Gate and Software Factory Final Evidence. Accepted Web manifests now fail closed unless source assurance, QA source-assurance promotion, certified source/build binding and PASS design/accessibility/SEO/security/performance receipts are present.
- Governed Vercel Web delivery boundary PR #258 is merged at `26885fa4b1c585dbf24d446e6858caf7ab6de500`. Its exact pre-merge head `a5222af70a8ef7189986a98cb414bb0be8082759` passed Required CI, Web Factory Browser E2E, Desktop Windows Gate and Software Factory Final Evidence. The adapter is preview-first, requires authorization and budget proof before credential/network access, rejects secret-bearing `.env*` source, binds exact source/artifact provenance, verifies immutable preview HTTPS health, promotes only after preview acceptance, requires the predeclared production alias, rejects off-host redirects, and revalidates exact provenance/alias/health on rollback. This proves the repository-side provider boundary only; it does not prove a current live ILAIOS Vercel production deployment.
- Software Factory remains verified for its bounded local finished-product scope with real Windows evidence; arbitrary software generation and commercial external delivery are not implied.
- App Factory PR #250 is merged. A bounded Windows task/checklist Flutter application is generated through the canonical Coordinator, formatted, analyzed, tested, built as a real Windows release, packaged, smoke-tested and persisted with exact-head content-addressed evidence. The exact pre-merge head `ddf6ca4e4a79c4dfb024788a4513bfa5f7eec6f4` passed Required CI, Desktop CI, MSIX Packaging, Windows Gate, Web Factory Browser E2E and Software Factory Final Evidence. Issue #97 is closed for this bounded Windows-first scope.
- The exact App Windows evidence artifact for that head was `app-windows-finished-product-ddf6ca4e4a79c4dfb024788a4513bfa5f7eec6f4-31971331229`, size `113078073` bytes, digest `sha256:a6660940d445cb9067d6b1cdacf8300c801df48cad3177cd17723e29c172aff7`.
- Desktop interactive/current-master closure PR #253 is merged at `61a86f9c1cbb309d06a9df69c3fb48477936c253`. Its exact head `af333a8e6d72c7c02e0cc9b9f39960d0fcb72280` passed Required CI, Desktop CI, Windows Gate, MSIX Packaging and Software Factory Final Evidence. The Desktop shell now has real product navigation, persistent light/dark theme behavior, responsive shell/drawer behavior and truthful operational rendering: authoritative event counts are not mislabeled as rates and unknown progress is not rendered as implied activity.
- Desktop repository readiness also preserves the earlier PR #249 EN/TR surfaces, MSIX language resources, package-identity regression coverage, responsive/scaling coverage and truthful Store-listing material. Real Microsoft App Registration/client ID, Microsoft external login acceptance, Partner Center identity, production signing, certification and Store publication remain separate external gates.
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

- Stale Desktop PR chains were consolidated rather than treated as parallel authorities.
- Generic Web finished-product issue #96 and Software finished-product issue #98 were closed after exact-head finished-product/CI evidence.
- Web closure PR #248 was merged after exact-head Required CI and Web Factory Browser E2E passed; older parallel Web closure PR #238 was closed as superseded.
- App closure PR #250 was rebuilt on the current post-Web master rather than merging stale PR #233. Exact-head Required CI and real Windows packaged-app evidence passed; #250 was squash-merged and #233 was closed as superseded.
- App finished-product issue #97 is closed with exact artifact evidence for the bounded Windows-first scope.
- Desktop interactive closure PR #253 was rebuilt on current master; stale PR #251 was superseded. Exact-head repository, Desktop, Windows and MSIX gates passed before merge.
- Web accepted-assurance hardening was rebuilt as PR #255 on post-Desktop master rather than using stale-base PR #254. The stale PR was closed and #255 was merged only after exact-head Required CI and browser/Windows evidence passed.
- Vercel production-delivery adapter PR #257 was rejected as a merge authority after red-team review found premature production targeting, weak alias proof and a Windows regression. Successor PR #258 rebuilt the boundary on current master with preview-first promotion, exact expected-alias proof, strict HTTPS host checks and documented Vercel REST semantics; all exact-head gates passed before merge.
- At this status snapshot there are no known open implementation issues from the previously audited P0/P1 closure set; a final live GitHub scan remains authoritative for newly-created work.

### Remaining governance/repository gaps

- Required approving review count is currently `0`; CODEOWNER approval and last-push approval are not enforced by the active ruleset. Required CI is therefore the current independent automated verifier, not a human-review guarantee.
- Repository metadata still requires owner-level/API-capability cleanup where the connector cannot mutate repository description/homepage/topics.
- `docs/governance/LICENSE_DECISION.md` records publicly visible source with a proprietary-by-default/no-open-source-grant posture. A release-specific legal/redistribution package, dependency notices and exact commercial distribution terms still require governed release review; no root OSI license is implied or invented.
- GitHub Releases and immutable version tags remain empty even though platform production deployment evidence exists. The first formal product release must not be created until an exact release-ready SHA and release/licensing gates are satisfied.

## External/public deployment truth

- The repository now has a verified governed Vercel delivery adapter that can create a preview, reconcile exact source/artifact provenance, health-check it, promote it, prove the expected production alias and perform a provenance-checked rollback.
- The connected Vercel API context did not resolve the `ilaios` project during the latest audit even though the GitHub Vercel integration has historical ILAIOS deployment records.
- On 16 August 2026 the Vercel Git integration reported the Free-plan daily deployment limit (`api-deployments-free-per-day`) for new ILAIOS deployments. That is an external quota/account condition, not a repository code failure.
- Therefore current Web Factory evidence remains `VERIFIED bounded/local finished-product + VERIFIED provider delivery boundary` rather than `public production deployed` until an exact green master SHA is actually deployed through the correct Vercel project/team, canonical-domain linked, health/browser certified and rollback-proven.
- The configured external quota/project-access watch may observe when a safe public deployment becomes possible; it must not change billing, plans, credentials or DNS automatically.

## Post-v1 product integration status

Product integration has advanced on `master` without creating a second Core, router, scheduler, policy engine or Coordinator.

Current dependency-ordered direction:

1. preserve the single canonical Coordinator and adapter registry;
2. preserve the verified bounded Video/Web/Software/App Windows finished-product paths, Web accepted-evidence fail-closed semantics and the governed Vercel delivery boundary;
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

The platform v1 build/release chain has production deployment evidence and the canonical Coordinator now has verified bounded finished-product paths for Video, Web, Software and Windows-first App generation. Desktop interactive repository closure, Web accepted-assurance hardening and the governed Vercel delivery boundary are merged and exact-head verified. Remaining work is external/public proof, production hardening, capability breadth, mobile/commercial layers and governed release closure on the existing architecture—not `Core 2`, a parallel Coordinator, an invented `PLATFORM.P21`, or an evidence-free `RELEASE.R04`.
