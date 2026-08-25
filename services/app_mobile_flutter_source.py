"""Deterministic Flutter Android source materialization for the canonical App Factory path.

This module produces repository-owned source inputs for the existing Android source executor.
It does not write the repository, run Flutter/Gradle, sign binaries, access credentials, call
Store APIs, or create a second App Factory/build authority. Binary Gradle wrapper bytes must
be supplied by the governed caller and are preserved byte-for-byte in the source plan.
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape as xml_escape

from services.mobile_android_executor import AndroidImplementationError, AndroidSourceChange

_APP_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{1,127}")
_APPLICATION_ID_PATTERN = re.compile(
    r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+"
)


def build_flutter_android_project_sources(
    *,
    app_id: str,
    application_id: str,
    display_name: str,
    gradle_wrapper_jar: bytes,
) -> tuple[AndroidSourceChange, ...]:
    """Create the minimum repository-owned Flutter/Android project source set.

    The returned paths are relative to ``apps/mobile/android/<app_id>/`` and are intended
    to flow through ``build_flutter_android_materialization_plan`` and the incumbent
    governed Software Factory executor.
    """
    if _APP_ID_PATTERN.fullmatch(app_id) is None:
        raise AndroidImplementationError("app_id must be a lowercase bounded path token")
    if _APPLICATION_ID_PATTERN.fullmatch(application_id) is None:
        raise AndroidImplementationError("application_id must be a dotted Android package id")
    if not display_name.strip() or display_name != display_name.strip():
        raise AndroidImplementationError("display_name must be non-blank and trimmed")
    if len(display_name) > 80:
        raise AndroidImplementationError("display_name exceeds the bounded length")
    if not gradle_wrapper_jar:
        raise AndroidImplementationError("gradle_wrapper_jar must be supplied")
    if len(gradle_wrapper_jar) > 1_000_000:
        raise AndroidImplementationError("gradle_wrapper_jar exceeds the bounded size")

    escaped_name = xml_escape(display_name, {'"': '&quot;', "'": '&apos;'})
    dart_title = display_name.replace("\\", "\\\\").replace("'", "\\'")

    files: tuple[tuple[str, bytes], ...] = (
        (
            "pubspec.yaml",
            (
                "name: " + app_id.replace("-", "_").replace(".", "_") + "\n"
                "description: ILAIOS governed Flutter Android application.\n"
                "publish_to: 'none'\n"
                "version: 0.1.0+1\n"
                "environment:\n"
                "  sdk: '>=3.4.0 <4.0.0'\n"
                "dependencies:\n"
                "  flutter:\n"
                "    sdk: flutter\n"
                "dev_dependencies:\n"
                "  flutter_test:\n"
                "    sdk: flutter\n"
                "flutter:\n"
                "  uses-material-design: true\n"
            ).encode("utf-8"),
        ),
        (
            "lib/main.dart",
            (
                "import 'package:flutter/material.dart';\n\n"
                "void main() => runApp(const IlaiosMobileApp());\n\n"
                "class IlaiosMobileApp extends StatelessWidget {\n"
                "  const IlaiosMobileApp({super.key});\n\n"
                "  @override\n"
                "  Widget build(BuildContext context) {\n"
                "    return MaterialApp(\n"
                "      debugShowCheckedModeBanner: false,\n"
                f"      title: '{dart_title}',\n"
                "      home: const Scaffold(\n"
                "        body: Center(child: Text('ILAIOS')),\n"
                "      ),\n"
                "    );\n"
                "  }\n"
                "}\n"
            ).encode("utf-8"),
        ),
        (
            "android/settings.gradle.kts",
            b"pluginManagement {\n"
            b"    val flutterSdkPath = run {\n"
            b"        val properties = java.util.Properties()\n"
            b"        file(\"local.properties\").inputStream().use { properties.load(it) }\n"
            b"        requireNotNull(properties.getProperty(\"flutter.sdk\")) { \"flutter.sdk not set in local.properties\" }\n"
            b"    }\n"
            b"    includeBuild(\"$flutterSdkPath/packages/flutter_tools/gradle\")\n"
            b"    repositories { google(); mavenCentral(); gradlePluginPortal() }\n"
            b"}\n"
            b"plugins {\n"
            b"    id(\"dev.flutter.flutter-plugin-loader\") version \"1.0.0\"\n"
            b"    id(\"com.android.application\") version \"8.7.3\" apply false\n"
            b"    id(\"org.jetbrains.kotlin.android\") version \"2.1.0\" apply false\n"
            b"}\n"
            b"include(\":app\")\n",
        ),
        (
            "android/app/build.gradle.kts",
            (
                "plugins {\n"
                "    id(\"com.android.application\")\n"
                "    id(\"kotlin-android\")\n"
                "    id(\"dev.flutter.flutter-gradle-plugin\")\n"
                "}\n\n"
                "android {\n"
                f"    namespace = \"{application_id}\"\n"
                "    compileSdk = flutter.compileSdkVersion\n"
                "    ndkVersion = flutter.ndkVersion\n\n"
                "    compileOptions {\n"
                "        sourceCompatibility = JavaVersion.VERSION_17\n"
                "        targetCompatibility = JavaVersion.VERSION_17\n"
                "    }\n"
                "    kotlinOptions { jvmTarget = JavaVersion.VERSION_17.toString() }\n\n"
                "    defaultConfig {\n"
                f"        applicationId = \"{application_id}\"\n"
                "        minSdk = flutter.minSdkVersion\n"
                "        targetSdk = flutter.targetSdkVersion\n"
                "        versionCode = flutter.versionCode\n"
                "        versionName = flutter.versionName\n"
                "    }\n"
                "}\n\n"
                "flutter { source = \"../..\" }\n"
            ).encode("utf-8"),
        ),
        (
            "android/app/src/main/AndroidManifest.xml",
            (
                "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">\n"
                f"  <application android:label=\"{escaped_name}\" android:name=\"${{applicationName}}\">\n"
                "    <activity android:name=\".MainActivity\" android:exported=\"true\" android:launchMode=\"singleTop\" android:theme=\"@style/LaunchTheme\">\n"
                "      <intent-filter>\n"
                "        <action android:name=\"android.intent.action.MAIN\"/>\n"
                "        <category android:name=\"android.intent.category.LAUNCHER\"/>\n"
                "      </intent-filter>\n"
                "    </activity>\n"
                "    <meta-data android:name=\"flutterEmbedding\" android:value=\"2\"/>\n"
                "  </application>\n"
                "</manifest>\n"
            ).encode("utf-8"),
        ),
        (
            "android/gradlew",
            b"#!/bin/sh\nAPP_HOME=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\nexec java -classpath \"$APP_HOME/gradle/wrapper/gradle-wrapper.jar\" org.gradle.wrapper.GradleWrapperMain \"$@\"\n",
        ),
        (
            "android/gradlew.bat",
            b"@echo off\r\nset APP_HOME=%~dp0\r\njava -classpath \"%APP_HOME%\\gradle\\wrapper\\gradle-wrapper.jar\" org.gradle.wrapper.GradleWrapperMain %*\r\n",
        ),
        (
            "android/gradle/wrapper/gradle-wrapper.properties",
            b"distributionBase=GRADLE_USER_HOME\n"
            b"distributionPath=wrapper/dists\n"
            b"distributionUrl=https\\://services.gradle.org/distributions/gradle-8.10.2-bin.zip\n"
            b"networkTimeout=10000\n"
            b"validateDistributionUrl=true\n"
            b"zipStoreBase=GRADLE_USER_HOME\n"
            b"zipStorePath=wrapper/dists\n",
        ),
        ("android/gradle/wrapper/gradle-wrapper.jar", gradle_wrapper_jar),
    )
    return tuple(
        AndroidSourceChange(operation="create", relative_path=path, content=content)
        for path, content in files
    )
