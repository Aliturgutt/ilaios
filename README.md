# ILAIOS

**ILAIOS is a governed AI operating system designed to turn one authenticated user goal into a verified finished product.**

> **SIGN IN → ONE PROMPT → GOVERNED AUTONOMOUS EXECUTION → VERIFIED FINISHED PRODUCT**

ILAIOS is not intended to be a thin wrapper around a single model, a collection of unrelated agents, or a bundle of third-party tools. The platform owns the execution authority, capability contracts, policy boundaries, routing decisions, evidence chain, and native product workflows. Models, providers, tools, and external services remain replaceable execution resources.

> **Architecture is a target contract. It is not proof that every described capability is already implemented or production-deployed. Implementation claims require code, tests, CI, runtime, deployment, and evidence.**

---

## What ILAIOS Is

ILAIOS accepts a user outcome such as:

```text
"Build a premium website for my furniture company."
```

and resolves the work internally:

```text
SIGN IN
   │
   ▼
IDENTITY / TENANT / PROJECT
   │
   ▼
USER PROMPT
   │
   ▼
GOAL + ACCEPTANCE CRITERIA
   │
   ▼
AUTHORIZED CONTEXT
   │
   ▼
BOUNDED EXECUTION DAG
   │
   ▼
CAPABILITY RESOLUTION
   │
   ▼
FACTORY ORCHESTRATION
   │
   ▼
EXECUTION ADMISSION
   │
   ▼
APPROVAL IF REQUIRED
   │
   ▼
ONE ROUTING DECISION
   │
   ▼
WORKER + SKILL + TOOL + PROVIDER
   │
   ▼
VALIDATION
   │
   ▼
EVIDENCE + STATE + CHECKPOINT
   │
   ▼
INDEPENDENT FINAL EVALUATION
   │
   ├──── FAIL ───► BOUNDED REPAIR ───► RE-EVALUATION
   │
   ▼ PASS
DELIVERY / DEPLOY / PUBLISH
   │
   ▼
VERIFIED FINISHED PRODUCT
```

The user should not need to manually select a model, provider, worker, skill, or framework.

---

## Product Direction

ILAIOS is built as one governed platform with nine native factory families plus shared platform and intelligence capabilities.

Current factory families include:

- Web Factory
- Video / Media Factory
- Software Factory
- App Factory
- Research / Data Factory
- Security Factory
- Creative / Document Factory
- Commerce / Growth Factory
- Personal Operations Factory

Knowledge / RAG is **not a tenth factory**. It is the shared canonical `ilaios.capability.knowledge` intelligence/context capability used across governed workflows where authorized knowledge retrieval is required.

A factory is a **bounded domain workflow / DAG**. It does not become a second runtime, second router, second policy engine, or second Core.

---

## Architectural Identity

```text
ILAIOS
=
Authoritative Control Plane
+ Frozen-by-Default Constitutional Core
+ Governed Capability Fabric
+ Native Factories
+ Authorized Context / Knowledge
+ Single Routing Truth
+ Governed Workers
+ Permissioned Tools
+ Replaceable Providers
+ Human Approval Where Required
+ Continuous Evidence
+ Durable State / Checkpoint / Resume
+ Independent Evaluation
+ Bounded Repair
+ Verified Finished Product
```

### Global invariants

ILAIOS preserves the following platform-wide rules:

1. **ONE Authoritative Control Plane**
2. **ONE Governed Execution Runtime**
3. **ONE Canonical Capability / Skill / Agent Identity System**
4. **ONE RoutingDecision Truth**
5. **ONE Evidence / Provenance Truth**
6. **Providers are replaceable**
7. **Factories cannot bypass governance**
8. **Repair and retry are bounded**
9. **Client/UI projections are not execution authority**
10. **Core is frozen by default and evolvable only by proof**

### Core rule

> **CORE = FROZEN BY DEFAULT, EVOLVABLE BY PROOF**

The Core may evolve only when a platform-wide invariant or canonical contract cannot be implemented correctly inside an existing governed capability boundary.

A new provider, model, factory, skill, UI, open-source reference, or domain-specific workflow is **not** sufficient reason to enlarge Core.

---

## How the Repository Works

ILAIOS separates architectural authority, governed platform logic, product factories, applications, infrastructure, tests, and evidence.

High-level repository responsibilities are expected to remain structurally separated:

```text
ilaios/
│
├── README.md
│
├── SECURITY.md
├── CONTRIBUTING.md
│
├── docs/
│   ├── canonical/
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   ├── AUTONOMOUS_NODE_ARCHITECTURE.md
│   │   └── ...
│   │
│   ├── platform/
│   ├── operations/
│   ├── security/
│   ├── engineering/
│   ├── governance/
│   │   └── GOVERNANCE.md
│   └── products/
│
├── apps/
├── services/
├── src/
├── workers/
├── tests/
└── infrastructure/
```

