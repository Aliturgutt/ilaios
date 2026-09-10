import '../../identity/identity_client.dart';
import 'agent_runtime_status.dart';

enum PixelAgentView { front, rear }

enum PixelAgentMotion { idle, working, waiting, offline }

const pixelAgentTeams = <String>{
  'core',
  'engineering',
  'security',
  'web',
  'media',
  'intelligence',
  'operations',
  'meta',
};

PixelAgentMotion pixelMotionForRuntimeState(AgentRuntimeDisplayState state) =>
    switch (state) {
      AgentRuntimeDisplayState.working => PixelAgentMotion.working,
      AgentRuntimeDisplayState.waiting => PixelAgentMotion.waiting,
      AgentRuntimeDisplayState.idle || AgentRuntimeDisplayState.active =>
        PixelAgentMotion.idle,
      AgentRuntimeDisplayState.offline => PixelAgentMotion.offline,
    };

int pixelFrameCount(PixelAgentMotion motion) =>
    motion == PixelAgentMotion.offline ? 1 : 4;

String? pixelAgentAssetPath({
  required String team,
  required PixelAgentView view,
  required PixelAgentMotion motion,
  required int frame,
}) {
  final normalizedTeam = team.trim().toLowerCase();
  if (!pixelAgentTeams.contains(normalizedTeam)) return null;
  final count = pixelFrameCount(motion);
  if (frame < 1 || frame > count) return null;
  final frameName = frame.toString().padLeft(2, '0');
  return 'assets/pixel_agents/$normalizedTeam/${view.name}/${motion.name}/$frameName.png';
}

/// Presentation-only operator label. It never changes identity authority.
String desktopOperatorLabel(
  DesktopUserSession? session, {
  String fallback = 'Sistem Koordinatörü',
}) {
  if (session == null) return fallback;
  final raw = session.displayIdentity?.trim();
  if (raw == null || raw.isEmpty) return fallback;
  final at = raw.indexOf('@');
  if (at > 0) {
    final localPart = raw.substring(0, at).trim();
    if (localPart.isNotEmpty) return localPart;
  }
  return raw;
}
