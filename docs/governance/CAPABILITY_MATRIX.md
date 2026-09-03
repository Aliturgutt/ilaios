# ILAIOS Capability Matrix

Historical evidence snapshot: 17 August 2026
Observed implementation baseline for this snapshot: `1489183e6f5e19a50ba1d35f1c21955a63420f8d`
Truth-sync audit anchor (3 September 2026): `master` HEAD `b93f20b36ac7c8d611e54023d38ffe78b22b14f4`

> **Truth boundary:** The maturity rows below record the 17 August evidence snapshot. They MUST NOT be read as the current maturity state of 3 September 2026 unless the relevant claim is independently revalidated against current code, tests, exact-SHA CI, runtime, deployment, provider/E2E evidence, and durable evidence as applicable.

Canonical capability maturity:

`DESIGNED -> SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> DEPLOYED / PRODUCTION`

Planning and external-gate annotations such as `PLANNED`, `EXTERNAL PROOF PENDING`, and `NOT_VERIFIED` are conservative status notes, not new maturity stages. File presence alone never promotes a capability.

| Capability | Evidence observed | Conservative state | Next proof needed |
|---|---|---:|---|
| Canonical v1 execution/release chain | Durable evidence through `RELEASE.R03` for the governed platform release scope | PRODUCTION scope-specific | Ongoing operational evidence; do not generalize to every product surface |
| Canonical Core / capability identity | Core, canonical registry, consolidation tests, Required CI | VERIFIED | Revalidate on semantics changes |
| Canonical Execution Coordinator | Durable lifecycle, fail-closed routing, cancellation/recovery, evidence, bounded DAG execution, current factory composition | VERIFIED coordinator | Capability adapters keep independent breadth/production gates |
| Governance / approvals / evidence | Governance and evidence services plus tests/release evidence | VERIFIED foundation | Production effect/retention evidence per action class |
| Identity / tenant boundary | Identity implementation and platform tests | VERIFIED foundation | Dedicated production tenant-isolation exercise |
| Privacy / DLP | Privacy services and cross-capability tests | VERIFIED reference boundary | Production-safe runtime and applicable external compliance proof |
| Cryptography | Provider-neutral managed-cryptography service/tests | VERIFIED provider-neutral boundary | Real KMS/HSM, rotation, cryptoperiod evidence |
| Observability / recovery | Observability, operations, drills, release health/recovery evidence | VERIFIED foundation | Production SLO/alerts and recurring retained drills |
| Provider routing / cost governance | Runtime routing and AI governance services | VERIFIED / IMPLEMENTED foundation | Real provider fallback/quota/cost/deprecation evidence |
| Video / Media Factory — local bounded pipeline | Existing `VIDEO.V01-V30`, Windows Gate 20s finished-product E2E/evidence | VERIFIED bounded local pipeline | Preserve technical/evidence regressions |
| Video / Media Factory — Desktop requested-content path | Issue #259 fixed by merged #267 at `1489183e6f5e19a50ba1d35f1c21955a63420f8d`; exact combined head `214720c5bd7ebff35e25ebaf71d4b3a15668d65d` passed Required CI, Desktop CI, Windows Gate, MSIX and Software evidence; provider-backed generation, retrieval/assembly, technical QA, independent semantic/perceptual QA, finished-product-only delivery, negation handling and proposal identity repair are fail-closed | VERIFIED repository/runtime composition | Live exact zero-cost provider availability and provider-backed production MP4 evidence under production secrets boundary |
| Video free-provider availability | Catalog preflight requires exact model plus all `pricing_skus == 0` before generation POST; terminal cost must also equal zero. Observed `bytedance/seedance-2.0-fast:free` live attempt reported `USD 0.1704948` | NOT_VERIFIED external availability | Find/prove an exact zero-priced provider/model before submission and at terminal accounting; otherwise remain unavailable/fail-closed |
| Web Factory integration | #248 bounded Next.js/Chromium finished-product closure; #255 accepted-state assurance hardening | VERIFIED bounded adapter | Public exact-SHA deployment/domain/health/rollback proof |
| Governed Vercel delivery boundary | #258 preview-first provider adapter, auth/budget before effects, exact provenance, same-host health, exact alias promotion and rollback validation | VERIFIED provider boundary | Correct live project/team access, quota, canonical-domain and public rollback evidence |
| Website public deployment | Repository path is verified; exact current public canonical-domain deployment is not proven | EXTERNAL PROOF PENDING | Exact green master deployment identity, canonical-domain linkage, browser/health and rollback proof |
| Software Factory | Registered bounded Windows product runtime, finalization/recovery, source provenance, repeated Windows evidence | VERIFIED bounded adapter | Broader workload/external repository/provider/commercial evidence |
| App Factory Windows | #250 exact-head CI and real generated Flutter Windows build/package/smoke evidence | VERIFIED bounded Windows adapter | Broader Windows apps; Android/iOS and Store/signing separately gated |
| Windows Desktop repository | Interactive shell lineage through #253 and later reference-shell/branding/DPI commits `32df7fc...`, `678b2bbc...`, `c643871e...`; current combined Video/desktop gates green before #267 merge | TESTED / PRE-MICROSOFT REPOSITORY READY | Microsoft App Registration/login acceptance, Partner Center identity, signing, certification, Store publication |
| Knowledge / RAG — shared intelligence/context capability, not a factory | Merged bounded RAG implementation plus RAG.14 repository machinery | VERIFIED bounded reference implementation | Approved live production embeddings/index persistence, tenant/auth/DLP/leakage, SLO/recovery and exact deploy/rollback evidence |
| Knowledge Graph | Repository implementation and targeted integration tests | VERIFIED foundation | Durable production-like graph persistence/query evidence |
| Project Manager | Repository implementation and targeted integration tests | VERIFIED foundation | Durable workspace/project lifecycle evidence |
| Security Factory | Defensive bounded SAST/secret/supply-chain/infra/local-DAST tests | VERIFIED bounded defensive factory | Production-safe exercises and independent external pentest where applicable |
| Research / Data Factory | Registry binding, provenance/claim gates and tests | VERIFIED bounded factory | Broader governed ingestion/persistence/data-source exercises |
| Creative / Document Factory | Trusted-source/provenance/approval tests and registry binding | VERIFIED bounded factory | Broader format adapters and governed external publishing evidence |
| Commerce / Growth Factory | Trusted-evidence/approval/paid-spend-denial tests | VERIFIED bounded review-only factory | Governed external channels; no paid-spend authority implied |
| Personal Operations | Draft-plan/approval/external-mutation-denial tests | VERIFIED bounded review-only factory | Governed external account execution |
| Mobile Android/iOS | No production implementation/build/sign/store path proven | PLANNED | Platform implementation plus build/sign/test/store gates |
| Billing / subscriptions / entitlements | No production implementation proven | PLANNED | Commercial requirements and governed payment/entitlement lifecycle |
| Formal GitHub release/version | Release policy exists; exact commercial release/tag not established | SPECIFIED / PROCESS DEFINED | Exact release-ready SHA, SBOM/notices/artifacts and licensing/redistribution clearance |
| Repository licensing | Proprietary-by-default/no-open-source-grant decision; no root OSI license | SPECIFIED / RELEASE CLEARANCE PENDING | Release-specific third-party/provider/model/output rights and redistribution terms |
| External certification/compliance | No external certification assumed | PLANNED / EXTERNAL | Applicable independent certification/compliance process |

