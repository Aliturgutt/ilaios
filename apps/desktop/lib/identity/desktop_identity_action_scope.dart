import 'package:flutter/widgets.dart';

/// Carries the DesktopBootstrap-owned identity actions through legacy/reference
/// shell layers without creating a second authentication implementation.
///
/// The callbacks remain optional and consumers must fail closed when absent.
class DesktopIdentityActionScope extends InheritedWidget {
  const DesktopIdentityActionScope({
    required this.onSignIn,
    required this.onLogout,
    required super.child,
    super.key,
  });

  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;

  static DesktopIdentityActionScope? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<DesktopIdentityActionScope>();

  @override
  bool updateShouldNotify(DesktopIdentityActionScope oldWidget) =>
      oldWidget.onSignIn != onSignIn || oldWidget.onLogout != onLogout;
}
