# ILAIOS Integration Contract

## Architectural position

`ilaios.skill.diagram-design` belongs below governed worker execution and above artifact validation. It does not belong in Constitutional Core.

```text
Control Plane
  ↓
Capability / Factory
  ↓
Policy + Budget + Approval
  ↓
RoutingDecision
  ↓
Governed Worker
  ↓
ilaios.skill.diagram-design
  ↓
DiagramSpec
  ↓
Native deterministic renderer
  ↓
Artifact + evidence
  ↓
Independent acceptance
```

## Allowed callers

Typical callers include:
- Creative / Document;
- Research / Data;
- Web Factory;
- Software Factory;
- Security Factory;
- documentation workflows;
- desktop/report artifact workflows.

A factory remains the bounded domain workflow. This skill is a reusable execution capability inside those workflows.

## Permission posture

Native runtime needs:
- read: caller-provided spec;
- write: caller-declared artifact/evidence path;
- network: none;
- shell: none;
- secrets: none;
- provider credentials: none.

A caller that obtains source information from GitHub, Drive, APIs, or other tools must do so through the normal governed tool path before invoking the renderer.

## Model posture

A model may:
- choose a supported diagram type;
- propose nodes/edges;
- reduce complexity;
- propose labels;
- explain an artifact.

A model may not:
- bypass validation;
- inject SVG/HTML;
- expand permissions;
- fabricate current-reality claims;
- convert architectural target truth into deployment truth.

## Evidence posture

The skill produces cryptographic artifact evidence, but cryptographic evidence only proves byte identity/reproducibility. It does not prove that labels about the real system are true. System-state claims still require authoritative repository/runtime/deployment evidence.

## Third-party references

External open-source diagram projects may be inspected for general ideas such as:
- progressive disclosure;
- semantic type selection;
- complexity budgets;
- accessible SVG;
- style-token separation;
- geometry checks;
- deterministic export.

ILAIOS implementation code, prompts, templates, and brand assets must remain native. External repositories are not runtime dependencies.
