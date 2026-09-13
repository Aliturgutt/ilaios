"""Phase 7: ilaios-mobile-android-cost-aware-routing tests.

Validates Android cost-aware routing SHA256 against canonical golden references.
These tests ensure the cost-aware routing validation contract is sound
before proceeding to later phases that will replace the placeholder
with content-addressed pricing tier identities.
"""

from services.store_release_certification import (
    validate_android_cost_aware_routing,
    StoreCertificationError,
)


def test_cost_aware_routing_mismatch_raises_error() -> None:
    """Mismatched routing SHA256 should raise StoreCertificationError (fail-closed)."""
    try:
        validate_android_cost_aware_routing("aaaa" * 16, "bbbb" * 16)
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e)
        assert "cost-aware routing" in str(e)


def test_cost_aware_routing_match_passes() -> None:
    """Matching routing SHA256 (using placeholder) should pass validation."""
    placeholder = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    try:
        validate_android_cost_aware_routing(placeholder, placeholder)
    except StoreCertificationError as e:
        assert False, f"Matching routing SHA256 should pass: {e}"


def test_cost_aware_routing_different_lengths_raises_error() -> None:
    """Cost-aware routing SHA256 with wrong length should raise StoreCertificationError."""
    try:
        validate_android_cost_aware_routing("short", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e) or "must be a lowercase SHA-256 hex digest" in str(e)


if __name__ == "__main__":
    test_cost_aware_routing_mismatch_raises_error()
    print("PASS: test_cost_aware_routing_mismatch_raises_error")
    test_cost_aware_routing_match_passes()
    print("PASS: test_cost_aware_routing_match_passes")
    test_cost_aware_routing_different_lengths_raises_error()
    print("PASS: test_cost_aware_routing_different_lengths_raises_error")
    print("\nAll Phase 7 cost-aware routing tests passed!")