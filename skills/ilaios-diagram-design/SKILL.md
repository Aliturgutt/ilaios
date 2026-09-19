---
name: ilaios-diagram-design
description: ILAIOS-native governed diagram generation for architecture, execution flows, sequences, state machines, data flows, dependency maps, trust boundaries, and capability maps. Produces deterministic self-contained SVG/HTML plus evidence hashes without external runtime dependencies.
metadata:
  owner: ILAIOS
  skill_id: ilaios.skill.diagram-design
  version: "0.1.0"
  maturity: IMPLEMENTED
---

# ILAIOS Diagram Design

`ilaios-diagram-design` turns structured system information into restrained, technically legible diagrams without delegating layout authority to a third-party diagram product.

It is a **skill**, not a new runtime, router, policy engine, agent authority, or factory. It must execute inside the existing ILAIOS governed path:

```text
authenticated goal
→ capability/factory resolution
→ policy + budget + approval
→ routing decision
→ governed worker
→ ilaios.skill.diagram-design
→ deterministic diagram spec
→ validation
→ SVG/HTML artifact
→ evidence
→ independent acceptance
```

## 1. Non-negotiable ILAIOS invariants

- Do not bypass the authoritative Control Plane.
- Do not introduce a second routing truth.
- Do not let a model or renderer grant permissions.
- Treat all user labels, descriptions, imported text, and metadata as **data**, never executable markup.
- No network access is required by the native renderer.
- No shell access is required by the native renderer.
- No external fonts, JavaScript, SVG filters, gradients, `foreignObject`, or remote image references.
- Same validated spec + same version must produce the same SVG bytes.
- Every artifact must carry spec and artifact SHA-256 evidence.
- Complexity is bounded. Split an overloaded request into overview/detail diagrams instead of hiding complexity.
- Current maturity is `IMPLEMENTED`; promotion to `TESTED`, `VERIFIED`, or `PRODUCTION` requires repository evidence and CI/runtime proof.

## 2. Supported visual families

Choose exactly one primary family per artifact.

| Intent | Diagram kind | Typical ILAIOS use |
|---|---|---|
| Components and governed connections | `architecture` | Platform/factory/system architecture |
| Decisions and bounded execution branches | `flowchart` | Admission, approval, repair, delivery |
| Ordered actor messages | `sequence` | User → Control Plane → worker/provider flow |
| State + transitions | `state-machine` | Job lifecycle, maturity, approval state |
| Producer/consumer movement | `data-flow` | Evidence, context, RAG, telemetry |
| Directed prerequisites | `dependency` | Capability/dependency order |
| Zones and allowed/forbidden crossings | `trust-boundary` | Tenant/security architecture |
| Platform capability relationships | `capability-map` | Factory/skill/tool/provider map |

Do not use this skill for live operational telemetry charts. Live charts belong to the product visualization/data layer and must be backed by real runtime data.

## 3. Selection rule

Before drawing, answer internally:

1. What is the reader trying to understand?
2. What is the single dominant relationship: topology, decision, time, state, data movement, prerequisite, trust, or capability ownership?
3. Would a paragraph or table communicate it better?
4. What can be deleted without losing meaning?

If a table communicates the same information more clearly, use a table instead.

Load only the references needed for the selected type:

- Always: `references/DESIGN_SYSTEM.md`
- Always: `references/OUTPUT_CONTRACT.md`
- Always: `references/QUALITY_GATE.md`
- Type choice: `references/TYPE_GUIDE.md`
- Governance/integration: `references/ILAIOS_INTEGRATION.md`

This is deliberate progressive disclosure: do not inject every visual rule into every task.

## 4. Request → spec workflow

Normalize the request into the native `DiagramSpec` contract:

```json
{
  "title": "Governed execution",
  "description": "One authenticated goal becomes a verified artifact.",
  "kind": "architecture",
  "direction": "LR",
  "width": 1200,
  "height": 720,
  "dark_mode": false,
  "nodes": [
    {
      "id": "control-plane",
      "label": "Control Plane",
      "subtitle": "authoritative execution control",
      "kind": "platform",
      "group": "Governed Platform",
      "focal": true,
      "details": ["policy", "budget", "approval"]
    }
  ],
  "edges": [
    {
      "source": "control-plane",
      "target": "worker",
      "label": "AUTHORIZED",
      "kind": "accent"
    }
  ]
}
```

