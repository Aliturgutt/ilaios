# ILAIOS — MILESTONES

**Document Type:** Canonical Mutable Milestone & Execution Status Register
**Status:** CURRENT EXECUTION TRUTH — Mutable by Evidence
**Snapshot Date:** 2026-08-15
**Repository:** `Aliturgutt/ilaios`
**Default Branch:** `master`
**RAG Implementation Merge Anchor:** `cb0fde61ba0fd74add11c227bf827cb62c01ff48`
**RAG Verified PR:** `#111`
**RAG Exact-Head CI:** Required CI Gate `#185` — PASS on `38476e8a23313baf6206b37183693fbad5d29dab`
**Core Milestone Principle:** **STATUS IS MUTABLE; ARCHITECTURE IS NOT**

> This file owns mutable execution status only. It does not redefine canonical architecture, product requirements, security architecture, data architecture, API contracts, testing semantics, deployment semantics, or governance policy. Current code, tests, CI, runtime, deployment and external evidence outrank stale status prose.

---

## 1. Authority Rule

Current-state authority order:

```text
CURRENT CODE
    ↓
CURRENT TEST RESULTS
    ↓
CURRENT CI
    ↓
CURRENT RUNTIME EVIDENCE
    ↓
CURRENT DEPLOYMENT / EXTERNAL EVIDENCE
    ↓
THIS STATUS REGISTER
```

If this file conflicts with stronger current evidence, stronger evidence wins and this file must be corrected.

Normative behavior remains governed by the canonical documentation set. This register records only mutable program state and evidence linkage.

---

## 2. Historical Status Preservation

The previous planning-oriented milestone register is preserved by Git history. Its exact historical contents remain recoverable at:

```text
blob: d5b87d2ee588f362e5674280d82fb936752f0186
path: docs/governance/MILESTONES.md
historical repository state: cb0fde61ba0fd74add11c227bf827cb62c01ff48 before the governance status-sync changes
```

That historical register contained stale planning values such as:

```text
RAG.00 = READY
RAG.01-RAG.14 = PLANNED
```

Those values are historical planning evidence only. They are not current execution truth after PR #111 and Required CI Gate #185.

No duplicate archival file is required in the current tree because immutable Git history already preserves the exact prior bytes.

---

## 3. Status Vocabulary

Execution milestone states:

```text
PLANNED
READY
IN_PROGRESS
BLOCKED
NEEDS_OWNER
VERIFIED
DORMANT
DEFERRED
CANCELLED
```

Capability maturity is separate:

```text
DESIGNED
→ SPECIFIED
→ IMPLEMENTED
→ TESTED
→ VERIFIED
→ DEPLOYED / PRODUCTION
```

A milestone may be `VERIFIED` for a bounded scope while the capability is not `DEPLOYED / PRODUCTION`.

---

## 4. Current Program Snapshot

```text
GOV_BASELINE
    = VERIFIED

CAPABILITY_REVALIDATION
    = VERIFIED

EXISTING_FACTORY_PROMOTION
    = VERIFIED

FINAL_LINEAGE_REDTEAM
    = VERIFIED

PRODUCT_SELECTION
    = RAG_KNOWLEDGE

RAG_KNOWLEDGE
    = VERIFIED
      scope: BOUNDED_REFERENCE_IMPLEMENTATION

RAG.14 PRODUCTION PROMOTION
    = BLOCKED / NO-GO
      pending production runtime/deployment evidence

MOBILE
    = DORMANT_NOT_SELECTED

COMMERCIAL_SAAS
    = DORMANT_NOT_SELECTED
```

Website and Desktop remain separate workstreams and are not advanced by RAG verification.

---

## 5. RAG Constitutional Boundary

Knowledge/RAG is a shared governed plane, not a factory-local authority.

It must not create:

```text
a second Core
a second Control Plane
a second router
a second identity authority
a second tenant authority
a parallel policy authority
a factory-local private RAG authority
a client-side authorization authority
```

Canonical capability identity remains:

```text
ilaios.capability.knowledge
```

Implementation roots include:

```text
src/knowledge_graph
src/project_manager
services/knowledge_rag.py
```

The registry evolution is in-place. No parallel `rag` capability identity was introduced.

