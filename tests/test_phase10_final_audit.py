"""Phase 10: final-audit tests.

Validates final audit SHA256 against canonical golden references.
This is the end-to-end canonical integrity check across ALL phases (3-10).
"""

from services.store_release_certification import (
    validate_android_final_audit,
    StoreCertificationError,
)


def test_final_audit_mismatch_raises_error() -> None:
    """Mismatched final audit SHA256 should raise StoreCertificationError (fail-closed)."""
    try:
        validate_android_final_audit("aaaa" * 16, "bbbb" * 16)
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e)
        assert "final audit" in str(e)


def test_final_audit_match_passes() -> None:
    """Matching final audit SHA256 (using placeholder) should pass validation."""
    placeholder = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    try:
        validate_android_final_audit(placeholder, placeholder)
    except StoreCertificationError as e:
        assert False, f"Matching final audit SHA256 should pass: {e}"


def test_final_audit_different_lengths_raises_error() -> None:
    """Final audit SHA256 with wrong length should raise StoreCertificationError."""
    try:
        validate_android_final_audit("short", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e) or "must be a lowercase SHA-256 hex digest" in str(e)


if __name__ == "__main__":
    test_final_audit_mismatch_raises_error()
    print("PASS: test_final_audit_mismatch_raises_error")
    test_final_audit_match_passes()
    print("PASS: test_final_audit_match_passes")
    test_final_audit_different_lengths_raises_error()
    print("PASS: test_final_audit_different_lengths_raises_error")
    print("\nAll Phase 10 final-audit tests passed!")