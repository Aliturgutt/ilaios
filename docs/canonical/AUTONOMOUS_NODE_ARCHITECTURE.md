# ILAIOS — AUTONOMOUS NODE ARCHITECTURE

**Document Type:** Canonical Autonomous Node / Execution Topology  
**Format:** GitHub Markdown + Mermaid  
**Status:** Proposed Canonical Companion to `SYSTEM_ARCHITECTURE.md`  
**Purpose:** Show how ILAIOS components connect, delegate, execute, validate, repair, checkpoint, and complete work as an autonomous governed system.  
**Core Principle:** **SIGN IN → ONE PROMPT → GOVERNED AUTONOMOUS EXECUTION → VERIFIED FINISHED PRODUCT**  
**Authority Rule:** This document visualizes node relationships and autonomous execution topology. It does not override `SYSTEM_ARCHITECTURE.md`; any conflict must be resolved in favor of the canonical system architecture.

---

# 00. Reading Model

This document is intentionally **node-first**.

Each node represents one bounded responsibility in the ILAIOS system.

A node may:

- receive a typed input;
- make a bounded decision;
- emit a typed output;
- create evidence;
- update execution state;
- request another governed node;
- pause for approval;
- fail closed;
- resume from checkpoint.

A node may **not** silently create new authority.

```mermaid
flowchart LR
    INPUT["Typed Input"]
    NODE["Governed Node"]
    OUTPUT["Typed Output"]
    EVID["Evidence"]
    STATE["State Update"]
    NEXT["Next Node"]

    INPUT --> NODE
    NODE --> OUTPUT
    NODE --> EVID
    NODE --> STATE
    OUTPUT --> NEXT
```

## Global Node Invariants

```mermaid
flowchart TD
    A["ONE Authoritative Control Plane"]
    B["ONE Governed Runtime"]
    C["ONE Canonical Identity System"]
    D["ONE Capability Truth"]
    E["ONE RoutingDecision Truth"]
    F["ONE Evidence / Provenance Truth"]
    G["Core Frozen by Default"]
    H["Providers Replaceable"]
    I["Factories Cannot Bypass Governance"]

    A --> B --> C --> D --> E --> F
    G --> A
    H --> E
    I --> B
```

**Forbidden:** second Core, second Planner, second routing authority, second capability registry, factory-specific hidden runtime, self-approved privileged action, uncontrolled retry loop, direct factory-to-provider bypass.

---

# 01. Full Autonomous Node Topology

This is the primary node view of ILAIOS.

```mermaid
flowchart TD
    USER["USER"]
    AUTH["N01 Auth / Identity"]
    PRINCIPAL["N02 Principal / Tenant / Project"]
    PROMPT["N03 Prompt Intake"]
    INTENT["N04 Intent Analysis"]
    GOAL["N05 GoalSpec + Acceptance"]
    CONTEXT["N06 Authorized Context"]
    PLAN["N07 Planner / Bounded DAG"]
    CAP["N08 Capability Resolver"]
    FACTORY["N09 Factory / Domain Orchestrator"]
    ADMIT["N10 Execution Admission"]
    APPROVAL{"N11 Approval Required?"}
    WAIT["N12 WAITING_FOR_APPROVAL"]
    GRANT["N13 ExecutionGrant"]
    ROUTE["N14 ONE RoutingDecision"]
    SCHED["N15 Scheduler / Lease / Fencing"]
    WORKER["N16 Governed Worker"]
    SKILL["N17 Approved Skill"]
    TOOL["N18 Tool / API / Browser / Shell"]
    PROVIDER["N19 Replaceable Provider"]
    STEP["N20 Step Output"]
    VALIDATE["N21 Step Validation"]
    EVID["N22 Step Evidence"]
    STATE["N23 State Update"]
    CHECKPOINT["N24 Checkpoint"]
    MORE{"N25 More DAG Nodes?"}
    FINALART["N26 Final Artifact"]
    VERIFY["N27 Independent Evaluation"]
    PASS{"N28 Acceptance PASS?"}
    REPAIR["N29 Bounded Repair"]
    FINALEVID["N30 Final Evidence / Provenance"]
    DELIVERY["N31 Delivery / Deploy / Publish"]
    PRODUCT["N32 VERIFIED FINISHED PRODUCT"]

    USER --> AUTH --> PRINCIPAL --> PROMPT --> INTENT --> GOAL
    GOAL --> CONTEXT --> PLAN --> CAP --> FACTORY --> ADMIT --> APPROVAL

    APPROVAL -->|No| GRANT
    APPROVAL -->|Yes| WAIT
    WAIT -->|Approved| GRANT
    WAIT -->|Rejected / Expired| STATE

    GRANT --> ROUTE --> SCHED --> WORKER
    WORKER --> SKILL
    WORKER --> TOOL
    WORKER --> PROVIDER
    SKILL --> STEP
    TOOL --> STEP
    PROVIDER --> STEP

    STEP --> VALIDATE
    VALIDATE --> EVID --> STATE --> CHECKPOINT --> MORE

    MORE -->|Yes| FACTORY
    MORE -->|No| FINALART

    FINALART --> VERIFY --> PASS
    PASS -->|No| REPAIR --> ADMIT
    PASS -->|Yes| FINALEVID --> DELIVERY --> PRODUCT
```

