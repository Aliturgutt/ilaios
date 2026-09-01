# ILAIOS — SECURITY ARCHITECTURE

**Document Type:** Canonical Security Architecture  
**Format:** GitHub Markdown + ASCII architecture diagrams  
**Status:** Canonical Baseline v1.0 — Pending Repository Publication  
**Architecture Authority:** `SYSTEM_ARCHITECTURE.md`  
**Product Authority:** `PRODUCT_REQUIREMENTS.md`  
**Implementation Authority:** `IMPLEMENTATION_SPEC.md`  
**Dependency Authority:** `DEPENDENCY_GRAPH.md`  
**Threat Analysis Companion:** `THREAT_MODEL.md`  
**Core Security Principle:** **NO PRIVILEGED EXECUTION WITHOUT VERIFIED IDENTITY, TENANT SCOPE, POLICY, AND EVIDENCE**

> This document defines **where security authority lives in ILAIOS, how trust boundaries are enforced, and which controls are mandatory before data, tools, providers, workers, or external side effects can be used**. It defines target security architecture, not current deployment status.

---

# 00. Purpose

ILAIOS is an autonomous AI operating system.

Autonomy increases the consequences of weak identity, over-broad permissions, prompt injection, data leakage, tool misuse, cross-tenant access, provider compromise, and unbounded side effects.

Therefore ILAIOS security is designed around one rule:

```text
AUTONOMY
    MUST NEVER
OUTRUN AUTHORITY
```

The security system must answer, for every material action:

```text
Who is asking?
For which tenant?
For which project?
For what purpose?
Against which data?
Using which capability?
Using which tool/provider?
Under what permission?
Under what privacy/residency rules?
Under what budget/risk bounds?
Does human approval apply?
What evidence proves the decision?
```

If a mandatory answer is missing:

```text
FAIL CLOSED
```

---

# 01. Security Architecture Scope

This document owns:

- security trust boundaries;
- authentication architecture;
- authorization architecture;
- tenant isolation;
- policy admission;
- data classification;
- privacy/DLP enforcement points;
- prompt/content injection defenses;
- agent/skill/worker authority boundaries;
- tool permission architecture;
- secrets/key management architecture;
- sandbox/isolation architecture;
- network/egress security;
- provider/model trust boundaries;
- RAG/Knowledge security;
- artifact/evidence security;
- approval/HITL security;
- API/client security boundaries;
- repository/software-factory security;
- supply-chain boundaries;
- deployment security requirements;
- security logging/audit boundaries;
- recovery/security continuity requirements;
- security verification gates.

This document does **not** own:

```text
specific threat enumeration
    → THREAT_MODEL.md

exact database schemas
    → DATA_ARCHITECTURE.md

exact API request/response schemas
    → API_CONTRACTS.md

test implementation detail
    → TESTING_AND_EVALUATION.md

deployment topology detail
    → DEPLOYMENT_ARCHITECTURE.md

incident/recovery procedures
    → FAILURE_RECOVERY.md

engineering coding rules
    → ENGINEERING_STANDARDS.md

governance/change authority
    → docs/governance/GOVERNANCE.md
```

---

# 02. Security Constitutional Invariants

The following are non-negotiable:

```text
ONE Authoritative Identity Truth
ONE Tenant / Project Scope per Governed Execution
ONE Policy / Admission Authority
ONE RoutingDecision Truth
ONE Evidence / Provenance Truth
NO client-side security authority
NO provider-owned authorization
NO worker self-authorization
NO agent self-approval
NO skill authority expansion
NO raw unrestricted production tool access
NO broad secret injection
NO cross-tenant retrieval
NO security decision from untrusted model output alone
NO privileged side effect without admission
NO missing-context permissive fallback
NO infinite repair/retry
```

---

# 03. Security Trust Model

ILAIOS is not based on implicit trust between internal components.

The default model is:

```text
VERIFY
    │
    ▼
AUTHORIZE
    │
    ▼
SCOPE
    │
    ▼
EXECUTE
    │
    ▼
VALIDATE
    │
    ▼
EVIDENCE
```

Every boundary assumes inputs may be malformed, stale, over-privileged, adversarial, or compromised.

---

# 04. Trust Zones

```text
┌───────────────────────────────────────────────────────────────┐
│ ZONE 0 — USER / ENTERPRISE IDENTITY                           │
│ Google / Microsoft / GitHub / Apple / Email / Enterprise SSO │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ ZONE 1 — CLIENT / PROJECTION PLANE                            │
│ Web / Desktop / Mobile / CLI / API Client                     │
│ NO AUTHORITATIVE EXECUTION STATE                              │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ ZONE 2 — ILAIOS CONTROL PLANE                                 │
│ Identity / Tenant / Project / Policy / Goal / State / HITL    │
│ AUTHORITATIVE SECURITY DECISIONS                              │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ ZONE 3 — GOVERNED EXECUTION PLANE                             │
│ Queue / Scheduler / Lease / Worker / Tool Gateway / Sandbox   │
│ BOUNDED EXECUTION ONLY                                        │
└───────────────────────────────┬───────────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ ZONE 4A          │  │ ZONE 4B          │  │ ZONE 4C          │
│ External         │  │ Local Providers  │  │ External Tools   │
│ AI Providers     │  │ vLLM / Ollama    │  │ Cloud/Git/API    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

Security controls must be enforced when crossing zones.

---

# 05. Security Control Plane

The security-critical decision chain is:

```text
ExecutionRequest
      │
      ▼
Authentication
      │
      ▼
Authorization
      │
      ▼
Tenant / Project Isolation
      │
      ▼
Data Classification
      │
      ▼
Privacy / DLP
      │
      ▼
Prompt / Content Injection Defense
      │
      ▼
Capability / Tool Permission
      │
      ▼
Secrets / Credential Policy
      │
      ▼
Budget / Quota
      │
      ▼
Risk / Blast Radius
      │
      ▼
