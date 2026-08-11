# ILAIOS Capability Matrix

Snapshot: 11 August 2026

Lifecycle vocabulary:

`PLANNED -> SPECIFIED -> IMPLEMENTED -> VERIFIED -> PRODUCTION`

Release state is tracked separately from capability maturity.

This matrix is deliberately conservative. File presence alone cannot promote a capability to VERIFIED or PRODUCTION. Historical Hermes, ILAKOS and ILATEN designs are provenance; active capability identity is defined only by ILAIOS.

| Capability | Evidence observed | Conservative state | Next proof needed |
|---|---|---:|---|
| Canonical v1 execution/release chain | Durable evidence through `RELEASE.R03` | PRODUCTION | Ongoing operational monitoring only |
| Canonical capability identity registry | `services/capability_registry.py`, consolidation tests | IMPLEMENTED pending branch CI | Full platform CI and merge evidence |
| Core validation/audit/evidence foundations | `src/core`, historical quality-gate evidence | VERIFIED | Revalidate when core semantics change |
| Control Plane runtime | `services/control_plane`, production release package/evidence | PRODUCTION baseline | Capability-specific production SLO evidence |
| Runtime execution / scheduler / grants | `services/runtime/*`, governed local agent/skill/provider execution, platform recovery evidence | VERIFIED | Capability-specific production exercise |
| Governance / approvals | `services/governance`, governance services and tests | VERIFIED | Production usage/effect evidence per governed action |
| Evidence / provenance | `services/evidence`, release/recovery evidence chain | VERIFIED | Production retention/integrity operating evidence |
| Identity / tenant boundary | `services/identity.py`, platform implementation evidence | VERIFIED | Dedicated production tenant-isolation evidence |
| Privacy / DLP-oriented services | `services/privacy.py` and governance architecture | IMPLEMENTED | Independent negative/e2e privacy tests and runtime proof |
| Cryptography services | `services/cryptography.py` | IMPLEMENTED | Threat-model-driven verification and runtime proof |
| Observability | `services/observability.py`, release health evidence | VERIFIED | Defined production SLO/alert evidence |
| Operations / recovery drills | `services/operations.py`, `services/operational_drills.py`, recovery evidence | VERIFIED | Recurring production-safe drill schedule |
| Deployment / cloud path | `services/deployment`, `infra`, R01-R03 workflows/evidence | PRODUCTION | Ongoing release/runbook maintenance |
| Agent governance / permission firewall | `services/agent_governance.py`, `tests/test_agent_governance.py` | VERIFIED primitive | Production invocation/effect evidence per agent class |
| Canonical named agent organization | `services/agent_registry.py`, `tests/test_agent_registry.py` | IMPLEMENTED pending branch CI | Specialized executors + E2E proof before EXECUTABLE/VERIFIED readiness claims |
| Security specialist organization | ILAIOS machine IDs for coordinator, CodeSec, Web/API, supply-chain, infrastructure and independent verifier | IMPLEMENTED registry pending branch CI | Dedicated authorized-scope executors and Security Factory E2E |
| Provider routing / cost governance | `services/runtime/routing.py`, `services/ai_governance.py` | VERIFIED / IMPLEMENTED foundation | Real provider-specific production evidence as applicable |
| Video / Media Factory | `VIDEO.V01-V30`, `PRE.S01`, `src/video_automation` | VERIFIED | External-provider/publishing production proof where required |
| Code Intelligence | `src/code_intelligence` | IMPLEMENTED | Fresh targeted + regression verification against current master |
| Knowledge Graph | `src/knowledge_graph` | IMPLEMENTED | Fresh targeted + integration verification |
| Project Manager | `src/project_manager` | IMPLEMENTED | Fresh targeted + integration verification |
| Web Factory integration | `services/integrations/web_factory.py`, governed deterministic artifact workflow | IMPLEMENTED | Bounded production-like E2E generation verification |
| Software Factory | `services/software_factory.py`, isolated proposal/test/review design, direct production mutation forbidden | IMPLEMENTED | Bounded build/test/review E2E verification |
| Security Factory | Security roles + firewall/security/governance foundations; no dedicated factory implementation root | SPECIFIED / PARTIAL | Authorized-scope SAST/DAST/supply-chain/infra/remediation/retest implementation + E2E |
| App Factory platform capability | Architecture target; no dedicated factory implementation root assessed here | PLANNED / SPECIFIED | Dedicated bounded factory implementation; Desktop remains separate workstream |
| Research / Data Factory | Knowledge/data foundations exist; no dedicated factory implementation root | PLANNED / SPECIFIED | Bounded contracts, implementation and acceptance evidence |
| Creative / Document Factory | Architecture target; no dedicated factory implementation root | PLANNED / SPECIFIED | Bounded contracts, implementation and acceptance evidence |
| Commerce / Growth Factory | Architecture target; no dedicated factory implementation root | PLANNED / SPECIFIED | Bounded contracts, implementation and acceptance evidence |
| Personal Operations / Automation | Generic workflow/runtime foundation exists; no dedicated factory implementation root | PLANNED / SPECIFIED | Bounded contracts, implementation and acceptance evidence |
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

The generic governed runtime is implemented and tested separately from the named specialist organization. A named agent being present in `services/agent_registry.py` proves canonical identity/governance metadata, not that a specialized provider-backed executor is verified. Named specialist readiness therefore remains `REGISTERED` until bounded executor and E2E evidence exists.

## Priority interpretation

The matrix does **not** recommend implementing every PLANNED item immediately. Existing implementation is revalidated before rewrite, and net-new factories are opened only as bounded packages with explicit security, evidence, recovery and acceptance gates.

## Immediate consolidation gate

The current unified-lineage package must pass full platform tests, Ruff, strict mypy, scoped pre-commit and diff hygiene without touching Website or Desktop implementation paths before any lifecycle promotion or merge.
