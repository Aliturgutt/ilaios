---
name: ilaios-ui-design
skill_id: ilaios.skill.ui-design
version: 1.0.0
status: IMPLEMENTED
owner: ILAIOS
runtime: services.runtime.skill_runtime.NativeSkillRuntime
implementation: services.skills.ilaios_ui_design.ILAIOSUIDesignSkill
---

# ILAIOS UI Design Skill

## Purpose

`ilaios-ui-design` converts natural-language product UI intent into a bounded, machine-readable component specification that a coding agent can implement and existing ILAIOS design-quality gates can verify.

It is not a template pack and it does not generate arbitrary executable code. The skill resolves interaction/component intent, responsive behavior, accessibility requirements, design-system policy, quality gates, and coding constraints.

## Relationship to existing ILAIOS design intelligence

This skill complements rather than replaces `tools/design-intelligence` and the deterministic evaluators in `services/design_quality.py` and `services/app_design_quality.py`.

- `ilaios-ui-design`: intent -> component/specification.
- Existing design strategy engines: project/page composition strategy.
- Existing design-quality evaluators: evidence -> PASS/FAIL findings.

No second policy authority, deployment authority, or visual-QA truth source is created here.

## Runtime contract

The executable runtime is `services/runtime/skill_runtime.py`. It accepts only explicitly registered in-process native skills; requires the `ilaios.skill.*` namespace; fingerprints artifacts with SHA-256; reuses the existing ILAIOS `SkillRegistry` supply-chain validation; never dynamically imports code named by user input; never grants authorities requested by prompt text; bounds prompts to 4096 characters and rejects blank/NUL input; routes deterministically; fails closed on unknown/ambiguous routes; and returns artifact digest plus routing evidence.

`ilaios.skill.ui-design` requests zero runtime authorities. It cannot request shell, filesystem, network, provider, deployment, or secret access. Those capabilities remain behind their existing governed ILAIOS paths.

## UI specification schema

The output schema is `ilaios.ui-spec.v1` and includes resolved component/category, bounded confidence and evidence, design-read profile, placement and compact behavior, interaction requirements, accessibility requirements, design-system policy, mandatory quality gates, and coding-agent hints.

Supported v1 patterns are drawer, multi-select, avatar group, text truncation, dialog, tabs, command palette, data table, toast, and generic surface layout. The knowledge base is intentionally small and testable; new patterns require routing and behavior tests.

## Design rules

- Infer from the brief instead of selecting a fashionable default aesthetic.
- Reuse the incumbent project design system and tokens before adding a dependency.
- Do not mix component systems without an explicit migration decision.
- Inspect the target project before assuming any third-party package exists.
- Do not default to gradients, glass, card walls, decorative motion, or similar generic AI motifs.
- Compact/tablet/wide behavior must be intentional, not a blind desktop stack.
- Keyboard operation, visible focus, semantics, interaction states, and reduced motion are mandatory where applicable.
- Generated UI remains subject to existing ILAIOS design-quality evaluators.

## Brand boundary

The skill must not leak ILAIOS corporate styling into customer products. ILAIOS tokens are selected only when execution context explicitly sets `product=ILAIOS`; otherwise the output requires inheritance from the target project's brand system.

## Examples

`sağdan ayarlar açılsın` resolves to a right-side drawer with focus containment, Escape dismissal, focus restoration, and full-screen compact behavior.

`birden fazla seçenek seçebileyim` resolves to a multi-select with keyboard navigation and announced selection state.

`üst üste küçük kullanıcı resimleri` resolves to an avatar group with bounded visible avatars and overflow count.

`uzun metin üç noktayla bitsin` resolves to text truncation while preserving a way to discover the full value.

## Invocation

```bash
python -m services.skills.cli "sağdan ayarlar açılsın"
python -m services.skills.cli --skill ilaios.skill.ui-design "sağdan ayarlar açılsın"
```

Python callers use `build_default_skill_runtime().invoke(...)`.

## Clean-room / provenance boundary

The external design-skill reference was used only to study high-level concepts: infer design intent before selecting an aesthetic, use bounded design parameters, choose a coherent design system, avoid generic AI defaults, and apply pre-flight quality review. This implementation was written independently for ILAIOS.

No third-party implementation code, prompt body, template, detector, script, component source, runtime, or dependency is copied or required. The executable code uses the Python standard library and existing ILAIOS runtime contracts.

## Maturity rule

`IMPLEMENTED` means code and tests exist in the repository. Promotion to `TESTED`, `VERIFIED`, `DEPLOYED`, or `PRODUCTION` requires actual CI/runtime/deployment evidence; documentation alone cannot promote maturity.
