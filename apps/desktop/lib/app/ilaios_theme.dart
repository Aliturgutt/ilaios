import 'package:flutter/material.dart';

abstract final class IlaiosTheme {
  // Canonical ILAIOS brand palette. Product UI must derive its visual identity
  // from these exact tokens instead of inventing feature-local colors.
  static const Color carbon = Color(0xFF0B0F14);
  static const Color charcoal = Color(0xFF111827);
  static const Color graphite = Color(0xFF1F2937);
  static const Color white = Color(0xFFFFFFFF);
  static const Color enterpriseCyan = Color(0xFF00C2D1);
  static const Color coreBlue = Color(0xFF146BFF);
  static const Color violet = Color(0xFF5C58FE);

  // Desktop semantic aliases. Foundation stays neutral; brand accents are
  // reserved for identity, interaction and real system state.
  static const Color canvas = carbon;
  static const Color sidebar = charcoal;
  static const Color surface = charcoal;
  static const Color surfaceRaised = graphite;
  static const Color surfaceSoft = charcoal;
  static const Color border = graphite;
  static const Color borderStrong = Color(0x99146BFF);
  static const Color primary = enterpriseCyan;
  static const Color cyan = enterpriseCyan;
  static const Color cyanSoft = Color(0x9900C2D1);
  static const Color blue = coreBlue;
  static const Color selectiveAccent = violet;
  static const Color text = white;
  static const Color muted = Color(0x99FFFFFF);
  static const Color mutedStrong = Color(0xCCFFFFFF);

  // Semantic status colors remain distinct from brand identity colors so
  // success/warning/error meaning is never confused with branding.
  static const Color success = Color(0xFF45D98B);
  static const Color warning = Color(0xFFF1BE45);
  static const Color danger = Color(0xFFFF6A78);

  static ThemeData get dark {
    final scheme = ColorScheme.fromSeed(
      seedColor: enterpriseCyan,
      brightness: Brightness.dark,
      surface: surface,
    ).copyWith(
      primary: enterpriseCyan,
      onPrimary: carbon,
      secondary: coreBlue,
      onSecondary: white,
      tertiary: violet,
      onTertiary: white,
      surface: surface,
      onSurface: white,
      outline: border,
      outlineVariant: border,
      error: danger,
      onError: carbon,
    );
    return ThemeData(
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: canvas,
      useMaterial3: true,
      fontFamily: 'Segoe UI',
      dividerColor: border,
      splashFactory: InkSparkle.splashFactory,
      iconTheme: const IconThemeData(color: mutedStrong),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(
          color: text,
          fontSize: 30,
          height: 1.12,
          fontWeight: FontWeight.w700,
          letterSpacing: -.6,
        ),
        headlineMedium: TextStyle(
          color: text,
          fontSize: 23,
          height: 1.15,
          fontWeight: FontWeight.w700,
          letterSpacing: -.4,
        ),
        titleLarge: TextStyle(
          color: text,
          fontSize: 18,
          height: 1.2,
          fontWeight: FontWeight.w700,
          letterSpacing: -.2,
        ),
        titleMedium: TextStyle(
          color: text,
          fontSize: 14.5,
          height: 1.25,
          fontWeight: FontWeight.w600,
        ),
        titleSmall: TextStyle(
          color: text,
          fontSize: 12.5,
          height: 1.25,
          fontWeight: FontWeight.w600,
          letterSpacing: .1,
        ),
        bodyLarge: TextStyle(
          color: text,
          fontSize: 13.5,
          height: 1.42,
          fontWeight: FontWeight.w400,
        ),
        bodyMedium: TextStyle(
          color: muted,
          fontSize: 12,
          height: 1.4,
          fontWeight: FontWeight.w400,
        ),
        bodySmall: TextStyle(
          color: muted,
          fontSize: 10.5,
          height: 1.35,
          fontWeight: FontWeight.w400,
        ),
        labelLarge: TextStyle(
          color: text,
          fontSize: 11.5,
          height: 1.2,
          fontWeight: FontWeight.w600,
          letterSpacing: .1,
        ),
        labelMedium: TextStyle(
          color: mutedStrong,
          fontSize: 10,
          height: 1.2,
          fontWeight: FontWeight.w600,
          letterSpacing: .2,
        ),
        labelSmall: TextStyle(
          color: muted,
          fontSize: 9,
          height: 1.2,
          fontWeight: FontWeight.w600,
          letterSpacing: .35,
        ),
      ),
      cardTheme: const CardThemeData(
        color: surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(10)),
          side: BorderSide(color: border),
        ),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: surfaceRaised,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: border),
        ),
        textStyle: const TextStyle(color: text, fontSize: 11),
      ),
    );
  }
}
