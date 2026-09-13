"""Phase 5: ilaios-mobile-android-device-receipt tests.

Validates Android device receipt SHA256 against canonical golden references.
These tests ensure the device receipt validation contract is sound
before proceeding to later phases that will replace the placeholder
with content-addressed hardware identities.
"""

from services.store_release_certification import (
    validate_android_device_receipt,
    StoreCertificationError,
)


def test_device_receipt_mismatch_raises_error() -> None:
    """Mismatched receipt SHA256 should raise StoreCertificationError (fail-closed)."""
    try:
        validate_android_device_receipt("aaaa" * 16, "bbbb" * 16)
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e)
        assert "device receipt" in str(e)


def test_device_receipt_match_passes() -> None:
    """Matching receipt SHA256 (using placeholder) should pass validation."""
    placeholder = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    try:
        validate_android_device_receipt(placeholder, placeholder)
    except StoreCertificationError as e:
        assert False, f"Matching receipt SHA256 should pass: {e}"


def test_device_receipt_different_lengths_raises_error() -> None:
    """Device receipt SHA256 with wrong length should raise StoreCertificationError."""
    try:
        validate_android_device_receipt("short", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e) or "must be a lowercase SHA-256 hex digest" in str(e)


if __name__ == "__main__":
    test_device_receipt_mismatch_raises_error()
    print("PASS: test_device_receipt_mismatch_raises_error")
    test_device_receipt_match_passes()
    print("PASS: test_device_receipt_match_passes")
    test_device_receipt_different_lengths_raises_error()
    print("PASS: test_device_receipt_different_lengths_raises_error")
    print("\nAll Phase 5 device receipt tests passed!")