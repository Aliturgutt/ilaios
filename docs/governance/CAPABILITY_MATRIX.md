# ILAIOS Capability Matrix

Snapshot: 16 August 2026

Canonical capability maturity:

`DESIGNED -> SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> DEPLOYED / PRODUCTION`

Planning, process, external-gate and assessment labels in this matrix (for example `PLANNED`, `NOT ASSESSED HERE`, or `PROCESS DEFINED`) are conservative annotations; they are not additional capability-maturity stages. Release state is tracked separately from capability maturity.

This matrix is deliberately conservative. File presence alone cannot promote a capability to VERIFIED or PRODUCTION. Historical Hermes, ILAKOS and ILATEN designs are provenance; active capability identity is defined only by ILAIOS.

| Capability | Evidence observed | Conservative state | Next proof needed |
|---|---|---:|---|
| Canonical v1 execution/release chain | Durable evidence through `RELEASE.R03` | PRODUCTION | Ongoing operational monitoring only |
| Canonical capability identity registry | `services/capability_registry.py`, consolidation tests, merged Platform CI | VERIFIED | Revalidate on registry semantics change |
| Core validation/audit/evidence foundations | `src/core`, historical quality-gate evidence | VERIFIED | Revalidate when core semantics change |
| Control Plane runtime | `services/control_plane`, production release package/evidence | PRODUCTION baseline | Capability-specific production SLO evidence |
| Runtime execution / scheduler / grants | `services/runtime/*`, governed local agent/skill/provider execution, platform recovery evidence | VERIFIED | Capability-specific production exercise |
| Canonical Execution Coordinator | PR #223 durable lifecycle/state machine, canonical-registry-aware routing, fail-closed ambiguity, cancellation/recovery, evidence/metrics and bounded DAG execution; exact-head Required CI PASS | VERIFIED coordinator | Capability adapters still require their own breadth and production evidence |
| Governance / approvals | `services/governance`, governance services and tests | VERIFIED | Production usage/effect evidence per governed action |
| Evidence / provenance | `services/evidence`, release/recovery evidence chain | VERIFIED | Production retention/integrity operating evidence |
| Identity / tenant boundary | `services/identity.py`, platform implementation evidence | VERIFIED | Dedicated production tenant-isolation evidence |
| Privacy / DLP-oriented services | `services/privacy.py`, `tests/test_tenant_privacy.py`, cross-capability revalidation and Platform CI | VERIFIED reference boundary | Production-safe runtime exercise and applicable external compliance evidence |
| Cryptography services | `services/cryptography.py`, `tests/test_managed_cryptography.py`, cross-capability revalidation and Platform CI | VERIFIED provider-neutral boundary | Real managed KMS/HSM provider evidence and production cryptoperiod operations |
| Observability | `services/observability.py`, release health evidence | VERIFIED | Defined production SLO/alert evidence |
| Operations / recovery drills | `services/operations.py`, `services/operational_drills.py`, recovery evidence | VERIFIED | Recurring production-safe drill schedule and retained operating evidence |
| Deployment / cloud path | `services/deployment`, `infra`, R01-R03 workflows/evidence | PRODUCTION | Ongoing release/runbook maintenance |
| Agent governance / permission firewall | `services/agent_governance.py`, `tests/test_agent_governance.py` | VERIFIED primitive | Production invocation/effect evidence per agent class |
| Canonical named agent organization | `services/agent_registry.py`, `tests/test_agent_registry.py`, bounded named-agent executor E2E and Platform CI | VERIFIED bounded executor organization | Production invocation/effect evidence per specialist role |
| Security specialist organization | ILAIOS machine IDs for coordinator, CodeSec, Web/API, supply-chain, infrastructure and independent verifier | VERIFIED registry | Production-safe specialist exercises where applicable |
| Provider routing / cost governance | `services/runtime/routing.py`, `services/ai_governance.py` | VERIFIED / IMPLEMENTED foundation | Real provider-specific production evidence, fallback and quota/cost exercises as applicable |
| Video / Media Factory | `VIDEO.V01-V30`, `PRE.S01`, `src/video_automation`; repeated real 20s local finished-product evidence in Windows Gate | VERIFIED bounded finished-product path | External-provider/publishing production proof where required |
| Code Intelligence | `src/code_intelligence`, targeted tests, `tests/test_intelligence_project_integration.py`, merged CI evidence | VERIFIED foundation | Expand symbol/dependency intelligence and production-like repository exercises as needed |
| Knowledge Graph | `src/knowledge_graph`, targeted tests and integration evidence | VERIFIED foundation | Durable graph persistence/query evidence before stronger runtime claims |
| Project Manager | `src/project_manager`, targeted tests and integration evidence | VERIFIED foundation | Durable project/workspace lifecycle evidence before stronger runtime claims |
| Knowledge / RAG | `services/knowledge_rag.py`, in-place `ilaios.capability.knowledge` registry binding, functional + adversarial tests, PR #111 and RAG.14 repository-side machinery including merged PR #205 | VERIFIED bounded reference implementation | RAG.14 live production evidence: approved production embedding/index persistence, tenant/auth/DLP/leakage exercise, recovery/SLO and exact deploy/rollback evidence under explicit external authority |
| Web Factory integration | PR #248 merged after exact-head Required CI + certified Next.js/Chromium E2E; source assurance and bounded repair, real production build/start, 320-1440 responsive checks, EN/TR workload, accessibility/SEO/security receipts, first-party contact/content/newsletter/search, content-addressed local deployment/rollback evidence | VERIFIED bounded finished-product adapter | Governed exact-SHA public production deployment, live domain health and public rollback proof; broader real-user workloads |
| Software Factory | Registered `software.product-runtime.v1`, crash-safe finalization/cancellation/recovery, exact source-HEAD provenance and repeated real Windows finished-product evidence | VERIFIED bounded finished-product adapter | Expand beyond currently verified local task-manager/todo class; controlled external repository/build/provider and commercial release evidence |
| App Factory Windows finished product | PR #250 merged at `c1883342816011dd1c359f90cce104d6384dfe1a`; exact head `ddf6ca4e4a79c4dfb024788a4513bfa5f7eec6f4` passed Required CI, Desktop CI, MSIX, Windows Gate, Web E2E and Software evidence; real generated Flutter task/checklist app was formatted, analyzed, tested, release-built, packaged and smoke-tested; exact App artifact ID `9269933251`, size `113078073`, digest `sha256:a6660940d445cb9067d6b1cdacf8300c801df48cad3177cd17723e29c172aff7` | VERIFIED bounded Windows finished-product adapter | Broader Windows application classes; Android/iOS only after platform-specific implementation/build/sign/store gates; production signing/Store/publication separately governed |
| Security Factory | `services/security_factory.py`, bounded SAST/secret/supply-chain/infra/local-DAST tests and merged CI | VERIFIED bounded defensive factory | Production-safe exercises and independent external pentest where applicable |
| Research / Data Factory | `services/research_data_factory.py`, capability-registry binding, provenance/claim-gate tests, master Platform CI | VERIFIED bounded factory | Broader governed ingestion adapters, durable persistence and production-safe data-source exercises |
| Creative / Document Factory | `services/creative_document_factory.py`, trusted-source/provenance/approval tests and capability-registry binding | VERIFIED bounded factory | Broader document-format adapters and production-safe external publishing evidence |
| Commerce / Growth Factory | `services/commerce_growth_factory.py`, trusted-evidence/approval/paid-spend-denial tests and capability-registry binding | VERIFIED bounded review-only factory | External channel adapters remain separately governed; no paid-spend authority is implied |
| Personal Operations / Automation | `services/personal_operations_factory.py`, deterministic draft-plan/approval/external-mutation-denial tests and capability-registry binding | VERIFIED bounded review-only factory | External account execution remains separately governed and is not implied by this state |
| Promoted factory enterprise hardening | `services/enterprise_hardening.py`, cross-cutting recovery/isolation/provenance/observability/security/cost gates and tests | VERIFIED bounded gate | Production-specific SLO, backup/restore and independent release evidence where applicable |
| Website public deployment | Web Factory source/runtime is verified, but on 16 August the connected Vercel API account did not resolve the `ilaios` project and Git integration reported Free-plan daily deployment quota exhaustion (`api-deployments-free-per-day`) | EXTERNAL PROOF PENDING | Exact green master SHA public deployment, canonical-domain linkage, live browser/health certification and public rollback evidence after external quota/account access clears |
| Windows Desktop | Merged Desktop workstream through PR #249: fail-closed packaged sidecar, Python 3.12 contract, persistent Google session, Microsoft OIDC readiness, premium EN/TR surfaces, localized scaling matrix, canonical branding, MSIX EN/TR resources, package identity regression coverage and truthful Store metadata; exact CI/Windows/MSIX evidence passed | TESTED / PRE-MICROSOFT REPOSITORY READY; EXTERNAL ACCEPTANCE PENDING | Real Microsoft App Registration/client ID and sign-in persistence acceptance, then Partner Center identity, production signing, certification and Store publication |
| Mobile Android/iOS | No production implementation/release path proven in repository audit | PLANNED | Platform architecture/package implementation plus Android/iOS build, signing, test and store gates after higher-priority closure |
| Billing / subscription / entitlements | No production implementation found in repository audit | PLANNED | Product/commercial requirements, entitlement/usage backend and payment lifecycle before monetized public SaaS launch |
| Formal GitHub release/version model | `docs/governance/RELEASE_VERSION_POLICY.md`, governance policy and regression tests; live immutable product tag/GitHub Release not yet established | SPECIFIED / PROCESS DEFINED | Select exact release-ready SHA and create tag/Release only after licensing/redistribution clearance and exact-head CI |
| Default-branch protection | Active `ILAIOS Master Protection`: non-fast-forward/deletion protection, PR requirement, review-thread resolution, required `Required CI Gate`, no bypass actors, `.github/CODEOWNERS` | PROCESS ACTIVE | Human approving review count remains 0 and CODEOWNER/last-push approval are not enforced; add independent review only if operationally appropriate |
| Repository security policy | `SECURITY.md` present on master | SPECIFIED / PROCESS ACTIVE | Enforce through protected review/CI process |
| Repository governance policy | `GOVERNANCE.md` present on master | SPECIFIED / PROCESS ACTIVE | Enforce through protected review/CI process |
| Repository licensing | `docs/governance/LICENSE_DECISION.md` records proprietary-by-default/no-open-source-grant posture while repository visibility is public; GitHub metadata reports no root OSI license | SPECIFIED / RELEASE CLEARANCE PENDING | Reconcile exact-release third-party notices, provider/model/generated-output rights and redistribution terms before commercial/public release |
| External certification/compliance claims | No external certification assumed | PLANNED / EXTERNAL | Independent applicable certification/compliance process |

