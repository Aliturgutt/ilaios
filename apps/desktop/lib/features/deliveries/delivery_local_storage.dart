import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

import '../../control_plane/evidence_record.dart';
import '../../identity/identity_client.dart';

class DeliveryLocalStorage {
  DeliveryLocalStorage({
    Map<String, String>? environment,
    Directory? systemTemp,
  })  : _environment = environment ?? Platform.environment,
        _systemTemp = systemTemp ?? Directory.systemTemp;

  final Map<String, String> _environment;
  final Directory _systemTemp;

  Directory get deliveryRoot {
    final userProfile = _environment['USERPROFILE']?.trim();
    final localAppData = _environment['LOCALAPPDATA']?.trim();
    final separator = Platform.pathSeparator;
    if (userProfile?.isNotEmpty == true) {
      return Directory('$userProfile${separator}Downloads${separator}ILAIOS');
    }
    if (localAppData?.isNotEmpty == true) {
      return Directory(
        '$localAppData${separator}ILAIOS${separator}Deliveries',
      );
    }
    return Directory(
      '${_systemTemp.path}${separator}ILAIOS${separator}Deliveries',
    );
  }

  Directory get disposableRoot {
    final localAppData = _environment['LOCALAPPDATA']?.trim();
    final separator = Platform.pathSeparator;
    if (localAppData?.isNotEmpty == true) {
      return Directory(
        '$localAppData${separator}ILAIOS${separator}Deliveries${separator}disposable',
      );
    }
    return Directory(
      '${_systemTemp.path}${separator}ILAIOS${separator}Deliveries${separator}disposable',
    );
  }

  File resolveArtifactFile(EvidenceRecord record) {
    final separator = Platform.pathSeparator;
    final safeExecution =
        record.executionId.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
    final extension =
        record.action.toLowerCase().contains('video') ? '.mp4' : '.bin';
    final digestPrefix = record.artifactDigest.length <= 16
        ? record.artifactDigest
        : record.artifactDigest.substring(0, 16);
    return File(
      '${deliveryRoot.path}$separator'
      'ILAIOS-$safeExecution-$digestPrefix$extension',
    );
  }

  DeliveryStorageSummary summarize(Iterable<EvidenceRecord> records) {
    var count = 0;
    var bytes = 0;
    for (final record in records) {
      final file = resolveArtifactFile(record);
      try {
        if (!file.existsSync()) continue;
        count += 1;
        bytes += file.lengthSync();
      } on FileSystemException {
        // Local storage telemetry is best-effort only and never changes
        // authoritative evidence truth.
      }
    }
    return DeliveryStorageSummary(count: count, bytes: bytes);
  }

  Future<DeliveryCleanupReport> cleanupDisposable({
    Duration retention = const Duration(days: 7),
    DateTime? now,
  }) async {
    final root = disposableRoot;
    if (!await root.exists()) {
      return const DeliveryCleanupReport(
        scannedFiles: 0,
        deletedFiles: 0,
        deletedBytes: 0,
      );
    }

    final cutoff = (now ?? DateTime.now().toUtc()).subtract(retention);
    var scannedFiles = 0;
    var deletedFiles = 0;
    var deletedBytes = 0;
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is! File) continue;
      scannedFiles += 1;
      try {
        final stat = await entity.stat();
        if (!stat.modified.toUtc().isBefore(cutoff)) continue;
        final size = stat.size;
        await entity.delete();
        deletedFiles += 1;
        deletedBytes += size;
      } on FileSystemException {
        // Cleanup is bounded to disposable payloads and fails per-file without
        // widening into saved deliveries or evidence metadata.
      }
    }
    return DeliveryCleanupReport(
      scannedFiles: scannedFiles,
      deletedFiles: deletedFiles,
      deletedBytes: deletedBytes,
    );
  }
}

class DeliveryStorageSummary {
  const DeliveryStorageSummary({required this.count, required this.bytes});

  final int count;
  final int bytes;
}

class DeliveryCleanupReport {
  const DeliveryCleanupReport({
    required this.scannedFiles,
    required this.deletedFiles,
    required this.deletedBytes,
  });

  final int scannedFiles;
  final int deletedFiles;
  final int deletedBytes;
}

