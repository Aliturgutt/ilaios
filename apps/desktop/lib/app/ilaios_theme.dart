import 'package:flutter/material.dart';

abstract final class IlaiosTheme {
  // Canonical ILAIOS brand palette.
  static const Color carbon = Color(0xFF0B0F14);
  static const Color charcoal = Color(0xFF111827);
  static const Color graphite = Color(0xFF1F2937);
  static const Color white = Color(0xFFFFFFFF);
  static const Color enterpriseCyan = Color(0xFF00C2D1);
  static const Color coreBlue = Color(0xFF146BFF);
  static const Color violet = Color(0xFF5C58FE);

  static const Color canvas = carbon;
  static const Color sidebar = charcoal;
  static const Color surface = charcoal;
  static const Color surfaceRaised = graphite;
  static const Color surfaceSoft = charcoal;
  static const Color border = graphite;
  static const Color borderStrong = Color(0xCC00C2D1);
  static const Color primary = enterpriseCyan;
  static const Color cyan = enterpriseCyan;
  static const Color cyanSoft = Color(0xB300C2D1);
  static const Color cyanWash = Color(0x2E00C2D1);
  static const Color blue = coreBlue;
  static const Color blueWash = Color(0x2B146BFF);
  static const Color selectiveAccent = violet;
  static const Color violetWash = Color(0x265C58FE);
  static const Color focusRing = Color(0xE600C2D1);
  static const Color text = white;
  static const Color muted = Color(0xC7FFFFFF);
  static const Color mutedStrong = Color(0xE6FFFFFF);

  static const Color lightCanvas = Color(0xFFF4F7FB);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceRaised = Color(0xFFEAF0F7);
  static const Color lightBorder = Color(0xFFC7D2DF);
  static const Color lightText = Color(0xFF0B0F14);
  static const Color lightMuted = Color(0xFF42526A);
  static const Color lightMutedStrong = Color(0xFF26364A);

  static const Color success = Color(0xFF45D98B);
  static const Color warning = Color(0xFFF1BE45);
  static const Color danger = Color(0xFFFF6A78);

  static ThemeData get dark => _buildTheme(Brightness.dark);
  static ThemeData get light => _buildTheme(Brightness.light);

  static ThemeData _buildTheme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final canvasColor = isDark ? carbon : lightCanvas;
    final surfaceColor = isDark ? charcoal : lightSurface;
    final raisedColor = isDark ? graphite : lightSurfaceRaised;
    final outlineColor = isDark ? graphite : lightBorder;
    final foreground = isDark ? white : lightText;
    final mutedColor = isDark ? muted : lightMuted;
    final strongSecondary = isDark ? mutedStrong : lightMutedStrong;

    final scheme = ColorScheme.fromSeed(
      seedColor: enterpriseCyan,
      brightness: brightness,
      surface: surfaceColor,
    ).copyWith(
      primary: enterpriseCyan,
      onPrimary: carbon,
      secondary: coreBlue,
      onSecondary: white,
      tertiary: violet,
      onTertiary: white,
      surface: surfaceColor,
      onSurface: foreground,
      surfaceContainerLowest: isDark ? carbon : white,
      surfaceContainerLow: surfaceColor,
      surfaceContainer: isDark ? const Color(0xFF151F2E) : const Color(0xFFF1F5FA),
      surfaceContainerHigh: isDark ? const Color(0xFF192536) : const Color(0xFFEAF0F7),
      surfaceContainerHighest: raisedColor,
      outline: outlineColor,
      outlineVariant: isDark ? const Color(0xFF26364B) : const Color(0xFFD0DAE6),
      error: danger,
      onError: carbon,
    );

