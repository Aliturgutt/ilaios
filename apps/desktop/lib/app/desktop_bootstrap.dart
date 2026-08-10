import 'package:flutter/material.dart';

import '../control_plane/client.dart';
import '../control_plane/config.dart';
import '../control_plane/projection.dart';
import 'desktop_app.dart';

class DesktopBootstrap extends StatefulWidget {
  const DesktopBootstrap({required this.config, super.key});

  final ControlPlaneConfig? config;

  @override
  State<DesktopBootstrap> createState() => _DesktopBootstrapState();
}

class _DesktopBootstrapState extends State<DesktopBootstrap> {
  ControlPlaneProjection _projection = const ControlPlaneProjection.unavailable();
  ControlPlaneClient? _client;

  @override
  void initState() {
    super.initState();
    final config = widget.config;
    if (config == null) {
      return;
    }
    try {
      _client = ControlPlaneClient(baseUri: config.baseUri, token: config.token);
      _refresh();
    } on ArgumentError {
      _projection = const ControlPlaneProjection.unavailable(
        status: 'Control plane configuration rejected',
      );
    }
  }

  Future<void> _refresh() async {
    final client = _client;
    if (client == null) {
      return;
    }
    try {
      final projection = await client.fetchProjection();
      if (!mounted) {
        return;
      }
      setState(() => _projection = projection);
    } on ControlPlaneClientException catch (error) {
      if (!mounted) {
        return;
      }
      setState(
        () => _projection = ControlPlaneProjection.unavailable(
          status: error.message,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return IlaiosDesktopApp(
      projection: _projection,
      onRefreshRequested: _client == null ? null : _refresh,
    );
  }
}