---

## 6. Required RAG Gates

The adopted post-v1 graph requires:

```text
tenant_isolation
authorization_aware_retrieval
source_provenance
privacy_dlp
deterministic_evidence
full_platform_ci
```

Bounded verification evidence for these gates is attached to PR #111 and Required CI Gate #185.

Production-strength evidence remains separately required by RAG.14.

---

## 7. RAG Milestone State Summary

| Milestone | Current State | Verified Scope / Blocker |
|---|---|---|
| `RAG.00` Baseline & Gap Confirmation | `VERIFIED` | Current implementation inventory, gap classification, single-authority ownership map |
| `RAG.01` Source / Data Contract | `VERIFIED` | Bounded source/version/knowledge-unit contracts and SHA-256 lineage |
| `RAG.02` Tenant Isolation & Authorization | `VERIFIED` | Tenant/project/classification/purpose/residency authorization and negative tests |
| `RAG.03` Ingestion & Provenance | `VERIFIED` | Deterministic ingestion/chunking, source-version/unit hashes and citations |
| `RAG.04` Chunk / Knowledge Unit / Index Lifecycle | `VERIFIED` | Update/supersede/revoke/delete reconciliation and active-version-only indexing |
| `RAG.05` Embedding / Index Provider Adapter | `VERIFIED` | Provider-neutral protocols plus deterministic local verification adapters |
| `RAG.06` Retrieval & Reranking | `VERIFIED` | Authorized candidate set, vector scoring, deterministic reranking and budgets |
| `RAG.07` Authorization-Aware Query Path | `VERIFIED` | Authorization before scoring; malicious index candidate smuggling fails closed |
| `RAG.08` AuthorizedContext Integration | `VERIFIED` | Request/result/query/evidence/citation/current-authorization binding |
| `RAG.09` Privacy / DLP / Injection Hardening | `VERIFIED` | Bounded RAG guard plus existing platform privacy boundary |
| `RAG.10` Evaluation & Leakage Red-Team | `VERIFIED` | Cross-tenant leakage, tamper, revocation and forged-snapshot adversarial tests |
| `RAG.11` Full Platform Integration / CI | `VERIFIED` | Required CI Gate #185 exact-head PASS |
| `RAG.12` Recovery / Observability / FinOps | `VERIFIED` | Bounded snapshot/restore integrity, metrics and retrieval budgets |
| `RAG.13` Final RAG Lineage Red-Team | `VERIFIED` | End-to-end bounded lineage and no hidden parallel authority in defined scope |
| `RAG.14` Production Promotion Decision | `BLOCKED` | Production provider/index/runtime/deployment/recovery/SLO evidence absent |

`VERIFIED` above always means:

```text
VERIFIED FOR THE BOUNDED REFERENCE IMPLEMENTATION
```

It does not mean:

```text
DEPLOYED
PRODUCTION
LIVE
GA
unbounded autonomous authority
production-scale vector infrastructure
```

---

## 8. RAG.00 — Baseline & Gap Confirmation

**State:** `VERIFIED`

Evidence:

```text
docs/governance/RAG_KNOWLEDGE_BASELINE_2026-08-15.md
PR #111
```

Verified outcomes:

```text
existing Knowledge Graph preserved
existing Project Manager preserved
Research/Data provenance primitives preserved
Privacy/DLP authority preserved
Evidence authority preserved
provider-routing authority preserved
single Knowledge capability preserved
net-new gaps classified before implementation
```

No second authority was justified or created.

---

## 9. RAG.01–RAG.04 — Data, Isolation, Provenance and Lifecycle

**State:** `VERIFIED`

Bounded contracts and controls include:

```text
KnowledgeSource
SourceVersion
KnowledgeUnit
tenant_id
project_id
classification
purpose
residency
source identity
source version
content hash
```

Critical lifecycle behavior:

```text
CREATE
    → index active version

UPDATE
    → previous version SUPERSEDED
    → previous units de-indexed
    → new version indexed

REVOKE
    → source/version inactive
    → active units de-indexed

DELETE
    → source/version DELETED
    → units de-indexed
    → deleted unit text cleared
```

Stale versions cannot remain active retrieval candidates in the bounded implementation.

