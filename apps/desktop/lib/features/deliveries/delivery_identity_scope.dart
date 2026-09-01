import 'package:flutter/widgets.dart';

import '../../identity/identity_client.dart';
export '../../identity/identity_client.dart' show DesktopUserSession;

class DeliveryIdentityScope extends InheritedWidget {
  const DeliveryIdentityScope({
    required this.session,
    required super.child,
    super.key,
  });

  final DesktopUserSession? session;

  static DesktopUserSession? maybeSessionOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<DeliveryIdentityScope>()?.session;

  @override
  bool updateShouldNotify(DeliveryIdentityScope oldWidget) =>
      oldWidget.session?.sessionId != session?.sessionId ||
      oldWidget.session?.tenantId != session?.tenantId ||
      oldWidget.session?.principalId != session?.principalId ||
      oldWidget.session?.providerId != session?.providerId;
}