PolicyDecision
      │
      ├──── DENY
      │
      ├──── REQUIRE_APPROVAL
      │
      └──── ALLOW
                │
                ▼
         Scoped ExecutionGrant
```

No factory, agent, worker, provider, or tool may bypass this chain for privileged execution.

---

# 06. Authentication Architecture

Target sign-in families:

```text
Consumer / Individual
├─ Google
├─ Microsoft
│  ├─ Outlook
│  ├─ Hotmail
│  └─ Live
├─ GitHub
├─ Apple
└─ Email Account Flow

Enterprise
├─ Microsoft Entra ID
├─ Google Workspace
├─ SAML 2.0
└─ OIDC
```

All providers normalize into:

```text
External Identity
      │
      ▼
Identity Adapter
      │
      ▼
ILAIOS Principal
      │
      ▼
Tenant Membership
      │
      ▼
Project Scope
```

External provider identity is not canonical ILAIOS identity.

---

# 07. Authentication Requirements

Authentication must support:

- secure session issuance;
- session expiration;
- session revocation;
- provider token validation;
- replay protection where applicable;
- CSRF protection for browser flows;
- secure redirect URI handling;
- account linking controls;
- assurance-level tracking;
- step-up authentication;
- phishing-resistant MFA for privileged/high-risk enterprise operations where supported/required;
- enterprise IdP policy compatibility.

Privileged security/admin operations should prefer phishing-resistant MFA methods such as passkeys/FIDO2/WebAuthn or equivalent IdP-enforced strong authentication.

SMS-only MFA must not be treated as the strongest available assurance level.

---

# 08. Account Linking Security

Multiple authentication providers may belong to one ILAIOS Principal.

Account linking must not rely only on matching email strings.

Required safeguards may include:

```text
verified provider assertion
existing authenticated session
explicit link confirmation
provider/domain policy
risk checks
evidence
```

A hostile provider identity must not be able to claim another Principal solely by presenting the same display email.

---

# 09. Authorization Architecture

Authentication proves identity.

Authorization determines allowed action.

Canonical authorization input:

```text
Principal
+ Tenant
+ Project
+ Role / Attributes
+ Capability
+ Resource
+ Requested Action
+ Risk
+ Data Classification
+ Context
```

Authorization may combine:

```text
RBAC
+
ABAC
+
resource ownership
+
tenant policy
+
project policy
+
action-specific policy
```

---

# 10. Deny-by-Default Authorization

Default behavior:

```text
No explicit authority
        │
        ▼
      DENY
```

Permissions must not be inferred from:

- UI visibility;
- model suggestion;
- previous successful action;
- provider availability;
- worker capability;
- tool availability;
- repository visibility alone;
- user text claiming permission.

---

# 11. Tenant Isolation Architecture

Tenant isolation is a P0 security invariant.

```text
Principal
   │
   ▼
Tenant Membership
   │
   ▼
TenantContext
   │
   ├──── Operational Data
   ├──── Knowledge / RAG
   ├──── Artifacts
   ├──── Evidence
   ├──── Jobs / Tasks
   ├──── Queue / Worker Scope
   ├──── Secrets
   └──── Provider Context
```

Every protected object must be scoped to tenant or explicitly global/system-owned.

---

# 12. Project Isolation

Within a tenant, project isolation must be explicit where product policy requires it.

```text
Tenant
  │
  ├── Project A
  │     ├─ Knowledge
  │     ├─ Artifacts
  │     ├─ Jobs
  │     └─ Evidence
  │
  └── Project B
        ├─ Knowledge
        ├─ Artifacts
        ├─ Jobs
        └─ Evidence
```

Project membership must not be inferred merely from knowing an object ID.

---

# 13. Cross-Tenant Access Rule

Unauthorized retrieval or mutation across tenant boundaries is a security violation even if:

- the model never displays the result;
- the data is later discarded;
- the request came from an internal worker;
- the content was semantically relevant;
- the provider call failed;
- the UI hid the response.

Security boundary is enforced **before** protected data is released.

---

# 14. Security Context Propagation

Every governed request must carry or resolve:

```text
principal_id
tenant_id
project_id where applicable
session_id
job_id
task_id
capability_id
risk_class
data_class
purpose
policy references
```

Security context must survive:

```text
API
→ Control Plane
→ Scheduler
→ Worker
→ Tool Gateway
→ Provider Adapter
→ Evidence
```

Loss of mandatory security context fails closed.

---

# 15. Data Classification Architecture

Minimum canonical classes:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

The exact policy mapping may vary by tenant.

Classification influences:

- provider eligibility;
- logging;
- retrieval;
- secret handling;
- retention;
- residency;
- tool access;
- export;
- approval;
- evidence redaction.

---

# 16. Privacy / DLP Plane

Privacy/DLP is cross-cutting.

```text
Input
  │
  ▼
Classification
  │
  ▼
PII / Secret / Sensitive Content Detection
  │
  ▼
Purpose + Tenant Policy
  │
  ▼
Allowed Processing?
  │
  ├─ NO → DENY / REDACT / REQUIRE_APPROVAL
  │
  └─ YES
       │
       ▼
Minimized Authorized Context
```

DLP must operate before sensitive data is sent to broad telemetry or external providers.

---

# 17. Data Minimization

Workers and providers receive only the data required for the task.

Forbidden pattern:

```text
Entire Tenant Dataset
        │
        ▼
Every Worker / Every Provider
```

Required pattern:

```text
Task Purpose
    │
    ▼
Authorization Filter
    │
    ▼
Minimum Necessary Context
    │
    ▼