---

## 10. RAG.05–RAG.07 — Provider Contracts and Authorization-Aware Retrieval

**State:** `VERIFIED`

Provider-neutral contracts:

```text
EmbeddingProvider
VectorIndex
```

Bounded verification adapters:

```text
DeterministicHashEmbeddingProvider
InMemoryVectorIndex
```

These prove replaceable contracts and deterministic testing. They do not prove production embedding quality, durable persistence, horizontal scale, HA or provider SLA.

Canonical retrieval order:

```text
PrincipalScope
    ↓
Authorized Eligible Unit IDs
    ↓
VectorIndex.search(eligible IDs only)
    ↓
Semantic Score
    ↓
Deterministic Rerank
    ↓
Top-K / Context Budget
    ↓
RetrievedUnit + Citation
```

Forbidden order:

```text
search all tenant data
    ↓
let model see it
    ↓
filter afterward
```

The implementation fails closed if an index attempts to return an ID outside the authorized candidate set.

---

## 11. RAG.08 — AuthorizedContext Integration

**State:** `VERIFIED`

`AuthorizedContext` is assembled only after revalidating:

```text
retrieval_id
query SHA
result evidence fingerprint
top-k budget
candidate budget
context-size budget
canonical unit text and lineage
citation source/version/unit hashes
current source authorization
current version authorization
current revocation state
```

Security-critical behavior:

```text
retrieve
    ↓
source revoked
    ↓
build context
    ↓
DENY
```

Retrieved content is explicitly treated as:

```text
UNTRUSTED_KNOWLEDGE_DATA
```

Retrieved data cannot grant control-plane authority.

---

## 12. RAG.09–RAG.10 — Privacy, DLP and Leakage Red-Team

**State:** `VERIFIED`

Bounded RAG-specific defenses include:

```text
tenant/project authorization
classification authorization
purpose authorization
residency authorization
prompt-injection quarantine
high-confidence credential-pattern quarantine
quarantined-unit non-index behavior
```

The RAG guard is defense in depth. It does not replace `services/privacy.py`, Security Factory secret scanning, canonical identity/policy authority, external compliance controls or production DLP providers.

Adversarial cases include:

```text
cross-tenant retrieval attempt
restricted classification retrieval
unauthorized purpose
stale source version
revoked source
deleted source
prompt-injected knowledge
credential-bearing knowledge
malicious vector index candidate smuggling
query-hash tampering
evidence-fingerprint tampering
citation-provenance tampering
revocation after retrieval
cross-scope snapshot forgery
```

Expected security result:

```text
FAIL CLOSED
```

---

## 13. RAG.11 — Full Platform Integration / CI

**State:** `VERIFIED`

Exact verification revision:

```text
38476e8a23313baf6206b37183693fbad5d29dab
```

Required CI Gate:

```text
#185 = PASS
```

Validated on the exact RAG head:

```text
change classification / diff hygiene
CI supply-chain hardening
secret scanning
DB migration safety
pre-commit end-of-file
pre-commit whitespace
pre-commit YAML
pre-commit Ruff
pre-commit Mypy
full pytest
Ruff
strict Mypy
diff hygiene
Required CI Gate aggregator
```

PR #111 then merged with expected-head protection.

Merge anchor:

```text
cb0fde61ba0fd74add11c227bf827cb62c01ff48
```

No test or security gate was weakened to obtain PASS.

---

## 14. RAG.12 — Recovery / Observability / FinOps

**State:** `VERIFIED`

Bounded operational primitives include:

```text
RAGSnapshot
snapshot deterministic fingerprint
embedding-provider identity binding
source/version/unit scope validation
content-hash validation
active-state validation
active-index rebuild
retrieval counters
ingestion counters
quarantine counters
active-unit count
max top-k
max candidate scan
max context size
```

Snapshot fingerprint is deterministic integrity evidence, not a cryptographic signature or production backup certification.

Production SLOs, alerts, durable-store backup/restore, provider outage exercises and real provider cost attribution remain RAG.14 requirements.

---

## 15. RAG.13 — Final RAG Lineage Red-Team

**State:** `VERIFIED`

Bounded end-to-end lineage:

