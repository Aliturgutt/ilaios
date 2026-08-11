# ILAIOS Capability Matrix

Snapshot: 11 August 2026

Lifecycle vocabulary:

`PLANNED -> SPECIFIED -> IMPLEMENTED -> VERIFIED -> PRODUCTION`

This matrix is deliberately conservative. File presence alone cannot promote a capability to VERIFIED or PRODUCTION. Where direct current evidence was not inspected, the lower defensible state is used.

| Capability | Evidence observed | Conservative state | Next proof needed |
|---|---|---:|---|
| Canonical v1 execution/release chain | Durable evidence through `RELEASE.R03` | PRODUCTION | Ongoing operational monitoring only |
| Core validation/audit/evidence foundations | `src/core`, historical quality-gate evidence | VERIFIED | Revalidate when core semantics change |
| Control Plane runtime | `services/control_plane`, production release package/evidence | PRODUCTION baseline | Capability-specific production SLO evidence |
| Runtime execution / scheduler / grants | `services/runtime/*`, platform recovery evidence | VERIFIED | Capability-specific production exercise |
| Governance / approvals | `services/governance`, governance services and tests | VERIFIED | Production usage/effect evidence per governed action |
| Evidence / provenance | `services/evidence`, release/recovery evidence chain | VERIFIED | Production retention/integrity operating evidence |
| Identity / tenant boundary | `services/identity.py`, platform implementation evidence | VERIFIED | Dedicated production tenant-isolation evidence |
| Privacy / DLP-oriented services | `services/privacy.py` and governance architecture | IMPLEMENTED | Independent negative/e2e privacy tests and runtime proof |
| Cryptography services | `services/cryptography.py` | IMPLEMENTED | Threat-model-driven verification and runtime proof |
| Observability | `services/observability.py`, release health evidence | VERIFIED | Defined production SLO/alert evidence |
| Operations / recovery drills | `services/operations.py`, `services/operational_drills.py`, recovery evidence | VERIFIED | Recurring production-safe drill schedule |
| Deployment / cloud path | `services/deployment`, `infra`, R01-R03 workflows/evidence | PRODUCTION | Ongoing release/runbook maintenance |
| Video Automation | `VIDEO.V01-V30`, `PRE.S01`, `src/video_automation` | VERIFIED | External-provider/publishing production proof where required |
| Code Intelligence | `src/code_intelligence` | IMPLEMENTED | Fresh targeted + regression verification against current master |
| Knowledge Graph | `src/knowledge_graph` | IMPLEMENTED | Fresh targeted + integration verification |
| Project Manager | `src/project_manager` | IMPLEMENTED | Fresh targeted + integration verification |
| Web Factory integration | `services/integrations/web_factory.py` | IMPLEMENTED | Bounded end-to-end generation verification |
| Software/App Factory foundation | `services/software_factory.py` | IMPLEMENTED | Bounded build/test/delivery verification |
| Website | Active separate workstream | NOT ASSESSED HERE | Continue in Website workstream |
| Windows Desktop | Merged consolidated Desktop workstream exists | NOT ASSESSED HERE | Continue in Desktop/Store workstream |
| Mobile Android/iOS | No implementation path found in repository search | PLANNED | Post-v1 architecture/package definition |
| Billing / subscription / entitlements | No obvious implementation found in repository search | PLANNED | Product/commercial requirements and backend design |
| RAG / embeddings / vector retrieval | No obvious implementation found in repository search | PLANNED | Data/security architecture and bounded specification |
| Formal GitHub release/version model | GitHub Releases empty | PLANNED | Version/tag/release policy |
| Default-branch protection | `master` currently reported unprotected | PLANNED OWNER POLICY | Enable appropriate GitHub protection rules |
| Repository security policy | `SECURITY.md` added on governance branch | SPECIFIED | Merge and enforce through process |
| Repository governance policy | `GOVERNANCE.md` added on governance branch | SPECIFIED | Merge and apply to post-v1 work |
| External certification/compliance claims | No external certification assumed | PLANNED / EXTERNAL | Independent applicable certification process |

## Priority interpretation

The matrix does **not** recommend implementing every PLANNED item immediately.

The correct next sequence is:

1. merge governance truth synchronization;
2. choose one post-v1 product objective;
3. re-audit that objective at code/test/evidence level;
4. define its dependency package and acceptance gates;
5. implement only that bounded package;
6. independently verify before lifecycle promotion.

## First post-v1 candidates

Based on repository absence rather than architecture enthusiasm, the clearest net-new product areas are Mobile and commercial-account/billing capabilities. They must not be started automatically until product requirements and authority boundaries are frozen.

Code Intelligence, Knowledge Graph, Project Manager and factory services already have implementation material and should be **revalidated before rewritten**.
