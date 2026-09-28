import 'package:flutter/widgets.dart';

typedef CanonicalAgentProvisioner = Future<void> Function(String agentId);
typedef GovernedAgentAssigner =
    Future<String> Function(String agentId, String objective);

/// Carries the already-governed Desktop provisioning callback through the
/// presentation shell without exposing transport credentials or authority
/// fields to the Agents surface.
class AgentProvisioningScope extends InheritedWidget {
  const AgentProvisioningScope({
    required super.child,
    required this.onProvisionAgent,
    this.onAssignAgent,
    this.readyAgentIds = const <String>{},
    super.key,
  });

  final CanonicalAgentProvisioner? onProvisionAgent;
  final GovernedAgentAssigner? onAssignAgent;
  final Set<String> readyAgentIds;
  static bool readyFor(BuildContext context, String agentId) =>
      context
          .dependOnInheritedWidgetOfExactType<AgentProvisioningScope>()
          ?.readyAgentIds
          .contains(agentId) ??
      false;

  static GovernedAgentAssigner? assignerOf(BuildContext context) => context
      .dependOnInheritedWidgetOfExactType<AgentProvisioningScope>()
      ?.onAssignAgent;

  static CanonicalAgentProvisioner? maybeOf(BuildContext context) => context
      .dependOnInheritedWidgetOfExactType<AgentProvisioningScope>()
      ?.onProvisionAgent;

  @override
  bool updateShouldNotify(AgentProvisioningScope oldWidget) =>
      oldWidget.onProvisionAgent != onProvisionAgent ||
      oldWidget.onAssignAgent != onAssignAgent ||
      oldWidget.readyAgentIds != readyAgentIds;
}
