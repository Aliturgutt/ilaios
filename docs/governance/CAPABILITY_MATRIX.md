# ILAIOS Capability Matrix

Snapshot: 11 August 2026
Truth-correction baseline: `a02a2c8897616afcafa45aafee6c1ac36c15898a`

Lifecycle vocabulary:

`PLANNED -> SPECIFIED -> IMPLEMENTED -> VERIFIED -> PRODUCTION`

This matrix is deliberately conservative. File presence, historical milestone PASS, release prose, or a deployment-oriented implementation does not promote a capability to VERIFIED or PRODUCTION when stronger current recovery/deployment evidence contradicts that promotion. The lower proven lifecycle state wins.

## Current controller constraint

`dev/openclaw/execution_plan.yaml` has active recovery beginning at `PLATFORM.P05`, states that historical PASS for affected platform/release milestones is insufficient for current readiness, and records `release_state: NOT_DEPLOYED`. `infra/deployment/ext-e01-prerequisites.yaml` independently records `deployment_performed: false` and `PREPARED_AWAITING_APPROVALS`.

| Capability | Evidence observed | Conservative state | Next proof needed |
|---|---|---:|---|
| Canonical v1 namespace / release history | Namespace through `RELEASE.R03`; active recovery rejects affected historical PASS as current readiness | VERIFIED only for accepted completed context through `PLATFORM.P04`; higher affected stages REVALIDATION REQUIRED | Accepted recovery evidence and coherent dependency chain |
| Core validation/audit/evidence foundations | `src/core`, historical quality-gate evidence | VERIFIED | Revalidate when core semantics change |
| Control Plane runtime | `services/control_plane`; historical platform/release artifacts; active recovery affects current readiness | IMPLEMENTED / REVALIDATION REQUIRED | Current targeted + integration/runtime evidence after dependencies are restored |
| Runtime execution / scheduler / grants | `services/runtime/*`, recovery-oriented evidence | IMPLEMENTED / REVALIDATION REQUIRED | Current runtime/e2e verification under accepted recovery chain |
| Governance / approvals | `services/governance`, governance services and tests | VERIFIED | Production usage/effect evidence per governed action before PRODUCTION claim |
| Evidence / provenance | `services/evidence`, release/recovery evidence chain | VERIFIED | Retention/integrity operating evidence before PRODUCTION claim |
| Identity / tenant boundary | `services/identity.py`, platform implementation evidence | IMPLEMENTED / REVALIDATION REQUIRED | Current tenant-isolation/integration evidence under accepted dependencies |
| Privacy / DLP-oriented services | `services/privacy.py` and governance architecture | IMPLEMENTED | Independent negative/e2e privacy tests and runtime proof |
| Cryptography services | `services/cryptography.py` | IMPLEMENTED | Threat-model-driven verification and runtime proof |
| Observability | `services/observability.py`; `OBS.I06.md` explicitly says no infrastructure/collector/dashboard/production-monitoring deployment | IMPLEMENTED | Current integration/runtime proof and real operating evidence before VERIFIED/PRODUCTION promotion |
| Operations / recovery framework | `services/operations.py`, `services/operational_drills.py`; `OPS.I05.md` explicitly avoids fabricated production recovery evidence | IMPLEMENTED | Current executable recovery/drill evidence appropriate to the capability |
| Deployment / cloud path | `infra`; EXT.E01 prerequisites say `PREPARED_AWAITING_APPROVALS`, `deployment_performed: false`, `release_state: NOT_DEPLOYED` | SPECIFIED / PREPARED, NOT DEPLOYED | Required approvals plus actual bounded deployment/promotion evidence |
| Video Automation | `VIDEO.V01-V30`, `PRE.S01`, `src/video_automation`; accepted completed context retained by controller | VERIFIED | External-provider/publishing production proof where required |
| Code Intelligence | `src/code_intelligence` | IMPLEMENTED | Fresh targeted + regression verification against current master |
| Knowledge Graph | `src/knowledge_graph` | IMPLEMENTED | Fresh targeted + integration verification |
| Project Manager | `src/project_manager` | IMPLEMENTED | Fresh targeted + integration verification |
| Web Factory integration | `services/integrations/web_factory.py` | IMPLEMENTED | Bounded end-to-end generation verification; Website implementation excluded here |
| Software/App Factory foundation | `services/software_factory.py` | IMPLEMENTED | Bounded build/test/delivery verification |
| Website | Active separate workstream | NOT ASSESSED HERE | Continue in Website workstream |
| Windows Desktop | Merged consolidated Desktop workstream exists | NOT ASSESSED HERE | Continue in Desktop/Store workstream |
| Mobile Android/iOS | No implementation path found in repository audit search | PLANNED | Post-v1 architecture/package definition after current recovery is resolved |
| Billing / subscription / entitlements | No obvious implementation found in repository audit search | PLANNED | Product/commercial requirements and backend design after current recovery is resolved |
| RAG / embeddings / vector retrieval | No obvious implementation found in repository audit search | PLANNED | Data/security architecture and bounded specification after current recovery is resolved |
| Formal GitHub release/version model | GitHub Releases empty during audit | PLANNED | Version/tag/release policy |
| Default-branch protection | `master` reported unprotected during audit | PLANNED OWNER POLICY | Explicit safe branch-protection decision |
| Repository security policy | `SECURITY.md` present | SPECIFIED | Apply/enforce through repository process |
| Repository governance policy | `GOVERNANCE.md` present | SPECIFIED | Apply to subsequent bounded work |
| External certification/compliance claims | No external certification assumed | PLANNED / EXTERNAL | Independent applicable certification process |

## Priority interpretation

The matrix does **not** recommend implementing every PLANNED item immediately.

The correct next sequence is:

1. preserve the repository truth correction;
2. resolve the active `PLATFORM.P05.RECOVERY.v1` dependency chain using accepted evidence;
3. reconcile release/deployment state without autonomous promotion;
4. refresh this matrix against that resolved state;
5. only then choose one post-v1 product objective;
6. define its dependency package and acceptance gates before bounded implementation.

## Post-v1 candidates

Mobile, commercial-account/billing, RAG/knowledge retrieval, and further factory promotion remain planning candidates only. They must not be started automatically while the current v1 recovery gate is active or merely because architecture/planning prose names them.

Code Intelligence, Knowledge Graph, Project Manager and factory services already have implementation material and should be **revalidated before rewritten** after their required dependency state is coherent.
