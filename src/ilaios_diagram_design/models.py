"""Native data contracts for the ILAIOS diagram-design skill."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DiagramKind(str, Enum):
    """Diagram families implemented by the native renderer."""

    ARCHITECTURE = "architecture"
    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    STATE_MACHINE = "state-machine"
    DATA_FLOW = "data-flow"
    DEPENDENCY = "dependency"
    TRUST_BOUNDARY = "trust-boundary"
    CAPABILITY_MAP = "capability-map"


class Direction(str, Enum):
    """Primary layout axis for graph-like diagrams."""

    LEFT_TO_RIGHT = "LR"
    TOP_TO_BOTTOM = "TB"


class EdgeKind(str, Enum):
    """Semantic edge treatments; these never change execution authority."""

    DEFAULT = "default"
    ACCENT = "accent"
    ASYNC = "async"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True, slots=True)
class DiagramTheme:
    """Semantic visual tokens used by the renderer."""

    background: str
    surface: str
    surface_alt: str
    text: str
    muted: str
    accent: str
    border: str
    danger: str


ILAIOS_LIGHT = DiagramTheme(
    background="#FFFFFF",
    surface="#FFFFFF",
    surface_alt="#F8FAFC",
    text="#1F2937",
    muted="#667085",
    accent="#00C2D1",
    border="#D0D5DD",
    danger="#B42318",
)

ILAIOS_DARK = DiagramTheme(
    background="#0B0F14",
    surface="#111827",
    surface_alt="#161D28",
    text="#F8FAFC",
    muted="#98A2B3",
    accent="#00C2D1",
    border="#344054",
    danger="#F97066",
)


@dataclass(frozen=True, slots=True)
class DiagramNode:
    """One semantic node in a diagram."""

    node_id: str
    label: str
    subtitle: str = ""
    kind: str = "component"
    group: str | None = None
    focal: bool = False
    details: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DiagramEdge:
    """One directed relationship between nodes."""

    source: str
    target: str
    label: str = ""
    kind: EdgeKind = EdgeKind.DEFAULT


@dataclass(frozen=True, slots=True)
class DiagramSpec:
    """Validated request contract consumed by the renderer."""

    title: str
    description: str
    kind: DiagramKind
    nodes: tuple[DiagramNode, ...]
    edges: tuple[DiagramEdge, ...]
    width: int = 1200
    height: int = 720
    direction: Direction = Direction.LEFT_TO_RIGHT
    dark_mode: bool = False

    @property
    def theme(self) -> DiagramTheme:
        return ILAIOS_DARK if self.dark_mode else ILAIOS_LIGHT
