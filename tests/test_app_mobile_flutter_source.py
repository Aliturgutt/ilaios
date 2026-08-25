from __future__ import annotations

import hashlib

import pytest

from services.app_mobile_flutter_source import build_flutter_android_project_sources
from services.mobile_android_executor import AndroidImplementationError


def _by_path(changes):
    return {change.relative_path: change for change in changes}


def test_build_flutter_android_project_sources_emits_required_repository_project_files() -> None:
    wrapper = b"fake-gradle-wrapper-binary"
    changes = build_flutter_android_project_sources(
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        display_name="ILAIOS",
        gradle_wrapper_jar=wrapper,
    )

    by_path = _by_path(changes)
    required = {
        "pubspec.yaml",
        "lib/main.dart",
        "android/settings.gradle.kts",
        "android/app/build.gradle.kts",
        "android/app/src/main/AndroidManifest.xml",
        "android/gradlew",
        "android/gradle/wrapper/gradle-wrapper.properties",
        "android/gradle/wrapper/gradle-wrapper.jar",
    }
    assert required <= set(by_path)
    assert all(change.operation == "create" for change in changes)
    assert by_path["android/gradle/wrapper/gradle-wrapper.jar"].content == wrapper
    assert hashlib.sha256(by_path["android/gradle/wrapper/gradle-wrapper.jar"].content).hexdigest() == hashlib.sha256(wrapper).hexdigest()


def test_sources_bind_application_id_and_product_identity_without_external_runtime() -> None:
    changes = build_flutter_android_project_sources(
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        display_name="ILAIOS",
        gradle_wrapper_jar=b"wrapper",
    )
    by_path = _by_path(changes)

    app_gradle = by_path["android/app/build.gradle.kts"].content.decode()
    manifest = by_path["android/app/src/main/AndroidManifest.xml"].content.decode()
    main = by_path["lib/main.dart"].content.decode()
    wrapper_properties = by_path["android/gradle/wrapper/gradle-wrapper.properties"].content.decode()

    assert 'applicationId = "com.ilaios.mobile"' in app_gradle
    assert 'namespace = "com.ilaios.mobile"' in app_gradle
    assert 'android:label="ILAIOS"' in manifest
    assert "Text('ILAIOS')" in main
    assert "services.gradle.org/distributions/gradle-8.10.2-bin.zip" in wrapper_properties
    assert "http://" not in wrapper_properties


def test_sources_escape_display_name_for_xml_and_dart() -> None:
    changes = build_flutter_android_project_sources(
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        display_name="ILAIOS & Founder's",
        gradle_wrapper_jar=b"wrapper",
    )
    by_path = _by_path(changes)

    manifest = by_path["android/app/src/main/AndroidManifest.xml"].content.decode()
    main = by_path["lib/main.dart"].content.decode()
    assert "ILAIOS &amp; Founder&apos;s" in manifest
    assert "ILAIOS & Founder\\'s" in main


@pytest.mark.parametrize(
    ("app_id", "application_id", "display_name", "wrapper"),
    [
        ("ILAIOS", "com.ilaios.mobile", "ILAIOS", b"wrapper"),
        ("ilaios-mobile", "ilaios", "ILAIOS", b"wrapper"),
        ("ilaios-mobile", "com.ilaios.mobile", " ILAIOS", b"wrapper"),
        ("ilaios-mobile", "com.ilaios.mobile", "ILAIOS", b""),
    ],
)
def test_sources_fail_closed_on_invalid_identity_or_missing_binary_wrapper(
    app_id: str,
    application_id: str,
    display_name: str,
    wrapper: bytes,
) -> None:
    with pytest.raises(AndroidImplementationError):
        build_flutter_android_project_sources(
            app_id=app_id,
            application_id=application_id,
            display_name=display_name,
            gradle_wrapper_jar=wrapper,
        )


def test_wrapper_payload_is_bounded() -> None:
    with pytest.raises(AndroidImplementationError, match="bounded size"):
        build_flutter_android_project_sources(
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            display_name="ILAIOS",
            gradle_wrapper_jar=b"x" * 1_000_001,
        )
