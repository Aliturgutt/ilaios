# ILAIOS — Repository Project Status

Historical status snapshot: 17 August 2026
Baseline branch: `master`
Observed implementation baseline for this snapshot: `1489183e6f5e19a50ba1d35f1c21955a63420f8d`
Current truth-sync audit anchor: 3 September 2026, `master` HEAD `b93f20b36ac7c8d611e54023d38ffe78b22b14f4`

> **Truth boundary:** The status narrative below records the 17 August repository snapshot and later evidence explicitly named inside it. It is not a complete 3 September CURRENT REALITY report. Any current maturity, CI, runtime, deployment, provider-E2E, Desktop, Website, RAG, or factory claim must be revalidated against the applicable live authoritative evidence before being treated as current.

## Authority rule

This file is a mutable human-readable status projection, not canonical architecture or release authority. If it conflicts with code, tests, Required CI, runtime evidence, deployment evidence, or canonical implementation authorities, the lower proven lifecycle state wins until reconciled.

Canonical maturity remains:

`DESIGNED -> SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> DEPLOYED / PRODUCTION`

`VERIFIED` never means `PRODUCTION` unless real production/external evidence exists for that capability.

## Repository truth recorded by this snapshot

- Commercial/product identity in the active repository is ILAIOS.
- There is one canonical Core and one canonical Execution Coordinator. No `Core 2`, parallel coordinator, router, scheduler, policy engine, capability registry, or evidence authority has been introduced.
- The canonical v1 implementation/release chain remains complete through `RELEASE.R03` for its governed platform release scope.
- Bounded finished-product execution exists for Web, Software, Windows-first App, and Video, but each capability keeps its own external/provider/public-production boundary.
- Repository branch governance remains fail-closed around Required CI, PR review flow, evidence/provenance, and non-bypass safety controls.

## Closure evidence recorded by this snapshot

### Web Factory

- PR #248 is merged with bounded generated-source assurance, repair, real Next.js build/start, Chromium E2E, responsive checks, accessibility/SEO/security validation, first-party contact/content/newsletter/search behavior, and content-addressed local delivery/rollback evidence.
- PR #255 hardened durable Web acceptance so accepted state fails closed unless source assurance, QA promotion, certified source/build binding, and PASS design/accessibility/SEO/security/performance receipts exist.
- PR #258 added the governed Vercel delivery boundary: preview-first creation, authorization/budget checks before network effects, exact source/artifact provenance, same-host HTTPS health, explicit production-alias proof, documented promotion, and rollback revalidation.
- These repository/provider-boundary proofs do **not** prove that the current exact ILAIOS master is publicly deployed on the canonical domain. Public Vercel production remains external-evidence gated.

### Software Factory

- Software Factory remains VERIFIED for its bounded local Windows finished-product scope with crash-safe finalization/recovery and exact source provenance.
- Arbitrary software breadth, external repository/provider effects, and commercial release are not implied.

### App Factory

- PR #250 is merged. Its exact pre-merge head `ddf6ca4e4a79c4dfb024788a4513bfa5f7eec6f4` passed Required CI, Desktop CI, MSIX Packaging, Windows Gate, Web E2E, and Software evidence.
- The bounded generated Flutter Windows task/checklist application was formatted, analyzed, tested, release-built, packaged, smoke-tested, and persisted with content-addressed evidence.
- The recorded artifact remains `app-windows-finished-product-ddf6ca4e4a79c4dfb024788a4513bfa5f7eec6f4-31971331229`, size `113078073` bytes, digest `sha256:a6660940d445cb9067d6b1cdacf8300c801df48cad3177cd17723e29c172aff7`.
- Android/iOS, production signing, Store publication, and arbitrary-app breadth remain separate gates.

### Desktop

- PR #253 closed the earlier interactive Desktop repository pass with truthful operational labels/progress and responsive navigation.
- Subsequent current-master work finalized the approved reference Home composition and interactive workspace behavior, packaged the untouched canonical runtime brand assets, and added Windows DPI/reference-shell regression coverage.
- Master commits `32df7fc56cd6eda39016205001579ef078804e65`, `678b2bbc933173da18a86e0d4f8cdd890f9bf35f`, and `c643871e64b641c961fc4de650291f258e1f8f88` are part of that current Desktop lineage.
- Microsoft App Registration/client ID, external sign-in acceptance, Partner Center identity, production signing, certification, and Store publication remain external gates.

### Video Factory P0 closure

- Issue #259 identified a real false-acceptance defect: Desktop could mark a deterministic placeholder MP4 as `video.desktop.finished_product` even though the requested cinematic content had not been generated.
- Clean current-master successor PR #267 is merged as `1489183e6f5e19a50ba1d35f1c21955a63420f8d`; stale PR #260 was closed rather than merged.
- The exact combined pre-merge head `214720c5bd7ebff35e25ebaf71d4b3a15668d65d` passed Required CI, Desktop CI, Windows Gate, MSIX Packaging, and Software Factory Final Evidence.
- Windows Gate on that exact combined head passed packaged Desktop -> control-plane E2E, real 20s finished-product video E2E with persisted evidence, Software Factory finished-product E2E, App Factory Windows finished-product E2E, and release executable/sidecar verification.
- The Desktop production path no longer promotes the deterministic placeholder runtime as the requested finished product. Missing provider configuration fails closed.
- Provider-backed Video execution now requires generation, media retrieval/assembly, technical validation, independent semantic/perceptual acceptance, zero-cost evidence, and final finished-product evidence before acceptance.
- Deliveries exposes only `*.finished_product` evidence; coordinator/admission evidence remains evidence, not a user deliverable.
- Explicit negated external-effect intent such as `do not publish` is handled as local-only intent without weakening positive publish/upload/deploy blocking.
- Repeated equivalent requests under different goals no longer collide on one unscoped durable proposal identity.

