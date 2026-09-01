# ILAIOS Diagram Design System

## Purpose

This file is the single visual-token authority for `ilaios-diagram-design`. The renderer uses semantic roles; a diagram request must not hard-code ad hoc visual effects.

## Canonical default palette

| Role | Light | Dark | Meaning |
|---|---:|---:|---|
| Background | `#FFFFFF` | `#0B0F14` | Canvas |
| Surface | `#FFFFFF` | `#111827` | Node surface |
| Surface alt | `#F8FAFC` | `#161D28` | Focal/secondary surface |
| Text | `#1F2937` | `#F8FAFC` | Primary information |
| Muted | `#667085` | `#98A2B3` | Secondary information/ordinary edges |
| Accent | `#00C2D1` | `#00C2D1` | Enterprise Cyan focal signal |
| Border | `#D0D5DD` | `#344054` | Structural rule |
| Danger | `#B42318` | `#F97066` | Explicitly forbidden/failed path |

The public brand rule remains restrained: roughly 70% Graphite/neutral structure, 20% white/negative space, 10% cyan emphasis. Cyan is not a generic "active" fill.

## Geometry

- 8px base grid.
- Node width: dynamic 128–192px in the native v0.1 graph renderer.
- Node radius: 8px maximum.
- Structural stroke: 1–1.4px.
- Layout coordinates snap to 8px.
- Keep node groups visually bounded without shadows.
- Prefer whitespace over decorative containers.

## Typography

Preferred family order:

```text
Sora → Segoe UI → Arial → sans-serif
```

Technical detail lines use a system monospace stack:

```text
ui-monospace → SFMono-Regular → Consolas → monospace
```

The native SVG does not fetch external fonts. Installed fonts may improve fidelity, but rendering must remain legible without them.

## Hierarchy

1. Diagram title
2. Focal node/path
3. Primary node label
4. Node kind / subtitle
5. Detail line / connector label
6. Group boundary

Never make every node visually equivalent when semantics differ.

## Hard visual prohibitions

Do not emit:

- gradients;
- drop shadows or SVG filters;
- 3D perspective;
- glassmorphism;
- neon glow;
- decorative noise/dot fields by default;
- oversized pill controls;
- remote image/icon references;
- JavaScript;
- `foreignObject`.

## Focality

Maximum two focal nodes. Usually one is better.

A focal node gets:
- cyan stroke;
- restrained alternative surface;
- cyan label.

Everything else stays neutral.

## Dark mode

Dark mode changes surfaces/text only. It does not increase effects, glow, saturation, or decoration. Enterprise Cyan remains the same accent token.
