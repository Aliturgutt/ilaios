"""Tests for the bounded deterministic Web Factory repair policy."""

from __future__ import annotations

from dataclasses import replace

import pytest

from services.integrations.web_factory import derive_website_spec
from services.integrations.web_repair import BoundedWebRepairPolicy, WebRepairError


def test_repair_normalizes_structural_spec_once_with_hash_evidence() -> None:
    base = derive_website_spec(
        "repair-structural",
        "Build a bilingual Turkish/English website for a corporate law firm",
    )
    invalid = replace(
        base,
        pages=("about", "about"),
        locales=("fr",),
    )
    repaired, attempt = BoundedWebRepairPolicy().repair_spec(
        invalid,
        ValueError("generated website pages must be non-empty and unique"),
        prior_attempts=0,
    )

    assert repaired.pages == ("home", "about", "contact")
    assert repaired.locales == ("en",)
    assert attempt.attempt == 1
    assert attempt.category == "requirements-structure"
    assert attempt.before_spec_hash != attempt.after_spec_hash
    assert len(attempt.before_spec_hash) == 64
    assert len(attempt.after_spec_hash) == 64


def test_repair_budget_is_exactly_one_attempt() -> None:
    spec = derive_website_spec(
        "repair-budget",
        "Build a website for a professional services company",
    )
    with pytest.raises(WebRepairError, match="budget exhausted"):
        BoundedWebRepairPolicy().repair_spec(
            spec,
            ValueError("generated website requires home and contact routes"),
            prior_attempts=1,
        )


def test_unknown_or_integrity_defect_is_never_auto_repaired() -> None:
    spec = derive_website_spec(
        "repair-integrity",
        "Build a website for a professional services company",
    )
    with pytest.raises(WebRepairError, match="outside the deterministic repair policy"):
        BoundedWebRepairPolicy().repair_spec(
            spec,
            ValueError("generated website file hash validation failed"),
            prior_attempts=0,
        )
