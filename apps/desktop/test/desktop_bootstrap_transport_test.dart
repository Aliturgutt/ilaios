import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_bootstrap.dart';
import 'package:ilaios_desktop/control_plane/client.dart';

class _ChangingTransport implements ControlPlaneTransport {
  int status = 200;
  String suffix = 'OLD';
  bool disconnected = false;
  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const {},
  }) async {
    if (disconnected) {
      throw const ControlPlaneClientException('Control plane is unreachable');
    }
    if (uri.path == '/health/ready') {
      return const ControlPlaneResponse(
        statusCode: 200,
        body: '{"status":"ready"}',
      );
    }
    if (status != 200) {
      return ControlPlaneResponse(statusCode: status, body: '{}');
    }
    final path = uri.path;
    final body = switch (path) {
      '/v1/events' => '{"events":[]}',
      '/v1/runtime/routes' => '{"routes":[]}',
      '/v1/agents/state' => '{"agents":[]}',
      '/v1/scheduler/state' => '{"leases":[]}',
      '/v1/grants/state' => '{"grants":[]}',
      '/v1/governance/state' =>
        '{"work":[{"request_id":"req-$suffix","title":"APPROVAL_$suffix","status":"pending"}]}',
      '/v1/evidence/verify' =>
        '{"records":[{"sequence":1,"execution_id":"OUTPUT_$suffix","artifact_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","action":"web.finished_product","previous_hash":"","record_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}]}',
      '/v1/live/events' => '{"events":[]}',
      _ => throw StateError('Unexpected request: $path'),
    };
    return ControlPlaneResponse(statusCode: 200, body: body);
  }

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const {},
  }) => throw UnimplementedError();
}

void main() {
  testWidgets(
    'HTTP client to bootstrap to Outputs and Approvals: 401, 403, disconnect, fresh reconnect',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1648, 1024));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final transport = _ChangingTransport();
      final client = ControlPlaneClient(
        baseUri: Uri.parse('http://127.0.0.1:4123'),
        token: 'test-token',
        transport: transport,
      );
      await tester.pumpWidget(
        DesktopBootstrap(config: null, controlPlaneClient: client),
      );
      await tester.pumpAndSettle();
      Future<void> refresh() async {
        tester.binding.handleAppLifecycleStateChanged(
          AppLifecycleState.resumed,
        );
        await tester.pump();
        await tester.pumpAndSettle();
      }

      await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
      await tester.pumpAndSettle();
      expect(find.text('OUTPUT_OLD'), findsWidgets);
      for (final code in <int>[401, 403]) {
        transport.status = code;
        await refresh();
        expect(find.text('OUTPUT_OLD'), findsNothing);
        expect(
          find.textContaining(
            RegExp(
              'Access to outputs was denied|Çıktılara erişim yetkisi reddedildi',
            ),
          ),
          findsOneWidget,
        );
        await tester.tap(find.byKey(const ValueKey('nav-approvals')));
        await tester.pumpAndSettle();
        expect(find.text('APPROVAL_OLD'), findsNothing);
        expect(
          find.textContaining(
            RegExp(
              'Access to approvals was denied|Onaylara erişim yetkisi reddedildi',
            ),
          ),
          findsOneWidget,
        );
        transport.status = 200;
        await refresh();
        expect(find.text('APPROVAL_OLD'), findsWidgets);
        await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
        await tester.pumpAndSettle();
      }
      transport.disconnected = true;
      await refresh();
      expect(find.text('OUTPUT_OLD'), findsNothing);
      expect(
        find.textContaining(
          RegExp(
            'Connection lost; output data cannot be verified|Bağlantı kesildi; çıktı verileri doğrulanamıyor',
          ),
        ),
        findsOneWidget,
      );
      transport.disconnected = false;
      transport.suffix = 'NEW';
      await refresh();
      expect(find.text('OUTPUT_NEW'), findsWidgets);
      expect(find.text('OUTPUT_OLD'), findsNothing);
      await tester.tap(find.byKey(const ValueKey('nav-approvals')));
      await tester.pumpAndSettle();
      expect(find.text('APPROVAL_NEW'), findsWidgets);
      expect(find.text('APPROVAL_OLD'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
}
