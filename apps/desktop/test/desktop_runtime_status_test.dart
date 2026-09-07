import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/presentation/desktop_runtime_status.dart';

void main() {
  group('presentDesktopRuntimeStatus', () {
    test('local control-plane startup failure is concise in Turkish', () {
      const raw =
          'Bundled local control plane failed to start: DesktopRuntimeException: Bundled local control plane did not become identity-ready';

      final status = presentDesktopRuntimeStatus(
        raw,
        connected: false,
        turkish: true,
      );

      expect(status.kind, DesktopRuntimeStatusKind.localControlPlaneFailure);
      expect(status.label, 'Yerel kontrol düzlemine bağlanılamadı.');
      expect(status.detail, raw);
    });

    test('local control-plane startup failure is concise in English', () {
      const raw = 'Bundled local control plane failed to start: socket failure';

      final status = presentDesktopRuntimeStatus(
        raw,
        connected: false,
        turkish: false,
      );

      expect(status.kind, DesktopRuntimeStatusKind.localControlPlaneFailure);
      expect(status.label, 'Could not connect to the local control plane.');
      expect(status.detail, raw);
    });

    test('missing bundled runtime is localized in Turkish', () {
      const raw = 'Bundled ILAIOS control plane is not present in this build';

      final status = presentDesktopRuntimeStatus(
        raw,
        connected: false,
        turkish: true,
      );

      expect(status.kind, DesktopRuntimeStatusKind.unavailable);
      expect(status.label, 'Bu derlemede yerel kontrol düzlemi kullanılamıyor.');
      expect(status.detail, raw);
    });

    test('known unreachable control plane is localized in Turkish', () {
      const raw = 'Control plane is unreachable';

      final status = presentDesktopRuntimeStatus(
        raw,
        connected: false,
        turkish: true,
      );

      expect(status.kind, DesktopRuntimeStatusKind.offline);
      expect(status.label, 'Kontrol düzlemine ulaşılamıyor.');
      expect(status.detail, raw);
    });

    test('known healthy local runtime has a distinct connected status', () {
      final status = presentDesktopRuntimeStatus(
        'Bundled local control plane started',
        connected: true,
        turkish: true,
      );

      expect(status.kind, DesktopRuntimeStatusKind.connected);
      expect(status.label, 'Yerel kontrol düzlemi bağlı.');
    });

    test('execution coordinator status does not leak raw English in Turkish', () {
      const raw = 'Execution coordinator accepted the work item';

      final status = presentDesktopRuntimeStatus(
        raw,
        connected: true,
        turkish: true,
      );

      expect(status.kind, DesktopRuntimeStatusKind.unknown);
      expect(status.label, 'İş yürütme durumu güncellendi.');
      expect(status.detail, raw);
    });

    test('blocked execution coordinator status stays truthful in Turkish', () {
      const raw = 'Execution coordinator blocked the work item';

      final status = presentDesktopRuntimeStatus(
        raw,
        connected: true,
        turkish: true,
      );

      expect(status.kind, DesktopRuntimeStatusKind.unavailable);
      expect(status.label, 'İş yürütmesi engellendi.');
      expect(status.detail, raw);
    });

    test('evidence status does not leak raw English in Turkish', () {
      const raw = 'Evidence record updated';

      final status = presentDesktopRuntimeStatus(
        raw,
        connected: true,
        turkish: true,
      );

      expect(status.kind, DesktopRuntimeStatusKind.unknown);
      expect(status.label, 'Kanıt durumu güncellendi.');
      expect(status.detail, raw);
    });

    test('unknown authoritative status is never rewritten into a false state', () {
      const raw = 'Provider-specific degraded state';

      final status = presentDesktopRuntimeStatus(
        raw,
        connected: true,
        turkish: true,
      );

      expect(status.kind, DesktopRuntimeStatusKind.unknown);
      expect(status.label, raw);
      expect(status.detail, raw);
    });
  });
}