## Lineage consolidation rule

The machine-readable registry in `services/capability_registry.py` maps useful Hermes, ILAKOS and ILATEN lineage into one `ilaios.capability.*` namespace. Legacy names in `legacy_sources` are provenance metadata only and never active orchestration identities.

Detailed migration requirement status remains governed by its dedicated migration matrix; this high-level matrix does not bulk-promote granular requirements.

## Agent readiness rule

The generic governed runtime and named-agent bounded executor path are implemented and tested separately from provider-specific production effects. Registry identity and bounded E2E evidence do not imply unrestricted external authority; specialist production effects remain governed by permissions, evidence and approval gates.

## Security Factory boundary

Security Factory v1 is defensive and fail-closed. It may analyze an explicitly authorized repository and validate supplied HTTP observations only for configured localhost/test targets. It does not exploit systems or authorize arbitrary external network scanning. Independent production penetration testing and external certification remain separate evidence requirements.

## RAG verification boundary

Knowledge/RAG is VERIFIED only for the merged bounded implementation and repository-side RAG.14 machinery. Deterministic/reference embedding/index paths do not establish production embedding quality, durable production vector persistence, production SLOs, live external deployment or spend authority.

RAG.14 remains an explicit production promotion NO-GO until the live external evidence listed in the capability row is satisfied under governed credentials/spend authority.

## Finished-product verification boundary

Video, Web, Software and Windows-first App rows record bounded finished-product evidence only. Their exact-head artifacts, runtime/browser/Windows tests and Coordinator composition do not prove arbitrary product generation, paid/external provider authority, public deployment, signing, app-store publication or commercial release readiness. Production promotion remains separate and capability-specific.

## Revalidation result

Fresh repository evidence now revalidates the single-Core/single-Coordinator architecture with verified bounded finished-product paths for Video, Web, Software and Windows-first App generation. App issue #97 is closed for the bounded Windows task/checklist scope after real packaged-app evidence. Enterprise hardening remains a shared fail-closed evidence gate rather than a bypass of capability-specific controls.

## Current product-integration direction

The next work is to preserve the existing architecture while closing real external/public proof and production-hardening gaps: public Web deployment after the Vercel quota/account blocker clears; Microsoft external Desktop identity/signing/Store acceptance; guarded RAG.14 live evidence under explicit authority; production tenant isolation/KMS/SLO/recovery proof; broader factory workloads; mobile; billing/entitlements; and finally a governed formal commercial release. No second Core, Coordinator, router or evidence-free maturity promotion is authorized.
