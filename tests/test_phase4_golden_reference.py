"""Phase 4: ilaios-mobile-android-golden-reference tests.

Validates Android artifact SHA256 against canonical golden references.
These tests ensure the golden reference validation contract is sound
before proceeding to later phases that will replace the placeholder
with content-addressed binary identities.
"""

from services.store_release_certification import (
    validate_android_golden_reference,
    StoreCertificationError,
)


def test_golden_reference_mismatch_raises_error() -> None:
    """Mismatched SHA256 should raise StoreCertificationError (fail-closed)."""
    try:
        validate_android_golden_reference("aaaa" * 16, "bbbb" * 16)
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e)
        assert "golden reference" in str(e)


def test_golden_reference_match_passes() -> None:
    """Matching SHA256 (using placeholder) should pass validation."""
    placeholder = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    try:
        validate_android_golden_reference(placeholder, placeholder)
    except StoreCertificationError as e:
        assert False, f"Matching SHA256 should pass: {e}"


def test_golden_reference_different_lengths_raises_error() -> None:
    """SHA256 with wrong length should raise StoreCertificationError."""
    try:
        validate_android_golden_reference("short", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "must be a lowercase SHA-256 hex digest" in str(e) or "does not match" in str(e)


if __name__ == "__main__":
    test_golden_reference_mismatch_raises_error()
    print("PASS: test_golden_reference_mismatch_raises_error")
    test_golden_reference_match_passes()
    print("PASS: test_golden_reference_match_passes")
    test_golden_reference_different_lengths_raises_error()
    print("PASS: test_golden_reference_different_lengths_raises_error")
    print("\nAll Phase 4 golden reference tests passed!")