---

# 02. Autonomous Control Loop

ILAIOS autonomy is not an infinite agent loop. It is a bounded control loop.

```mermaid
flowchart LR
    OBSERVE["Observe State"]
    DECIDE["Decide Next Valid Node"]
    AUTHORIZE["Authorize"]
    EXECUTE["Execute"]
    VERIFY["Verify"]
    RECORD["Record Evidence"]
    CHECKPOINT["Checkpoint"]
    COMPLETE{"Goal Complete?"}

    OBSERVE --> DECIDE --> AUTHORIZE --> EXECUTE --> VERIFY --> RECORD --> CHECKPOINT --> COMPLETE
    COMPLETE -->|No| OBSERVE
    COMPLETE -->|Yes| DONE["Finish"]
```

## Autonomous Loop Rules

- Every loop iteration must be attached to a known `GoalSpec`.
- Every execution must be bounded by policy, permissions, cost, time, and retry limits.
- Every material execution emits evidence.
- Every resumable execution updates durable state.
- `Goal Complete?` is determined by acceptance criteria, not by an agent claiming completion.
- A failed verification may trigger bounded repair, never unbounded self-retry.

---

# 03. Control Plane Node Graph

```mermaid
flowchart TD
    CP["AUTHORITATIVE CONTROL PLANE"]

    ID["Identity Node"]
    TENANT["Tenant Boundary Node"]
    PROJECT["Project Context Node"]
    GOAL["Goal / Job Node"]
    STATE["Execution State Node"]
    POLICY["Policy Decision Node"]
    APPROVAL["Approval Node"]
    CAP["Capability Resolution Node"]
    ROUTE["RoutingDecision Node"]
    WF["Workflow / Scheduler Node"]
    EVID["Evidence Node"]

    CP --> ID
    CP --> TENANT
    CP --> PROJECT
    CP --> GOAL
    CP --> STATE
    CP --> POLICY
    CP --> APPROVAL
    CP --> CAP
    CP --> ROUTE
    CP --> WF
    CP --> EVID
```

## Control Plane Ownership

The Control Plane owns **authority and state**, not every domain implementation.

It is the source of truth for:

- who is acting;
- for which tenant/project;
- what goal is active;
- which plan is authorized;
- which state the job is in;
- whether execution is permitted;
- whether approval is required;
- which route was chosen;
- what evidence was recorded.

---

# 04. Constitutional Core vs Governed Capability Nodes

```mermaid
flowchart TD
    subgraph CORE["CONSTITUTIONAL CORE — FROZEN BY DEFAULT"]
        AUTHORITY["Authority Boundaries"]
        IDENTITY["Canonical Identity"]
        STATE["Lifecycle / State Invariants"]
        EVIDENCE["Evidence Primitives"]
        CONTRACTS["Core Contracts"]
        RECOVERY["Durable Recovery Invariants"]
    end

    subgraph PLATFORM["GOVERNED PLATFORM CAPABILITIES"]
        POLICY["Policy / Trust"]
        ROUTING["Routing"]
        KNOWLEDGE["Knowledge / RAG"]
        AGENTS["Agent Runtime"]
        FINOPS["FinOps"]
        HITL["Human Approval"]
        TOOLS["Tool Governance"]
        CAPFABRIC["Capability Fabric"]
    end

    CORE --> PLATFORM
```

## Core Evolution Rule

**CORE = FROZEN BY DEFAULT, EVOLVABLE BY PROOF.**

A Core change is permitted only when a platform-wide invariant or canonical contract cannot be correctly implemented inside an existing governed capability boundary.

The following do **not** justify a Core change by themselves:

- a new provider;
- a new model;
- a new factory;
- a new skill;
- a new UI;
- a new open-source reference;
- a new domain-specific workflow.

