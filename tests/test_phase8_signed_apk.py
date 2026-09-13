"""Phase 8: ilaios-mobile-android-signed-apk tests.

Validates Android signed-APK SHA256 against canonical golden references.
These tests ensure the signed-APK validation contract is sound
before proceeding to later phases that will replace the placeholder
with content-addressed binary hash references.
"""

from services.store_release_certification import (
    validate_android_signed_apk,
    StoreCertificationError,
)


def test_signed_apk_mismatch_raises_error() -> None:
    """Mismatched signed-APK SHA256 should raise StoreCertificationError (fail-closed)."""
    try:
        validate_android_signed_apk("aaaa" * 16, "bbbb" * 16)
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e)
        assert "signed-APK" in str(e)


def test_signed_apk_match_passes() -> None:
    """Matching signed-APK SHA256 (using placeholder) should pass validation."""
    placeholder = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    try:
        validate_android_signed_apk(placeholder, placeholder)
    except StoreCertificationError as e:
        assert False, f"Matching signed-APK SHA256 should pass: {e}"


def test_signed_apk_different_lengths_raises_error() -> None:
    """Signed-APK SHA256 with wrong length should raise StoreCertificationError."""
    try:
        validate_android_signed_apk("short", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e) or "must be a lowercase SHA-256 hex digest" in str(e)


if __name__ == "__main__":
    test_signed_apk_mismatch_raises_error()
    print("PASS: test_signed_apk_mismatch_raises_error")
    test_signed_apk_match_passes()
    print("PASS: test_signed_apk_match_passes")
    test_signed_apk_different_lengths_raises_error()
    print("PASS: test_signed_apk_different_lengths_raises_error")
    print("\nAll Phase 8 signed-APK tests passed!")