import 'package:flutter/material.dart';

abstract final class IlaiosTheme {
  static const Color canvas = Color(0xFF07111F);
  static const Color sidebar = Color(0xFF091827);
  static const Color surface = Color(0xFF0D1D2E);
  static const Color surfaceRaised = Color(0xFF11263A);
  static const Color border = Color(0xFF1D3850);
  static const Color primary = Color(0xFF4B7DFF);
  static const Color cyan = Color(0xFF48C7E8);
  static const Color text = Color(0xFFEAF2FA);
  static const Color muted = Color(0xFF8EA4B8);
  static const Color success = Color(0xFF45D49C);

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
      textTheme: const TextTheme(
        headlineMedium: TextStyle(color: text, fontWeight: FontWeight.w700),
        titleLarge: TextStyle(color: text, fontWeight: FontWeight.w600),
        titleMedium: TextStyle(color: text, fontWeight: FontWeight.w600),
        bodyLarge: TextStyle(color: text),
        bodyMedium: TextStyle(color: muted),
      ),
      cardTheme: const CardThemeData(
        color: surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(14)),
          side: BorderSide(color: border),
        ),
      ),
    );
  }
}