---

# 05. Intent → Goal → DAG Node Chain

```mermaid
flowchart TD
    PROMPT["Raw User Prompt"]
    INTENT["Intent Node"]
    REQUIREMENTS["Requirement Extraction"]
    CONSTRAINTS["Constraints"]
    ACCEPT["Acceptance Criteria"]
    GOAL["GoalSpec"]
    DAG["Bounded Execution DAG"]
    TASKS["Typed Task Nodes"]

    PROMPT --> INTENT
    INTENT --> REQUIREMENTS
    INTENT --> CONSTRAINTS
    REQUIREMENTS --> ACCEPT
    CONSTRAINTS --> ACCEPT
    ACCEPT --> GOAL
    GOAL --> DAG
    DAG --> TASKS
```

## Invariants

- Planning does not itself grant execution permission.
- A DAG must be acyclic and bounded.
- Every task node must have a stable identity.
- Every task node declares dependencies.
- Acceptance criteria exist before final verification.
- Planner cannot silently redefine the user's authorized goal.

---

# 06. Authorized Context / Memory / RAG Node Network

```mermaid
flowchart TD
    REQUEST["ContextRequest"]
    PRINCIPAL["PrincipalContext"]
    TENANT["TenantContext"]
    PROJECT["ProjectContext"]
    PURPOSE["Purpose"]
    POLICY["Authorization Filter"]

    SOURCES["Authorized Sources"]
    INGEST["Ingestion"]
    PARSE["Parse / Normalize"]
    CLASSIFY["Classification"]
    INDEX["Index / Knowledge Graph"]
    RETRIEVE["Authorized Retrieval"]
    RERANK["Rerank"]
    ASSEMBLE["Context Assembly"]
    OUTPUT["AuthorizedContext"]
    PROV["Source Provenance"]

    SOURCES --> INGEST --> PARSE --> CLASSIFY --> INDEX
    REQUEST --> POLICY
    PRINCIPAL --> POLICY
    TENANT --> POLICY
    PROJECT --> POLICY
    PURPOSE --> POLICY
    INDEX --> POLICY
    POLICY -->|Allow| RETRIEVE --> RERANK --> ASSEMBLE --> OUTPUT
    POLICY -->|Deny| DENIED["Denied + Evidence"]
    OUTPUT --> PROV
```

## Critical Rule

**Retrieval is an authorized action.**

A retrieved unit must preserve enough metadata to enforce:

- tenant;
- principal;
- project;
- classification;
- purpose;
- region;
- retention;
- authorization;
- provenance.

---

# 07. Capability Resolution Node Graph

```mermaid
flowchart TD
    GOAL["GoalSpec"]
    REQUIRE["Required Outcome"]
    REGISTRY["Canonical Capability Registry"]
    RESOLVE["Capability Resolver"]
    SET["Capability Set"]
    FACTORY["Factory Selection / Composition"]

    GOAL --> REQUIRE --> RESOLVE
    REGISTRY --> RESOLVE
    RESOLVE --> SET --> FACTORY
```

## Capability Node Rule

A capability answers:

> **What can ILAIOS do?**

A capability does not automatically create:

- a new agent;
- a new worker;
- a new provider;
- a new runtime.

---

# 08. Factory / Domain Orchestration Nodes

A Factory is a bounded domain DAG that composes capabilities into a finished product.

```mermaid
flowchart TD
    GOAL["Goal"]
    FACTORY["Selected Factory"]
    DAG["Domain DAG"]

    WEB["Web Factory"]
    VIDEO["Video Factory"]
    SOFTWARE["Software Factory"]
    APP["App Factory"]
    RESEARCH["Research / Data Factory"]
    SECURITY["Security Factory"]
    DOCS["Creative / Document Factory"]
    COMMERCE["Commerce / Growth"]
    PERSONAL["Personal Operations"]

    GOAL --> FACTORY --> DAG
    FACTORY --> WEB
    FACTORY --> VIDEO
    FACTORY --> SOFTWARE
    FACTORY --> APP
    FACTORY --> RESEARCH
    FACTORY --> SECURITY
    FACTORY --> DOCS
    FACTORY --> COMMERCE
    FACTORY --> PERSONAL
```

## Factory Invariants

- Factory ≠ Core.
- Factory ≠ Agent.
- Factory ≠ Worker.
- Factory ≠ Provider.
- Factory cannot create its own routing authority.
- Factory cannot bypass Policy Gateway.
- Factory cannot bypass Evidence.
- Factory cannot directly gain secrets.
- Factory cannot self-approve privileged actions.

