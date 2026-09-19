import 'package:flutter/widgets.dart';

import '../../control_plane/client.dart';
import '../../identity/identity_client.dart';

/// Narrow binding that carries the already-authorized Desktop Home callbacks
/// through the reference shell layers without giving Home any new authority.
///
/// The callback still terminates at [DesktopBootstrap], where verified account
/// sign-in and the canonical identity/control-plane boundaries remain mandatory.
class HomeRuntimeBinding extends InheritedWidget {
  const HomeRuntimeBinding({
    required this.userSession,
    required this.onPromptSubmit,
    required super.child,
    super.key,
  });

  final DesktopUserSession? userSession;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;

  static HomeRuntimeBinding? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<HomeRuntimeBinding>();

  @override
  bool updateShouldNotify(HomeRuntimeBinding oldWidget) =>
      userSession != oldWidget.userSession ||
      onPromptSubmit != oldWidget.onPromptSubmit;
}