```text
PrincipalScope
    ↓
RetrievalRequest
    ↓
Authorization
    ↓
Eligible Knowledge Unit IDs
    ↓
VectorIndex.search(authorized set only)
    ↓
Reject unauthorized provider/index output
    ↓
Rerank
    ↓
RetrievalResult
    ↓
Evidence Fingerprint
    ↓
Citation Provenance Validation
    ↓
Current Authorization / Revocation Revalidation
    ↓
AuthorizedContext
```

Final red-team conclusions for the bounded scope:

```text
second Core created?                      NO
second router created?                    NO
parallel Knowledge authority created?     NO
factory-private retrieval authority?       NO
cross-tenant scoring allowed?              NO
post-hoc-only tenant filtering?            NO
index can smuggle unauthorized ID?         NO
revoked data can form new context?          NO
citation tamper accepted?                   NO
forged cross-scope snapshot accepted?       NO
```

---

## 16. RAG.14 — Production Promotion Decision

**State:** `BLOCKED`

**Current Decision:** `NO_GO_PENDING_PRODUCTION_RUNTIME_EVIDENCE`

RAG.14 is intentionally not marked `VERIFIED` or production-approved.

Required production evidence not yet present includes at least:

```text
1. approved production embedding provider/model revision and integrity
2. approved durable production vector/index persistence
3. production tenant-isolation exercise
4. production authorization-policy integration
5. production DLP / secret / indirect-injection controls
6. production leakage red-team
7. production backup/restore
8. production deletion/revocation reconciliation
9. production observability / SLO / alert evidence
10. real provider/routing/FinOps evidence where external providers are used
11. exact release artifact/version
12. exact deployment target/result
13. deployment health verification
14. rollback/recovery evidence
```

Allowed current claim:

```text
Knowledge/RAG = VERIFIED bounded reference implementation
```

Forbidden current claim:

```text
Knowledge/RAG = DEPLOYED / PRODUCTION
```

Passing repository CI does not autonomously authorize production promotion.

---

## 17. Current Evidence Package

Primary immutable RAG implementation evidence:

```text
PR #111
RAG head 38476e8a23313baf6206b37183693fbad5d29dab
Required CI Gate #185 PASS
merge cb0fde61ba0fd74add11c227bf827cb62c01ff48
```

Implementation/evaluation files:

```text
services/knowledge_rag.py
services/capability_registry.py
tests/test_knowledge_rag.py
tests/test_knowledge_rag_redteam.py
tests/test_knowledge_rag_registry.py
docs/governance/RAG_KNOWLEDGE_BASELINE_2026-08-15.md
docs/governance/RAG_KNOWLEDGE_IMPLEMENTATION.md
```

Mutable projections:

```text
docs/governance/post_v1_dependency_graph.yaml
docs/governance/CAPABILITY_MATRIX.md
docs/governance/MILESTONES.md
```

---

## 18. Red-Team Defects Found and Closed

The RAG implementation was not promoted on first draft. Red-team and CI found and corrected real issues:

```text
RT-01 AuthorizedContext insufficient binding
    → query SHA + evidence fingerprint + citation + current authorization validation

RT-02 Snapshot restore scope/lineage hardening
    → tenant/project/source/version/unit/provider/content-hash validation

RT-03 Malicious index candidate smuggling
    → out-of-authorized-set candidate rejection

RT-04 Secret-scanner fixture collision
    → synthetic credential assembled at runtime; scanner not weakened

RT-05 Strict typing restore narrowing
    → explicit Optional narrowing; no type-ignore bypass
```

All are closed for the bounded implementation and covered by the verified test/CI scope.

---

## 19. Current RAG Gate Matrix

| Gate | Bounded State | Production State |
|---|---|---|
| Tenant isolation | `VERIFIED` | Production exercise required |
| Authorization-aware retrieval | `VERIFIED` | Production policy integration required |
| Source provenance | `VERIFIED` | Production durable lineage required |
| Privacy / DLP | `VERIFIED` bounded defense-in-depth | Production DLP/provider eligibility required |
| Deterministic evidence | `VERIFIED` | Production durable/auditable evidence required |
| Full Platform CI | `VERIFIED` | Release/deployment CI remains scope-specific |
| Embedding provider contract | `VERIFIED` | Production provider/model evidence required |
| Index contract | `VERIFIED` | Durable production persistence required |
| Recovery | `VERIFIED` bounded snapshot/restore | Production backup/restore drill required |
| Observability / budgets | `VERIFIED` bounded metrics/limits | Production SLO/alerts/cost evidence required |
| Production deployment | `NOT VERIFIED` | `BLOCKED` |

