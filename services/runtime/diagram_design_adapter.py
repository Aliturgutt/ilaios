"""First-party deterministic adapter for governed ILAIOS diagram rendering."""

from __future__ import annotations

import hashlib
from typing import Any

from services.runtime.routing import RuntimeError
from src.ilaios_diagram_design.cli import DiagramInputError, parse_spec
from src.ilaios_diagram_design.quality import DiagramValidationError
from src.ilaios_diagram_design.renderer import render_diagram, wrap_html

DIAGRAM_DESIGN_AGENT_ID = "ilaios.agent.web.asset.v1"
DIAGRAM_DESIGN_SKILL_ID = "ilaios.skill.diagram-design"
DIAGRAM_DESIGN_CAPABILITY = "web.asset"
DIAGRAM_DESIGN_PROVIDER_ID = "ilaios.provider.local.diagram-design.v1"
DIAGRAM_DESIGN_ADAPTER_KIND = "ilaios-diagram-design-v1"

_ALLOWED_PAYLOAD_KEYS = frozenset({"spec", "format"})
_SUPPORTED_FORMATS = frozenset({"svg", "html"})


def execute_diagram_design_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Render caller-provided structured data without shell, network, or templates."""

    if not isinstance(payload, dict):
        raise RuntimeError("diagram-design payload must be an object")
    unexpected = set(payload) - _ALLOWED_PAYLOAD_KEYS
    if unexpected:
        raise RuntimeError(
            "diagram-design payload contains unsupported fields: "
            + ", ".join(sorted(unexpected))
        )

    raw_spec = payload.get("spec")
    if not isinstance(raw_spec, dict):
        raise RuntimeError("diagram-design payload requires a spec object")

    output_format = payload.get("format", "svg")
    if not isinstance(output_format, str) or output_format not in _SUPPORTED_FORMATS:
        raise RuntimeError("diagram-design format must be exactly svg or html")

    try:
        spec = parse_spec(raw_spec)
        rendered = render_diagram(spec)
    except (DiagramInputError, DiagramValidationError, ValueError) as error:
        raise RuntimeError(f"diagram-design rejected input: {error}") from error

    if output_format == "svg":
        content = rendered.svg
        mime_type = "image/svg+xml"
    else:
        content = wrap_html(rendered, page_title=spec.title)
        mime_type = "text/html"

    artifact_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {
        "format": output_format,
        "mime_type": mime_type,
        "content": content,
        "spec_sha256": rendered.spec_sha256,
        "artifact_sha256": artifact_sha256,
        "svg_sha256": rendered.artifact_sha256,
        "checks": list(rendered.checks),
        "maturity": "IMPLEMENTED",
    }
