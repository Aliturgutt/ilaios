# Hermes → ILAKOS → ILATEN → ILAIOS Unified Lineage Audit

Audit baseline: `master` at `a02a2c8897616afcafa45aafee6c1ac36c15898a` on 11 August 2026.

## Decision

ILAIOS is the single active product, platform, runtime identity and capability authority.

Hermes, ILAKOS and ILATEN are migration/provenance sources. Useful implementation, architecture, governance and requirements are retained only by mapping them to one canonical ILAIOS capability. Duplicate active runtimes are not created to preserve a legacy name.

Website and Desktop implementation paths are explicitly outside this consolidation package.

## Evidence precedence

Implementation claims follow this order:

1. current repository/runtime evidence;
2. current tests and CI evidence;
3. canonical contracts/architecture;
4. migration requirement matrices;
5. historical roadmap/design material.

Historical provenance is preserved even when later evidence supersedes an old lifecycle projection.

## Four-way capability audit

| Final ILAIOS capability | Hermes lineage | ILAKOS design | ILATEN contribution | Repository evidence at baseline | Conservative result |
|---|---|---|---|---|---|
| Core Platform | audit, evidence chain, immutable context, tool gateway, validation | control-plane foundation | deterministic control/governance requirements | `src/core`, `services/control_plane` | VERIFIED foundation |
| Identity / Tenant | limited early foundation | explicit identity/tenant service | RBAC/ABAC, sessions, recovery, break-glass, tenant controls | `services/identity.py`, IAM.I02 evidence | VERIFIED reference controls |
| Workflow / Runtime | video automation execution lineage | durable workflow/worker model | bounded authority and operational control | `services/runtime`, control-plane workflows | VERIFIED foundation |
| Policy / Governance | approval/evidence principles | policy, HITL, FinOps | extensive enterprise governance and approval controls | `services/governance`, `services/ai_governance.py`, `services/agent_governance.py` | VERIFIED/implemented foundations; detailed ILATEN rows remain partial where not fully proven |
| Evidence / Audit / Provenance | proven core lineage | independent verification and artifact model | audit/evidence governance | `src/core`, `services/evidence` | VERIFIED foundation |
| Privacy / DLP | security lineage | privacy gate design | residency, retention, legal hold, deletion/export/DLP | `services/privacy.py`, DATA.I04 | IMPLEMENTED reference controls |
| Secrets / Cryptography | security lineage | secrets service design | KMS/HSM-compatible lifecycle and tenant secret controls | `services/cryptography.py`, CRYPTO.I03 | IMPLEMENTED reference controls |
| Observability / Operations / Recovery | recovery/evidence lineage | monitoring/recovery worker model | SLO, incident, backup/restore/DR requirements | `services/observability.py`, `services/operations.py`, `services/operational_drills.py` | VERIFIED foundation |
| Agent governance | agent concepts | coordinated digital workforce | complete manifest/permission/security requirements | `services/agent_governance.py` and tests | VERIFIED governance primitive |
| Named specialist organization | named engineering/security/specialist designs | expanded team taxonomy | verifier/governance constraints | newly consolidated `services/agent_registry.py` | IMPLEMENTED registry pending CI; specialist executors remain REGISTERED only |
| Provider routing / FinOps | provider adapters | replaceable provider router | token/cost/provider governance | `services/runtime/routing.py`, `services/ai_governance.py` | VERIFIED/implemented foundation |
| Code Intelligence | implemented Hermes module | retained intelligence capability | governance constraints | `src/code_intelligence` | IMPLEMENTED; fresh targeted revalidation remains desirable |
| Knowledge / Project Context | knowledge graph/project manager | knowledge/memory target | enterprise data governance | `src/knowledge_graph`, `src/project_manager` | IMPLEMENTED; fresh targeted revalidation remains desirable |
| Video / Media Factory | M01-M30 and VIDEO.V01-V30 lineage | canonical Video Factory | governance/security/cost controls | `src/video_automation`, durable video integration/evidence | VERIFIED baseline; external publishing/provider proof remains environment-dependent |
| Web Factory | early factory design | production Web Factory target | enterprise governance requirements | `services/integrations/web_factory.py`, tests | IMPLEMENTED bounded factory foundation |
| Software Factory | controlled code work lineage | Software Factory | strict governance/approval/security | `services/software_factory.py`, tests | IMPLEMENTED bounded isolated proposal factory |
| Security Factory | five-agent defensive/security design | dedicated factory target | strong enterprise security/governance controls | agent firewall/security roles exist; no dedicated factory implementation root | SPECIFIED/PARTIAL foundation, not a complete factory |
| App Factory | client/factory design | explicit App Factory | governance/release controls | no dedicated platform factory implementation root assessed here | PLANNED/SPECIFIED; Desktop excluded from this package |
| Research / Data | research/data concepts | factory target | data governance | knowledge/code foundations only; no dedicated factory root | PLANNED/SPECIFIED |
| Creative / Document | design concept | factory target | governance requirements | no dedicated factory root | PLANNED/SPECIFIED |
| Commerce / Growth | automation concept | factory target | enterprise governance/cost controls | no dedicated factory root | PLANNED/SPECIFIED |
| Personal Operations / Automation | Hermes automation goal | factory target | policy/governance controls | generic workflow/runtime exists; no dedicated factory root | PLANNED/SPECIFIED |

