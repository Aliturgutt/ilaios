import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/dashboard/pixel_agent_presentation.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

void main() {
  test('login logout and user switch never retain stale operator identity', () {
    const first = DesktopUserSession(
      sessionId: 'session-a',
      providerId: 'google',
      principalId: 'user-a',
      tenantId: 'tenant-a',
      displayIdentity: 'first@example.com',
    );
    const second = DesktopUserSession(
      sessionId: 'session-b',
      providerId: 'google',
      principalId: 'user-b',
      tenantId: 'tenant-b',
      displayIdentity: 'Second User',
    );

    expect(desktopOperatorLabel(first), 'first');
    expect(desktopOperatorLabel(null), 'Sistem Koordinatörü');
    expect(desktopOperatorLabel(second), 'Second User');
  });

  test('session ids principals and tenant ids are never used as display fallback', () {
    const session = DesktopUserSession(
      sessionId: 'secret-session-shape',
      providerId: 'google',
      principalId: 'usr-internal',
      tenantId: 'tenant-internal',
    );
    final label = desktopOperatorLabel(session);
    expect(label, 'Sistem Koordinatörü');
    expect(label, isNot(contains(session.sessionId)));
    expect(label, isNot(contains(session.principalId)));
    expect(label, isNot(contains(session.tenantId)));
  });
}
