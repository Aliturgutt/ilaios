"""Generate the ILATEN-to-ILAIOS normative requirement migration matrix."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

SOURCE_NAME = "ILATEN_Enterprise_AI_Operating_System_Canonical_Architecture_v1.0(3)(4).md"
CANONICAL_NAME = "ILAIOS_ENTERPRISE_AI_OPERATING_SYSTEM_CANONICAL_ARCHITECTURE.md"


@dataclass(frozen=True)
class EvidenceRule:
    sections: tuple[str, ...]
    evidence: tuple[str, ...]


EVIDENCE_RULES = (
    EvidenceRule(("2.2", "2.9"), ("src/core/evidence_chain.py", "services/evidence/store.py", "tests/test_evidence_chain.py", "tests/test_evidence_store.py")),
    EvidenceRule(("2.3", "2.6"), ("src/core/agent.py", "src/core/immutable_context.py", "src/core/tool_gateway.py", "services/control_plane/workflows.py", "tests/test_governed_runtime.py")),
    EvidenceRule(("2.5",), ("services/runtime/scheduler.py", "services/control_plane/workflows.py", "tests/test_worker_scheduler.py", "tests/test_durable_workflows.py")),
    EvidenceRule(("2.8",), ("src/core/validation_pipeline.py", "tests/test_validation_pipeline.py")),
    EvidenceRule(("2.10",), ("src/core/audit_engine.py", "tests/test_audit_engine.py")),
    EvidenceRule(("2.11", "6.5"), ("src/code_intelligence/source_file_analyzer.py", "src/code_intelligence/models.py", "tests/test_source_file_analyzer.py", "tests/test_code_intelligence_models.py")),
    EvidenceRule(("3.3",), ("services/runtime/grants.py", "services/governance/gates.py", "tests/test_execution_grants.py")),
    EvidenceRule(("3.7", "4.1", "4.5", "4.6", "4.7", "4.8"), ("pyproject.toml", ".pre-commit-config.yaml", "tests/test_architecture_boundaries.py")),
    EvidenceRule(("6.3",), ("src/core/confidence_scoring.py", "tests/test_confidence_scoring.py")),
    EvidenceRule(("6.4",), ("src/knowledge_graph/models.py", "tests/test_knowledge_graph_models.py")),
    EvidenceRule(("6.7",), ("services/control_plane/proposals.py", "tests/test_goal_proposals.py")),
    EvidenceRule(("7.1", "7.2"), ("services/cloud.py", "tests/test_cloud_boundaries.py")),
)

MIGRATION_ONLY_PREFIXES = ("1.", "4.3", "4.4", "4.9", "4.10", "5.")
BINDING_RE = re.compile(r"\b(shall|must|required|prohibited|cannot|may not|non-conformant|binding)\b", re.IGNORECASE)
SECTION_RE = re.compile(r"^## (\d+\.\d+) (.+)")
HEADING_RE = re.compile(r"^#{1,6} (.+)")


def evidence_for(section: str, root: Path) -> tuple[str, ...]:
    for rule in EVIDENCE_RULES:
        if section in rule.sections:
            return tuple(path for path in rule.evidence if (root / path).exists())
    return ()


def status_for(section: str, evidence: tuple[str, ...], canonical_exists: bool) -> str:
    if not canonical_exists:
        return "MISSING_DOCUMENTATION"
    if section.startswith(MIGRATION_ONLY_PREFIXES):
        return "MIGRATED"
    if evidence:
        return "PARTIAL"
    return "MISSING_IMPLEMENTATION"


def iter_requirements(source: Path) -> list[tuple[int, str, str, str]]:
    section = "PREAMBLE"
    heading = "Canonical Authority"
    requirements: list[tuple[int, str, str, str]] = []
    gate_heading = False
    in_comment = False
    for line_number, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if "<!--" in raw:
            in_comment = True
        if in_comment:
            if "-->" in raw:
                in_comment = False
            continue
        section_match = SECTION_RE.match(raw)
        if section_match:
            section = section_match.group(1)
            heading = section_match.group(2)
            gate_heading = False
            continue
        heading_match = HEADING_RE.match(raw)
        if heading_match:
            heading = heading_match.group(1)
            gate_heading = heading in {"Quality Gates", "Prohibited Practices", "Conformance Requirements", "Canonical Invariants"}
            continue
        text = raw.strip()
        if not text:
            continue
        if BINDING_RE.search(text) or (gate_heading and text.startswith("- ")):
            requirements.append((line_number, section, heading, text))
    return requirements


def generate(root: Path, output: Path, canonical_exists: bool) -> int:
    source = root / "dev/openclaw/migration_input" / SOURCE_NAME
    canonical = root / "docs/canonical" / CANONICAL_NAME
    rows = iter_requirements(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("requirement_id", "legacy_source", "ilaten_requirement", "current_ilaios_canonical_equivalent", "repository_implementation_evidence", "status"))
        for number, (line, section, heading, requirement) in enumerate(rows, 1):
            evidence = evidence_for(section, root)
            canonical_ref = f"{canonical.relative_to(root)} :: {section} / {heading}" if canonical_exists else "NONE"
            writer.writerow((f"ILATEN-{number:05d}", f"{source.relative_to(root)}:{line}", requirement, canonical_ref, "; ".join(evidence) or "NONE", status_for(section, evidence, canonical_exists)))
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pre-migration", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    count = generate(root, args.output.resolve(), not args.pre_migration)
    print(f"wrote {count} requirements to {args.output}")


if __name__ == "__main__":
    main()