## ILATEN detailed requirement boundary

The authoritative detailed ILATEN requirement audit remains `ILATEN_TO_ILAIOS_MIGRATION_MATRIX.csv` and `ILATEN_TO_ILAIOS_AUDIT_REPORT.md`. That audit contains 8,346 granular requirements and deliberately does not equate related reference implementation with complete satisfaction of every composite enterprise requirement.

This unified audit does not bulk-promote those rows. It supplies a platform-level consolidation map above the detailed requirement matrix.

## Duplicate/conflict decisions

- One active product identity: ILAIOS.
- One active capability namespace: `ilaios.capability.*`.
- One active machine-agent namespace: `ilaios.agent.*`.
- Hermes Video Automation implementation evolves into the ILAIOS Video/Media Factory capability; it is not duplicated.
- ILATEN governance/security requirements strengthen ILAIOS controls; they do not create a second enterprise runtime.
- ILAKOS factory taxonomy becomes ILAIOS capability taxonomy; it does not survive as a parallel product.
- Historical names remain in Git history, migration evidence and provenance documents where rewriting them would damage traceability.

## Identity rules

Active machine IDs must not contain `Hermes`, `ILAKOS` or `ILATEN`. Human-facing historical provenance may contain those terms. Active agent display aliases must also avoid legacy product names; the integration role uses the neutral `Integration Bridge` label.

## Security conclusions

The current repository contains a fail-closed `AgentManifest`/`PermissionFirewall` model with caller, target, capability, permission, input/output class, prompt-injection, secret, DLP, security-scan and scoped-grant checks. The consolidated security team is registered under ILAIOS machine IDs, but dedicated specialist executors and a complete Security Factory must not be claimed VERIFIED until separate implementation and acceptance evidence exists.

## CI truth discovered during consolidation

The prior platform-CI attempt proved 948 tests passing (1 skipped), Ruff passing and strict mypy passing. Its final failure was CI hygiene/configuration rather than a platform regression: `pre-commit --all-files` touched out-of-scope Desktop markdown and its isolated mypy hook lacked `types-PyYAML`. The consolidation branch repairs the isolated hook dependency and scopes platform pre-commit validation without weakening the platform gates.

## Lifecycle and release-state boundary

Capability maturity and release state remain separate. Historical migration package documents that prohibited R01-R03 promotion describe the safety boundary of that earlier workflow and are not evidence that a later approved deployment did not occur. Current lifecycle claims must follow the strongest current runtime/deployment evidence.

## Completion gate for this package

This consolidation package may merge only if:

- no Website or Desktop implementation file changed;
- canonical ILAIOS capability/agent registries pass tests;
- full Python tests pass;
- Ruff passes;
- strict mypy passes;
- scoped pre-commit passes;
- diff hygiene passes;
- PR diff contains no production credentials, DNS, cloud mutation or release promotion;
- final CI is green.

After merge, legacy source documents remain provenance. New active platform work must bind to ILAIOS capability and machine-agent identities.