---

## 20. No-Rewrite and Revalidation Rules

Do not rebuild working RAG foundations merely because future provider/runtime adapters are added.

Correct evolution:

```text
preserve canonical contracts
    ↓
add replaceable production adapters
    ↓
bind through existing routing/policy/evidence authorities
    ↓
run production-grade tests
    ↓
collect RAG.14 evidence
```

Forbidden:

```text
RAG v2 Core
second RAG router
parallel Knowledge store authority
factory-local authorization bypass
provider-owned tenant truth
```

Revalidate RAG.01-RAG.13 if materially affected by identity/tenant semantics, policy/authorization semantics, classification/residency rules, embedding/index contracts, source lifecycle, evidence format, critical security invariants, major data migration or recovery model changes.

---

## 21. Status Regression Rule

A previously verified bounded milestone may regress to `BLOCKED` if current evidence proves a hard invariant no longer holds.

Examples:

```text
cross-tenant leak discovered
authorization moved after retrieval
revoked data remains accessible
provenance can be forged without detection
required CI fails on a behavior-changing RAG change
```

Never preserve `VERIFIED` merely for appearance.

---

## 22. Workstream Separation

The following remain independent unless a governed dependency explicitly connects them:

```text
Website
Windows Desktop / Store
Mobile Android/iOS
Commercial SaaS / billing
Marketing / LinkedIn / X
Founder certifications
```

Progress in those workstreams does not automatically advance RAG maturity, and RAG verification does not prove those workstreams complete.

---

## 23. External Owner Gates

Repository code cannot prove external owner/account gates complete.

Known external gates may include:

```text
master branch protection policy
repository license decision
store/developer-account actions
payment/provider/account actions
production cloud/provider credentials and account authority
```

Use `NEEDS_OWNER`, `BLOCKED` or `VERIFIED` only from real external evidence.

---

## 24. CI, Merge and Deployment Evidence Rules

CI PASS applies only to the exact tested revision.

For PR #111:

```text
exact tested RAG head
    = 38476e8a23313baf6206b37183693fbad5d29dab

Required CI Gate
    = #185 PASS
```

Merged implementation may still be not deployed, not live and not production-healthy.

A future production deployment record must identify at minimum:

```text
release revision
artifact/version
deployment target
approval
deployment result
health verification
rollback status
```

Provider/index configuration alone is not deployment proof.

---

## 25. Current Program Position and Next Action

```text
V1 / Post-v1 governance baseline
    = recorded complete

Existing Factory Promotion
    = VERIFIED

Final Lineage Red-Team
    = VERIFIED

RAG_KNOWLEDGE bounded implementation
    = VERIFIED

RAG production promotion
    = BLOCKED / NO-GO pending production evidence

Next governed RAG step
    = RAG.14 production evidence and decision
```

The next governed RAG action is not another bounded RAG rewrite. It is production evidence collection and an explicit RAG.14 promotion decision.

If production infrastructure/account/deployment actions are not authorized or evidence is incomplete, the safe state remains:

```text
Knowledge/RAG
    = VERIFIED bounded capability
    = NOT DEPLOYED / NOT PRODUCTION
```

---

## 26. Final Invariant

```text
STATUS
    follows evidence

MILESTONE ORDER
    follows dependencies

VERIFIED
    follows tests + evidence

PRODUCTION
    follows deployment authority + runtime evidence

WORKSTREAM SELECTION
    follows explicit governance
```

**Current Knowledge/RAG truth:**

> **ILAIOS Knowledge/RAG is VERIFIED as a bounded, tenant-isolated, authorization-aware reference implementation through RAG.13. It is not DEPLOYED / PRODUCTION. RAG.14 remains fail-closed until production runtime, security, operations and deployment evidence exists.**
