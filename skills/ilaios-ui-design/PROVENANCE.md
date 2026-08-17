# ILAIOS UI Design Skill - Clean-Room Provenance

Status: CONTROLLED RESEARCH RECORD
Research date: 2026-08-17

## External reference inspected

- Repository: `Leonxlnx/taste-skill`
- Revision inspected: `e988add20dab0fa97d7a76781c48961c8184288e` (`main`)
- Runtime dependency: NO
- Vendored files: NO
- Copied implementation code: NO
- Copied prompt body/templates/scripts/assets: NO

The reference was used only for high-level design-engineering ideas: read the brief before selecting an aesthetic, represent design intensity/density as bounded parameters, select one coherent component/design system, verify dependencies before importing them, avoid generic AI visual defaults, design responsive behavior intentionally, and run a pre-flight quality review.

## ILAIOS implementation boundary

The native implementation is independently written in:

- `services/runtime/skill_runtime.py`
- `services/skills/ilaios_ui_design.py`
- `services/skills/cli.py`
- `tests/test_skill_runtime.py`
- `tests/test_ilaios_ui_design_skill.py`

The implementation reuses only existing ILAIOS-owned runtime contracts, especially the immutable `SkillArtifact` / `SkillRegistry` supply-chain validation. It introduces no third-party Python dependency and does not execute external skill content.

## Relationship to prior design-intelligence research

`tools/design-intelligence/PROVENANCE.md` already records the same pinned Taste Skill revision plus other design references used for ILAIOS web design-quality research. This UI skill does not replace that record. It narrows the new executable capability to product-UI intent resolution and reuses existing ILAIOS strategy/evaluation authority rather than creating a parallel quality system.

Any future decision to copy source code or substantial protected expression from an external repository requires a new license review and explicit provenance update before merge.
