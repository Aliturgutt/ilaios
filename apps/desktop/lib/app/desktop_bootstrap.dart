import 'dart:io';

import 'package:flutter/material.dart';

import '../control_plane/client.dart';
import '../control_plane/config.dart';
import '../control_plane/evidence_record.dart';
import '../control_plane/local_runtime.dart';
import '../control_plane/operational_snapshot.dart';
import '../control_plane/projection.dart';
import 'desktop_app.dart';

class DesktopBootstrap extends StatefulWidget {
  const DesktopBootstrap({
    required this.config,
    this.runtime,
    super.key,
  });

  final ControlPlaneConfig? config;
  final DesktopRuntime? runtime;

  @override
  State<DesktopBootstrap> createState() => _DesktopBootstrapState();
}

class _DesktopBootstrapState extends State<DesktopBootstrap> {
  ControlPlaneProjection _projection = const ControlPlaneProjection.unavailable();
  OperationalSnapshot _operationalSnapshot =
      const OperationalSnapshot.unavailable();
  String _operationalStatus = 'Operational APIs not connected';
  ControlPlaneClient? _client;
  int _lastLiveSequence = 0;
  bool _refreshing = false;

  @override
  void initState() {
    super.initState();
    final config = widget.config;
    if (config == null) {
      _operationalStatus =
          widget.runtime?.status ?? 'Control plane configuration unavailable';
      return;
    }
    try {
      _client = ControlPlaneClient(baseUri: config.baseUri, token: config.token);
      _operationalStatus = widget.runtime?.status ?? 'Control plane configured';
      _refresh();
    } on ArgumentError {
      _projection = const ControlPlaneProjection.unavailable(
        status: 'Control plane configuration rejected',
      );
      _operationalStatus = 'Control plane configuration rejected';
    }
  }

  @override
  void dispose() {
    widget.runtime?.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    if (_refreshing) return;
    final client = _client;
    if (client == null) return;
    _refreshing = true;
    try {
      ControlPlaneProjection projection;
      try {
        projection = await client.fetchProjection();
      } on ControlPlaneClientException catch (error) {
        if (!mounted) return;
        setState(() {
          _projection = ControlPlaneProjection.unavailable(status: error.message);
          _operationalSnapshot = const OperationalSnapshot.unavailable();
          _operationalStatus = error.message;
          _lastLiveSequence = 0;
        });
        return;
      }

      try {
        final fresh = await client.fetchOperationalSnapshot(
          afterSequence: _lastLiveSequence,
        );
        final mergedEvents = <Map<String, Object?>>[
          ..._operationalSnapshot.liveEvents,
          ...fresh.liveEvents,
        ];
        final boundedEvents =
            mergedEvents.length <= ControlPlaneClient.maxLiveEvents
                ? mergedEvents
                : mergedEvents.sublist(
                    mergedEvents.length - ControlPlaneClient.maxLiveEvents,
                  );
        if (boundedEvents.isNotEmpty) {
          final sequence = boundedEvents.last['sequence'];
          if (sequence is int && sequence > _lastLiveSequence) {
            _lastLiveSequence = sequence;
          }
        }
        final operationalSnapshot = OperationalSnapshot(
          runtimeRoutes: fresh.runtimeRoutes,
          schedulerState: fresh.schedulerState,
          grantsState: fresh.grantsState,
          governanceState: fresh.governanceState,
          evidenceRecords: fresh.evidenceRecords,
          liveEvents: List<Map<String, Object?>>.unmodifiable(boundedEvents),
        );
        if (!mounted) return;
        setState(() {
          _projection = projection;
          _operationalSnapshot = operationalSnapshot;
          _operationalStatus = 'Operational APIs connected';
        });
      } on ControlPlaneClientException catch (error) {
        if (!mounted) return;
        setState(() {
          _projection = projection;
          _operationalSnapshot = const OperationalSnapshot.unavailable();
          _operationalStatus = error.message;
          _lastLiveSequence = 0;
        });
      }
    } finally {
      _refreshing = false;
    }
  }

  Future<PromptSubmission> _submitPrompt(String objective) async {
    final client = _client;
    if (client == null) {
      throw const ControlPlaneClientException('Control plane is unavailable');
    }
    final submission = await client.submitPrompt(objective);
    if (mounted) {
      setState(() {
        _operationalStatus =
            'Accepted ${submission.goalId}; ${submission.jobId} is ${submission.state}';
      });
    }
    await _refresh();
    return submission;
  }

  Future<String> _saveArtifact(EvidenceRecord record) async {
    final client = _client;
    if (client == null) {
      throw const ControlPlaneClientException('Control plane is unavailable');
    }
    final artifact = await client.fetchVerifiedArtifact(record.artifactDigest);
    final userProfile = Platform.environment['USERPROFILE']?.trim();
    final localAppData = Platform.environment['LOCALAPPDATA']?.trim();
    final rootPath = userProfile?.isNotEmpty == true
        ? '$userProfile\\Downloads\\ILAIOS'
        : (localAppData?.isNotEmpty == true
            ? '$localAppData\\ILAIOS\\Deliveries'
            : '${Directory.systemTemp.path}\\ILAIOS\\Deliveries');
    final root = Directory(rootPath);
    await root.create(recursive: true);
    final safeExecution =
        record.executionId.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
    final extension =
        record.action.toLowerCase().contains('video') ? '.mp4' : '.bin';
    final filename =
        'ILAIOS-$safeExecution-${artifact.digest.substring(0, 16)}$extension';
    final output = File('${root.path}\\$filename');
    await output.writeAsBytes(artifact.bytes, flush: true);
    if (await output.length() != artifact.size) {
      throw const ControlPlaneClientException(
        'Saved delivery size does not match verified artifact',
      );
    }
    if (mounted) {
      setState(() => _operationalStatus = 'Verified artifact saved');
    }
    return output.path;
  }

  Future<void> _decideGovernance(
    String requestId,
    GovernanceDecision decision,
  ) async {
    final client = _client;
    final approver = widget.config?.approverId;
    if (client == null || approver == null) return;
    try {
      await client.decideGovernanceRequest(
        requestId: requestId,
        approver: approver,
        decision: decision,
      );
      if (!mounted) return;
      setState(() => _operationalStatus = 'Governance decision accepted');
      await _refresh();
    } on ControlPlaneClientException catch (error) {
      if (!mounted) return;
      setState(() => _operationalStatus = error.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return IlaiosDesktopApp(
      projection: _projection,
      operationalSnapshot: _operationalSnapshot,
      operationalStatus: _operationalStatus,
      approverId: widget.config?.approverId,
      onPromptSubmit: _client == null ? null : _submitPrompt,
      onSaveArtifact: _client == null ? null : _saveArtifact,
      onRefreshRequested: _client == null ? null : _refresh,
      onGovernanceDecision:
          _client == null || widget.config?.approverId == null
              ? null
              : _decideGovernance,
    );
  }
}