## Video P0 verification boundary

The #259 closure means the repository no longer accepts the deterministic Desktop placeholder as fulfillment of requested generated video content. It does **not** mean an external free video model is currently available in production.

The free-provider policy is deliberately two-stage and fail-closed:

1. before a generation POST, authoritative catalog evidence must identify the exact model and every pricing SKU must parse to exactly zero;
2. terminal provider accounting must independently prove zero cost.

A `:free` suffix is metadata, not cost proof. The observed non-zero live charge is retained as a negative production-readiness finding. No paid/unpriced fallback is authorized.

## Finished-product verification boundary

Video, Web, Software and Windows-first App evidence is bounded to the tested workloads and artifact/evidence chains. It does not prove arbitrary generation breadth, unrestricted provider authority, public deployment, production signing, app-store publication, or commercial release readiness.

## External-action boundary

Credentials, OAuth/provider registration, billing/spend, production DNS/deployment mutations, signing material, Partner Center/Store decisions, paid channel effects, and legal/licensing acceptance remain separately governed. Repository code or CI cannot fabricate those proofs.

## Architecture invariant

The 17 August snapshot evidenced one Core, one Execution Coordinator, one capability registry, and shared governance/evidence authorities. Current-state use of this invariant still requires current evidence; no second Core, router, scheduler, policy engine, Coordinator, or evidence-free maturity promotion is authorized.
