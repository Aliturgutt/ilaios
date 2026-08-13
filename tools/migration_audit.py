"""Generate the ILATEN-to-ILAIOS normative requirement migration matrix."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

SOURCE_NAME = (
    "ILATEN_Enterprise_AI_Operating_System_Canonical_Architecture_v1.0(3)(4).md"
)
SOURCE_DIRECTORY = "docs/archive/pre-2026-08-13/migration-input"
CANONICAL_NAME = (
    "../archive/pre-2026-08-13/"
    "ILAIOS_ENTERPRISE_AI_OPERATING_SYSTEM_CANONICAL_ARCHITECTURE.md"
)


@dataclass(frozen=True)
class EvidenceRule:
    sections: tuple[str, ...]
    pattern: re.Pattern[str]
    evidence: tuple[str, ...]


EVIDENCE_RULES = (
    EvidenceRule(
        ("2.2", "2.9"),
        re.compile(r"evidence|append-only|hash|tamper", re.IGNORECASE),
        (
            "src/core/evidence_chain.py",
            "services/evidence/store.py",
            "tests/test_evidence_chain.py",
            "tests/test_evidence_store.py",
        ),
    ),
    EvidenceRule(
        ("2.3", "2.6"),
        re.compile(
            r"immutable context|tool gateway|validation|execution grant|workflow",
            re.IGNORECASE,
        ),
        (
            "src/core/immutable_context.py",
            "src/core/tool_gateway.py",
            "services/control_plane/workflows.py",
            "tests/test_governed_runtime.py",
        ),
    ),
    EvidenceRule(
        ("2.5",),
        re.compile(r"scheduler|lease|retry|checkpoint|reconcil", re.IGNORECASE),
        (
            "services/runtime/scheduler.py",
            "services/control_plane/workflows.py",
            "tests/test_worker_scheduler.py",
            "tests/test_durable_workflows.py",
        ),
    ),
    EvidenceRule(
        ("2.4", "3.3", "3.8", "6.1", "6.2", "8.4", "8.9"),
        re.compile(
            r"agent|machine ID|alias|role|team|capabilit|permission|allowed caller|"
            r"allowed target|escalat|verifier|prompt injection|exfiltrat|secret|"
            r"permission firewall|security scan|independent verification|grant",
            re.IGNORECASE,
        ),
        (
            "services/agent_governance.py",
            "services/runtime/grants.py",
            "tests/test_agent_governance.py",
            "evidence/migration/ILATEN_TO_ILAIOS/AGENT.I07.md",
        ),
    ),
    EvidenceRule(
        ("2.8",),
        re.compile(r"validation|rule|waiver", re.IGNORECASE),
        ("src/core/validation_pipeline.py", "tests/test_validation_pipeline.py"),
    ),
    EvidenceRule(
        ("2.10",),
        re.compile(r"audit event|audit engine|redact|material event", re.IGNORECASE),
        ("src/core/audit_engine.py", "tests/test_audit_engine.py"),
    ),
    EvidenceRule(
        ("2.11", "6.5"),
        re.compile(r"source file|code entity|repository|analy", re.IGNORECASE),
        (
            "src/code_intelligence/source_file_analyzer.py",
            "src/code_intelligence/models.py",
            "tests/test_source_file_analyzer.py",
            "tests/test_code_intelligence_models.py",
        ),
    ),
    EvidenceRule(
        ("3.3",),
        re.compile(r"grant|scope|revocation|authoriz", re.IGNORECASE),
        (
            "services/runtime/grants.py",
            "services/governance/gates.py",
            "tests/test_execution_grants.py",
        ),
    ),
    EvidenceRule(
        ("3.1", "3.2", "3.3", "8.1", "8.2"),
        re.compile(
            r"OIDC|OAuth|federat|authenticat|identity|session|tenant|RBAC|ABAC|"
            r"role|attribute|privileg|high-risk|approval|revocation|recovery|"
            r"break-glass|service-to-service|workload",
            re.IGNORECASE,
        ),
        (
            "services/identity.py",
            "tests/test_identity_access.py",
            "evidence/migration/ILATEN_TO_ILAIOS/IAM.I02.md",
        ),
    ),
    EvidenceRule(
        ("3.7", "4.1", "4.5", "4.6", "4.7", "4.8"),
        re.compile(
            r"ruff|mypy|test|quality gate|pre-commit|architecture", re.IGNORECASE
        ),
        (
            "pyproject.toml",
            ".pre-commit-config.yaml",
            "tests/test_architecture_boundaries.py",
        ),
    ),
    EvidenceRule(
        ("3.4", "3.5", "3.6"),
        re.compile(
            r"secret|credential|key|KMS|HSM|envelope|encrypt|crypt|rotation|"
            r"revocation|destruction|tenant|customer-managed|audit",
            re.IGNORECASE,
        ),
        (
            "services/cryptography.py",
            "tests/test_managed_cryptography.py",
            "evidence/migration/ILATEN_TO_ILAIOS/CRYPTO.I03.md",
        ),
    ),
    EvidenceRule(
        ("6.3",),
        re.compile(r"confidence|uncertain", re.IGNORECASE),
        ("src/core/confidence_scoring.py", "tests/test_confidence_scoring.py"),
    ),
    EvidenceRule(
        ("3.9", "3.10", "3.11", "7.9", "8.7", "8.8"),
        re.compile(
            r"SLI|SLO|error budget|health|readiness|incident|severity|escalat|"
            r"runbook|backup|restore|disaster recovery|recovery exercise|RPO|"
            r"RTO|rollback|post-incident|monitor|alert",
            re.IGNORECASE,
        ),
        (
            "services/operations.py",
            "tests/test_operations_framework.py",
            "evidence/migration/ILATEN_TO_ILAIOS/OPS.I05.md",
        ),
    ),
    EvidenceRule(
        ("6.4",),
        re.compile(r"knowledge graph|node|edge|provenance", re.IGNORECASE),
        ("src/knowledge_graph/models.py", "tests/test_knowledge_graph_models.py"),
    ),
    EvidenceRule(
        ("6.7",),
        re.compile(r"plan|proposal|goal", re.IGNORECASE),
        ("services/control_plane/proposals.py", "tests/test_goal_proposals.py"),
    ),
    EvidenceRule(
        ("7.1", "7.2"),
        re.compile(r"tenant|region|deployment profile|quota", re.IGNORECASE),
        ("services/cloud.py", "tests/test_cloud_boundaries.py"),
    ),
    EvidenceRule(
        ("7.3", "7.4", "7.5", "7.6", "7.7", "7.8", "7.9", "7.10", "8.8"),
        re.compile(
            r"container|OCI|orchestrat|relational|object|queue|event|network|"
            r"ingress|log|metric|trac|correlation|telemetry|observab|health|"
            r"capacity|cost|evidence|authoriz",
            re.IGNORECASE,
        ),
        (
            "services/observability.py",
            "tests/test_observability_contracts.py",
            "evidence/migration/ILATEN_TO_ILAIOS/OBS.I06.md",
        ),
    ),
    EvidenceRule(
        ("2.7", "7.1", "7.2", "7.5", "8.10"),
        re.compile(
            r"tenant|privacy|residency|region|retention|deletion|legal hold|"
            r"minimi|purpose|export|DLP|regulatory|data class",
            re.IGNORECASE,
        ),
        (
            "services/privacy.py",
            "tests/test_tenant_privacy.py",
            "evidence/migration/ILATEN_TO_ILAIOS/DATA.I04.md",
        ),
    ),
    EvidenceRule(
        ("8.1", "8.10"),
        re.compile(r"tenant_id|cross-tenant|region", re.IGNORECASE),
        ("services/cloud.py", "tests/test_cloud_boundaries.py"),
    ),
    EvidenceRule(
        ("8.5",),
        re.compile(r"release|promotion", re.IGNORECASE),
        ("services/readiness.py", "tests/test_promotion_readiness.py"),
    ),
    EvidenceRule(
        ("8.1", "8.2", "8.3", "8.4", "8.5", "8.6", "8.11", "8.12"),
        re.compile(
            r"owner|ownership|RACI|accountable|responsible|consulted|informed|"
            r"risk|treatment|acceptance|change|approval|exception|waiver|review|"
            r"deprecat|retire|lifecycle|audit|compliance|certif|claim|evidence",
            re.IGNORECASE,
        ),
        (
            "services/governance/records.py",
            "tests/test_governance_records.py",
            "evidence/migration/ILATEN_TO_ILAIOS/ORG.I08.md",
        ),
    ),
    EvidenceRule(
        ("8.8", "8.9"),
        re.compile(r"budget|cost|pricing|reservation|hard ceiling", re.IGNORECASE),
        ("services/governance/gates.py", "tests/test_security_finance_gates.py"),
    ),
    EvidenceRule(
        ("8.9",),
        re.compile(r"provider|routing|deterministic|skill|agent", re.IGNORECASE),
        ("services/runtime/routing.py", "tests/test_governed_runtime.py"),
    ),
    EvidenceRule(
        ("8.8", "8.9"),
        re.compile(
            r"model|provider|routing|fallback|token|context|budget|cost|GPU|"
            r"runtime|quota|concurrency|retry|circuit|usage|FinOps",
            re.IGNORECASE,
        ),
        (
            "services/ai_governance.py",
            "tests/test_ai_governance.py",
            "evidence/migration/ILATEN_TO_ILAIOS/GOV.I01.md",
        ),
    ),
)

# Exact implementation rules are deliberately separate from thematic evidence.
# A row may become IMPLEMENTED only when its complete assertion is covered by a
# bounded implementation package, tests, and durable package evidence.
GOV_I01_PROOF = (
    "services/ai_governance.py",
    "tests/test_ai_governance.py",
    "evidence/migration/ILATEN_TO_ILAIOS/GOV.I01.md",
)
IMPLEMENTATION_RULES = (
    EvidenceRule(
        ("8.8", "8.9"),
        re.compile(
            r"^(Per-user, tenant, project, job, provider, and model usage shall "
            r"be attributable|Warning thresholds shall notify without granting "
            r"authority|Hard ceilings shall block or safely degrade new billable "
            r"work|Retry-cost ceilings, concurrency limits, rate limits, circuit "
            r"breakers, and kill switches shall prevent runaway agents and "
            r"economic amplification|Models and providers shall be admitted "
            r"through versioned registries|Routing shall be deterministic and "
            r"evidence-producing for the same approved inputs and registry state|"
            r"Usage controls shall support per-user, per-tenant, per-project, "
            r"per-job, per-provider, and per-model scopes|Hard ceilings block new "
            r"governed consumption; they shall not be converted into warnings by "
            r"a model or provider)\.?$",
            re.IGNORECASE,
        ),
        GOV_I01_PROOF,
    ),
)

MIGRATION_ONLY_PREFIXES = ("1.", "4.3", "4.4", "4.9", "4.10", "5.")
BINDING_RE = re.compile(
    r"\b(shall|must|required|prohibited|cannot|may not|non-conformant|binding)\b",
    re.IGNORECASE,
)
SECTION_RE = re.compile(r"^## (\d+\.\d+) (.+)")
HEADING_RE = re.compile(r"^#{1,6} (.+)")


def evidence_for(section: str, requirement: str, root: Path) -> tuple[str, ...]:
    matches: list[str] = []
    for rule in EVIDENCE_RULES:
        if section in rule.sections and rule.pattern.search(requirement):
            matches.extend(path for path in rule.evidence if (root / path).exists())
    return tuple(dict.fromkeys(matches))


def implementation_proof_for(
    section: str, requirement: str, root: Path
) -> tuple[str, ...]:
    for rule in IMPLEMENTATION_RULES:
        if (
            section in rule.sections
            and rule.pattern.search(requirement)
            and all((root / path).exists() for path in rule.evidence)
        ):
            return rule.evidence
    return ()


def status_for(
    section: str,
    evidence: tuple[str, ...],
    canonical_exists: bool,
    *,
    completion_requirement: bool = False,
    exact_proof: bool = False,
) -> str:
    if not canonical_exists:
        return "MISSING_DOCUMENTATION"
    if section.startswith(MIGRATION_ONLY_PREFIXES) or section.startswith("9."):
        return "MIGRATED"
    if exact_proof:
        return "IMPLEMENTED"
    if evidence:
        return "PARTIAL"
    return "MISSING_IMPLEMENTATION"


def iter_requirements(source: Path) -> list[tuple[int, str, str, str]]:
    section = "PREAMBLE"
    heading = "Canonical Authority"
    requirements: list[tuple[int, str, str, str]] = []
    gate_heading = False
    in_comment = False
    for line_number, raw in enumerate(
        source.read_text(encoding="utf-8").splitlines(), 1
    ):
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
            gate_heading = heading in {
                "Quality Gates",
                "Prohibited Practices",
                "Conformance Requirements",
                "Canonical Invariants",
            }
            continue
        text = raw.strip()
        if not text:
            continue
        if BINDING_RE.search(text) or (gate_heading and text.startswith("- ")):
            requirements.append((line_number, section, heading, text))
    return requirements


def iter_completion_requirements(canonical: Path) -> list[tuple[int, str, str, str]]:
    requirements = iter_requirements(canonical)
    return [item for item in requirements if item[1].startswith(("8.", "9."))]


def generate(root: Path, output: Path, canonical_exists: bool) -> int:
    source = root / SOURCE_DIRECTORY / SOURCE_NAME
    canonical = root / "docs/canonical" / CANONICAL_NAME
    rows = iter_requirements(source)
    completion_rows = (
        iter_completion_requirements(canonical) if canonical_exists else []
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            (
                "requirement_id",
                "legacy_source",
                "ilaten_requirement",
                "current_ilaios_canonical_equivalent",
                "repository_implementation_evidence",
                "status",
            )
        )
        for number, (line, section, heading, requirement) in enumerate(rows, 1):
            proof = implementation_proof_for(section, requirement, root)
            evidence = tuple(
                dict.fromkeys((*evidence_for(section, requirement, root), *proof))
            )
            canonical_ref = (
                f"{canonical.relative_to(root)} :: {section} / {heading}"
                if canonical_exists
                else "NONE"
            )
            writer.writerow(
                (
                    f"ILATEN-{number:05d}",
                    f"{source.relative_to(root)}:{line}",
                    requirement,
                    canonical_ref,
                    "; ".join(evidence) or "NONE",
                    status_for(
                        section, evidence, canonical_exists, exact_proof=bool(proof)
                    ),
                )
            )
        for number, (line, section, heading, requirement) in enumerate(
            completion_rows, 1
        ):
            proof = implementation_proof_for(section, requirement, root)
            evidence = tuple(
                dict.fromkeys((*evidence_for(section, requirement, root), *proof))
            )
            writer.writerow(
                (
                    f"ILAIOS-C-{number:05d}",
                    "HUMAN_ARCHITECTURE_DECISION_PACKAGE:2026-08-09",
                    requirement,
                    f"{canonical.relative_to(root)}:{line} :: {section} / {heading}",
                    "; ".join(evidence) or "NONE",
                    status_for(
                        section,
                        evidence,
                        canonical_exists,
                        completion_requirement=True,
                        exact_proof=bool(proof),
                    ),
                )
            )
    return len(rows) + len(completion_rows)


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
