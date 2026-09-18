"""Phase 3: android-build-google-play-certification tests.

Validates Android google-play-certification SHA256 against canonical golden references.
This is the first phase in the certification chain - validates against Google Play
certification requirements before proceeding to golden reference (Phase 4) and beyond.
"""

from services.store_release_certification import (
    validate_android_google_play_certification,
    StoreCertificationError,
)


def test_google_play_certification_mismatch_raises_error() -> None:
    """Mismatched certification SHA256 should raise StoreCertificationError (fail-closed)."""
    try:
        validate_android_google_play_certification("aaaa" * 16, "bbbb" * 16)
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e)
        assert "google-play-certification" in str(e)


def test_google_play_certification_match_passes() -> None:
    """Matching certification SHA256 (using placeholder) should pass validation."""
    placeholder = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    try:
        validate_android_google_play_certification(placeholder, placeholder)
    except StoreCertificationError as e:
        assert False, f"Matching certification SHA256 should pass: {e}"


def test_google_play_certification_different_lengths_raises_error() -> None:
    """Google play certification SHA256 with wrong length should raise StoreCertificationError."""
    try:
        validate_android_google_play_certification("short", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        assert False, "Expected StoreCertificationError not raised"
    except StoreCertificationError as e:
        assert "does not match" in str(e) or "must be a lowercase SHA-256 hex digest" in str(e)


if __name__ == "__main__":
    test_google_play_certification_mismatch_raises_error()
    print("PASS: test_google_play_certification_mismatch_raises_error")
    test_google_play_certification_match_passes()
    print("PASS: test_google_play_certification_match_passes")
    test_google_play_certification_different_lengths_raises_error()
    print("PASS: test_google_play_certification_different_lengths_raises_error")
    print("\nAll Phase 3 android-build-google-play-certification tests passed!")