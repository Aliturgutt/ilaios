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

  // Legacy dark semantic aliases remain canonical for existing components and
  // regression tests. New/updated Desktop surfaces read Theme.of(context) so
  // they adapt correctly to the light theme.
  static const Color canvas = carbon;
  static const Color sidebar = charcoal;
  static const Color surface = charcoal;
  static const Color surfaceRaised = graphite;
  static const Color surfaceSoft = charcoal;
  static const Color border = graphite;
  static const Color borderStrong = Color(0xCC146BFF);
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
  static const Color muted = Color(0x99FFFFFF);
  static const Color mutedStrong = Color(0xCCFFFFFF);

  // Light foundation uses the same identity colors, never alternate brand
  // colors. These are semantic application surfaces only.
  static const Color lightCanvas = Color(0xFFF4F7FB);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceRaised = Color(0xFFEAF0F7);
  static const Color lightBorder = Color(0xFFD5DFEA);
  static const Color lightText = Color(0xFF0B0F14);
  static const Color lightMuted = Color(0xFF617084);

  // Semantic state colors stay separate from brand identity.
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
      surfaceContainer: isDark ? Color(0xFF151F2E) : Color(0xFFF1F5FA),
      surfaceContainerHigh: isDark ? Color(0xFF192536) : Color(0xFFEAF0F7),
      surfaceContainerHighest: raisedColor,
      outline: outlineColor,
      outlineVariant: isDark ? Color(0xFF26364B) : Color(0xFFDCE5EF),
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
      focusColor: enterpriseCyan.withValues(alpha: .18),
      hoverColor: coreBlue.withValues(alpha: .10),
      highlightColor: violet.withValues(alpha: .10),
      splashColor: enterpriseCyan.withValues(alpha: .12),
      splashFactory: InkSparkle.splashFactory,
      iconTheme: IconThemeData(color: isDark ? mutedStrong : lightMuted),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: enterpriseCyan,
        linearTrackColor: raisedColor,
        circularTrackColor: raisedColor,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? carbon : white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        hintStyle: TextStyle(color: mutedColor),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(9),
          borderSide: BorderSide(color: outlineColor),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(9),
          borderSide: const BorderSide(color: focusRing, width: 1.5),
        ),
        hoverColor: coreBlue.withValues(alpha: .08),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          foregroundColor: const WidgetStatePropertyAll(carbon),
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) {
              return enterpriseCyan.withValues(alpha: .28);
            }
            if (states.contains(WidgetState.hovered) ||
                states.contains(WidgetState.focused)) {
              return coreBlue;
            }
            return enterpriseCyan;
          }),
          overlayColor: WidgetStatePropertyAll(violet.withValues(alpha: .16)),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: ButtonStyle(
          foregroundColor: const WidgetStatePropertyAll(coreBlue),
          side: WidgetStateProperty.resolveWith(
            (states) => BorderSide(
              color: states.contains(WidgetState.hovered)
                  ? enterpriseCyan
                  : coreBlue.withValues(alpha: .72),
            ),
          ),
          overlayColor: WidgetStatePropertyAll(coreBlue.withValues(alpha: .08)),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: ButtonStyle(
          foregroundColor: const WidgetStatePropertyAll(coreBlue),
          overlayColor: WidgetStatePropertyAll(coreBlue.withValues(alpha: .08)),
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? white : foreground,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? coreBlue : raisedColor,
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
          height: 1.12,
          fontWeight: FontWeight.w700,
          letterSpacing: -.6,
        ),
        headlineMedium: TextStyle(
          color: foreground,
          fontSize: 23,
          height: 1.15,
          fontWeight: FontWeight.w700,
          letterSpacing: -.4,
        ),
        titleLarge: TextStyle(
          color: foreground,
          fontSize: 18,
          height: 1.2,
          fontWeight: FontWeight.w700,
          letterSpacing: -.2,
        ),
        titleMedium: TextStyle(
          color: foreground,
          fontSize: 14.5,
          height: 1.25,
          fontWeight: FontWeight.w600,
        ),
        titleSmall: TextStyle(
          color: foreground,
          fontSize: 12.5,
          height: 1.25,
          fontWeight: FontWeight.w600,
          letterSpacing: .1,
        ),
        bodyLarge: TextStyle(
          color: foreground,
          fontSize: 13.5,
          height: 1.42,
          fontWeight: FontWeight.w400,
        ),
        bodyMedium: TextStyle(
          color: mutedColor,
          fontSize: 12,
          height: 1.4,
          fontWeight: FontWeight.w400,
        ),
        bodySmall: TextStyle(
          color: mutedColor,
          fontSize: 10.5,
          height: 1.35,
          fontWeight: FontWeight.w400,
        ),
        labelLarge: TextStyle(
          color: foreground,
          fontSize: 11.5,
          height: 1.2,
          fontWeight: FontWeight.w600,
          letterSpacing: .1,
        ),
        labelMedium: TextStyle(
          color: isDark ? mutedStrong : Color(0xFF334155),
          fontSize: 10,
          height: 1.2,
          fontWeight: FontWeight.w600,
          letterSpacing: .2,
        ),
        labelSmall: TextStyle(
          color: mutedColor,
          fontSize: 9,
          height: 1.2,
          fontWeight: FontWeight.w600,
          letterSpacing: .35,
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
            color: isDark ? borderStrong : coreBlue.withValues(alpha: .45),
          ),
        ),
        textStyle: const TextStyle(color: white, fontSize: 11),
      ),
    );
  }
}