The exact physical layout may evolve through governed changes. Architecture ownership and authority boundaries must not be changed merely to match a preferred folder layout.

---

## Canonical Architecture

The first architecture documents should be read in this order:

### 1. `SYSTEM_ARCHITECTURE.md`

The primary system architecture authority.

It defines:

- product/platform boundaries;
- Constitutional Core boundaries;
- Control Plane;
- capability fabric;
- factories;
- policy and approval;
- routing;
- workers and providers;
- tools;
- data and tenant isolation;
- Knowledge / RAG;
- evidence and provenance;
- recovery;
- deployment;
- cross-system invariants.

### 2. `AUTONOMOUS_NODE_ARCHITECTURE.md`

The node-level autonomous execution view of the same architecture.

It shows:

- sign-in nodes;
- identity / tenant / project flow;
- prompt-to-goal flow;
- planner and DAG nodes;
- factory nodes;
- admission and approval nodes;
- provider/model routing;
- tool routing;
- worker execution;
- state machine;
- checkpoint/resume;
- evaluation/repair;
- continuous evidence.

This node map is a **companion view**, not a competing architecture authority.

If a companion diagram conflicts with the canonical System Architecture, the canonical architecture must be corrected or the companion view must be brought back into alignment through a governed change.

---

## Runtime Mental Model

A developer should be able to reason about any ILAIOS execution using this chain:

```text
USER
  │
  ▼
AUTH / IDENTITY
  │
  ▼
PRINCIPAL / TENANT / PROJECT
  │
  ▼
PROMPT
  │
  ▼
INTENT / GOAL / ACCEPTANCE
  │
  ▼
CONTROL PLANE
  │
  ▼
AUTHORIZED CONTEXT
  │
  ▼
PLANNER / BOUNDED DAG
  │
  ▼
CAPABILITY RESOLVER
  │
  ▼
FACTORY / DOMAIN ORCHESTRATOR
  │
  ▼
EXECUTION ADMISSION
  │
  ▼
APPROVAL GATE IF REQUIRED
  │
  ▼
ROUTING
  │
  ▼
SCHEDULER / WORKER
  │
  ├── Approved Skill
  ├── Permissioned Tool
  └── Replaceable Provider
  │
  ▼
STEP OUTPUT
  │
  ▼
VALIDATION
  │
  ▼
EVIDENCE / STATE / CHECKPOINT
  │
  ▼
NEXT DAG NODE
  │
  ▼
FINAL ARTIFACT
  │
  ▼
INDEPENDENT EVALUATION
  │
  ├── FAIL → BOUNDED REPAIR
  │
  └── PASS
          │
          ▼
       DELIVERY
          │
          ▼
VERIFIED FINISHED PRODUCT
```

---

## Identity and Sign-In Model

The target identity architecture supports consumer and enterprise sign-in while normalizing all authenticated users into ILAIOS-owned identity context.

```text
Google ─────────────┐
Microsoft ──────────┤
Outlook / Hotmail ──┤
GitHub ─────────────┤
Apple ──────────────┤
Email ──────────────┤
Microsoft Entra ────┤
Google Workspace ───┤
SAML / OIDC ────────┘
        │
        ▼
   ILAIOS Identity
        │
        ▼
      Principal
        │
        ▼
       Tenant
        │
        ▼
      Project
```

Provider-specific authentication must not become the platform's canonical identity truth.

---

## Provider and Model Independence

Provider-specific logic belongs behind ILAIOS-controlled adapters.

```text
                      ILAIOS Policy / Admission
                                │
                                ▼
                       ONE RoutingDecision
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
        Native Route       External Adapter     Local Route
             │                  │                  │
      ┌──────┼──────┐           │            ┌────┴────┐
      ▼      ▼      ▼           ▼            ▼         ▼
   OpenAI  Gemini Anthropic  Optional      vLLM      Ollama
                            external
                            routing
```

An external routing project may be studied or used behind a bounded adapter. It does not become the authoritative ILAIOS router.

---

## Tools and Execution

Tools are bounded actuators, not autonomous authorities.

Typical tool families include:

```text
Browser
Shell / Code
Git / Repository
Files
External APIs
Cloud
Search
Media
```

Every privileged tool request must flow through:

```text
Task
→ Policy / Execution Admission
→ Scoped ExecutionGrant
→ Permissioned Adapter
→ Sandboxed / Bounded Execution
→ Result Validation
→ Evidence
```

Factories and agents do not receive unrestricted browser, shell, repository, secret, or cloud authority.

---

## Evidence-Driven Development

ILAIOS distinguishes:

```text
Architecture definition
≠
Implementation
≠
Test PASS
≠
CI PASS
≠
Deployment
≠
Current live production state
```

A document stating that a component exists does not prove that the component is implemented or operational.

Implementation status must be established from current code, tests, CI, runtime, deployment, and evidence.

---

## Quick Start — Repository Validation