class DeliveryArchiveStateException implements Exception {
  const DeliveryArchiveStateException(this.message);

  final String message;

  @override
  String toString() => 'DeliveryArchiveStateException: $message';
}

class DeliveryArchiveStore {
  DeliveryArchiveStore._({
    required String scopeMaterial,
    required this._environment,
    required this._systemTemp,
    Directory? stateRoot,
  })  : _scopeDigest = sha256.convert(utf8.encode(scopeMaterial)).toString(),
        _stateRootOverride = stateRoot;

  factory DeliveryArchiveStore.forSession(
    DesktopUserSession session, {
    Map<String, String>? environment,
    Directory? systemTemp,
    Directory? stateRoot,
  }) {
    final tenant = session.tenantId.trim();
    final principal = session.principalId.trim();
    final provider = session.providerId.trim();
    if (tenant.isEmpty || principal.isEmpty || provider.isEmpty) {
      throw const DeliveryArchiveStateException(
        'Authenticated archive scope is incomplete',
      );
    }
    return DeliveryArchiveStore._(
      scopeMaterial: '$tenant\u0000$principal\u0000$provider',
      environment: environment ?? Platform.environment,
      systemTemp: systemTemp ?? Directory.systemTemp,
      stateRoot: stateRoot,
    );
  }

  final String _scopeDigest;
  final Map<String, String> _environment;
  final Directory _systemTemp;
  final Directory? _stateRootOverride;

  Directory get stateRoot {
    final override = _stateRootOverride;
    if (override != null) return override;
    final localAppData = _environment['LOCALAPPDATA']?.trim();
    final separator = Platform.pathSeparator;
    if (localAppData?.isNotEmpty == true) {
      return Directory(
        '$localAppData${separator}ILAIOS${separator}DesktopState',
      );
    }
    return Directory(
      '${_systemTemp.path}${separator}ILAIOS${separator}DesktopState',
    );
  }

  File get stateFile {
    final separator = Platform.pathSeparator;
    return File(
      '${stateRoot.path}$separator'
      'delivery_archive_${_scopeDigest.substring(0, 32)}.json',
    );
  }

  Future<Set<String>> load() async {
    final file = stateFile;
    if (!await file.exists()) return <String>{};
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! Map<String, dynamic> || decoded['version'] != 1) {
        throw const DeliveryArchiveStateException(
          'Delivery archive state is malformed',
        );
      }
      if (decoded['scope_digest'] != _scopeDigest) {
        throw const DeliveryArchiveStateException(
          'Delivery archive state belongs to another authenticated scope',
        );
      }
      final rawDigests = decoded['archived_digests'];
      if (rawDigests is! List<dynamic>) {
        throw const DeliveryArchiveStateException(
          'Delivery archive digest list is malformed',
        );
      }
      final result = <String>{};
      for (final value in rawDigests) {
        if (value is! String || value.isEmpty || value.length > 256) {
          throw const DeliveryArchiveStateException(
            'Delivery archive digest entry is malformed',
          );
        }
        result.add(value);
      }
      return result;
    } on DeliveryArchiveStateException {
      rethrow;
    } on Object {
      throw const DeliveryArchiveStateException(
        'Delivery archive state is unreadable',
      );
    }
  }

  Future<void> persist(Set<String> archivedDigests) async {
    for (final digest in archivedDigests) {
      if (digest.isEmpty || digest.length > 256) {
        throw const DeliveryArchiveStateException(
          'Refusing to persist malformed delivery archive state',
        );
      }
    }
    final root = stateRoot;
    await root.create(recursive: true);
    final file = stateFile;
    final temp = File('${file.path}.tmp');
    final payload = jsonEncode(<String, Object?>{
      'version': 1,
      'scope_digest': _scopeDigest,
      'archived_digests': archivedDigests.toList(growable: false)..sort(),
    });
    try {
      await temp.writeAsString(payload, flush: true);
      if (await file.exists()) await file.delete();
      await temp.rename(file.path);
    } on FileSystemException catch (error) {
      try {
        if (await temp.exists()) await temp.delete();
      } on FileSystemException {
        // Preserve the original persistence failure.
      }
      throw DeliveryArchiveStateException(
        'Delivery archive state could not be persisted: ${error.message}',
      );
    }
  }
}