Specific Worker / Provider
```

---

# 18. Data Residency

Provider and storage eligibility must be able to account for:

```text
tenant residency policy
data classification
provider region
processing region
storage region
legal/contractual requirement
```

Routing may optimize only among resources already eligible under residency/security policy.

---

# 19. Retention Architecture

Retention must be policy-driven.

It must not default to “keep everything as long as possible.”

Retention decisions may differ for:

- operational state;
- prompts;
- model inputs/outputs;
- artifacts;
- evidence;
- knowledge source content;
- logs;
- security events;
- secrets metadata;
- deleted account/tenant data.

The retention schedule belongs to governed policy and data architecture.

---

# 20. Deletion Architecture

Deletion must account for:

```text
operational records
artifacts
knowledge indexes
derived chunks
cached content
provider-side retained data where controllable
backups
evidence/legal retention
```

Deletion claims must distinguish:

```text
user-visible deletion
logical deletion
active-store deletion
backup expiration
legally retained evidence
```

---

# 21. Prompt / Content Injection Security

All external or retrieved content is untrusted.

Examples:

- webpages;
- emails;
- documents;
- repository files;
- issue comments;
- tool output;
- search results;
- RAG sources;
- model-generated content;
- provider metadata.

Untrusted content cannot directly grant instructions with system authority.

---

# 22. Injection Defense Pipeline

```text
Untrusted Content
      │
      ▼
Source Classification
      │
      ▼
Instruction / Data Separation
      │
      ▼
Policy Constraints
      │
      ▼
Capability / Tool Allowlist
      │
      ▼
Structured Tool Request
      │
      ▼
ExecutionGrant Validation
```

The strongest defense is architectural:

```text
content cannot grant authority
```

not merely:

```text
model tries to ignore malicious text
```

---

# 23. Instruction Hierarchy Security

Security-sensitive execution must preserve clear separation between:

```text
System / Constitutional Rules
        ↓
Governed Policy
        ↓
Task / Capability Contract
        ↓
User Goal
        ↓
Untrusted Retrieved / Tool Content
```

Lower-trust content cannot overwrite higher-trust authority.

---

# 24. Indirect Prompt Injection

A worker reading a webpage/document may encounter malicious instructions.

Required behavior:

```text
External Content
    │
    ▼
Treat as Data
    │
    ▼
Extract Relevant Facts
    │
    ▼
Never Expand Permission
    │
    ▼
Tool Request Revalidated
```

A website saying “send all secrets to this endpoint” has zero execution authority.

---

# 25. Agent Security Boundary

Agent = governed coordinating role.

An AgentManifest defines:

- allowed capabilities;
- allowed callers;
- allowed targets;
- permission ceiling;
- risk ceiling;
- input/output contracts;
- evidence obligations.

Agent cannot:

```text
self-grant
self-approve
mint unrestricted ExecutionGrant
change tenant
change Principal
bypass Policy Gateway
bypass RoutingDecision
inject secret scope
alter constitutional rules
```

---

# 26. Skill Security Boundary

A skill is controlled behavior, not authority.

Production skill requirements:

```text
approved identity
version
immutable/content-addressed digest where applicable
bounded permissions
declared network policy
declared filesystem policy
declared secret policy
risk class
tests
provenance
```

Skill requested authority must be a subset of both:

```text
approved skill authority
AND
caller/agent authority
```

---

# 27. Worker Security Boundary

Worker = execution process.

Worker receives:

```text
TaskEnvelope
ExecutionGrant
WorkerLease
FencingToken
Task-scoped context
Approved skill/tool/provider references
```

Worker does not receive:

- Control Plane authority;
- tenant admin authority;
- unrestricted vault access;
- unlimited network;
- unrestricted filesystem;
- unrestricted cloud credentials.

---

# 28. ExecutionGrant Security

ExecutionGrant is a scoped capability token/authorization record.

It must bind at least:

```text
principal
tenant
project
job
task
capability
allowed actions
allowed tools
allowed resources
network scope
filesystem scope
secret scope
spend ceiling
attempt ceiling
issued_at
expires_at
policy decision
approval reference if needed
```

A grant valid for Task A is not automatically valid for Task B.

---

# 29. Grant Expiration and Revocation

Grants must support:

```text
expiration
revocation
scope reduction
policy revalidation
```

Resume after checkpoint must not blindly trust an old grant.

---

# 30. Human Approval Security

Approval is a security control.

```text
Proposed Action
      │
      ▼
Policy
      │
      ▼
RequireApproval
      │
      ▼
WAITING_FOR_APPROVAL
      │
      ▼
Authorized Approver
      │
      ├─ Reject
      │
      └─ Approve
            │
            ▼
      Scoped ExecutionGrant
```

Approval must be bound to the exact action/scope.

---

# 31. Approval Candidates

Policy must be able to require approval for:

- production deploy;
- DNS changes;
- external email/message sends;
- destructive repository operations;
- destructive database operations;
- payment/spend;
- billing changes;
- account/security changes;
- high-risk cloud mutation;
- publication/release;
- security control weakening;
- credential rotation with blast radius;
- sensitive data export.

---

# 32. Self-Approval Prohibition

The following must be structurally impossible:

```text
Agent proposes action
      │
      ▼
Same Agent approves action
```

Likewise:

```text
Worker
Provider
Tool
Factory
```

cannot approve their own privileged execution.

---

# 33. Tool Security Architecture

Canonical tool path:

```text
Worker / Agent Task
      │
      ▼
ToolRequest
      │
      ▼
ExecutionGrant Validation
      │
      ▼
Tool Permission Firewall
      │
      ▼
Scoped Secret Resolution
      │
      ▼
Network / Filesystem Policy
      │
      ▼
Sandbox / Isolation
      │
      ▼
Tool Adapter
      │
      ▼
Tool
      │
      ▼
ToolResult
      │
      ▼
Validation / DLP
      │
      ▼