---

# 09. Execution Admission Node Graph

```mermaid
flowchart TD
    TASK["Task Envelope"]
    AUTH["Authority"]
    TENANT["Tenant Isolation"]
    PRIVACY["Privacy / Residency"]
    DLP["DLP / Secrets"]
    TOOL["Tool Permission"]
    RISK["Risk / Blast Radius"]
    QUALITY["Required Quality"]
    BUDGET["Budget / Quota"]
    DECISION{"Admission Decision"}

    DENY["DENY"]
    WAIT["REQUIRE APPROVAL"]
    GRANT["ExecutionGrant"]

    TASK --> AUTH --> TENANT --> PRIVACY --> DLP --> TOOL --> RISK --> QUALITY --> BUDGET --> DECISION
    DECISION -->|Denied| DENY
    DECISION -->|Approval Required| WAIT
    DECISION -->|Allowed| GRANT
```

## Admission Output

An admitted task produces a scoped `ExecutionGrant`.

The grant must bind at minimum:

- principal;
- tenant;
- project;
- job/task;
- allowed capability;
- allowed tools;
- allowed resources;
- expiration;
- risk/policy state;
- budget envelope.

---

# 10. Human Approval Node

```mermaid
flowchart TD
    ACTION["Proposed Privileged Action"]
    POLICY["Policy Decision"]
    WAIT["WAITING_FOR_APPROVAL"]
    NOTIFY["Notify Approver"]
    USERDEC{"Human Decision"}
    APPROVED["Recorded Approval"]
    REJECTED["Rejected"]
    EXPIRED["Expired / Revoked"]
    GRANT["Scoped ExecutionGrant"]
    EVID["Audit Evidence"]

    ACTION --> POLICY --> WAIT --> NOTIFY --> USERDEC
    USERDEC -->|Approve| APPROVED --> GRANT --> EVID
    USERDEC -->|Reject| REJECTED --> EVID
    WAIT -->|Timeout / Revoke| EXPIRED --> EVID
```

Typical approval candidates:

- production deployment;
- payment / external spend;
- DNS changes;
- destructive data operation;
- privileged identity/security change;
- external email/send action when policy requires;
- production publishing.

---

# 11. ONE RoutingDecision Node

```mermaid
flowchart TD
    NEED["Capability Requirement"]
    AUTH["Authority Eligibility"]
    PRIV["Privacy / Residency"]
    CTX["Context Window / Modality"]
    TOOL["Tool Requirements"]
    QUALITY["Quality Floor"]
    HEALTH["Provider Health"]
    QUOTA["Quota / Availability"]
    COST["Budget / Cost"]
    LAT["Latency"]
    REL["Historical Reliability"]
    SCORE["Historical Quality"]
    TIE["Deterministic Tie-Break"]
    ROUTE["ONE RoutingDecision"]
    WORKERCLASS["Worker Class"]
    ADAPTER["Approved Adapter"]
    PROVIDER["Replaceable Provider"]

    NEED --> AUTH --> PRIV --> CTX --> TOOL --> QUALITY --> HEALTH --> QUOTA --> COST --> LAT --> REL --> SCORE --> TIE --> ROUTE
    ROUTE --> WORKERCLASS
    ROUTE --> ADAPTER --> PROVIDER
```

## Routing Invariants

- One routing truth.
- Policy/security eligibility is evaluated before cost optimization.
- Provider-specific code remains behind adapters.
- Providers do not own routing authority.
- External routing projects may be references, not a second brain.
- Local, hosted, and external providers are all replaceable execution resources.

---

# 12. Worker / Skill / Tool / Provider Node Model

```mermaid
flowchart TD
    TASK["Authorized Task"]
    SCHED["Scheduler"]
    LEASE["Lease / Fencing"]
    WORKER["Worker Process"]

    SKILL["Approved Skill"]
    TOOL["Tool Adapter"]
    PROVIDER["Provider Adapter"]

    BROWSER["Browser"]
    SHELL["Shell / Code"]
    FILES["Files"]
    API["External API"]
    CLOUD["Cloud"]
    GIT["Git / Repository"]

    MODEL["LLM / Model"]
    IMAGE["Image"]
    VIDEO["Video"]
    VOICE["Voice"]
    SEARCH["Search"]
    LOCAL["Local Runtime"]

    RESULT["Step Result"]

    TASK --> SCHED --> LEASE --> WORKER
    WORKER --> SKILL
    WORKER --> TOOL
    WORKER --> PROVIDER

    TOOL --> BROWSER
    TOOL --> SHELL
    TOOL --> FILES
    TOOL --> API
    TOOL --> CLOUD
    TOOL --> GIT

    PROVIDER --> MODEL
    PROVIDER --> IMAGE
    PROVIDER --> VIDEO
    PROVIDER --> VOICE
    PROVIDER --> SEARCH
    PROVIDER --> LOCAL

    SKILL --> RESULT
    TOOL --> RESULT
    PROVIDER --> RESULT
```

