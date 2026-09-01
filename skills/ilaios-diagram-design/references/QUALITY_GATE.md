# Quality Gate

Run this gate before accepting an artifact.

## Semantic fit

- Does one visual type clearly dominate?
- Does the diagram answer a reader question better than a paragraph/table?
- Are dependency, chronology, state, and data flow kept semantically distinct?

## Truth

- Architecture target state is not presented as current production state.
- Current-reality labels are supported by code/tests/CI/runtime/deployment/evidence.
- A capability map does not imply maturity.
- A planned provider/tool is not drawn as active unless evidence supports it.

## Complexity

- Architecture/data-flow/dependency/trust/capability: ≤12 nodes, ≤18 edges.
- Flowchart: ≤12 nodes, ≤16 edges.
- State machine: ≤10 nodes, ≤16 edges.
- Sequence: ≤6 actors, ≤16 messages.
- Focal nodes: ≤2.
- Detail lines per node: ≤6.

## Geometry

- 8px-grid dimensions and coordinates.
- Connectors are orthogonal.
- Fan attach points when a node has multiple incoming/outgoing edges.
- Avoid connector overlap.
- Back/cycle edges use separate lanes.
- Group boundaries sit behind connectors/nodes.

## Visual design

- No gradients.
- No shadows/filters.
- No glass/3D/glow.
- Cyan is focal, not ubiquitous.
- Labels remain readable at intended size.
- Dark mode remains restrained.

## Security

- User strings are XML escaped.
- Node IDs are validated.
- Unknown edge references fail closed.
- No `<script>`.
- No `foreignObject`.
- No remote URL/href.
- No external fonts/assets.
- No raw user-authored SVG attributes.

## Accessibility

- `role="img"`.
- `<title>`.
- `<desc>`.
- `aria-labelledby` resolves to both.

## Evidence

- Spec SHA-256 emitted.
- Artifact SHA-256 emitted.
- Output validation checks emitted.
- Acceptance state is determined by the caller/governed evaluator, not by the skill itself.
