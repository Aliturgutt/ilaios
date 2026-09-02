import 'package:flutter/material.dart';

abstract final class IlaiosTheme {
  // Canonical ILAIOS dark UI neutrals. Logo colors are identity-only.
  static const Color carbon = Color(0xFF0A0A0A);
  static const Color charcoal = Color(0xFF141414);
  static const Color graphite = Color(0xFF1E1E1E);
  static const Color stone = Color(0xFF2A2A2A);
  static const Color white = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFE6E6E6);
  static const Color textTertiary = Color(0xFFB3B3B3);
  static const Color textDisabled = Color(0xFF808080);
  static const Color surfaceHover = Color(0xFF242424);
  static const Color surfaceActive = Color(0xFF2F2F2F);

  // Reserved ILAIOS identity colors: logo/symbol/icon identity only.
  static const Color enterpriseCyan = Color(0xFF00C2D1);
  static const Color coreBlue = Color(0xFF146BFF);

  // Legacy aliases remain for source compatibility, but resolve to neutrals
  // so existing UI call sites cannot introduce non-canonical dark accents.
  static const Color violet = textTertiary;
  static const Color canvas = carbon;
  static const Color sidebar = charcoal;
  static const Color surface = charcoal;
  static const Color surfaceRaised = graphite;
  static const Color surfaceSoft = charcoal;
  static const Color border = graphite;
  static const Color borderStrong = stone;
  static const Color primary = white;
  static const Color cyan = textSecondary;
  static const Color cyanSoft = textTertiary;
  static const Color cyanWash = surfaceHover;
  static const Color blue = textSecondary;
  static const Color blueWash = surfaceHover;
  static const Color selectiveAccent = textSecondary;
  static const Color violetWash = surfaceHover;
  static const Color focusRing = white;
  static const Color text = white;
  static const Color muted = textTertiary;
  static const Color mutedStrong = textSecondary;

  static const Color lightCanvas = Color(0xFFF4F7FB);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceRaised = Color(0xFFEAF0F7);
  static const Color lightBorder = Color(0xFFC7D2DF);
  static const Color lightText = Color(0xFF0B0F14);
  static const Color lightMuted = Color(0xFF42526A);
  static const Color lightMutedStrong = Color(0xFF26364A);

  // Semantic aliases are neutral in the Desktop visual layer. Meaning must
  // remain available through labels/icons rather than hue alone.
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
    final mutedColor = isDark ? textTertiary : lightMuted;
    final strongSecondary = isDark ? textSecondary : lightMutedStrong;

    final scheme = ColorScheme.fromSeed(
      seedColor: isDark ? white : coreBlue,
      brightness: brightness,
      surface: surfaceColor,
    ).copyWith(
      primary: isDark ? white : coreBlue,
      onPrimary: isDark ? carbon : white,
      secondary: isDark ? textSecondary : coreBlue,
      onSecondary: isDark ? carbon : white,
      tertiary: isDark ? textTertiary : coreBlue,
      onTertiary: isDark ? carbon : white,
      surface: surfaceColor,
      onSurface: foreground,
      surfaceContainerLowest: isDark ? carbon : white,
      surfaceContainerLow: surfaceColor,
      surfaceContainer: isDark ? graphite : const Color(0xFFF1F5FA),
      surfaceContainerHigh: isDark ? surfaceHover : const Color(0xFFEAF0F7),
      surfaceContainerHighest: isDark ? surfaceActive : raisedColor,
      outline: outlineColor,
      outlineVariant: isDark ? graphite : const Color(0xFFD0DAE6),
      error: isDark ? white : const Color(0xFFB3261E),
      onError: isDark ? carbon : white,
    );

    return ThemeData(
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: canvasColor,
      canvasColor: canvasColor,
      useMaterial3: true,
      fontFamily: 'Segoe UI',
      dividerColor: outlineColor,
      focusColor: isDark ? surfaceActive : coreBlue.withValues(alpha: .10),
      hoverColor: isDark ? surfaceHover : coreBlue.withValues(alpha: .08),
      highlightColor: isDark ? surfaceActive : coreBlue.withValues(alpha: .10),
      splashColor: isDark ? surfaceActive : coreBlue.withValues(alpha: .12),
      splashFactory: InkSparkle.splashFactory,
      disabledColor: isDark ? textDisabled : lightMuted,
      iconTheme: IconThemeData(color: strongSecondary),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: isDark ? white : coreBlue,
        linearTrackColor: raisedColor,
        circularTrackColor: raisedColor,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? carbon : white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        hintStyle: TextStyle(color: mutedColor, fontSize: 13.5, height: 1.35),
        labelStyle: TextStyle(color: strongSecondary, fontSize: 13.5, height: 1.3, fontWeight: FontWeight.w600),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(9), borderSide: BorderSide(color: outlineColor)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(9), borderSide: BorderSide(color: isDark ? white : coreBlue, width: 1.5)),
        hoverColor: isDark ? surfaceHover : coreBlue.withValues(alpha: .08),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          textStyle: const WidgetStatePropertyAll(TextStyle(fontSize: 14, height: 1.2, fontWeight: FontWeight.w600)),
          foregroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) return textDisabled;
            return isDark ? carbon : white;
          }),
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) return raisedColor;
            if (states.contains(WidgetState.pressed)) return isDark ? textSecondary : coreBlue;
            return isDark ? white : coreBlue;
          }),
          overlayColor: WidgetStatePropertyAll(isDark ? surfaceHover : coreBlue.withValues(alpha: .10)),
          shape: WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.circular(9))),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: ButtonStyle(
          textStyle: const WidgetStatePropertyAll(TextStyle(fontSize: 14, height: 1.2, fontWeight: FontWeight.w600)),
          foregroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) return textDisabled;
            return isDark ? textSecondary : coreBlue;
          }),
          side: WidgetStateProperty.resolveWith((states) => BorderSide(color: states.contains(WidgetState.disabled) ? outlineColor : (isDark ? stone : coreBlue))),
          overlayColor: WidgetStatePropertyAll(isDark ? surfaceHover : coreBlue.withValues(alpha: .08)),
          shape: WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.circular(9))),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: ButtonStyle(
          textStyle: const WidgetStatePropertyAll(TextStyle(fontSize: 14, height: 1.2, fontWeight: FontWeight.w600)),
          foregroundColor: WidgetStatePropertyAll(isDark ? textSecondary : coreBlue),
          overlayColor: WidgetStatePropertyAll(isDark ? surfaceHover : coreBlue.withValues(alpha: .08)),
        ),
      ),
      popupMenuTheme: PopupMenuThemeData(
        textStyle: TextStyle(color: foreground, fontSize: 13.5, height: 1.25, fontWeight: FontWeight.w400, letterSpacing: -1.75),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) => states.contains(WidgetState.selected) ? (isDark ? carbon : white) : foreground),
        trackColor: WidgetStateProperty.resolveWith((states) => states.contains(WidgetState.selected) ? (isDark ? white : coreBlue) : raisedColor),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) => states.contains(WidgetState.selected) ? (isDark ? white : coreBlue) : null),
        checkColor: WidgetStatePropertyAll(isDark ? carbon : white),
      ),
      textTheme: TextTheme(
        headlineLarge: TextStyle(color: foreground, fontSize: 30, height: 1.15, fontWeight: FontWeight.w700, letterSpacing: -.5),
        headlineMedium: TextStyle(color: foreground, fontSize: 26, height: 1.17, fontWeight: FontWeight.w700, letterSpacing: -.35),
        titleLarge: TextStyle(color: foreground, fontSize: 20, height: 1.25, fontWeight: FontWeight.w700, letterSpacing: -.15),
        titleMedium: TextStyle(color: foreground, fontSize: 17, height: 1.3, fontWeight: FontWeight.w600),
        titleSmall: TextStyle(color: foreground, fontSize: 15, height: 1.3, fontWeight: FontWeight.w600, letterSpacing: .05),
        bodyLarge: TextStyle(color: foreground, fontSize: 15, height: 1.45),
        bodyMedium: TextStyle(color: strongSecondary, fontSize: 14, height: 1.45),
        bodySmall: TextStyle(color: mutedColor, fontSize: 13, height: 1.4),
        labelLarge: TextStyle(color: foreground, fontSize: 14, height: 1.25, fontWeight: FontWeight.w600, letterSpacing: .05),
        labelMedium: TextStyle(color: strongSecondary, fontSize: 13, height: 1.25, fontWeight: FontWeight.w600, letterSpacing: .1),
        labelSmall: TextStyle(color: mutedColor, fontSize: 12.5, height: 1.25, fontWeight: FontWeight.w600, letterSpacing: .15),
      ),
      cardTheme: CardThemeData(
        color: surfaceColor,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(borderRadius: const BorderRadius.all(Radius.circular(12)), side: BorderSide(color: outlineColor)),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(color: isDark ? raisedColor : lightText, borderRadius: BorderRadius.circular(7), border: Border.all(color: outlineColor)),
        textStyle: const TextStyle(color: white, fontSize: 12.5, height: 1.25, fontWeight: FontWeight.w500),
      ),
    );
  }
}
