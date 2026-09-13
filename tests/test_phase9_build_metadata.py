"""Phase 9: ilaios-mobile-android-build-metadata tests.

Validates Android build metadata SHA256 against canonical golden references.
These tests ensure the build metadata validation contract is sound
before proceeding to Phase 10 (final audit) that will replace the placeholder
with content-addressed build provenance references.
"""

from services.store_release_certification import (
    validate_android_build_metadata,
    StoreCertificationError,
)


def test_build_metadata_mismatch_raises_error() -> None:
    """Mismatched build metadata SHA256 should raise StoreCertificationError (fail-closed)."""
    try:
        validate_android_build_metadata("aaaa" * 16, "bbbb" * 16)
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e)
        assert "build metadata" in str(e)


def test_build_metadata_match_passes() -> None:
    """Matching build metadata SHA256 (using placeholder) should pass validation."""
    placeholder = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    try:
        validate_android_build_metadata(placeholder, placeholder)
    except StoreCertificationError as e:
        assert False, f"Matching build metadata SHA256 should pass: {e}"


def test_build_metadata_different_lengths_raises_error() -> None:
    """Build metadata SHA256 with wrong length should raise StoreCertificationError."""
    try:
        validate_android_build_metadata("short", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e) or "must be a lowercase SHA-256 hex digest" in str(e)


if __name__ == "__main__":
    test_build_metadata_mismatch_raises_error()
    print("PASS: test_build_metadata_mismatch_raises_error")
    test_build_metadata_match_passes()
    print("PASS: test_build_metadata_match_passes")
    test_build_metadata_different_lengths_raises_error()
    print("PASS: test_build_metadata_different_lengths_raises_error")
    print("\nAll Phase 9 build metadata tests passed!")