Evidence
```

---

# 34. Tool Families

Governed tool families may include:

```text
Browser
Shell / Code
Files
Git / Repository
External API
Cloud
Search
Media
Deployment
Communication
Calendar
Payments
DNS
```

Tool availability does not imply permission.

---

# 35. Shell Security

Production shell/code execution must use risk-appropriate isolation.

Controls may include:

- sandbox/container/VM;
- non-root execution;
- read-only base filesystem;
- bounded writable workspace;
- network restrictions;
- CPU/memory/time limits;
- process limits;
- command policy;
- environment-variable minimization;
- no host socket exposure;
- no unrestricted Docker socket;
- no broad credential mounts.

---

# 36. Browser Security

Governed browser execution must consider:

- malicious webpages;
- download handling;
- cross-origin content;
- session/cookie isolation;
- credential scope;
- URL allow/deny policy;
- external redirects;
- file upload/download policy;
- prompt injection;
- clipboard exposure;
- local-network access.

Browser automation is a tool capability, not a trust zone bypass.

---

# 37. Filesystem Security

Worker filesystem access should be:

```text
task-scoped
path-scoped
time-scoped
```

Default:

```text
DENY outside assigned workspace
```

Sensitive host paths, user home directories, credential stores, and unrelated project directories must not be globally exposed.

---

# 38. Repository Security

GitHub/repository integration has two separate security roles.

```text
GitHub Login
    → Identity Provider

GitHub Repository Tool
    → Permissioned Tool / Connector
```

Repository mutation requires:

```text
repository scope
branch scope
write grant
policy
tests
diff review
CI
merge/release governance
```

No login identity automatically grants repository write authority.

---

# 39. Source Code Mutation Security

Software Factory must prevent:

- hidden unrelated changes;
- test weakening for PASS;
- branch protection bypass;
- secret introduction;
- unsigned/unreviewed production release where policy requires review;
- arbitrary force-push;
- dependency tampering without review;
- malicious generated code becoming trusted without tests/review.

---

# 40. Secrets Architecture

Secrets use references and scoped resolution.

```text
Policy-Approved Task
      │
      ▼
ExecutionGrant
      │
      ▼
Secret Reference
      │
      ▼
Secret / Key Service
      │
      ▼
Scoped Runtime Injection
      │
      ▼
Immediate Use
```

Secret value must not become ordinary task context.

---

# 41. Secret Types

Examples:

```text
provider API keys
OAuth tokens
cloud credentials
database credentials
signing keys
webhook secrets
deployment credentials
encryption keys
enterprise connector credentials
payment credentials
```

Each secret has owner, scope, purpose, rotation/revocation policy, and audit metadata.

---

# 42. Secret Exposure Prohibitions

Never intentionally place real secrets in:

- source code;
- README/canonical docs;
- prompt templates;
- general evidence payload;
- broad logs/traces;
- client bundles;
- public artifacts;
- unrestricted worker environment;
- model context unless absolutely required and specifically authorized.

---

# 43. Key Management Architecture

Cryptographic keys must be managed separately from ordinary application configuration.

Target characteristics:

- centralized governed key service/HSM/KMS-equivalent where appropriate;
- envelope encryption for protected data;
- key identifiers rather than raw keys in application records;
- least-privilege decrypt permissions;
- rotation;
- revocation;
- separation of signing vs encryption keys;
- audit of cryptographic operations;
- environment/tenant separation where required.

---

# 44. Key Management Bootstrap

Bootstrap credentials/keys are a special security boundary.

The architecture must define:

```text
initial trust root
key creation
secure storage
operator access
rotation
recovery
break-glass
audit
```

Bootstrap secrets must not become long-lived universal production credentials.

---

# 45. Encryption in Transit

Protected network traffic must use modern authenticated transport encryption appropriate to the deployment environment.

Internal service-to-service trust must not rely solely on “private network = trusted.”

Mutual authentication may be required for high-risk internal boundaries.

---

# 46. Encryption at Rest

Protected data stores should support encryption at rest.

Higher-sensitivity data may require:

- separate keys;
- tenant-aware encryption policy;
- field-level encryption;
- encrypted object storage;
- controlled decrypt operations.

Encryption does not replace authorization.

---

# 47. Provider Security Boundary

Providers are replaceable and untrusted beyond their explicit contract.

```text
ILAIOS Policy
      │
      ▼
Routing Eligibility
      │
      ▼
Approved Adapter
      │
      ▼
Provider
```

A provider never determines:

- who is authorized;
- which tenant owns the data;
- whether the action is allowed;
- whether the artifact is accepted;
- whether evidence is valid.

---

# 48. Provider Eligibility Security

Before provider selection:

```text
capability match
authority
data classification
privacy
residency
provider policy
context requirements
tool requirements
security posture
```

must be satisfied.

Only then may cost/latency/quality optimization occur.

---

# 49. External Provider Data Minimization

Provider request construction must minimize:

- tenant identifiers;
- user PII;
- secrets;
- unrelated project context;
- internal system metadata;
- other users' content.

Provider-specific telemetry/retention settings should be controlled where the provider supports them.

---

# 50. Local Provider Security

Local models such as vLLM/Ollama are not automatically “safe” merely because they are local.

Local execution still requires:

- process isolation;
- model provenance;
- artifact integrity;
- network policy;
- access controls;
- resource limits;
- tenant separation;
- logging/evidence;
- prompt/data security.

---

# 51. Routing Security

There is one `RoutingDecision` truth.

Routing cannot override policy.

```text
Policy Eligibility
      │
      ▼
Privacy / Residency Eligibility
      │
      ▼
Capability / Context Eligibility
      │
      ▼
Provider Health / Quota
      │
      ▼
Quality / Cost / Latency
      │
      ▼
RoutingDecision
```

A cheaper model cannot be chosen if it violates security or privacy constraints.

---

# 52. External Router Security

If an external router is used:

```text
ILAIOS Policy
      │
      ▼
ILAIOS Routing Authority
      │
      ▼
Bounded External Router Adapter
      │
      ▼
External Router
```

External router must not receive authority to bypass ILAIOS policy.

---

# 53. Knowledge / RAG Security Architecture

RAG security begins before retrieval.

```text
RetrievalRequest
      │
      ▼
Principal / Tenant / Project
      │
      ▼
Purpose / Data Classification
      │
      ▼
Authorization Filter
      │
      ▼
Retrieve
      │
      ▼
Rerank
      │
      ▼
DLP / Injection Defense
      │
      ▼