The repository is Python-based at the platform level. The current project metadata declares `requests` and `python-dotenv` as Python runtime dependencies. Repository contribution rules also define Python/platform quality gates including pytest, Ruff, mypy, pre-commit, and `git diff --check`.

### 1. Clone

```bash
git clone https://github.com/Aliturgutt/ilaios.git
cd ilaios
```

> Access requires repository permission while the repository is private.

### 2. Create a Python environment

#### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Install the currently required local verification dependencies

```bash
python -m pip install requests python-dotenv pytest ruff mypy pre-commit
```

This is a **minimal repository verification bootstrap**, not a statement that every future ILAIOS application, worker, infrastructure target, or product surface uses only these dependencies.

### 4. Run the core repository quality gates

```bash
python -m pytest -q
ruff check .
mypy --strict src tests
pre-commit run --all-files
git diff --check
```

Component-specific workflows may require additional gates.

A command being listed here does **not** mean it has passed for the current commit. Check current CI/test evidence before making a PASS claim.

---

## Development Workflow

Every change should be bounded, reviewable, testable, and evidence-backed.

```text
Current master
      │
      ▼
Focused branch
      │
      ▼
Bounded change
      │
      ▼
Targeted tests
      │
      ▼
Repository quality gates
      │
      ▼
Final diff review
      │
      ▼
Focused PR
      │
      ▼
CI / Evidence
      │
      ▼
Governed merge / release
```

### Development rules

- Do not create a second Core.
- Do not create a second Planner.
- Do not create a second routing authority.
- Do not create a parallel capability registry.
- Do not weaken tests to obtain PASS.
- Do not hide unrelated cleanup inside a functional change.
- Do not claim deployment or production readiness without direct evidence.
- Production-sensitive operations must respect approval policy.
- Architecture changes require governed architectural review.

---

## External Open-Source Projects

External repositories may be useful references, but they do not automatically become ILAIOS runtime dependencies.

Required assimilation path:

```text
External Reference
        │
        ▼
Pin Source / Commit
        │
        ▼
License Review
        │
        ▼
Security / Supply-Chain Review
        │
        ▼
Architecture / UX / Behavior Study
        │
        ▼
Requirement Extraction
        │
        ▼
ILAIOS Specification
        │
        ▼
ILAIOS-Native Implementation
        │
        ▼
Tests + Independent Evaluation
        │
        ▼
Evidence
        │
        ▼
Capability Registration
```

The test is simple:

> If an external reference disappears, the critical ILAIOS architecture and execution authority must remain intact.

---

## Security

Never commit:

- API keys;
- `.env` files containing real secrets;
- database credentials;
- production tokens;
- private signing keys;
- customer secrets;
- real user PII;
- private incident credentials;
- unrestricted cloud credentials.

Use schemas, examples, policies, secret references, and `.env.example` instead.

See `SECURITY.md` for repository security rules.

---

## Documentation Authority

ILAIOS avoids competing “master” documents.

Each architectural concern should have one canonical source of truth.

Companion documents may provide alternate views, diagrams, contracts, or implementation guidance, but they must not silently redefine architecture.

A useful authority model is:

```text
Canonical Architecture
        │
        ▼
Implementation Specification
        │
        ▼
Dependency / Milestone Definitions
        │
        ▼
Actual Code + Tests + CI + Runtime + Deployment Evidence
        │
        ▼
Execution Packages / Plans
        │
        ▼
Status / Roadmap Prose
```

Architecture describes what the system must be.

Evidence describes what the system actually is today.

---

## Current Documentation Build Order

The initial documentation set is being constructed from architecture outward:

```text
01  SYSTEM_ARCHITECTURE.md
02  AUTONOMOUS_NODE_ARCHITECTURE.md
03  README.md
04  PRODUCT_REQUIREMENTS.md
05  IMPLEMENTATION_SPEC.md
06  DEPENDENCY_GRAPH.md
07  API_CONTRACTS.md
08  SECURITY_ARCHITECTURE.md
09  DATA_ARCHITECTURE.md
10  THREAT_MODEL.md
11  TESTING_AND_EVALUATION.md
12  DEPLOYMENT_ARCHITECTURE.md
13  FINOPS.md
14  ENGINEERING_STANDARDS.md
15  GOVERNANCE.md
16  MILESTONES.md
17  ADR/
18  OBSERVABILITY.md
19  FAILURE_RECOVERY.md
```

This ordering is intentional: implementation, product, security, and operational documents must derive from the same architectural truth rather than invent parallel system models.

---

## Project Principle

```text
The user asks for an outcome.

ILAIOS owns the governed path from intent to verified result.

Providers execute.
Tools actuate.
Workers run.
Agents coordinate.
Skills constrain expertise.
Factories organize domain workflows.
The Control Plane owns authority.
Evidence proves what happened.
```

**ILAIOS is the system. Providers are replaceable parts.**