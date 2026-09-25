import 'package:flutter/material.dart';

/// Semantic icon roles shared by Desktop surfaces. Never use factory hues for
/// attachment actions, navigation, or runtime state.
abstract final class IlaiosIconPalette {
  static const Color web = Color(0xFF1976D2);
  static const Color media = Color(0xFF7445CC);
  static const Color software = Color(0xFFC65D13);
  static const Color application = Color(0xFF168650);
  static const Color security = Color(0xFFC62828);
  static const Color research = Color(0xFF087F9A);
  static const Color creative = Color(0xFFAA7400);
  static const Color marketing = Color(0xFF218347);
  static const Color operations = Color(0xFF6939B0);

  /// Preserve factory identity while increasing icon contrast on dark surfaces.
  static Color factory(BuildContext context, Color lightColor) {
    if (Theme.of(context).brightness != Brightness.dark) return lightColor;
    return switch (lightColor) {
      web => const Color(0xFF62ADFF),
      media => const Color(0xFFAE8AFF),
      software => const Color(0xFFFFA568),
      application => const Color(0xFF55D79A),
      security => const Color(0xFFFF6262),
      research => const Color(0xFF57C9E1),
      creative => const Color(0xFFFFCB60),
      marketing => const Color(0xFF70D9A0),
      operations => const Color(0xFFB58AFF),
      _ => lightColor,
    };
  }

  /// Attachment controls are neutral actions; the icon shape denotes file type.
  static Color attachment(BuildContext context) =>
      Theme.of(context).colorScheme.onSurfaceVariant;

  static Color navigation(BuildContext context, {bool selected = false}) =>
      selected
      ? Theme.of(context).colorScheme.onSurface
      : Theme.of(context).colorScheme.onSurfaceVariant;

  static Color success(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark
      ? const Color(0xFF52D99A)
      : const Color(0xFF137A48);
  static Color warning(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark
      ? const Color(0xFFFFCC63)
      : const Color(0xFF916000);
  static Color error(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark
      ? const Color(0xFFFF8D8D)
      : const Color(0xFFB32632);
}