## Concept Separation

```text
CAPABILITY = what can be done
SKILL      = bounded expertise / behavior contract
AGENT      = governed coordinating role
WORKER     = execution process
TOOL       = bounded actuator
PROVIDER   = replaceable model/service/resource
ADAPTER    = ILAIOS ↔ external/local implementation boundary
FACTORY    = bounded domain workflow / DAG
```

---

# 13. Step-Level Autonomous Execution Loop

Every DAG node follows this pattern.

```mermaid
flowchart TD
    READY["READY"]
    ADMIT["Admission"]
    ROUTE["RoutingDecision"]
    EXEC["Execute"]
    OUTPUT["Step Output"]
    VALIDATE["Validate"]
    RESULT{"Valid?"}
    EVID["Write Evidence"]
    STATE["Update State"]
    CHECKPOINT["Checkpoint"]
    NEXT["NEXT NODE"]
    FAIL["Failure Classifier"]
    REPAIR["Bounded Repair / Retry"]

    READY --> ADMIT --> ROUTE --> EXEC --> OUTPUT --> VALIDATE --> RESULT
    RESULT -->|PASS| EVID --> STATE --> CHECKPOINT --> NEXT
    RESULT -->|FAIL| FAIL --> REPAIR --> ADMIT
```

This is the atomic autonomous execution pattern of ILAIOS.

---

# 14. Runtime State Machine

```mermaid
stateDiagram-v2
    [*] --> PLANNING
    PLANNING --> QUEUED
    QUEUED --> RUNNING
    RUNNING --> WAITING_FOR_APPROVAL
    WAITING_FOR_APPROVAL --> RUNNING: approved
    WAITING_FOR_APPROVAL --> FAILED: rejected/expired

    RUNNING --> VALIDATING
    VALIDATING --> CHECKPOINTED: step pass
    VALIDATING --> REPAIRING: validation fail

    REPAIRING --> RETRYING
    RETRYING --> RUNNING

    CHECKPOINTED --> QUEUED: more nodes
    CHECKPOINTED --> FINAL_VALIDATION: final node

    FINAL_VALIDATION --> REPAIRING: fail
    FINAL_VALIDATION --> DONE: pass

    RUNNING --> FAILED: terminal runtime failure
    VALIDATING --> FAILED: policy/security failure
    DONE --> [*]
    FAILED --> [*]
```

## Minimum Runtime States

```text
PLANNING
QUEUED
RUNNING
WAITING_FOR_APPROVAL
VALIDATING
CHECKPOINTED
REPAIRING
RETRYING
FINAL_VALIDATION
DONE
FAILED
```

---

# 15. Checkpoint / Resume Node

```mermaid
flowchart TD
    STEP["Completed Step"]
    STATE["Persist Execution State"]
    ART["Persist Artifact References"]
    EVID["Persist Evidence Cursor"]
    BUDGET["Persist Budget / Retry State"]
    CHECK["Checkpoint"]
    INTERRUPT["Crash / Pause / Restart"]
    LOAD["Load Checkpoint"]
    REAUTH["Revalidate Authority / Policy"]
    RESUME["Resume Next Valid Node"]

    STEP --> STATE --> ART --> EVID --> BUDGET --> CHECK
    CHECK --> INTERRUPT --> LOAD --> REAUTH --> RESUME
```

## Resume Rule

A checkpoint never means old authorization remains valid forever.

Before resume:

- current identity/policy must be revalidated when required;
- expired grants must not be reused;
- budget/retry limits must be reloaded;
- immutable artifact/evidence references must be preserved.

---

# 16. Evaluation / Repair Node Loop