AuthorizedContext
      │
      ▼
Model / Worker
```

Unauthorized retrieval itself is a security failure.

---

# 54. Knowledge Unit Security Metadata

Every protected retrievable unit should retain:

```text
tenant_id
project_id
source_id
classification
purpose constraints
region/residency
retention
authorization attributes
provenance
content hash
ingestion version
```

Principal-specific authorization may be evaluated at retrieval time rather than embedded as a static permanent field.

---

# 55. RAG Security Gates

Production RAG requires:

```text
tenant isolation
authorization-aware retrieval
source provenance
privacy/DLP
prompt injection defense
deterministic evidence
negative isolation tests
full integration testing
```

Embedding generation and vector indexing alone are insufficient.

---

# 56. Knowledge Ingestion Security

Source ingestion pipeline:

```text
Authorized Source
      │
      ▼
Source Identity
      │
      ▼
Malware / Format Safety Checks
      │
      ▼
Parse / Normalize
      │
      ▼
Classification
      │
      ▼
Injection / Active Content Handling
      │
      ▼
Provenance Binding
      │
      ▼
Chunk / Index
```

Source authorization must be preserved through derived chunks/indexes.

---

# 57. Artifact Security

Artifacts may contain sensitive or executable content.

ArtifactRecord must retain:

```text
tenant/project ownership
classification
producer
content hash
storage reference
version
validation status
```

Executable artifacts must not be trusted solely because ILAIOS generated them.

---

# 58. Artifact Integrity

Material artifacts should be integrity-verifiable.

Typical mechanisms:

```text
content hash
version ID
immutable object version
signature where appropriate
evidence link
```

Repair creates a new version rather than silently rewriting historical accepted content.

---

# 59. Evidence Security

Evidence is security-critical.

It must be:

```text
integrity-verifiable
tenant-scoped
minimally sufficient
privacy-aware
append-oriented / tamper-evident where appropriate
linked to exact artifacts/decisions
```

Evidence must not become a secret dump.

---

# 60. Security Event Evidence

Material security events include:

```text
authentication
authorization decision
policy denial
approval request/decision
grant issuance/revocation
secret access
tool execution
provider route
tenant isolation violation
DLP decision
security validation
artifact acceptance
deployment approval
break-glass use
```

---

# 61. Security Logging vs Evidence

```text
SECURITY LOG
    operational diagnostic stream

EVIDENCE
    canonical proof of material decision/action
```

They may reference one another but are not interchangeable.

---

# 62. Observability Security

Logs/metrics/traces must minimize:

- secrets;
- tokens;
- full prompts with sensitive data;
- protected payloads;
- private source documents;
- payment data;
- authentication assertions.

Structured IDs should be preferred over raw sensitive content.

---

# 63. API Security Boundary

All API entrypoints must enforce:

```text
authentication
authorization
tenant validation
request validation
rate/abuse controls
idempotency where needed
policy admission for privileged actions
safe error handling
audit/evidence
```

Client-provided tenant IDs must be validated against authenticated membership.

---

# 64. API Input Validation

Inputs must be:

- schema validated;
- size bounded;
- type checked;
- canonicalized where required;
- rejected on ambiguous/malformed privileged fields;
- protected against injection into SQL/shell/templates/paths;
- treated as untrusted.

---

# 65. API Error Security

Errors must not disclose:

- stack secrets;
- credentials;
- internal tokens;
- raw vault references;
- sensitive tenant existence;
- unnecessary provider internals;
- filesystem paths where risky.

Diagnostic detail belongs in protected operational telemetry.

---

# 66. Rate / Abuse Protection

Entry points should support controls for:

```text
request frequency
concurrency
cost
token use
job creation
provider calls
tool calls
authentication attempts
suspicious automation
```

Rate limits supplement, not replace, authorization.

---

# 67. Client Security

Clients are projections.

They must not contain:

- backend provider master keys;
- unrestricted cloud credentials;
- canonical policy authority;
- authoritative scheduler state;
- hidden privileged bypass endpoints.

Sensitive actions must be reauthorized server-side.

---

# 68. Web Client Security

Web surface should support standard protections such as:

- secure cookies where appropriate;
- HttpOnly/Secure/SameSite;
- CSRF defense;
- CSP;
- frame protections;
- XSS prevention;
- secure dependency handling;
- OAuth state/nonce validation;
- origin validation;
- secure cache headers for sensitive pages.

Specific deployment values belong in deployment/engineering docs.

---

# 69. Desktop / Mobile Client Security

Desktop/mobile clients must treat local storage as potentially exposed.

Avoid storing long-lived high-privilege secrets locally.

Where tokens are stored:

- use OS secure storage;
- minimize scope;
- support revocation;
- avoid embedding provider master credentials;
- validate all privileged operations server-side.

---

# 70. Enterprise SSO Security

Enterprise identity integration must support:

```text
issuer validation
audience validation
signature validation
nonce/state
domain/tenant mapping
role/group mapping policy
session lifetime
deprovisioning
revocation
MFA/assurance signals
```

Group claims must not automatically become administrator rights without governed mapping.

---

# 71. Service-to-Service Security

Internal services should authenticate each other.

Security should not rely solely on network location.

Controls may include:

```text
service identity
short-lived credentials
mTLS
signed tokens
audience restriction
least privilege
network segmentation
```

---

# 72. Scheduler Security

Scheduler may assign work but cannot expand authority.

It must validate:

```text
task eligibility
worker capability
grant validity
lease
tenant/project scope
fencing state
```

Queue contents must not become a covert privilege escalation path.

---

# 73. Lease / Fencing Security

WorkerLease protects against duplicate/stale execution.

Commit is valid only if:

```text
lease is current
fencing token is current
job state allows commit
grant remains valid
```

A stale worker cannot overwrite resumed/cancelled/newer state.

---

# 74. Cancellation Security

Cancellation requires authority.

```text
CancellationRequest
      │
      ▼
Authorization
      │
      ▼
