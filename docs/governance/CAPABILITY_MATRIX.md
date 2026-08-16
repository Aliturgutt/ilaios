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
| Canonical Execution Coordinator | PR #223, durable lifecycle/state machine, canonical-registry-aware routing, fail-closed ambiguity, cancellation/recovery, evidence/metrics and bounded DAG execution; exact-head Required CI PASS | VERIFIED coordinator | Capability adapters still require their own finished-product and production evidence |
| Governance / approvals | `services/governance`, governance services and tests | VERIFIED | Production usage/effect evidence per governed action |
| Evidence / provenance | `services/evidence`, release/recovery evidence chain | VERIFIED | Production retention/integrity operating evidence |
| Identity / tenant boundary | `services/identity.py`, platform implementation evidence | VERIFIED | Dedicated production tenant-isolation evidence |
| Privacy / DLP-oriented services | `services/privacy.py`, `tests/test_tenant_privacy.py`, cross-capability revalidation and Platform CI #17 | VERIFIED reference boundary | Production-safe runtime exercise and applicable external compliance evidence |
| Cryptography services | `services/cryptography.py`, `tests/test_managed_cryptography.py`, cross-capability revalidation and Platform CI #17 | VERIFIED provider-neutral boundary | Real managed KMS/HSM provider evidence and production cryptoperiod operations |
| Observability | `services/observability.py`, release health evidence | VERIFIED | Defined production SLO/alert evidence |
| Operations / recovery drills | `services/operations.py`, `services/operational_drills.py`, recovery evidence | VERIFIED | Recurring production-safe drill schedule |
| Deployment / cloud path | `services/deployment`, `infra`, R01-R03 workflows/evidence | PRODUCTION | Ongoing release/runbook maintenance |
| Agent governance / permission firewall | `services/agent_governance.py`, `tests/test_agent_governance.py` | VERIFIED primitive | Production invocation/effect evidence per agent class |
| Canonical named agent organization | `services/agent_registry.py`, `tests/test_agent_registry.py`, bounded named-agent executor E2E and Platform CI | VERIFIED bounded executor organization | Production invocation/effect evidence per specialist role |
| Security specialist organization | ILAIOS machine IDs for coordinator, CodeSec, Web/API, supply-chain, infrastructure and independent verifier | VERIFIED registry | Production-safe specialist exercises where applicable |
| Provider routing / cost governance | `services/runtime/routing.py`, `services/ai_governance.py` | VERIFIED / IMPLEMENTED foundation | Real provider-specific production evidence as applicable |
| Video / Media Factory | `VIDEO.V01-V30`, `PRE.S01`, `src/video_automation` | VERIFIED | External-provider/publishing production proof where required |
| Code Intelligence | `src/code_intelligence`, targeted tests, `tests/test_intelligence_project_integration.py`, PR #24 + master Platform CI | VERIFIED foundation | Expand symbol/dependency intelligence and production-like repository exercises as needed |
| Knowledge Graph | `src/knowledge_graph`, targeted tests, `tests/test_intelligence_project_integration.py`, PR #24 + master Platform CI | VERIFIED foundation | Durable graph persistence/query evidence before stronger runtime claims |
| Project Manager | `src/project_manager`, targeted tests, `tests/test_intelligence_project_integration.py`, PR #24 + master Platform CI | VERIFIED foundation | Durable project/workspace lifecycle evidence before stronger runtime claims |
| Knowledge / RAG | `services/knowledge_rag.py`, in-place `ilaios.capability.knowledge` registry binding, functional + adversarial tests, PR #111, Required CI Gate #185 PASS, merge `cb0fde61ba0fd74add11c227bf827cb62c01ff48` | VERIFIED bounded reference implementation | RAG.14 production evidence: approved production embedding/index persistence, production tenant/auth/DLP/leakage exercise, recovery/SLO and exact deploy/rollback evidence |
| Web Factory integration | PR #223 registered `web.product-runtime.v1`; PR #227 added generated-artifact Chromium browser E2E covering EN/TR, desktop/tablet/mobile responsiveness, navigation, console/page errors, accessibility basics and SEO basics; exact-head Required CI and Web Factory Browser E2E PASS | VERIFIED bounded finished-product adapter | Governed public production deployment, live health and rollback evidence; broader real-user workload coverage |
| Software Factory | PR #227 registered `software.product-runtime.v1`, crash-safe finalization/cancellation/recovery, exact source-HEAD provenance and real Windows finished-product E2E; exact-head Required CI and Software Factory Final Evidence PASS | VERIFIED bounded finished-product adapter | Expand beyond the currently verified local task-manager/todo scope; controlled external repository/build/provider and commercial release evidence before stronger claims |
| Security Factory | `services/security_factory.py`, bounded SAST/secret/supply-chain/infra/local-DAST tests, merged PR #23 and master CI | VERIFIED bounded defensive factory | Production-safe exercises and independent external pentest where applicable |
| App Factory platform capability | `services/app_factory.py`, capability-registry binding, review-only client request boundary and Platform CI | VERIFIED bounded platform factory | Issue #97: Windows-first finished-product adapter with real Flutter implementation/build/package evidence; Android/iOS only after platform-specific gates |
| Research / Data Factory | `services/research_data_factory.py`, capability-registry binding, provenance/claim-gate tests, master Platform CI | VERIFIED bounded factory | Broader governed ingestion adapters, durable persistence and production-safe data-source exercises before stronger runtime claims |
| Creative / Document Factory | `services/creative_document_factory.py`, trusted-source/provenance/approval tests and capability-registry binding | VERIFIED bounded factory | Broader document-format adapters and production-safe external publishing evidence before stronger claims |
| Commerce / Growth Factory | `services/commerce_growth_factory.py`, trusted-evidence/approval/paid-spend-denial tests and capability-registry binding | VERIFIED bounded review-only factory | External channel adapters remain separately governed; no paid-spend authority is implied |
| Personal Operations / Automation | `services/personal_operations_factory.py`, deterministic draft-plan/approval/external-mutation-denial tests and capability-registry binding | VERIFIED bounded review-only factory | External account execution remains separately governed and is not implied by this state |
| Promoted factory enterprise hardening | `services/enterprise_hardening.py`, cross-cutting recovery/isolation/provenance/observability/security/cost gates and tests | VERIFIED bounded gate | Production-specific SLO, backup/restore and independent release evidence where applicable |
| Website | Active separate workstream; public Vercel production identity was not independently visible through the connected Vercel account during the 16 August truth-sync | NOT ASSESSED HERE / EXTERNAL PROOF PENDING | Exact-SHA public production deployment, live browser certification and domain/deployment linkage |
| Windows Desktop | Merged consolidated Desktop workstream plus PR #228 OIDC launcher propagation and PR #229 fail-closed packaged-sidecar import smoke; Windows Gate/MSIX/Desktop CI passed on those changes | TESTED / EXTERNAL ACCEPTANCE PENDING | Real Windows first-click OIDC acceptance with rebuilt sidecar, then signing/Partner Center/Store evidence |
| Mobile Android/iOS | No implementation path found in repository audit | PLANNED | Post-v1 architecture/package definition after higher-priority closure |
| Billing / subscription / entitlements | No obvious implementation found in repository audit | PLANNED | Product/commercial requirements and backend design; raise priority only when public SaaS launch requires it |
| Formal GitHub release/version model | `docs/governance/RELEASE_VERSION_POLICY.md`, `GOVERNANCE.md`, policy regression tests; live GitHub tags and Releases are both empty on 16 August 2026 | SPECIFIED / PROCESS DEFINED | Select first formal version in a dedicated release package; create immutable tag + GitHub Release only after governed approval, licensing clearance and exact-head CI |
| Default-branch protection | Active `ILAIOS Master Protection` ruleset: non-fast-forward/deletion protection, PR requirement, review-thread resolution and required `Required CI Gate`; no bypass actors; `.github/CODEOWNERS` exists | PROCESS ACTIVE | Human approving review count remains 0 and CODEOWNER/last-push approval are not enforced; add independent review only if it does not make the single-developer workflow unusable |
| Repository security policy | `SECURITY.md` present on master | SPECIFIED / PROCESS ACTIVE | Enforce through protected review/CI process |
| Repository governance policy | `GOVERNANCE.md` present on master | SPECIFIED / PROCESS ACTIVE | Enforce through protected review/CI process |
| Repository licensing | GitHub repository metadata reports `license: null`; third-party/license provenance mechanisms do not substitute for the repository distribution decision | BLOCKED EXTERNAL LEGAL DECISION | Owner/legal decision on proprietary/open-source distribution terms, then reconcile notices/provider/model/generated-output rights |
| External certification/compliance claims | No external certification assumed | PLANNED / EXTERNAL | Independent applicable certification process |

