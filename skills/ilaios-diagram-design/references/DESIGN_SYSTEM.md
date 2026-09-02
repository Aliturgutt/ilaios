# ILAIOS Diagram Design System

## Purpose

This file is the single visual-token authority for `ilaios-diagram-design`. The renderer uses semantic roles; a diagram request must not hard-code ad hoc visual effects.

## Canonical default palette

| Role | Light | Dark | Meaning |
|---|---:|---:|---|
| Background | `#FFFFFF` | `#0A0A0A` | Canvas |
| Surface | `#FFFFFF` | `#141414` | Node surface |
| Surface alt | `#E6E6E6` | `#1E1E1E` | Focal/secondary surface |
| Text | `#0A0A0A` | `#FFFFFF` | Primary information |
| Muted | `#808080` | `#B3B3B3` | Secondary information/ordinary edges |
| Accent | `#2A2A2A` | `#E6E6E6` | Monochrome focal signal |
| Border | `#B3B3B3` | `#2A2A2A` | Structural rule |
| Danger | `#B42318` | `#F97066` | Explicitly forbidden/failed path |

The canonical ILAIOS brand board is the authority: UI and supporting system visuals are monochrome by design. ILAIOS Cyan `#00C2D1` and ILAIOS Blue `#146BFF` are reserved for the official logo/symbol identity and must not be used as diagram accents.

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
- `foreignObject`;
- ILAIOS logo cyan/blue as diagram or UI accents.

## Focality

Maximum two focal nodes. Usually one is better.

A focal node gets:
- a neutral high-emphasis stroke;
- restrained alternative surface;
- high-emphasis neutral label.

Everything else stays neutral.

## Dark mode

Dark mode changes surfaces/text only. It does not increase effects, glow, saturation, or decoration. Logo identity colors remain reserved for the official logo/symbol assets only.