CANCEL_REQUESTED
      │
      ▼
Stop New Work
      │
      ▼
Fence Late Results
      │
      ▼
CANCELLED
```

Cancellation must not erase evidence of already executed external side effects.

---

# 75. Sandbox Architecture

Risk-appropriate sandboxing may use:

- process isolation;
- containers;
- microVMs;
- restricted OS users;
- filesystem namespaces;
- seccomp/sandbox profiles;
- network namespaces;
- ephemeral environments.

Sandbox design must reflect task risk and tool capability.

---

# 76. Sandbox Escape Assumption

Security architecture assumes sandbox escape is possible.

Therefore:

```text
sandbox
≠
only control
```

Also required:

```text
least privilege
scoped credentials
network restriction
host separation
short-lived grants
monitoring
fencing
```

---

# 77. Network Egress Architecture

Default worker egress should be limited to task need.

Possible policies:

```text
DENY ALL
ALLOW provider endpoints
ALLOW approved domains
ALLOW via controlled proxy
ALLOW temporary destination set
```

High-risk tasks should not have unrestricted internet access by default.

---

# 78. Local Network Protection

Browser/tool workers must be protected against unintended access to:

- metadata services;
- localhost admin ports;
- RFC1918/internal networks;
- internal control-plane endpoints;
- developer workstation services;
- cloud instance credentials.

This reduces SSRF-style impact.

---

# 79. External Side-Effect Security

Examples:

```text
deploy
publish
send
pay
delete
merge
rotate
change DNS
change identity
modify firewall
```

Each external side effect is a governed task, not a post-processing shortcut.

---

# 80. External Side-Effect Flow

```text
Proposed Side Effect
      │
      ▼
Policy / Risk
      │
      ▼
Approval if Required
      │
      ▼
Scoped Grant
      │
      ▼
Tool Gateway
      │
      ▼
External Action
      │
      ▼
Verification
      │
      ▼
Evidence
```

---

# 81. Financial / Cost Security

Budget is part of execution security because autonomous systems can create financial side effects.

Controls may include:

```text
tenant budget
project budget
job budget
task ceiling
provider cost ceiling
retry ceiling
repair ceiling
spend approval
concurrency limits
```

A fallback route cannot silently exceed permitted spend.

---

# 82. Payment Security Boundary

Payment capability, if enabled, must use specialized provider/tokenization architecture.

ILAIOS should minimize direct handling of sensitive payment credentials.

Payment execution requires:

- explicit scope;
- strong authentication where applicable;
- approval policy;
- exact amount/currency;
- merchant/recipient binding;
- replay protection;
- evidence;
- bounded provider credentials.

---

# 83. Security Factory Boundary

Security Factory is not the Policy Engine.

```text
Security Factory
    → analyze
    → detect
    → classify
    → recommend
    → verify

Policy Gateway
    → authorize
    → deny
    → require approval
```

Security Factory cannot grant itself remediation rights.

---

# 84. Web Factory Security

Web Factory security dependencies include:

```text
authorized research
safe content ingestion
dependency/security scanning
browser QA
secret protection
deployment policy
CSP/security headers as applicable
artifact integrity
evidence
```

Generated site code must still pass security validation.

---

# 85. Video / Media Security

Video/media workflows must consider:

- untrusted uploaded media;
- malformed codecs/files;
- external media providers;
- copyright/provenance metadata where applicable;
- temporary file isolation;
- command injection into media tools;
- path traversal;
- resource exhaustion;
- output artifact validation.

Media tooling must run within bounded execution.

---

# 86. Software Factory Security

Software Factory must enforce:

```text
repository authorization
branch scope
sandboxed execution
dependency review
secret scanning
static/security checks
test integrity
diff review
CI evidence
merge governance
release governance
```

Generated code is untrusted until reviewed/tested by required gates.

---

# 87. Dependency / Supply-Chain Security

Third-party packages, containers, actions, plugins, models, and external references can be attack vectors.

Required controls may include:

```text
source provenance
version pinning
lockfiles
hash/signature verification where available
license review
dependency scanning
malware/supply-chain review
minimal dependency introduction
controlled updates
rollback
```

---

# 88. Model Supply-Chain Security

Local/downloaded models require:

- source provenance;
- checksum/signature where available;
- safe serialization format preference;
- restricted loading;
- license review;
- version tracking;
- storage integrity;
- no arbitrary code execution during model loading unless explicitly trusted/sandboxed.

---

# 89. External Open-Source Assimilation Security

Canonical path:

```text
External Reference
      │
      ▼
Pin Source / Commit / Tag
      │
      ▼
License Review
      │
      ▼
Security / Supply-Chain Review
      │
      ▼
Behavior Study
      │
      ▼
Requirement Extraction
      │
      ▼
ILAIOS-Native Implementation
      │
      ▼
Security Tests
      │
      ▼
Evidence
```

Installing an external skill/project is not equivalent to trusting it.

---

# 90. CI/CD Security Architecture

CI/CD must not be treated as an unrestricted privileged shell.

Security requirements may include:

- least-privilege workflow tokens;
- protected environments;
- secret isolation;
- branch protections;
- required checks;
- dependency pinning;
- artifact integrity;
- trusted release provenance;
- approval for production;
- no pull-request secret exposure to untrusted forks;
- auditability.

---

# 91. Build Artifact Security

Release/build artifacts should support:

```text
deterministic/repeatable build where practical
artifact hash
source commit linkage
test/CI linkage
signing where appropriate
provenance metadata
```

Build artifacts must not contain accidental credentials.

---

# 92. Deployment Security Boundary

Target logical path:

```text
Internet / Enterprise Network
        │
        ▼
Edge / WAF / CDN
        │
        ▼
API / Entry
        │
        ▼
Control Plane
        │
        ├─ Identity / Policy
        ├─ Workflow / Scheduler
        ├─ Routing
        ├─ Knowledge
        ├─ Evidence
        └─ Observability
        │
        ▼
