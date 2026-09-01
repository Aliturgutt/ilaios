# ILAIOS — WEB DESIGN INTELLIGENCE

**Document Type:** Scoped Canonical Product / Architecture Invariant  
**Status:** Canonical Web Factory Design Invariants v1.0  
**Parent Product Authority:** `PRODUCT_REQUIREMENTS.md`  
**Parent Architecture Authority:** `SYSTEM_ARCHITECTURE.md`

This scoped document makes the existing Web Factory design requirements explicit. It does not replace the parent product or architecture authorities and does not state current runtime maturity.

## 1. Product invariant

ILAIOS Web Factory must not behave as:

```text
prompt → generic template → text/color swap → deploy
```

Its target design path is:

```text
User Goal
→ Brand / Business / Audience / Content Context
→ Design Context
→ Design Strategy
→ Information Architecture
→ Visual Direction
→ Composition Strategy
→ Typography / Spacing / Surface System
→ Contextual Components
→ Responsive Composition
→ Motion / Interaction
→ Implementation
→ Visual QA
→ Anti-Generic-AI Review
→ Accessibility / Responsive / Technical QA
→ Design Acceptance
→ Deployment Validation where authorized
```

The target outcome is a verified finished website, not a mockup, theme selection, or partial generation.

## 2. Context-derived design

Dynamic does not mean random. Design decisions must derive from structured project context, including where relevant:

- business category;
- company maturity;
- audience;
- primary user goal;
- conversion objective;
- brand personality;
- content volume and hierarchy;
- product complexity;
- trust requirements;
- visual asset availability;
- required functionality;
- information density;
- accessibility constraints;
- locale;
- device priorities;
- requested aesthetic direction;
- industry expectations.

A law firm, security company, developer platform, restaurant, architecture studio, SaaS company, and media brand must be capable of receiving meaningfully different compositions because their context differs.

## 3. Design Strategy

A structured, inspectable Design Strategy must be capable of expressing:

- visual character;
- information density;
- primary and secondary composition modes;
- typography behavior;
- spacing behavior;
- surface behavior;
- imagery behavior;
- CTA hierarchy;
- diagram usage;
- motion intensity;
- navigation behavior;
- section rhythm;
- mobile transformation strategy.

An LLM must not silently emit arbitrary CSS and thereby become policy, severity, acceptance, or deployment authority.

## 4. Composition intelligence

ILAIOS owns a composition vocabulary rather than a static template catalog. Useful composition families include:

- Editorial Split;
- Technical Flow;
- Layered Architecture;
- Narrative Scroll;
- Product Showcase;
- Data Dense;
- Minimal Institutional;
- Visual Portfolio;
- Structured Comparison;
- Process Pipeline;
- Evidence / Trust;
- Capability Map;
- Timeline;
- Case Study;
- Media-led;
- Documentation-led.

These are compositional building blocks, not `template_1`, `template_2`, or `template_3`.

## 5. Content-type-specific visualization

Different information types should receive appropriate representations.

- Architecture: layered maps, dependency and authority flows, control-plane diagrams, execution pipelines, trust boundaries.
- Factories: production sequences, staged pipelines, input/output systems, acceptance flows.
- Security: trust layers, control relationships, authorization flows, validation/evidence structures.
- Capabilities: structured maps, category relationships, progressive hierarchy.
- Enterprise: outcomes, use cases, deployment context, trust/evidence presentation.

Rendering every subject as the same marketing card wall is non-conforming.

## 6. Anti-generic-AI policy

The evaluator considers context + frequency + purpose + composition. Review includes:

- oversized vague hero headings;
- universal center alignment;
- repeated equal-height cards and grids;
- card-inside-card structures;
- excessive bordered or rounded surfaces;
- universal pill styling;
- meaningless icon tiles;
- arbitrary gradients or radial glows;
- excessive glass or dark-neon treatment;
- repetitive marketing-section skeletons;
- decorative abstraction without information purpose;
- weak CTA hierarchy;
- mobile layouts that merely stack desktop composition.

No individual technique fails solely because an AI tool often uses it. The failure condition is unjustified, repeated, context-insensitive composition.

## 7. Repetition and differentiation evidence

A generated project may retain a Composition Fingerprint containing fields such as:

- hero composition;
- navigation type;
- dominant alignment;
- section sequence;
- content density;
- repeated component counts;
- surface behavior;
- CTA structure;
- imagery and diagram usage;
- grid patterns;
- radius patterns;
- accent distribution.

This evidence exists to detect repeated structural skeletons. It must not be converted into a fake uniqueness score or pixel-similarity claim.

## 8. Responsive composition

Responsive design is not desktop content mechanically stacked into one column. Required reasoning includes where relevant:

- reordering;
- reduction of secondary detail;
- alternate diagram representations;
- navigation collapse;
- alignment changes;
- grid adaptation;
- CTA regrouping;
- information-density changes.

Minimum review viewports are 320, 360, 390, 412, 430, tablet, desktop, and large desktop. English and Turkish must both be evaluated.

## 9. Motion and interaction

Motion must explain state change, hierarchy, continuity, causality, or navigation. Universal decorative reveal motion is non-conforming. `prefers-reduced-motion` is mandatory.

Interactive controls must have clear affordance, visible focus and appropriate target size. Non-interactive content must not be visually misrepresented as actionable.

## 10. Project coherence

Within one generated website, typography, spacing, CTA hierarchy, visual language, motion and navigation remain coherent. Across different projects, composition must be capable of meaningful context-derived differentiation.

## 11. Performance and ownership

Visual quality must not require unnecessary JavaScript animation libraries, excessive client components, oversized media or decorative runtime dependencies when native CSS/React/Next capabilities are sufficient.

The implementation is ILAIOS-owned and independently implemented. No Taste Skill, Emil Kowalski Design Engineering, Impeccable, or other third-party design-skill implementation code, prompts, templates, detectors, scripts, assets or runtime logic may be copied into the product. External projects may be consulted only as non-authoritative research references with provenance where used.

Formal licensing conclusions require separate legal review.

## 12. Acceptance

The canonical native implementation is represented by:

- `tools/design-intelligence/`;
- `services/design_quality.py`;
- `services/integrations/web_factory.py`;
- `tests/test_design_quality.py`;
- `tests/test_web_factory.py`;
- `apps/website/`;
- `.github/workflows/website-ci.yml`.

Current implementation/release truth remains determined by repository code, tests, CI, runtime, deployment and evidence, not by this document alone.