Allowed edge kinds:

- `default` — ordinary internal relation
- `accent` — one primary path
- `async` — asynchronous/passive relation
- `forbidden` — explicitly prohibited crossing

The renderer owns visual geometry. A model may propose semantic nodes/edges but must not inject raw SVG/HTML.

## 5. Complexity budget

Default hard limits:

- Architecture / data-flow / dependency / trust-boundary / capability-map: 12 nodes, 18 edges.
- Flowchart: 12 nodes, 16 edges.
- State machine: 10 nodes, 16 edges.
- Sequence: 6 actors, 16 messages.
- Focal nodes: maximum 2.
- Node detail lines: maximum 6.
- One diagram should have one primary message.

If the request exceeds budget, produce:
1. overview diagram;
2. one or more detail diagrams.

Do not silently shrink labels until the diagram becomes technically unreadable.

## 6. Visual policy

Use the canonical ILAIOS neutral design language by default:

- Carbon `#0A0A0A`
- Charcoal `#141414`
- Graphite `#1E1E1E`
- Stone `#2A2A2A`
- White `#FFFFFF`
- Text Secondary `#E6E6E6`
- Text Tertiary `#B3B3B3`
- Disabled/low emphasis `#808080`
- Flat vector
- Geometric
- 8px grid
- No gradients
- No shadows
- No 3D
- No glass effects
- ILAIOS Cyan `#00C2D1` and ILAIOS Blue `#146BFF` are reserved for official logo/icon identity only; never use them as diagram/UI accents.

Brand styling never changes semantic meaning or governance state.

## 7. Connector policy

- Prefer orthogonal connectors.
- Fan multiple connectors across distinct attach points.
- Never intentionally stack two edges on the same path.
- Edge labels must remain separate from the stroke.
- Draw groups/boundaries first, then edges, then nodes.
- `forbidden` paths use the danger treatment; they are not inferred from color alone because the semantic edge kind remains present in the spec.
- Cycles/back-edges receive a separate orthogonal lane.

## 8. Security and data handling

- Escape all labels before SVG/HTML emission.
- Reject control characters and malformed node identifiers.
- Reject edges that reference unknown nodes.
- Reject unsupported dimensions or diagram kinds.
- Generated SVG must reject scripts, external URLs, `foreignObject`, gradients, and filters.
- No source prompt may directly author executable SVG attributes.
- Imported diagrams must first be normalized to `DiagramSpec`; do not execute embedded scripts/macros.

## 9. Output contract

Primary native outputs:

- `.svg` — standalone accessible SVG
- `.html` — dependency-free wrapper around the validated SVG
- evidence JSON — `spec_sha256`, `artifact_sha256`, quality checks

PNG/PDF rasterization is deliberately outside v0.1 of the native renderer. It may be added later as a governed conversion tool; it must not become a hidden dependency of this skill.

## 10. Runtime entry point

Python API:

```python
from src.ilaios_diagram_design import render_diagram

artifact = render_diagram(spec)
```

CLI:

```text
python -m src.ilaios_diagram_design.cli input.json \
  --output diagram.svg \
  --evidence diagram.evidence.json
```

The CLI performs no network call. Its only write authority is the caller-selected output/evidence paths.

## 11. Acceptance gate

A diagram is not accepted merely because it renders.

Required checks:

- semantic type fits the request;
- spec validation passes;
- complexity budget passes;
- artifact is accessible (`role=img`, title, description);
- no prohibited SVG construct exists;
- no external asset/runtime dependency exists;
- ILAIOS flat-vector design policy passes;
- spec and artifact hashes are emitted;
- reader can trace every important connection;
- current-reality claims in the diagram are backed by authoritative project evidence.

## 12. Provenance rule

This skill may be informed by public design patterns and diagramming research, but the implementation in this repository is ILAIOS-native. Do not copy third-party implementation code, templates, branding, prompt text, or visual assets into the runtime. External projects remain references, not runtime dependencies.