```mermaid
flowchart TD
    ART["Artifact / Step Output"]
    VERIFY["Independent Verifier"]
    FUNCTIONAL["Functional"]
    SECURITY["Security"]
    VISUAL["Visual / Audio"]
    ACCESS["Accessibility"]
    PERF["Performance"]
    PROV["Provenance"]
    ACCEPT["Acceptance Criteria"]
    DEC{"PASS?"}
    FINAL["Accepted"]
    CLASS["Failure Classification"]
    LIMIT{"Within Repair Limits?"}
    REPAIR["Repair Proposal"]
    ADMIT["Governed Re-Admission"]
    ESC["Safe Failure / Human Escalation"]

    ART --> VERIFY
    VERIFY --> FUNCTIONAL --> SECURITY --> VISUAL --> ACCESS --> PERF --> PROV --> ACCEPT --> DEC
    DEC -->|PASS| FINAL
    DEC -->|FAIL| CLASS --> LIMIT
    LIMIT -->|Yes| REPAIR --> ADMIT
    LIMIT -->|No| ESC
```

Hard limits:

```text
max_attempts
max_cost
max_elapsed_time
```

Producer and verifier should be independent where feasible.

---

# 17. Continuous Evidence Node Chain

Evidence is generated throughout execution, not only at the end.

```mermaid
flowchart LR
    GOAL["Goal"]
    PLAN["Plan"]
    POLICY["PolicyDecision"]
    ROUTE["RoutingDecision"]
    EXEC["Execution Event"]
    OUTPUT["Artifact Version"]
    VALID["Validation"]
    APPROVAL["Approval"]
    COST["Cost / Usage"]
    CHECK["Checkpoint"]
    FINAL["AcceptanceManifest"]

    GOAL --> FINAL
    PLAN --> FINAL
    POLICY --> FINAL
    ROUTE --> FINAL
    EXEC --> FINAL
    OUTPUT --> FINAL
    VALID --> FINAL
    APPROVAL --> FINAL
    COST --> FINAL
    CHECK --> FINAL
```

Final evidence must be able to answer:

```text
Who requested this?
Which tenant/project?
What goal?
Which plan?
Which permissions?
Which route?
Which worker?
Which skill/tool/provider?
Which inputs?
Which artifact version?
Which validations?
Which approvals?
Which cost?
Which checksum?
Why was it accepted?
```

---

# 18. Client / Projection Node Model

```mermaid
flowchart TD
    CP["Authoritative Control Plane"]
    EVENTS["Sequenced Events"]
    LIVESTATE["Live State Projection"]

    WEB["Web"]
    DESKTOP["Desktop"]
    MOBILE["Mobile"]
    API["API"]
    CLI["CLI"]
    ENTERPRISE["Enterprise Console"]

    CP --> EVENTS --> LIVESTATE
    LIVESTATE --> WEB
    LIVESTATE --> DESKTOP
    LIVESTATE --> MOBILE
    LIVESTATE --> API
    LIVESTATE --> CLI
    LIVESTATE --> ENTERPRISE
```

## Projection Rule

Clients may display:

- Planning
- Queued
- Running
- Waiting Approval
- Routing
- Executing
- Validating
- Retrying
- Repairing
- Failed
- Done

But UI state does not become authoritative execution state.

---

# 19. Web Factory Node Topology

```mermaid
flowchart TD
    GOAL["Website Goal"]
    RESEARCH["W01 Research"]
    IA["W02 Information Architecture"]
    COPY["W03 Copy"]
    DESIGN_SYS["W04 Design System"]
    DESIGN["W05 Visual Design"]
    BUILD["W06 Implementation"]
    BROWSER["W07 Browser QA"]
    SECURITY["W08 Security QA"]
    ACCESS["W09 Accessibility"]
    PERF["W10 Performance"]
    SEO["W11 SEO"]
    VISUAL["W12 Visual QA"]
    ACCEPT{"W13 Acceptance?"}
    REPAIR["W14 Repair"]
    DEPLOY["W15 Deployment Validation"]
    FINAL["FINISHED WEBSITE"]

    GOAL --> RESEARCH --> IA --> COPY --> DESIGN_SYS --> DESIGN --> BUILD
    BUILD --> BROWSER --> SECURITY --> ACCESS --> PERF --> SEO --> VISUAL --> ACCEPT
    ACCEPT -->|FAIL| REPAIR --> BROWSER
    ACCEPT -->|PASS| DEPLOY --> FINAL
```

Every Web Factory node still passes through the shared:

```text
Execution Admission
→ RoutingDecision
→ Worker
→ Evidence
→ State
→ Checkpoint
```

path.

---

# 20. Video Factory Node Topology

