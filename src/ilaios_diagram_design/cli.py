"""CLI adapter for governed ILAIOS diagram rendering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence, cast

from .models import (
    DiagramEdge,
    DiagramKind,
    DiagramNode,
    DiagramSpec,
    Direction,
    EdgeKind,
)
from .renderer import render_diagram, wrap_html


class DiagramInputError(ValueError):
    """Input JSON cannot be converted into a DiagramSpec."""


def _mapping(value: object, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DiagramInputError(f"{name} must be an object")
    return cast(dict[str, Any], value)


def _string(value: object, *, name: str, default: str | None = None) -> str:
    if value is None and default is not None:
        return default
    if not isinstance(value, str):
        raise DiagramInputError(f"{name} must be a string")
    return value


def _boolean(value: object, *, name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise DiagramInputError(f"{name} must be a boolean")
    return value


def _integer(value: object, *, name: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise DiagramInputError(f"{name} must be an integer")
    return value


def _list(value: object, *, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise DiagramInputError(f"{name} must be an array")
    return value


def parse_spec(raw_obj: object) -> DiagramSpec:
    """Convert untrusted structured data into a validated DiagramSpec shape."""

    raw = _mapping(raw_obj, name="root")

    nodes: list[DiagramNode] = []
    for index, item in enumerate(_list(raw.get("nodes"), name="nodes")):
        node = _mapping(item, name=f"nodes[{index}]")
        details_value = node.get("details", [])
        details = tuple(
            _string(detail, name=f"nodes[{index}].details")
            for detail in _list(details_value, name=f"nodes[{index}].details")
        )
        group_value = node.get("group")
        group = (
            None
            if group_value is None
            else _string(group_value, name=f"nodes[{index}].group")
        )
        nodes.append(
            DiagramNode(
                node_id=_string(node.get("id"), name=f"nodes[{index}].id"),
                label=_string(node.get("label"), name=f"nodes[{index}].label"),
                subtitle=_string(
                    node.get("subtitle"),
                    name=f"nodes[{index}].subtitle",
                    default="",
                ),
                kind=_string(
                    node.get("kind"),
                    name=f"nodes[{index}].kind",
                    default="component",
                ),
                group=group,
                focal=_boolean(
                    node.get("focal"),
                    name=f"nodes[{index}].focal",
                    default=False,
                ),
                details=details,
            )
        )

    edges: list[DiagramEdge] = []
    for index, item in enumerate(_list(raw.get("edges", []), name="edges")):
        edge = _mapping(item, name=f"edges[{index}]")
        try:
            edge_kind = EdgeKind(
                _string(
                    edge.get("kind"),
                    name=f"edges[{index}].kind",
                    default=EdgeKind.DEFAULT.value,
                )
            )
        except ValueError as exc:
            raise DiagramInputError(f"edges[{index}].kind is unsupported") from exc
        edges.append(
            DiagramEdge(
                source=_string(edge.get("source"), name=f"edges[{index}].source"),
                target=_string(edge.get("target"), name=f"edges[{index}].target"),
                label=_string(
                    edge.get("label"),
                    name=f"edges[{index}].label",
                    default="",
                ),
                kind=edge_kind,
            )
        )

    try:
        kind = DiagramKind(_string(raw.get("kind"), name="kind"))
        direction = Direction(
            _string(raw.get("direction"), name="direction", default="LR")
        )
    except ValueError as exc:
        raise DiagramInputError("unsupported diagram kind or direction") from exc

    return DiagramSpec(
        title=_string(raw.get("title"), name="title"),
        description=_string(raw.get("description"), name="description", default=""),
        kind=kind,
        nodes=tuple(nodes),
        edges=tuple(edges),
        width=_integer(raw.get("width"), name="width", default=1200),
        height=_integer(raw.get("height"), name="height", default=720),
        direction=direction,
        dark_mode=_boolean(raw.get("dark_mode"), name="dark_mode", default=False),
    )


def load_spec(path: Path) -> DiagramSpec:
    """Load untrusted JSON as data; no code or templates are executed."""

    raw_obj: object = json.loads(path.read_text(encoding="utf-8"))
    return parse_spec(raw_obj)


def _evidence_json(
    artifact_sha256: str, spec_sha256: str, checks: tuple[str, ...]
) -> str:
    return json.dumps(
        {
            "artifact_sha256": artifact_sha256,
            "spec_sha256": spec_sha256,
            "checks": list(checks),
        },
        indent=2,
        sort_keys=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render an ILAIOS-native diagram.")
    parser.add_argument("spec", type=Path, help="Path to a diagram JSON spec")
    parser.add_argument("--output", type=Path, required=True, help="SVG or HTML output")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=None,
        help="Optional JSON evidence output",
    )
    arguments = parser.parse_args(argv)

    spec = load_spec(arguments.spec)
    artifact = render_diagram(spec)
    output_suffix = arguments.output.suffix.casefold()
    if output_suffix == ".svg":
        output = artifact.svg
    elif output_suffix in {".html", ".htm"}:
        output = wrap_html(artifact, page_title=spec.title)
    else:
        raise DiagramInputError("output must end in .svg, .html, or .htm")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(output, encoding="utf-8")
    if arguments.evidence is not None:
        arguments.evidence.parent.mkdir(parents=True, exist_ok=True)
        arguments.evidence.write_text(
            _evidence_json(
                artifact.artifact_sha256,
                artifact.spec_sha256,
                artifact.checks,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
