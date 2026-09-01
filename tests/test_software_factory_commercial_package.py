from __future__ import annotations

from pathlib import Path

from services.software_factory_commercial_package import SoftwareFactoryCommercialPackage

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_software_factory_commercial_package_is_first_party_and_bounded() -> None:
    report = SoftwareFactoryCommercialPackage().audit(REPOSITORY_ROOT)
    assert report.passed is True
    assert report.scope == "SOFTWARE_FACTORY_IMPLEMENTATION"
    assert report.canonical_skill_count >= 25
    assert report.imported_code_text_resolved is True
    assert report.commercial_compatibility_resolved is True
    assert report.restrictive_or_unknown_license_present is False
    assert report.package_manifest_present is True
    assert report.ai_ip_clearance_claimed is False
    assert report.deployment_authorized is False
    assert report.production_mutation_authorized is False
    assert len(report.files) > 0
    assert len(report.report_sha256) == 64


def test_commercial_package_external_dependency_evidence_is_permissive_only() -> None:
    report = SoftwareFactoryCommercialPackage().audit(REPOSITORY_ROOT)
    allowed = {"MIT", "Apache-2.0", "BSD-3-Clause"}
    assert all(item.license_id in allowed for item in report.external_dependencies)
