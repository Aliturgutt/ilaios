import 'package:flutter/material.dart';

abstract final class IlaiosTheme {
  // Premium control-center palette. Keep these tokens centralized so every
  // Desktop surface stays visually coherent and no feature invents its own
  // colors.
  static const Color canvas = Color(0xFF030A12);
  static const Color sidebar = Color(0xFF06131F);
  static const Color surface = Color(0xFF081622);
  static const Color surfaceRaised = Color(0xFF0C2030);
  static const Color surfaceSoft = Color(0xFF0A1B29);
  static const Color border = Color(0xFF173247);
  static const Color borderStrong = Color(0xFF24516A);
  static const Color primary = Color(0xFF00BFE8);
  static const Color cyan = Color(0xFF19D3F3);
  static const Color cyanSoft = Color(0xFF0B8EAF);
  static const Color text = Color(0xFFF2F7FB);
  static const Color muted = Color(0xFF8FA6B8);
  static const Color mutedStrong = Color(0xFFB5C5D1);
  static const Color success = Color(0xFF45D98B);
  static const Color warning = Color(0xFFF1BE45);
  static const Color danger = Color(0xFFFF6A78);

  static ThemeData get dark {
    final scheme = ColorScheme.fromSeed(
      seedColor: primary,
      brightness: Brightness.dark,
      surface: surface,
    );
    return ThemeData(
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: canvas,
      useMaterial3: true,
      dividerColor: border,
      splashFactory: InkSparkle.splashFactory,
      iconTheme: const IconThemeData(color: mutedStrong),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          color: text,
          fontWeight: FontWeight.w700,
          letterSpacing: -.3,
        ),
        titleLarge: TextStyle(
          color: text,
          fontWeight: FontWeight.w700,
          letterSpacing: -.2,
        ),
        titleMedium: TextStyle(color: text, fontWeight: FontWeight.w600),
        bodyLarge: TextStyle(color: text),
        bodyMedium: TextStyle(color: muted),
        labelLarge: TextStyle(color: text, fontWeight: FontWeight.w600),
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
