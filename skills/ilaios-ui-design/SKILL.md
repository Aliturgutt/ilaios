# ilaios-ui-design

Identity: `ilaios-ui-design` v1.1.0, IMPLEMENTED.

Purpose: resolve bounded natural-language UI intent into `ilaios.ui-spec.v1`,
then hand structured constraints to the canonical governed Software Factory
`sf-frontend-engineering` coding skill through
`services.ui_design_orchestrator.UIDesignOrchestrator`.

## Runtime decision

ILAIOS already has a governed first-party skill execution boundary in
`services/software_factory_skills.py`. This skill does **not** create a second
generic Skill Runtime or parallel policy/design authority. UI intent resolution
is deterministic and authority-free; coding admission remains delegated to the
existing SF-7 `SkillExecutor`.

## Security boundary

- User prompt is data only.
- Maximum prompt length is 4096 characters.
- NUL input is rejected.
- UI/diagram ambiguity fails closed.
- Component ambiguity fails closed.
- The UI spec cannot request tools or capabilities.
- Shell, filesystem mutation, network, secrets, deployment, direct master
  mutation and production mutation are not granted by this skill.
- Coding work remains subject to existing Software Factory governance,
  repository-intelligence, runtime-adapter, independent-review, validation and
  promotion boundaries.

## Output

`ilaios.ui-spec.v1` carries component/category, placement, desktop and compact
behavior, interaction requirements, accessibility requirements, quality gates,
confidence/evidence and brand policy.

The quality-gate contract now explicitly carries, when applicable:

- semantic labels and text alternatives;
- field-local form feedback;
- layout stability;
- non-color-only data encoding;
- predictable navigation/back behavior;
- safe-area awareness;
- reduced-motion behavior;
- compact/wide adaptation.

ILAIOS brand tokens are selected only when orchestration context explicitly
identifies the target product as `ILAIOS`; customer products inherit their own
design system.

## Canonical path

```text
Prompt
 -> UIDesignOrchestrator
 -> ilaios-ui-design resolver
 -> ilaios.ui-spec.v1
 -> SF-7 sf-frontend-engineering
 -> governed coding proposal/review path
 -> existing Web/App design-quality authority
```

The existing ILAIOS design-quality evaluators remain authoritative. This skill
does not self-certify generated UI.
