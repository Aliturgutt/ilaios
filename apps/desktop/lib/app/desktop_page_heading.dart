import 'package:flutter/material.dart';

/// Shared canonical Desktop page-heading style (Evidence reference).
abstract final class DesktopPageHeading {
  static TextStyle style(BuildContext context) => Theme.of(context)
      .textTheme
      .headlineMedium!
      .copyWith(fontSize: 22, fontWeight: FontWeight.w700, height: 1.2);
}