Durable Queue
        │
        ▼
Isolated Worker Pool
        │
        ▼
Approved Adapters
        │
        ▼
External / Local Providers
```

Workers must be isolated from unrestricted Control Plane authority.

---

# 93. Edge Security

Edge controls may include:

- TLS termination;
- WAF;
- DDoS protection;
- request-size limits;
- bot/abuse controls;
- origin protection;
- rate limits;
- security headers;
- restricted admin entry.

Edge controls are supplemental; authorization remains in the platform.

---

# 94. Database Security

Operational data stores should use:

```text
least-privilege service roles
tenant-aware queries/policies
encrypted transport
backup encryption
schema constraints
migration controls
audit where required
```

Application authorization must not rely solely on obscure object IDs.

---

# 95. Object Storage Security

Artifact/object storage requires:

- tenant-scoped access;
- private-by-default objects;
- short-lived signed access when used;
- encryption;
- malware/content checks where relevant;
- upload type/size controls;
- integrity hashes;
- lifecycle policy.

---

# 96. Vector / Knowledge Store Security

Knowledge/vector stores require:

```text
server-side authorization
tenant/project filtering
classification-aware retrieval
source provenance
no direct untrusted client query authority
```

A vector similarity result is not authorization.

---

# 97. Cache / Coordination Security

Caches and coordination stores may contain security-sensitive state.

Protect:

- session metadata;
- leases;
- fencing tokens;
- rate limits;
- temporary authorization state;
- job coordination.

Do not store long-lived raw secrets unnecessarily.

---

# 98. Backup Security

Backups must consider:

- encryption;
- access separation;
- retention;
- tenant deletion implications;
- restore testing;
- tamper/ransomware resistance;
- region/residency;
- key availability;
- audit.

Backup existence does not substitute for recovery verification.

---

# 99. Security Recovery

Recovery must preserve security invariants.

After failover/restart:

```text
expired grants remain expired
revoked credentials remain revoked
tenant boundaries remain intact
fencing prevents stale commits
policy configuration is current
evidence lineage survives
```

Recovery must not start the system in a “temporarily permissive” mode.

---

# 100. Break-Glass Access

Emergency access may exist for tightly controlled operator recovery.

Break-glass must include:

```text
strong authentication
explicit role
short lifetime
limited scope
reason
alerting
evidence
post-use review
revocation
```

Break-glass is not a routine administrative shortcut.

---

# 101. Administrative Security

Administrative capabilities should be separated by function where practical.

Examples:

```text
identity admin
security admin
billing admin
deployment admin
audit viewer
tenant admin
```

A single routine role should not automatically own all high-risk powers.

---

# 102. Separation of Duties

High-risk workflows may require separation between:

```text
requester
approver
executor
verifier
```

Exact separation depends on risk/tenant policy.

---

# 103. Security Configuration

Security configuration hierarchy:

```text
constitutional platform rules
        ↓
environment controls
        ↓
tenant security policy
        ↓
project policy
        ↓
task-specific restrictions
```

Lower scopes may tighten rules.

They may not weaken constitutional invariants.

---

# 104. Policy Change Security

Changes to security policy can have broad blast radius.

High-risk policy modifications may require:

- strong authentication;
- approval;
- change diff;
- staged rollout;
- validation;
- rollback;
- evidence.

---

# 105. Security Feature Flags

Feature flags may control rollout but cannot bypass:

```text
authentication
tenant isolation
mandatory policy
mandatory evidence
critical approval
secret isolation
security verification
```

---

# 106. Security Maturity Model

Security capabilities use the canonical capability maturity chain:

```text
DESIGNED
→ SPECIFIED
→ IMPLEMENTED
→ TESTED
→ VERIFIED
→ DEPLOYED / PRODUCTION
```

`DEPRECATED` is a separate lifecycle exit state.

A security control is not production-ready merely because code exists.

---

# 107. Security Definition of Done — Identity

Identity security is `VERIFIED` for a defined scope only when:

```text
provider assertions validated
canonical Principal mapping works
tenant membership enforced
session expiry works
session revocation works
account linking is protected
strong-auth policy works where required
negative authorization tests pass
evidence exists
```

---

# 108. Security Definition of Done — Tenant Isolation

Tenant isolation requires:

```text
operational DB isolation
artifact isolation
knowledge isolation
job/task isolation
worker scope isolation
evidence isolation
secret isolation
search isolation
negative cross-tenant tests
```

A UI-only tenant selector is not isolation.

---

# 109. Security Definition of Done — Tool Gateway

Tool security requires:

```text
grant validation
permission allowlist
secret scoping
filesystem controls
network controls
sandbox
timeouts/resource limits
result validation
DLP
evidence
negative bypass tests
```

---

# 110. Security Definition of Done — RAG

Production RAG security requires:

```text
authorization-aware retrieval
tenant/project isolation
source provenance
classification
DLP
prompt injection handling
minimum necessary context
provider eligibility controls
evidence
negative isolation tests
```

---

# 111. Security Definition of Done — Provider Routing

Security-sensitive routing requires:

```text
policy before optimization
privacy/residency enforcement
provider eligibility
model/resource eligibility
cost cannot bypass policy
single RoutingDecision truth
fallback revalidation
evidence
negative tests
```

---

# 112. Security Definition of Done — HITL

Approval security requires:

```text
policy can require approval
exact action/scope shown
authorized approver only
approve/reject
expiration/revocation
no self-approval
grant bound to decision
modified action re-evaluated
evidence
```

---

# 113. Security Definition of Done — Secrets

Secrets architecture requires:

```text
secret references
scoped runtime resolution
least privilege
rotation/revocation
redacted telemetry
no client embedding
no source-control exposure
key separation
audit/evidence
```

---

# 114. Security Definition of Done — Sandboxed Execution

Sandboxed execution requires:

```text
bounded filesystem
bounded network
bounded compute/time
non-root/least privilege where applicable
no broad host credential access
no Control Plane authority
stale result fencing
security tests
```

---

# 115. Security Testing Requirements

Security-critical controls require both positive and negative tests.

Examples:

```text
valid tenant access succeeds
cross-tenant access fails

