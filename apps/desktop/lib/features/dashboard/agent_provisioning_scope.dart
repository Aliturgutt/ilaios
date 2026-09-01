import 'package:flutter/widgets.dart';

typedef CanonicalAgentProvisioner = Future<void> Function(String agentId);

/// Carries the already-governed Desktop provisioning callback through the
/// presentation shell without exposing transport credentials or authority
/// fields to the Agents surface.
class AgentProvisioningScope extends InheritedWidget {
  const AgentProvisioningScope({
    required super.child,
    required this.onProvisionAgent,
    super.key,
  });

  final CanonicalAgentProvisioner? onProvisionAgent;

  static CanonicalAgentProvisioner? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AgentProvisioningScope>()
          ?.onProvisionAgent;

  @override
  bool updateShouldNotify(AgentProvisioningScope oldWidget) =>
      oldWidget.onProvisionAgent != onProvisionAgent;
}
