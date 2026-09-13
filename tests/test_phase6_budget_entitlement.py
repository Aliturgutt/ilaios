"""Phase 6: ilaios-mobile-android-budget-entitlement tests.

Validates Android budget/entitlement SHA256 against canonical golden references.
These tests ensure the budget entitlement validation contract is sound
before proceeding to later phases that will replace the placeholder
with content-addressed cost center identities.
"""

from services.store_release_certification import (
    validate_android_budget_entitlement,
    StoreCertificationError,
)


def test_budget_entitlement_mismatch_raises_error() -> None:
    """Mismatched entitlement SHA256 should raise StoreCertificationError (fail-closed)."""
    try:
        validate_android_budget_entitlement("aaaa" * 16, "bbbb" * 16)
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e)
        assert "budget entitlement" in str(e)


def test_budget_entitlement_match_passes() -> None:
    """Matching entitlement SHA256 (using placeholder) should pass validation."""
    placeholder = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    try:
        validate_android_budget_entitlement(placeholder, placeholder)
    except StoreCertificationError as e:
        assert False, f"Matching entitlement SHA256 should pass: {e}"


def test_budget_entitlement_different_lengths_raises_error() -> None:
    """Budget entitlement SHA256 with wrong length should raise StoreCertificationError."""
    try:
        validate_android_budget_entitlement("short", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e) or "must be a lowercase SHA-256 hex digest" in str(e)


if __name__ == "__main__":
    test_budget_entitlement_mismatch_raises_error()
    print("PASS: test_budget_entitlement_mismatch_raises_error")
    test_budget_entitlement_match_passes()
    print("PASS: test_budget_entitlement_match_passes")
    test_budget_entitlement_different_lengths_raises_error()
    print("PASS: test_budget_entitlement_different_lengths_raises_error")
    print("\nAll Phase 6 budget entitlement tests passed!")