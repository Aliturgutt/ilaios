# ILAIOS IP, License and Legacy Identity Provenance Audit

Status: CONTROLLED — evidence-based repository audit  
Baseline: `c68d6d96394359200293eb557e567546c2c8de60`  
Canonical identity: ILAIOS  
Canonical namespaces: `ilaios.capability.*`, `ilaios.agent.*`

## Decision

ILAIOS is the single active product and platform identity. Hermes, ILAKOS and ILATEN are not active product, runtime, capability, agent or architecture identities. Historical truth is retained only in the bounded migration/provenance locations below. Git history was not rewritten. No parallel Core/runtime/registry was created.

## Legacy occurrence classification

| Surface | Category | Risk | Action and justification | Test |
|---|---|---:|---|---|
| `services/agent_registry.py` display alias | ACTIVE (corrected) | Medium | Renamed the active `Hermes` integration-agent alias to `Integration Bridge`; canonical machine ID remains `ilaios.agent.engineering.integration.v1`. | `tests/test_agent_registry.py`, `tests/test_final_lineage_redteam.py`, `tests/test_legacy_identity_cleanup.py` |
| `services/agent_registry.py` legacy lineage metadata | COMPATIBILITY | Low | Retained read-only provenance metadata; never used as an orchestration key or written as active identity. | Registry namespace and alias assertions |
| `services/capability_registry.py` `legacy_sources` | COMPATIBILITY | Low | Retained read-only migration mapping needed for audit traceability; active capability IDs remain ILAIOS-only. | Capability registry and cleanup tests |
| `dev/openclaw/migration_input/` | HISTORICAL | Low | Immutable migration inputs; filenames and source wording preserve historical truth. | Explicit path allowlist |
| `docs/migration/` | HISTORICAL | Low | Migration matrices and lineage audits; current language states ILAIOS is the sole active identity. | Explicit path allowlist |
| `evidence/migration/` | HISTORICAL | Low | Durable audit evidence supporting the migration decisions. | Explicit path allowlist |
| `docs/platform/IDENTITY_MIGRATION.md`, `docs/platform/MIGRATION_BASELINE.md` | HISTORICAL | Low | Bounded baseline and migration records; not current product architecture. | Manual classification recorded here |
| UNKNOWN identity occurrences | 0 | — | No unclassified active identity occurrence remains in the inspected active registries, source paths, tests and current public governance surfaces. | CI regression guard |

Removal condition for compatibility metadata: remove only when the migration matrices and audit consumers no longer require source-lineage mapping and a governed evidence-retention decision approves removal.

## License and provenance evidence

| Component | Path | Source/provenance | License / ownership | Modification | Redistribution obligations | Commercial risk | Required action | Status |
|---|---|---|---|---|---|---:|---|---|
| ILAIOS platform implementation | `src/`, `services/`, `packages/` | Repository-authored implementation | Private/proprietary by repository decision | Ongoing | No public license grant; third-party dependencies remain separately licensed | Medium | Preserve ownership records and dependency review | CONTROLLED |
| Python dependencies | `pyproject.toml`, CI install set | Third-party dependencies | Individual upstream licenses | Unmodified dependencies | Follow each dependency license and notices when distributing | Medium | Produce release-specific dependency SBOM/license report before commercial distribution | ACTION REQUIRED |
| Website dependencies | `apps/website/package-lock.json` | npm ecosystem | Individual upstream licenses | Unmodified dependencies | Package-specific attribution/source obligations | Medium | Generate production-lockfile license inventory before distribution | ACTION REQUIRED |
| Desktop dependencies | `apps/desktop/pubspec.lock` | Flutter/Dart ecosystem | Individual upstream licenses | Unmodified dependencies | Package-specific attribution obligations | Medium | Generate release-lockfile license inventory before Store/distribution | ACTION REQUIRED |
| Design-intelligence research record | `tools/design-intelligence/PROVENANCE.md` | Taste Skill, Emil Kowalski Skills, Impeccable research references | MIT / Apache-2.0 as recorded | Vocabulary research only; no copied implementation claimed | Preserve provenance; verify claims if redistributed | Low–Medium | Retain record and referenced commit identifiers | RETAINED |
| Native app design-quality implementation | `tools/app-design-quality/PROVENANCE.md`, `services/app_design_quality.py` | ILAIOS original implementation; earlier research record referenced | Proprietary ILAIOS implementation | Repository-authored | No third-party implementation copied according to recorded evidence | Low | Preserve provenance record | RETAINED |
| Migration source architecture | `dev/openclaw/migration_input/` | Historical internal lineage | HISTORICAL_INTERNAL | Adapted into canonical ILAIOS requirements | Preserve provenance and ownership evidence | Medium | Do not distribute externally until ownership authority is confirmed | RETAINED |
| Generated/migration matrices | `docs/migration/`, `evidence/migration/` | Generated from historical internal source | HISTORICAL_INTERNAL / GENERATED | Generated and reviewed | Preserve source mapping and generation evidence | Low | Retain with migration evidence | RETAINED |

## Findings and limits

- No repository-wide open-source license grant is inferred; `docs/governance/LICENSE_DECISION.md` controls the private/proprietary posture.
- Required third-party attribution was not removed.
- Dependency lockfiles identify third-party components but do not by themselves establish a complete commercial redistribution package. Release-specific SBOM and license-notice generation remains required before external commercial distribution.
- Historical internal source ownership must be confirmed by the repository owner before external redistribution. This is a commercial diligence action, not an unknown active identity occurrence.
- This document is engineering evidence, not legal advice.

## Scope attestations

- Website implementation changed: NO.
- Desktop implementation changed: NO.
- Production infrastructure, DNS, billing, stores, cloud resources, deployments and secrets changed: NO.
- Git history rewritten: NO.
- Duplicate or parallel Core/runtime/registry introduced: NO.