## Free-provider truth boundary recorded by this snapshot

The free-only rule is fail-closed.

- A provider/model name ending in `:free` is not sufficient proof of zero cost.
- A live OpenRouter attempt for `bytedance/seedance-2.0-fast:free` reported non-zero provider cost (`USD 0.1704948`). That route is therefore **not** accepted as evidence of a production-ready zero-cost provider.
- Before any OpenRouter video generation POST, the exact requested model must be present in the authoritative video-model catalog and every `pricing_skus` value must parse to exactly zero.
- Missing, malformed, negative, unknown, or non-zero catalog pricing blocks submission before generation spend.
- Terminal provider evidence must independently resolve to exactly zero cost as well.
- Live zero-cost external Video provider availability is currently `NOT_VERIFIED`. If no exact zero-priced provider is available, ILAIOS must report the capability unavailable/fail-closed rather than fabricate a finished product.
- The Desktop sidecar currently consumes provider credentials at the platform/runtime boundary. Repository evidence does not by itself prove a production deployment in which end users never supply third-party provider credentials; that deployment/secrets boundary remains separately evidence-gated.

## Repository governance state recorded by this snapshot

- P0 issue #259 is closed after #267 merged with exact combined-head evidence.
- Stale implementation PR #260 is closed as superseded.
- Stale Vercel-only truth PR #262 is closed; this document set replaces it with the later combined truth.
- Required CI remains the mandatory automated verifier. Human approving-review count/CODEOWNER enforcement must not be inferred where the active ruleset does not require it.
- Repository metadata still has owner-level cleanup gaps where the connected mutation surface cannot safely update description/homepage/topics.
- `docs/governance/LICENSE_DECISION.md` remains proprietary-by-default/no-open-source-grant. No root OSI license, redistribution clearance, or commercial release right is invented.
- No formal SemVer GitHub Release should be created until an exact release-ready SHA and licensing/redistribution/release gates are satisfied.

## External/public deployment truth recorded by this snapshot

### Website / Vercel

Repository code now contains a governed delivery adapter, but current public production proof remains incomplete. Required external proof still includes correct Vercel project/team resolution, available deployment quota, exact green master deployment identity, canonical-domain linkage, live browser/health evidence, and rollback evidence. Billing/plan changes, credentials, or DNS must not be mutated merely to manufacture this proof.

### Microsoft Desktop

Repository-side Desktop build/package behavior is tested. External completion still requires real Microsoft App Registration/client ID, authentication acceptance, Partner Center package/publisher identity, business verification where required, production signing material, Store declarations/markets/pricing decisions, signed candidate evidence, submission, and certification.

### Knowledge / RAG

Repository-side RAG.14 machinery remains bounded. Knowledge / RAG is a shared canonical intelligence/context capability, not a factory. Live production promotion still requires explicit approved credentials/spend scope and real production embedding/index persistence, tenant/auth/DLP/leakage evidence, recovery/SLO evidence, and exact deploy/rollback proof.

### Other production breadth

Still evidence-gated: production tenant-isolation exercise, managed KMS/HSM and rotation operations, privacy/compliance evidence, SLO/alert operations, recurring backup/recovery drills, independent security/pentest where applicable, broader factory workloads, Android/iOS, billing/subscriptions/entitlements, formal SBOM/notices/attestation/release packaging, and legal/licensing launch clearance.

## Dependency-ordered direction recorded by this snapshot

1. Preserve the single Core, Coordinator, governance, evidence, and capability registry authorities.
2. Preserve the merged Video P0 fail-closed behavior; do not replace it with a paid or unpriced fallback.
3. Obtain live zero-cost Video-provider evidence only when an exact provider/model can be proven zero-cost before submission and at terminal accounting.
4. Complete public Web exact-SHA deployment evidence only after Vercel project/quota/access permits it without billing or DNS shortcuts.
5. Complete Microsoft external identity/signing/Store evidence through the governed release boundary.
6. Execute RAG.14 live evidence only with explicit bounded external credentials/spend authority.
7. Continue production-hardening evidence for tenant isolation, managed cryptography, observability/SLOs, recovery, and provider routing.
8. Broaden factories, then mobile and commercial layers, only with capability-specific executable evidence.
9. Create a formal release/tag only after exact release readiness and licensing/redistribution clearance.

## Safety boundary

Repository automation must not autonomously create/rotate credentials, authorize paid spend, accept legal terms, change billing/plans, force public DNS/deployment state, submit Store releases, use production signing secrets, force-push protected history, weaken Required CI, or label mock/fixture/synthetic/local/preview evidence as external production proof.

## Decision recorded by this snapshot

Repository-side closure was materially stronger at the recorded evidence point: the Desktop lineage was integrated, the Video placeholder false-acceptance P0 was closed on master, and Web/Software/App bounded paths were evidence-backed. This paragraph does not promote those claims to 3 September CURRENT REALITY without revalidation. No second Core, parallel Coordinator, invented milestone, paid-fallback shortcut, or evidence-free production promotion is authorized.
