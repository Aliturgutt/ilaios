# ILAIOS Capability Matrix

Snapshot: 12 August 2026

Lifecycle vocabulary:

`PLANNED -> SPECIFIED -> IMPLEMENTED -> VERIFIED -> PRODUCTION`

Release state is tracked separately from capability maturity.

This matrix is deliberately conservative. File presence alone cannot promote a capability to VERIFIED or PRODUCTION. Historical Hermes, ILAKOS and ILATEN designs are provenance; active capability identity is defined only by ILAIOS.

| Capability | Evidence observed | Conservative state | Next proof needed |
|---|---|---:|---|
| Canonical v1 execution/release chain | Durable evidence through `RELEASE.R03` | PRODUCTION | Ongoing operational monitoring only |
| Canonical capability identity registry | `services/capability_registry.py`, consolidation tests, merged Platform CI | VERIFIED | Revalidate on registry semantics change |
| Core validation/audit/evidence foundations | `src/core`, historical quality-gate evidence | VERIFIED | Revalidate when core semantics change |
| Control Plane runtime | `services/control_plane`, production release package/evidence | PRODUCTION baseline | Capability-specific production SLO evidence |
| Runtime execution / scheduler / grants | `services/runtime/*`, governed local agent/skill/provider execution, platform recovery evidence | VERIFIED | Capability-specific production exercise |
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
| Web Factory integration | `services/integrations/web_factory.py`, deterministic artifact/tamper tests, cross-capability revalidation and Platform CI #17 | VERIFIED bounded factory | Production-like deployment/rollback/browser verification outside Website implementation workstream |
| Software Factory | `services/software_factory.py`, isolated proposal/test/review E2E, production mutation forbidden, Platform CI #17 | VERIFIED bounded proposal factory | Broader language/build adapters and controlled external PR/review evidence |
| Security Factory | `services/security_factory.py`, bounded SAST/secret/supply-chain/infra/local-DAST tests, merged PR #23 and master CI | VERIFIED bounded defensive factory | Production-safe exercises and independent external pentest where applicable |
| App Factory platform capability | `services/app_factory.py`, capability-registry binding, review-only client request boundary and Platform CI | VERIFIED bounded platform factory | Separate client implementation/build/signing evidence remains in Desktop/Mobile workstreams |
| Research / Data Factory | `services/research_data_factory.py`, capability-registry binding, provenance/claim-gate tests, master Platform CI | VERIFIED bounded factory | Broader governed ingestion adapters, durable persistence and production-safe data-source exercises before stronger runtime claims |
| Creative / Document Factory | `services/creative_document_factory.py`, trusted-source/provenance/approval tests and capability-registry binding | VERIFIED bounded factory | Broader document-format adapters and production-safe external publishing evidence before stronger claims |
| Commerce / Growth Factory | `services/commerce_growth_factory.py`, trusted-evidence/approval/paid-spend-denial tests and capability-registry binding | VERIFIED bounded review-only factory | External channel adapters remain separately governed; no paid-spend authority is implied |
| Personal Operations / Automation | `services/personal_operations_factory.py`, deterministic draft-plan/approval/external-mutation-denial tests and capability-registry binding | VERIFIED bounded review-only factory | External account execution remains separately governed and is not implied by this state |
| Promoted factory enterprise hardening | `services/enterprise_hardening.py`, cross-cutting recovery/isolation/provenance/observability/security/cost gates and tests | VERIFIED bounded gate | Production-specific SLO, backup/restore and independent release evidence where applicable |
| Website | Active separate workstream | NOT ASSESSED HERE | Continue in Website workstream |
| Windows Desktop | Merged consolidated Desktop workstream exists | NOT ASSESSED HERE | Continue in Desktop/Store workstream |
| Mobile Android/iOS | No implementation path found in repository audit | PLANNED | Post-v1 architecture/package definition |
| Billing / subscription / entitlements | No obvious implementation found in repository audit | PLANNED | Product/commercial requirements and backend design |
| RAG / embeddings / vector retrieval | No obvious implementation found in repository audit | PLANNED | Data/security architecture and bounded specification |
| Formal GitHub release/version model | No formal release object established in the governance audit | PLANNED | Version/tag/release policy |
| Default-branch protection | `master` reported unprotected during governance audit | PLANNED OWNER POLICY | Enable appropriate GitHub protection rules |
| Repository security policy | `SECURITY.md` present on master | SPECIFIED / PROCESS ACTIVE | Enforce through protected review/CI process |
| Repository governance policy | `GOVERNANCE.md` present on master | SPECIFIED / PROCESS ACTIVE | Enforce through protected review/CI process |
| External certification/compliance claims | No external certification assumed | PLANNED / EXTERNAL | Independent applicable certification process |

## Lineage consolidation rule

The machine-readable registry in `services/capability_registry.py` maps useful Hermes, ILAKOS and ILATEN lineage into one `ilaios.capability.*` namespace. Legacy names in its `legacy_sources` field are provenance metadata only and never active orchestration identities.

Detailed ILATEN requirement status remains governed by `docs/migration/ILATEN_TO_ILAIOS_MIGRATION_MATRIX.csv`; this high-level matrix does not bulk-promote those granular requirements.

## Agent readiness rule

The generic governed runtime and named-agent bounded executor path are implemented and tested separately from provider-specific production effects. Registry identity and bounded E2E evidence do not imply unrestricted external authority; specialist production effects remain governed by their permissions, evidence and approval gates.

## Security Factory boundary

Security Factory v1 is defensive and fail-closed. It may analyze an explicitly authorized repository and validate supplied HTTP observations only for configured localhost/test targets. It does not exploit systems or authorize arbitrary external network scanning. Independent production penetration testing and external certification remain separate evidence requirements.

## Revalidation result

Fresh repository evidence has revalidated the existing intelligence/platform foundations and promoted the bounded Research/Data, Creative/Document, Commerce/Growth, Personal Operations and App Factory platform boundaries without creating parallel runtimes. Enterprise hardening adds a shared fail-closed evidence gate rather than bypassing each factory's own controls.

## Selected post-v1 direction

The adopted **EXISTING_FACTORY_PROMOTION** workstream has reached its bounded implementation, hardening and lineage-red-team completion gate. Mobile, Website/Desktop implementation and Commercial SaaS/billing remain separate or dormant workstreams and are not implicitly activated by this completion.