    return ThemeData(
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: canvasColor,
      canvasColor: canvasColor,
      useMaterial3: true,
      fontFamily: 'Segoe UI',
      dividerColor: outlineColor,
      focusColor: cyanWash,
      hoverColor: cyanWash,
      highlightColor: violetWash,
      splashColor: enterpriseCyan.withValues(alpha: .12),
      splashFactory: InkSparkle.splashFactory,
      iconTheme: IconThemeData(color: strongSecondary),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: enterpriseCyan,
        linearTrackColor: raisedColor,
        circularTrackColor: raisedColor,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? carbon : white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        hintStyle: TextStyle(
          color: mutedColor,
          fontSize: 13.5,
          height: 1.35,
          fontWeight: FontWeight.w400,
        ),
        labelStyle: TextStyle(
          color: strongSecondary,
          fontSize: 13.5,
          height: 1.3,
          fontWeight: FontWeight.w600,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(9),
          borderSide: BorderSide(color: outlineColor),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(9),
          borderSide: const BorderSide(color: focusRing, width: 1.5),
        ),
        hoverColor: cyanWash,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          textStyle: const WidgetStatePropertyAll(
            TextStyle(fontSize: 14, height: 1.2, fontWeight: FontWeight.w600),
          ),
          foregroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) return mutedColor;
            return carbon;
          }),
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) return raisedColor;
            return enterpriseCyan;
          }),
          overlayColor: const WidgetStatePropertyAll(cyanWash),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: ButtonStyle(
          textStyle: const WidgetStatePropertyAll(
            TextStyle(fontSize: 14, height: 1.2, fontWeight: FontWeight.w600),
          ),
          foregroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) return mutedColor;
            return enterpriseCyan;
          }),
          side: WidgetStateProperty.resolveWith(
            (states) => BorderSide(
              color: states.contains(WidgetState.disabled)
                  ? outlineColor
                  : enterpriseCyan.withValues(alpha: .72),
            ),
          ),
          overlayColor: const WidgetStatePropertyAll(cyanWash),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
          ),
        ),
      ),
      textButtonTheme: const TextButtonThemeData(
        style: ButtonStyle(
          textStyle: WidgetStatePropertyAll(
            TextStyle(fontSize: 14, height: 1.2, fontWeight: FontWeight.w600),
          ),
          foregroundColor: WidgetStatePropertyAll(enterpriseCyan),
          overlayColor: WidgetStatePropertyAll(cyanWash),
        ),
      ),
      popupMenuTheme: PopupMenuThemeData(
        textStyle: TextStyle(
          color: foreground,
          fontSize: 13.5,
          height: 1.25,
          fontWeight: FontWeight.w400,
          letterSpacing: -1.75,
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? white : foreground,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? enterpriseCyan : raisedColor,
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? enterpriseCyan : null,
        ),
        checkColor: const WidgetStatePropertyAll(carbon),
      ),
      textTheme: TextTheme(
        headlineLarge: TextStyle(
          color: foreground,
          fontSize: 30,
          height: 1.15,
          fontWeight: FontWeight.w700,
          letterSpacing: -.5,
        ),
        headlineMedium: TextStyle(
          color: foreground,
          fontSize: 26,
          height: 1.17,
          fontWeight: FontWeight.w700,
          letterSpacing: -.35,
        ),
        titleLarge: TextStyle(
          color: foreground,
          fontSize: 20,
          height: 1.25,
          fontWeight: FontWeight.w700,
          letterSpacing: -.15,
        ),
        titleMedium: TextStyle(
          color: foreground,
          fontSize: 17,
          height: 1.3,
          fontWeight: FontWeight.w600,
        ),
        titleSmall: TextStyle(
          color: foreground,
          fontSize: 15,
          height: 1.3,
          fontWeight: FontWeight.w600,
          letterSpacing: .05,
        ),
        bodyLarge: TextStyle(
          color: foreground,
          fontSize: 15,
          height: 1.45,
          fontWeight: FontWeight.w400,
        ),
        bodyMedium: TextStyle(
          color: strongSecondary,
          fontSize: 14,
          height: 1.45,
          fontWeight: FontWeight.w400,
        ),
        bodySmall: TextStyle(
          color: mutedColor,
          fontSize: 13,
          height: 1.4,
          fontWeight: FontWeight.w400,
        ),
        labelLarge: TextStyle(
          color: foreground,
          fontSize: 14,
          height: 1.25,
          fontWeight: FontWeight.w600,
          letterSpacing: .05,
        ),
        labelMedium: TextStyle(
          color: strongSecondary,
          fontSize: 13,
          height: 1.25,
          fontWeight: FontWeight.w600,
          letterSpacing: .1,
        ),
        labelSmall: TextStyle(
          color: mutedColor,
          fontSize: 12.5,
          height: 1.25,
          fontWeight: FontWeight.w600,
          letterSpacing: .15,
        ),
      ),
      cardTheme: CardThemeData(
        color: surfaceColor,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: const BorderRadius.all(Radius.circular(12)),
          side: BorderSide(color: outlineColor),
        ),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: isDark ? raisedColor : lightText,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(
            color: enterpriseCyan.withValues(alpha: .45),
          ),
        ),
        textStyle: const TextStyle(
          color: white,
          fontSize: 12.5,
          height: 1.25,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}
