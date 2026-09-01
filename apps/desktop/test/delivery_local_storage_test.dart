import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/features/deliveries/delivery_local_storage.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

void main() {
  const record = EvidenceRecord(
    sequence: 7,
    executionId: 'exec:unsafe/value',
    artifactDigest:
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
    action: 'video.finished_product',
    previousHash: 'previous',
    recordHash: 'record',
  );

  test('save/delete resolver is deterministic for the same evidence record', () {
    final storage = DeliveryLocalStorage(
      environment: const <String, String>{'USERPROFILE': r'C:\Users\tester'},
      systemTemp: Directory.systemTemp,
    );

    final first = storage.resolveArtifactFile(record);
    final second = storage.resolveArtifactFile(record);

    expect(first.path, second.path);
    expect(first.path, contains('ILAIOS-exec_unsafe_value-0123456789abcdef.mp4'));
  });

  test('archive state persists across store recreation for authenticated scope', () async {
    final root = await Directory.systemTemp.createTemp('ilaios-archive-test-');
    addTearDown(() async {
      if (await root.exists()) await root.delete(recursive: true);
    });
    const session = DesktopUserSession(
      sessionId: 'session-a',
      providerId: 'google',
      principalId: 'principal-a',
      tenantId: 'tenant-a',
    );

    final first = DeliveryArchiveStore.forSession(session, stateRoot: root);
    await first.persist(<String>{record.artifactDigest});
    final recreated = DeliveryArchiveStore.forSession(session, stateRoot: root);

    expect(await recreated.load(), <String>{record.artifactDigest});
  });

  test('archive state is isolated by authenticated tenant and principal', () async {
    final root = await Directory.systemTemp.createTemp('ilaios-archive-scope-');
    addTearDown(() async {
      if (await root.exists()) await root.delete(recursive: true);
    });
    const firstSession = DesktopUserSession(
      sessionId: 'session-a',
      providerId: 'google',
      principalId: 'principal-a',
      tenantId: 'tenant-a',
    );
    const secondSession = DesktopUserSession(
      sessionId: 'session-b',
      providerId: 'google',
      principalId: 'principal-b',
      tenantId: 'tenant-a',
    );

    final first = DeliveryArchiveStore.forSession(firstSession, stateRoot: root);
    await first.persist(<String>{record.artifactDigest});
    final second = DeliveryArchiveStore.forSession(secondSession, stateRoot: root);

    expect(await second.load(), isEmpty);
    expect(first.stateFile.path, isNot(second.stateFile.path));
  });

  test('corrupt archive state fails closed instead of widening visibility', () async {
    final root = await Directory.systemTemp.createTemp('ilaios-archive-corrupt-');
    addTearDown(() async {
      if (await root.exists()) await root.delete(recursive: true);
    });
    const session = DesktopUserSession(
      sessionId: 'session-a',
      providerId: 'google',
      principalId: 'principal-a',
      tenantId: 'tenant-a',
    );
    final store = DeliveryArchiveStore.forSession(session, stateRoot: root);
    await root.create(recursive: true);
    await store.stateFile.writeAsString('{not-json', flush: true);

    expect(
      store.load,
      throwsA(isA<DeliveryArchiveStateException>()),
    );
  });

  test('cleanup only removes expired disposable payloads', () async {
    final root = await Directory.systemTemp.createTemp('ilaios-delivery-gc-');
    addTearDown(() async {
      if (await root.exists()) await root.delete(recursive: true);
    });
    final storage = DeliveryLocalStorage(
      environment: <String, String>{'LOCALAPPDATA': root.path},
      systemTemp: root,
    );
    final disposable = storage.disposableRoot;
    await disposable.create(recursive: true);
    final oldFile = File('${disposable.path}${Platform.pathSeparator}old.bin');
    final freshFile = File('${disposable.path}${Platform.pathSeparator}fresh.bin');
    await oldFile.writeAsBytes(<int>[1, 2, 3]);
    await freshFile.writeAsBytes(<int>[4, 5]);
    final now = DateTime.utc(2026, 8, 20, 16);
    await oldFile.setLastModified(now.subtract(const Duration(days: 10)));
    await freshFile.setLastModified(now.subtract(const Duration(hours: 1)));

    final report = await storage.cleanupDisposable(now: now);

    expect(report.scannedFiles, 2);
    expect(report.deletedFiles, 1);
    expect(report.deletedBytes, 3);
    expect(await oldFile.exists(), isFalse);
    expect(await freshFile.exists(), isTrue);
  });
}
