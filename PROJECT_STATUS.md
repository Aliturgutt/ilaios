# ILAIOS — Repository Project Status

Status snapshot: 16 August 2026
Baseline branch: `master`
Baseline commit at this truth-sync rebuild: `c795422c6cbb072719adfa8c2ffe56711ed8aed9`

## Authority rule

This file is a human-readable status projection. It is not a canonical architecture or release authority. If this file conflicts with repository code, tests, CI, runtime evidence, deployment evidence, or the canonical implementation authorities, the lower proven lifecycle state wins until the conflict is reconciled.

## Current verified state

- Master commercial/product identity: ILAIOS.
- Canonical v1 execution chain: completed through `RELEASE.R03`.
- `RELEASE.R01`: CANARY deployment evidence exists and is healthy.
- `RELEASE.R02`: LIMITED deployment evidence exists and is healthy.
- `RELEASE.R03`: PRODUCTION deployment evidence records `PRODUCTION_DEPLOYED_HEALTHY`.
- Production release evidence records TLS, OIDC, target health and rollback availability.
- Repository includes Core, Code Intelligence, Knowledge Graph, Project Manager, Video Automation, Control Plane, governance, evidence, privacy, observability, operations and deployment implementations.
- The one canonical Execution Coordinator is merged with durable lifecycle, fail-closed routing, recovery/cancellation, evidence and bounded multi-capability DAG execution.
- Verified bounded finished-product execution is currently wired for Video plus the registered Web and Software product runtimes; wider production/external claims remain evidence-gated.
- Web finished-product browser evidence and Software finished-product Windows evidence are merged; public production deployment and arbitrary-software scope are not implied by those bounded proofs.
- Desktop sidecar packaging is fail-closed and the Windows build contract is pinned to Python 3.12 after PR #231; real external Windows OIDC/signing/Store acceptance remains separately evidence-gated.
- Website and Desktop remain active product surfaces with their own live/external acceptance boundaries.

## Canonical v1 completion

The canonical implementation namespace remains:

1. `PRE.S00`
2. `VIDEO.V01` through `VIDEO.V30`
3. `PRE.S01`
4. `PLATFORM.P00` through `PLATFORM.P20`
5. `RELEASE.R00` through `RELEASE.R03`

No new milestone ID is considered canonical merely because it appears in a planning document. Post-v1 work must remain dependency-ordered, bounded and additive to the existing governance model.

## Current repository governance state

### Verified live controls

- `ILAIOS Master Protection` repository ruleset is active on the default branch.
- Non-fast-forward updates and branch deletion are blocked.
- Pull requests are required.
- Review-thread resolution is required.
- `Required CI Gate` is a required status check.
- No bypass actor is configured and the connected owner cannot bypass the ruleset.
- `.github/CODEOWNERS` exists for the repository default, canonical documentation, governance/security/operations/ADR areas, workflows, infrastructure and release-sensitive automation files.

### Completed truth/hygiene work

- Stale Desktop PR chain identified as superseded by merged consolidation PRs.
- Open duplicate Desktop PRs `#2` through `#11` were closed after confirming merged PR `#12` consolidated D01-D10.
- Open duplicate Store-readiness PR `#16` was closed after confirming merged PR `#18` carries the same content.
- Stale Execution Coordinator draft PR `#216` was closed after canonical successor work was merged.
- Generic Web finished-product issue `#96` and Software finished-product issue `#98` were closed after their exact-head finished-product/CI evidence was verified.

### Remaining governance/repository gaps

- Required approving review count is currently `0`; CODEOWNER approval and last-push approval are not enforced by the active ruleset. Required CI is therefore the current independent automated verifier, not a human-review guarantee.
- Repository metadata still requires owner-level cleanup: the public description is stale and topics are empty.
- `docs/governance/LICENSE_DECISION.md` records publicly visible source with a proprietary-by-default/no-open-source-grant posture. A release-specific legal/redistribution package, dependency notices and exact commercial distribution terms still require governed release review; no root OSI license should be inferred or invented.
- GitHub Releases and immutable version tags remain empty even though platform production deployment evidence exists. The first formal product release must not be created until an exact release-ready SHA and release/licensing gates are satisfied.

## Post-v1 product integration status

The 11 August planning-only snapshot is no longer current. Product integration has advanced on `master` without creating a second Core, router, scheduler, policy engine or Coordinator.

Current proven direction:

1. keep the canonical Coordinator and adapter registry singular;
2. preserve the bounded Video/Web/Software finished-product paths already merged;
3. complete real Desktop OIDC/packaged-sidecar acceptance on Windows;
4. close the remaining App finished-product adapter issue `#97` only with real packaged application evidence;
5. keep RAG.14, formal release/licensing, public deployment and other factory production promotions evidence-gated;
6. continue truth-sync, observability/recovery and external production proof without converting bounded verification into a production claim.

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

The platform v1 build/release chain has production deployment evidence, while product-level finished-product coverage is still being expanded and externally proven. The correct next work is closure of real product/evidence gaps on the existing architecture—not an invented continuation such as `Core 2`, a parallel Coordinator, `PLATFORM.P21`, or an evidence-free `RELEASE.R04`.