```mermaid
flowchart TD
    GOAL["Video Goal"]
    RESEARCH["V01 Research"]
    CONCEPT["V02 Concept"]
    SCRIPT["V03 Script"]
    STORY["V04 Storyboard"]
    SHOTS["V05 Shot Plan"]
    GEN["V06 Generation / Acquisition"]
    ASSET["V07 Assets"]
    VOICE["V08 Voice"]
    MUSIC["V09 Music"]
    SFX["V10 SFX"]
    CAPTION["V11 Captions"]
    TIMELINE["V12 Canonical Timeline"]
    EDIT["V13 Editing"]
    MIX["V14 Mix"]
    RENDER["V15 Render"]
    VQA["V16 Video QA"]
    AQA["V17 Audio QA"]
    ACCEPT{"V18 Acceptance?"}
    REPAIR["V19 Repair"]
    EVID["V20 Evidence"]
    FINAL["FINAL VIDEO"]

    GOAL --> RESEARCH --> CONCEPT --> SCRIPT --> STORY --> SHOTS --> GEN --> ASSET
    ASSET --> VOICE --> MUSIC --> SFX --> CAPTION --> TIMELINE --> EDIT --> MIX --> RENDER
    RENDER --> VQA --> AQA --> ACCEPT
    ACCEPT -->|FAIL| REPAIR --> EDIT
    ACCEPT -->|PASS| EVID --> FINAL
```

Existing ILAIOS timeline / FFmpeg / Remotion lineage remains authoritative. External editing projects are references, not a second video runtime.

---

# 21. Cross-Factory Autonomous Composition

One user goal may require more than one factory.

```mermaid
flowchart TD
    GOAL["Compound Goal"]
    PLAN["Bounded Cross-Factory DAG"]

    RESEARCH["Research / Data"]
    WEB["Web Factory"]
    VIDEO["Video Factory"]
    SOFTWARE["Software / App"]
    DOCS["Creative / Document"]
    SECURITY["Security Factory"]

    MERGE["Artifact Composition"]
    VERIFY["Cross-Factory Evaluation"]
    FINAL["Finished Product Bundle"]

    GOAL --> PLAN
    PLAN --> RESEARCH
    PLAN --> WEB
    PLAN --> VIDEO
    PLAN --> SOFTWARE
    PLAN --> DOCS
    PLAN --> SECURITY

    RESEARCH --> MERGE
    WEB --> MERGE
    VIDEO --> MERGE
    SOFTWARE --> MERGE
    DOCS --> MERGE
    SECURITY --> MERGE

    MERGE --> VERIFY --> FINAL
```

## Cross-Factory Rule

Cross-factory work is coordinated by the shared Control Plane and bounded DAG.

Factories must not directly create hidden dependencies on one another.

---

# 22. Example — “Mobilya şirketim için premium site yap”

```mermaid
flowchart TD
    U["User"]
    P["Prompt: Premium mobilya sitesi yap"]
    AUTH["Auth / Tenant / Project"]
    GOAL["Goal + Acceptance"]
    CONTEXT["Brand + Business + Authorized Research"]
    PLAN["Bounded Web DAG"]
    CAP["Capabilities"]
    FACTORY["Web Factory"]
    POLICY["Admission"]
    ROUTE["RoutingDecision"]
    EXEC["Governed Workers"]
    BUILD["Website Artifact"]
    QA["Browser + Security + A11y + Performance + Visual QA"]
    CHECK{"Acceptance PASS?"}
    REPAIR["Bounded Repair"]
    EVID["Evidence + Provenance"]
    DELIVERY["Preview / Deploy Policy"]
    DONE["FINISHED PREMIUM WEBSITE"]

    U --> P --> AUTH --> GOAL --> CONTEXT --> PLAN --> CAP --> FACTORY --> POLICY --> ROUTE --> EXEC --> BUILD --> QA --> CHECK
    CHECK -->|FAIL| REPAIR --> POLICY
    CHECK -->|PASS| EVID --> DELIVERY --> DONE
```

The user sees one request.

ILAIOS internally resolves:

```text
research
→ architecture
→ copy
→ design
→ implementation
→ testing
→ validation
→ repair
→ evidence
→ delivery
```

without requiring the user to manually choose agents, models, tools, or providers.

---

# 23. Core Bypass — Node-Level Red Line

```mermaid
flowchart LR
    FACTORY["Factory Node"]
    ADMIT["Execution Admission"]
    ROUTE["RoutingDecision"]
    WORKER["Worker"]
    ADAPTER["Adapter"]
    PROVIDER["Provider"]

    FACTORY --> ADMIT --> ROUTE --> WORKER --> ADAPTER --> PROVIDER

    FACTORY -. "FORBIDDEN" .-> PROVIDER
    FACTORY -. "FORBIDDEN" .-> ADAPTER
    WORKER -. "FORBIDDEN: unapproved" .-> PROVIDER
```

