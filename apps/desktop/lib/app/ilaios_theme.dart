import 'package:flutter/material.dart';

abstract final class IlaiosTheme {
  // Canonical ILAIOS UI foundation. Logo identity colors are reserved for
  // official raster/vector logo assets and must not be used as UI accents.
  static const Color carbon = Color(0xFF0A0A0A);
  static const Color charcoal = Color(0xFF141414);
  static const Color graphite = Color(0xFF1E1E1E);
  static const Color stone = Color(0xFF2A2A2A);
  static const Color white = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFE6E6E6);
  static const Color textTertiary = Color(0xFFB3B3B3);
  static const Color disabled = Color(0xFF808080);
  static const Color hover = Color(0xFF242424);
  static const Color active = Color(0xFF2F2F2F);

  // Reserved logo/icon identity colors. Do not bind these to controls,
  // selected states, links, borders, focus rings, charts or other UI chrome.
  static const Color logoCyan = Color(0xFF00C2D1);
  static const Color logoBlue = Color(0xFF146BFF);

  static const Color canvas = carbon;
  static const Color sidebar = charcoal;
  static const Color surface = charcoal;
  static const Color surfaceRaised = graphite;
  static const Color surfaceSoft = charcoal;
  static const Color border = stone;
  static const Color borderStrong = stone;
  static const Color primary = textSecondary;
  static const Color cyan = textSecondary;
  static const Color cyanSoft = textTertiary;
  static const Color cyanWash = hover;
  static const Color blue = textSecondary;
  static const Color blueWash = hover;
  static const Color selectiveAccent = textSecondary;
  static const Color violetWash = hover;
  static const Color focusRing = textSecondary;
  static const Color text = white;
  static const Color muted = textTertiary;
  static const Color mutedStrong = textSecondary;

  // Backward-compatible UI aliases. They intentionally resolve to neutral UI
  // values so legacy widgets cannot reintroduce reserved logo colors.
  static const Color enterpriseCyan = textSecondary;
  static const Color coreBlue = textSecondary;
  static const Color violet = textSecondary;

  static const Color lightCanvas = Color(0xFFF5F5F5);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceRaised = Color(0xFFE6E6E6);
  static const Color lightBorder = Color(0xFFB3B3B3);
  static const Color lightText = Color(0xFF0A0A0A);
  static const Color lightMuted = Color(0xFF555555);
  static const Color lightMutedStrong = Color(0xFF2A2A2A);

  // Semantic states remain monochrome in the product shell.
  static const Color success = textSecondary;
  static const Color warning = textTertiary;
  static const Color danger = white;

  static ThemeData get dark => _buildTheme(Brightness.dark);
  static ThemeData get light => _buildTheme(Brightness.light);

  static ThemeData _buildTheme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final canvasColor = isDark ? carbon : lightCanvas;
    final surfaceColor = isDark ? charcoal : lightSurface;
    final raisedColor = isDark ? graphite : lightSurfaceRaised;
    final outlineColor = isDark ? stone : lightBorder;
    final foreground = isDark ? white : lightText;
    final mutedColor = isDark ? muted : lightMuted;
    final strongSecondary = isDark ? mutedStrong : lightMutedStrong;
    final neutralPrimary = isDark ? textSecondary : lightText;

    final scheme = ColorScheme.fromSeed(
      seedColor: neutralPrimary,
      brightness: brightness,
      surface: surfaceColor,
    ).copyWith(
      primary: neutralPrimary,
      onPrimary: isDark ? carbon : white,
      secondary: strongSecondary,
      onSecondary: isDark ? carbon : white,
      tertiary: mutedColor,
      onTertiary: isDark ? carbon : white,
      surface: surfaceColor,
      onSurface: foreground,
      surfaceContainerLowest: isDark ? carbon : white,
      surfaceContainerLow: surfaceColor,
      surfaceContainer: isDark ? graphite : const Color(0xFFF0F0F0),
      surfaceContainerHigh: isDark ? stone : const Color(0xFFE6E6E6),
      surfaceContainerHighest: raisedColor,
      outline: outlineColor,
      outlineVariant: isDark ? stone : const Color(0xFFCCCCCC),
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
      focusColor: isDark ? hover : const Color(0xFFE6E6E6),
      hoverColor: isDark ? hover : const Color(0xFFF0F0F0),
      highlightColor: isDark ? active : const Color(0xFFE6E6E6),
      splashColor: neutralPrimary.withValues(alpha: .12),
      splashFactory: InkSparkle.splashFactory,
      iconTheme: IconThemeData(color: strongSecondary),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: neutralPrimary,
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
          borderSide: BorderSide(color: neutralPrimary, width: 1.5),
        ),
        hoverColor: isDark ? hover : const Color(0xFFF0F0F0),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          textStyle: const WidgetStatePropertyAll(
            TextStyle(fontSize: 14, height: 1.2, fontWeight: FontWeight.w600),
          ),
          foregroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) return mutedColor;
            return isDark ? carbon : white;
          }),
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) return raisedColor;
            if (states.contains(WidgetState.pressed)) return isDark ? active : lightMutedStrong;
            if (states.contains(WidgetState.hovered)) return isDark ? hover : lightMutedStrong;
            return neutralPrimary;
          }),
          overlayColor: const WidgetStatePropertyAll(Colors.transparent),
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
            return foreground;
          }),
          side: WidgetStateProperty.resolveWith(
            (states) => BorderSide(
              color: states.contains(WidgetState.disabled) ? outlineColor : outlineColor,
            ),
          ),
          overlayColor: WidgetStatePropertyAll(isDark ? hover : const Color(0xFFF0F0F0)),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: ButtonStyle(
          textStyle: const WidgetStatePropertyAll(
            TextStyle(fontSize: 14, height: 1.2, fontWeight: FontWeight.w600),
          ),
          foregroundColor: WidgetStatePropertyAll(foreground),
          overlayColor: WidgetStatePropertyAll(isDark ? hover : const Color(0xFFF0F0F0)),
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
          (states) => states.contains(WidgetState.selected) ? active : raisedColor,
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? neutralPrimary : null,
        ),
        checkColor: WidgetStatePropertyAll(isDark ? carbon : white),
      ),
      textTheme: TextTheme(
        headlineLarge: TextStyle(color: foreground, fontSize: 30, height: 1.15, fontWeight: FontWeight.w700, letterSpacing: -.5),
        headlineMedium: TextStyle(color: foreground, fontSize: 26, height: 1.17, fontWeight: FontWeight.w700, letterSpacing: -.35),
        titleLarge: TextStyle(color: foreground, fontSize: 20, height: 1.25, fontWeight: FontWeight.w700, letterSpacing: -.15),
        titleMedium: TextStyle(color: foreground, fontSize: 17, height: 1.3, fontWeight: FontWeight.w600),
        titleSmall: TextStyle(color: foreground, fontSize: 15, height: 1.3, fontWeight: FontWeight.w600, letterSpacing: .05),
        bodyLarge: TextStyle(color: foreground, fontSize: 15, height: 1.45, fontWeight: FontWeight.w400),
        bodyMedium: TextStyle(color: strongSecondary, fontSize: 14, height: 1.45, fontWeight: FontWeight.w400),
        bodySmall: TextStyle(color: mutedColor, fontSize: 13, height: 1.4, fontWeight: FontWeight.w400),
        labelLarge: TextStyle(color: foreground, fontSize: 14, height: 1.25, fontWeight: FontWeight.w600, letterSpacing: .05),
        labelMedium: TextStyle(color: strongSecondary, fontSize: 13, height: 1.25, fontWeight: FontWeight.w600, letterSpacing: .1),
        labelSmall: TextStyle(color: mutedColor, fontSize: 12.5, height: 1.25, fontWeight: FontWeight.w600, letterSpacing: .15),
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
          border: Border.all(color: outlineColor),
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
