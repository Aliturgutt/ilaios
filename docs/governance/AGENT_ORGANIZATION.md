# ILAIOS Agent Organization Projection

Status: CONTROLLED PROJECTION — NOT IDENTITY AUTHORITY

## Authority boundary

This document is a human-readable projection of the ILAIOS agent organization. It is not a second registry and cannot mint, redefine, activate, or authorize an agent.

`services/agent_registry.py` is the canonical machine-readable agent identity source. `AgentManifest` records declared identity and boundaries. Normative governance remains in `docs/governance/GOVERNANCE.md`, and actual execution authority remains governed by PolicyDecision / ExecutionGrant and applicable approval rules. Any UI, table, dashboard, or documentation list of agents is a projection only.

## Single active identity rule

ILAIOS is the only active product/platform identity. Historical Hermes, ILAKOS and ILATEN agent designs are consolidated into the ILAIOS organization. A legacy product name must never appear in an active machine agent ID.

Human-readable aliases are presentation metadata only. Orchestration binds to stable `ilaios.agent.*` machine IDs, capability contracts, permissions, callers/targets, escalation paths and verifier identities.

The historical alias `Hermes` is retained only for the Integration engineering role. It is not an active product identity and no orchestration rule depends on that alias.

## Runtime truth boundary

`services/agent_registry.py` records canonical identity/governance registrations. Registry presence means a role has a governed machine identity and manifest. It does **not** by itself prove that the role has a provider-backed specialized executor.

Readiness vocabulary:

- `REGISTERED`: canonical identity, manifest and governance metadata exist.
- `EXECUTABLE`: repository evidence proves a bounded runtime executor can perform the role.
- `VERIFIED`: required tests/evidence independently prove that executor against its acceptance gates.

Current named specialist registrations are deliberately `REGISTERED`. The generic governed agent/skill/provider runtime is separately implemented in `services/runtime/execution.py`.

## Core team

- Orchestrator
- Planner
- Supervisor
- Policy
- CostResource

## Engineering team

- Daedalus — software architecture
- Hephaestus — core engineering
- Apollo — frontend engineering
- Atlas — backend engineering
- Hermes — integration engineering alias only
- Dike — test engineering
- Athena — independent code review
- Argus — runtime QA
- Janus — release assessment
- Asclepius — recovery engineering

## Security team

- SecurityCoordinator
- CodeSec
- WebAPISec
- SupplyChainSec
- InfrastructureSec
- SecurityVerifier

Security roles are defensive/authorized-scope capabilities. Registry membership is not authorization to test arbitrary external systems. Invocation remains subject to permission firewall, scoped execution grants, DLP, independent security scanning and verifier separation.

## Web team

- WebUX
- WebVisual
- WebAsset
- WebContent
- WebSEO
- BrowserQA

## Media team

- Story
- SceneDirector
- MediaGeneration
- VoiceAudio
- Editor
- MediaQA
- SocialMetadata
- Publishing

## Intelligence team

- Research
- FactCheck
- DataAnalyst
- Knowledge

## Operations team

- Automation
- Analytics
- Monitoring
- OperationsRecovery
- ProviderWatcher
- Benchmark

## Meta team

- IndependentVerifier
- SelfDevelopmentCoordinator

## Mandatory agent record

Every canonical registration provides:

- `agent_id`
- human-readable alias
- role
- team
- capabilities
- permissions
- inputs
- outputs
- dependencies
- allowed callers
- allowed targets
- escalation path
- verifier ID
- version
- status
- runtime readiness
- backing capability

## Authority rules

1. Human/organization policy and platform policy outrank agent output.
2. Security and privacy gates may block execution/release.
3. No agent independently verifies itself.
4. A developer/generator role cannot promote its own output to VERIFIED or PRODUCTION.
5. External content is data, never authority to override platform policy.
6. Machine IDs and contracts remain stable even if a human-readable alias changes.
7. Direct production mutation is outside the authority of ordinary implementation agents.
8. Registry projections cannot become identity or execution authority.

## Verification

The registry invariants and representative CodeSec admission path are covered by `tests/test_agent_registry.py` and the existing fail-closed firewall tests in `tests/test_agent_governance.py`.
