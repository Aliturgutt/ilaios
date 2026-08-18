import 'dart:async';

import 'package:flutter/services.dart';

class ReferenceAssetPlatform {
  ReferenceAssetPlatform._() {
    _channel.setMethodCallHandler(_handleNativeCall);
  }

  static final ReferenceAssetPlatform instance = ReferenceAssetPlatform._();

  static const MethodChannel _channel = MethodChannel('ilaios/reference_assets');
  final StreamController<List<String>> _droppedFiles =
      StreamController<List<String>>.broadcast();

  Stream<List<String>> get droppedFiles => _droppedFiles.stream;

  Future<List<String>> pickImages() async {
    final result = await _channel.invokeMethod<List<Object?>>('pickImages');
    return _normalizePaths(result);
  }

  Future<void> _handleNativeCall(MethodCall call) async {
    if (call.method == 'filesDropped') {
      final arguments = call.arguments;
      if (arguments is List<Object?>) {
        final paths = _normalizePaths(arguments);
        if (paths.isNotEmpty) _droppedFiles.add(paths);
      }
    }
  }

  static List<String> _normalizePaths(List<Object?>? values) {
    if (values == null) return const <String>[];
    final paths = <String>[];
    for (final value in values) {
      if (value is String && value.trim().isNotEmpty) {
        paths.add(value.trim());
      }
    }
    return List<String>.unmodifiable(paths);
  }
}