Required path:

```text
Factory
→ Execution Admission
→ RoutingDecision
→ Worker
→ Approved Adapter
→ Provider
```

---

# 24. External Reference Assimilation Nodes

```mermaid
flowchart TD
    REF["External Reference"]
    PIN["Pin Repository + Commit / Tag"]
    LICENSE["License Review"]
    SECURITY["Supply-Chain Review"]
    STUDY["Architecture / UX / Behavior Study"]
    EXTRACT["Requirement Extraction"]
    SPEC["ILAIOS Specification"]
    NATIVE["ILAIOS-Native Implementation"]
    TEST["Tests"]
    EVAL["Independent Evaluation"]
    PROV["Provenance"]
    REGISTER["Capability Registration"]

    REF --> PIN --> LICENSE --> SECURITY --> STUDY --> EXTRACT --> SPEC --> NATIVE --> TEST --> EVAL --> PROV --> REGISTER
```

External references produce knowledge and requirements.

They do not automatically become:

- Core;
- runtime authority;
- permanent provider;
- permanent skill runtime;
- hidden dependency.

---

# 25. Node Contract Template

Every autonomous node should be specifiable using the following form.

```text
NODE_ID
│
├─ Responsibility
│  └─ Exact bounded responsibility
│
├─ Input Contract
│  └─ Required typed input
│
├─ Output Contract
│  └─ Produced typed output
│
├─ Authority
│  └─ What this node is allowed to decide
│
├─ Required Context
│  ├─ Principal
│  ├─ Tenant
│  ├─ Project
│  └─ Job / Task
│
├─ Policy Requirements
│  └─ Admission / permissions / privacy / budget
│
├─ Evidence
│  └─ Evidence records this node must emit
│
├─ State Transition
│  └─ Allowed runtime state transitions
│
├─ Failure Behavior
│  └─ Retry | Repair | Deny | Escalate | Fail Closed
│
└─ Invariants
   ├─ What cannot bypass this node
   ├─ What this node cannot authorize
   ├─ What it cannot persist
   └─ What must fail closed
```

---

# 26. Canonical Autonomous Execution Formula

```mermaid
flowchart LR
    A["USER INTENT"]
    B["GOAL + ACCEPTANCE"]
    C["AUTHORIZED CONTEXT"]
    D["BOUNDED DAG"]
    E["CAPABILITY RESOLUTION"]
    F["FACTORY ORCHESTRATION"]
    G["EXECUTION ADMISSION"]
    H["APPROVAL IF REQUIRED"]
    I["ONE ROUTING DECISION"]
    J["WORKER + SKILL + TOOL + PROVIDER"]
    K["STEP VALIDATION"]
    L["EVIDENCE + STATE + CHECKPOINT"]
    M["NEXT DAG NODE"]
    N["FINAL ARTIFACT"]
    O["INDEPENDENT EVALUATION"]
    P["BOUNDED REPAIR"]
    Q["FINAL EVIDENCE"]
    R["DELIVERY"]
    S["VERIFIED FINISHED PRODUCT"]

    A --> B --> C --> D --> E --> F --> G --> H --> I --> J --> K --> L --> M
    M -->|more work| F
    M -->|complete| N --> O
    O -->|FAIL| P --> G
    O -->|PASS| Q --> R --> S
```

---

# 27. ILAIOS Autonomous System Identity

```text
ILAIOS
=
Authoritative Control Plane
+ Constitutional Core
+ Governed Platform Capabilities
+ Native Factories
+ Bounded Autonomous DAG Execution
+ Single Routing Truth
+ Replaceable Workers / Tools / Providers
+ Human Approval Where Required
+ Step-Level Validation
+ Continuous Evidence
+ Durable State / Checkpoint / Resume
+ Independent Final Evaluation
+ Bounded Repair
+ Verified Finished Product
```

The user experiences:

```text
SIGN IN
→ ONE PROMPT
→ RESULT
```

ILAIOS internally performs:

```text
UNDERSTAND
→ PLAN
→ AUTHORIZE
→ RESOLVE
→ ORCHESTRATE
→ ROUTE
→ EXECUTE
→ VALIDATE
→ RECORD
→ CHECKPOINT
→ REPAIR WHEN BOUNDED
→ VERIFY
→ DELIVER
```

No external model, tool, routing proxy, agent framework, skill repository, or editing application becomes a second ILAIOS brain.