## Lineage consolidation rule

The machine-readable registry in `services/capability_registry.py` maps useful Hermes, ILAKOS and ILATEN lineage into one `ilaios.capability.*` namespace. Legacy names in its `legacy_sources` field are provenance metadata only and never active orchestration identities.

Detailed ILATEN requirement status remains governed by `docs/migration/ILATEN_TO_ILAIOS_MIGRATION_MATRIX.csv`; this high-level matrix does not bulk-promote those granular requirements.

## Agent readiness rule

The generic governed runtime and named-agent bounded executor path are implemented and tested separately from provider-specific production effects. Registry identity and bounded E2E evidence do not imply unrestricted external authority; specialist production effects remain governed by their permissions, evidence and approval gates.

## Security Factory boundary

Security Factory v1 is defensive and fail-closed. It may analyze an explicitly authorized repository and validate supplied HTTP observations only for configured localhost/test targets. It does not exploit systems or authorize arbitrary external network scanning. Independent production penetration testing and external certification remain separate evidence requirements.

## RAG verification boundary

The Knowledge/RAG capability is VERIFIED only for the merged bounded reference implementation proven by PR #111 and Required CI Gate #185. The deterministic hash embedding adapter and in-memory vector index are verification/reference implementations. They do not establish production embedding quality, durable production vector persistence, production SLOs, or production deployment.

RAG.14 remains an explicit production promotion NO-GO until the production evidence listed in the capability row and governed dependency graph is satisfied.

## Finished-product verification boundary

The Web and Software rows record bounded finished-product adapter evidence only. PR #223/#227 prove coordinator composition, artifacts and CI/browser/Windows evidence within their stated scopes; they do not prove public Web deployment, arbitrary software generation, paid/external provider authority or commercial release readiness. Production promotion remains separate.

## Revalidation result

Fresh repository evidence has revalidated the existing intelligence/platform foundations and the bounded Research/Data, Creative/Document, Commerce/Growth, Personal Operations, App Factory and Knowledge/RAG platform boundaries without creating parallel runtimes. The canonical Coordinator now composes verified bounded Web and Software finished-product adapters in addition to the existing Video path. Enterprise hardening remains a shared fail-closed evidence gate rather than a bypass of capability-specific controls.

## Current product-integration direction

The previous planning-only snapshot is superseded by live merged evidence. The next repository work is to preserve the single Core/Coordinator architecture, complete Desktop external OIDC/package acceptance, close App issue #97 with real packaged evidence, keep RAG.14 and public/external production promotions evidence-gated, and resolve formal release/licensing only when their exact external prerequisites are satisfied.