valid grant executes
expired grant fails

approved tool succeeds
unapproved tool fails

approved provider route succeeds
privacy-ineligible provider fails

authorized approver succeeds
self-approval fails

valid retrieval succeeds
unauthorized RAG retrieval fails
```

Detailed methodology belongs in `TESTING_AND_EVALUATION.md`.

---

# 116. Adversarial Testing

Security verification should include relevant adversarial classes:

- prompt injection;
- indirect prompt injection;
- data exfiltration attempts;
- tenant confusion;
- IDOR-style access;
- path traversal;
- shell injection;
- command injection;
- SSRF;
- malicious file upload;
- poisoned RAG source;
- provider compromise simulation;
- stale worker replay;
- approval bypass;
- secret leakage;
- malicious dependency;
- cancellation race;
- budget bypass.

Exact scenarios belong in `THREAT_MODEL.md`.

---

# 117. Security Evidence Requirements

A security-sensitive change is not verified until evidence can answer:

```text
What security boundary changed?
What requirement authorized the change?
Which tenant/data classes are affected?
Which controls enforce it?
Which negative tests prove denial?
Which CI gates passed?
Which artifact/version was tested?
Who approved privileged rollout?
What deployment/runtime evidence exists?
```

---

# 118. Security Incident Signal Sources

Potential signal sources:

```text
auth failures
tenant isolation violations
policy denials
DLP triggers
secret access anomalies
tool permission violations
sandbox violations
unexpected egress
provider anomalies
suspicious job patterns
artifact integrity failures
security test regressions
break-glass access
```

Incident response process belongs in `FAILURE_RECOVERY.md` / security operations procedures.

---

# 119. Security Telemetry Severity

Security events should support severity/risk classification such as:

```text
informational
low
medium
high
critical
```

Severity must not be determined solely by an LLM.

Deterministic rules and human/security review may be required for high-impact events.

---

# 120. Current Reality vs Target Security

This document defines target security architecture.

Current state must be determined from:

```text
current code
current tests
current CI
current runtime evidence
current deployment evidence
```

Therefore:

```text
SECURITY_ARCHITECTURE.md says control must exist
≠
proof control currently exists in production
```

Mutable security status belongs in evidence/milestone/operational status, not in this canonical architecture.

---

# 121. Security Red Lines

Reject any implementation that introduces:

```text
Factory → direct provider with no routing/policy
Worker → unrestricted shell
Worker → broad vault access
Agent → self approval
Agent → self grant
Skill → authority expansion
Client → authoritative job state
Client → backend master credentials
Cross-tenant RAG retrieval
Provider → authorization decision
External router → policy authority
UI hidden state → security authority
Security logs containing secrets
Infinite retry after security denial
Deployment bypassing approval
```

---

# 122. Canonical Security Request Flow

```text
USER / SERVICE
      │
      ▼
AUTHENTICATION
      │
      ▼
ILAIOS PRINCIPAL
      │
      ▼
TENANT / PROJECT RESOLUTION
      │
      ▼
REQUEST / GOAL
      │
      ▼
DATA / RISK CLASSIFICATION
      │
      ▼
AUTHORIZED CONTEXT
      │
      ▼
EXECUTION REQUEST
      │
      ▼
POLICY GATEWAY
      │
      ├─ Authentication assurance
      ├─ Authorization
      ├─ Tenant isolation
      ├─ Privacy / residency
      ├─ DLP / secret detection
      ├─ Prompt injection constraints
      ├─ Tool permission
      ├─ Budget / quota
      └─ Risk / blast radius
      │
      ▼
POLICY DECISION
      │
      ├──── DENY
      │
      ├──── REQUIRE APPROVAL
      │               │
      │               ▼
      │        AUTHORIZED HUMAN
      │               │
      │               ▼
      └────────────► EXECUTIONGRANT
                      │
                      ▼
              ONE ROUTINGDECISION
                      │
                      ▼
              SCHEDULER / LEASE
                      │
                      ▼
                    WORKER
                      │
                      ▼
                 TOOL GATEWAY
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
 Scoped Secret    Sandbox       Network Policy
        │             │             │
        └─────────────┼─────────────┘
                      ▼
              APPROVED ADAPTER
                      │
                      ▼
              TOOL / PROVIDER
                      │
                      ▼
                  RESULT
                      │
                      ▼
          VALIDATION / DLP / SECURITY
                      │
                      ▼
               EVIDENCE + STATE
                      │
                      ▼
                  CHECKPOINT
```

---

# 123. Canonical Security Formula

```text
IDENTITY
+ TENANT ISOLATION
+ LEAST PRIVILEGE
+ FAIL-CLOSED POLICY
+ DATA CLASSIFICATION
+ PRIVACY / DLP
+ INJECTION-RESISTANT AUTHORITY MODEL
+ SCOPED GRANTS
+ PERMISSIONED TOOLS
+ SCOPED SECRETS
+ SANDBOX / NETWORK BOUNDARIES
+ PROVIDER INDEPENDENCE
+ HUMAN APPROVAL FOR HIGH-RISK ACTIONS
+ CONTINUOUS EVIDENCE
+ NEGATIVE SECURITY TESTS
+ RECOVERY WITHOUT SECURITY DOWNGRADE
=
ILAIOS SECURITY ARCHITECTURE
```

---

# 124. Final Security Invariant

The final security rule is:

> **No model, agent, skill, worker, tool, provider, factory, client, or external project can grant itself authority inside ILAIOS.**

Authority originates from:

```text
authenticated identity
        +
tenant/project membership
        +
governed policy
        +
explicit bounded grants
        +
human approval when required
```

Execution remains:

```text
bounded
isolated
observable
revocable
verifiable
```

and every material security decision remains evidence-bearing.

**ILAIOS may automate work. It may not automate away accountability or authorization.**
