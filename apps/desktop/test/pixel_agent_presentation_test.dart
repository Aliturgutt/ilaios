import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/dashboard/agent_runtime_status.dart';
import 'package:ilaios_desktop/features/dashboard/pixel_agent_presentation.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

void main() {
  test('runtime state maps deterministically to real pixel motion', () {
    expect(
      pixelMotionForRuntimeState(AgentRuntimeDisplayState.working),
      PixelAgentMotion.working,
    );
    expect(
      pixelMotionForRuntimeState(AgentRuntimeDisplayState.waiting),
      PixelAgentMotion.waiting,
    );
    expect(
      pixelMotionForRuntimeState(AgentRuntimeDisplayState.idle),
      PixelAgentMotion.idle,
    );
    expect(
      pixelMotionForRuntimeState(AgentRuntimeDisplayState.active),
      PixelAgentMotion.idle,
    );
    expect(
      pixelMotionForRuntimeState(AgentRuntimeDisplayState.offline),
      PixelAgentMotion.offline,
    );
  });

  test('manifest-backed frame contract never fabricates missing frames', () {
    for (final team in pixelAgentTeams) {
      for (final view in PixelAgentView.values) {
        for (final motion in PixelAgentMotion.values) {
          final frameCount = pixelFrameCount(motion);
          expect(frameCount, motion == PixelAgentMotion.offline ? 1 : 4);
          for (var frame = 1; frame <= frameCount; frame++) {
            expect(
              pixelAgentAssetPath(
                team: team,
                view: view,
                motion: motion,
                frame: frame,
              ),
              'assets/pixel_agents/$team/${view.name}/${motion.name}/${frame.toString().padLeft(2, '0')}.png',
            );
          }
          expect(
            pixelAgentAssetPath(
              team: team,
              view: view,
              motion: motion,
              frame: frameCount + 1,
            ),
            isNull,
          );
        }
      }
    }
    expect(
      pixelAgentAssetPath(
        team: 'invented',
        view: PixelAgentView.front,
        motion: PixelAgentMotion.working,
        frame: 1,
      ),
      isNull,
    );
  });

  test('operator label uses canonical session display identity only', () {
    expect(desktopOperatorLabel(null), 'Sistem Koordinatörü');

    const emailSession = DesktopUserSession(
      sessionId: 'ses-1',
      providerId: 'google',
      principalId: 'usr-1',
      tenantId: 'tenant-a',
      displayIdentity: 'operator@example.com',
    );
    expect(desktopOperatorLabel(emailSession), 'operator');

    const namedSession = DesktopUserSession(
      sessionId: 'ses-2',
      providerId: 'google',
      principalId: 'usr-2',
      tenantId: 'tenant-b',
      displayIdentity: 'Verified Operator',
    );
    expect(desktopOperatorLabel(namedSession), 'Verified Operator');

    const missingDisplay = DesktopUserSession(
      sessionId: 'ses-3',
      providerId: 'google',
      principalId: 'usr-3',
      tenantId: 'tenant-c',
    );
    expect(desktopOperatorLabel(missingDisplay), 'Sistem Koordinatörü');
  });
}
