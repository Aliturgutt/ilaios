import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';

import '../business_context/business_capability_context.dart';
import '../control_plane/client.dart';
import '../control_plane/config.dart';
import '../control_plane/evidence_record.dart';
import '../control_plane/local_runtime.dart';
import '../control_plane/operational_snapshot.dart';
import '../control_plane/projection.dart';
import '../features/deliveries/delivery_local_storage.dart';
import '../identity/identity_client.dart';
import 'desktop_app.dart';
import 'ilaios_locale.dart';

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
  String _identityStatus = 'Account sign-in is not configured';
  IlaiosLocale _locale = IlaiosLocaleStore.platformDefault();
  ControlPlaneClient? _client;
  IdentityClient? _identityClient;
  List<IdentityProviderOption> _identityProviders =
      const <IdentityProviderOption>[];
  DesktopUserSession? _userSession;
  final DeliveryLocalStorage _deliveryStorage = DeliveryLocalStorage();
  int _lastLiveSequence = 0;
  bool _refreshing = false;

  @override
  void initState() {
    super.initState();
    unawaited(_loadLocale());
    unawaited(_deliveryStorage.cleanupDisposable());
    final config = widget.config;
    if (config == null) {
      _operationalStatus =
          widget.runtime?.status ?? 'Control plane configuration unavailable';
      return;
    }
    try {
      _client = ControlPlaneClient(baseUri: config.baseUri, token: config.token);
      final identityUri = config.identityUri;
      if (identityUri != null) {
        _identityClient = IdentityClient(
          baseUri: identityUri,
          transportToken: config.token,
        );
        unawaited(_loadIdentityProviders());
      }
      _operationalStatus = widget.runtime?.status ?? 'Control plane configured';
      unawaited(_refresh());
    } on ArgumentError {
      _projection = const ControlPlaneProjection.unavailable(
        status: 'Control plane configuration rejected',
      );
      _operationalStatus = 'Control plane configuration rejected';
      _identityStatus = 'Identity broker configuration rejected';
    }
  }

  @override
  void dispose() {
    widget.runtime?.dispose();
    super.dispose();
  }

  Future<void> _loadLocale() async {
    final locale = await IlaiosLocaleStore.load();
    if (!mounted || locale == _locale) return;
    setState(() => _locale = locale);
  }

  Future<void> _changeLocale(IlaiosLocale locale) async {
    if (_locale != locale && mounted) {
      setState(() => _locale = locale);
    }
    await IlaiosLocaleStore.save(locale);
  }

  Future<void> _loadIdentityProviders() async {
    final client = _identityClient;
    if (client == null) return;
    try {
      final providers = await client.fetchProviders();
      DesktopUserSession? restoredSession;
      if (providers.isNotEmpty) {
        try {
          restoredSession = await client.poll('__ilaios_restore__');
        } on IdentityClientException {
          // A missing, revoked, expired, or unreadable persistent credential must
          // fail closed to the ordinary signed-out state without blocking startup.
        }
      }
      if (!mounted) return;
      setState(() {
        _identityProviders = providers;
        _userSession = restoredSession;
        _identityStatus = restoredSession != null
            ? (restoredSession.displayIdentity == null
                ? 'Signed in with ${restoredSession.providerId}'
                : 'Signed in as ${restoredSession.displayIdentity}')
            : (providers.isEmpty
                ? 'Account sign-in is not configured; governed execution is disabled'
                : 'Sign in to submit governed work');
      });
    } on IdentityClientException catch (error) {
      if (!mounted) return;
      setState(() {
        _identityProviders = const <IdentityProviderOption>[];
        _identityStatus = error.message;
      });
    }
  }

  Future<void> _signIn(String providerId) async {
    final client = _identityClient;
    if (client == null) {
      throw const IdentityClientException('Identity broker is unavailable');
    }
    if (!Platform.isWindows) {
      throw const IdentityClientException(
        'Browser account sign-in is available in the Windows Desktop build',
      );
    }

    final started = await client.start(providerId);
    await Process.start(
      'rundll32.exe',
      <String>[
        'url.dll,FileProtocolHandler',
        started.authorizationUri.toString(),
      ],
      mode: ProcessStartMode.detached,
    );
    if (mounted) {
      setState(() => _identityStatus = 'Waiting for browser sign-in');
    }

    for (var attempt = 0; attempt < 240; attempt += 1) {
      await Future<void>.delayed(const Duration(milliseconds: 500));
      final session = await client.poll(started.state);
      if (session == null) continue;
      if (!mounted) return;
      setState(() {
        _userSession = session;
        _identityStatus = session.displayIdentity == null
            ? 'Signed in with ${session.providerId}'
            : 'Signed in as ${session.displayIdentity}';
      });
      return;
    }
    throw const IdentityClientException('Browser sign-in timed out');
  }

  Future<void> _logout() async {
    final client = _identityClient;
    final session = _userSession;
    if (client == null || session == null) return;
    await client.logout(session);
    BusinessCapabilitySubmissionBus.clear();
    if (!mounted) return;
    setState(() {
      _userSession = null;
      _identityStatus = 'Signed out';
    });
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
          agentState: fresh.agentState,
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
    if (_client == null) {
      throw const ControlPlaneClientException('Control plane is unavailable');
    }
    final identityClient = _identityClient;
    final session = _userSession;
    if (identityClient == null ||
        _identityProviders.isEmpty ||
        session == null) {
      throw const IdentityClientException(
        'Verified account sign-in is required before governed execution',
      );
    }

    final businessContext = BusinessCapabilitySubmissionBus.take();
    final submission = await identityClient.submitPrompt(
      objective,
      session,
      businessContext: businessContext,
    );
    if (mounted) {
      setState(() {
        _operationalStatus =
            'Accepted ${submission.goalId}; execution ${submission.executionStatus}';
      });
    }
    if (submission.executionStatus == 'ADMITTED' ||
        submission.executionStatus == 'EXECUTING') {
      unawaited(_monitorExecution(submission.requestId));
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
    if (artifact.digest != record.artifactDigest) {
      throw const ControlPlaneClientException(
        'Verified artifact digest does not match the evidence record',
      );
    }
    final output = _deliveryStorage.resolveArtifactFile(record);
    await output.parent.create(recursive: true);
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

  Future<void> _provisionAgent(String agentId) async {
    final client = _client;
    if (client == null) {
      throw const ControlPlaneClientException('Control plane is unavailable');
    }
    if (_userSession == null) {
      throw const IdentityClientException(
        'Verified account sign-in is required for agent provisioning',
      );
    }
    await client.provisionCanonicalAgent(agentId);
    if (mounted) {
      setState(() => _operationalStatus = 'Canonical agent provisioned');
    }
    await _refresh();
  }

  Future<void> _decideGovernance(
    String requestId,
    GovernanceDecision decision,
  ) async {
    final client = _client;
    if (client == null) return;
    try {
      if (requestId.startsWith('exec-')) {
        final identityClient = _identityClient;
        final session = _userSession;
        if (identityClient == null || session == null) {
          throw const IdentityClientException(
            'A verified approver session is required for execution decisions',
          );
        }
        final status = await identityClient.decideExecution(
          requestId,
          decision,
          session,
        );
        if (!mounted) return;
        if (status == 'EXECUTION_STARTED') {
          setState(() {
            _operationalStatus =
                'Independent approval recorded; governed execution started';
          });
          unawaited(_monitorExecution(requestId));
        } else {
          setState(() => _operationalStatus = 'Governed execution denied');
        }
      } else {
        final approver = widget.config?.approverId;
        if (approver == null) {
          throw const ControlPlaneClientException(
            'Independent operator approver is not configured',
          );
        }
        await client.decideGovernanceRequest(
          requestId: requestId,
          approver: approver,
          decision: decision,
        );
        if (!mounted) return;
        setState(() => _operationalStatus = 'Governance decision accepted');
      }
      await _refresh();
    } on ControlPlaneClientException catch (error) {
      if (!mounted) return;
      setState(() => _operationalStatus = error.message);
    } on IdentityClientException catch (error) {
      if (!mounted) return;
      setState(() => _operationalStatus = error.message);
      await _refresh();
    }
  }

  Future<void> _monitorExecution(String requestId) async {
    final identityClient = _identityClient;
    final session = _userSession;
    if (identityClient == null || session == null) return;
    for (var attempt = 0; attempt < 300; attempt += 1) {
      await Future<void>.delayed(const Duration(seconds: 1));
      if (!mounted || _userSession?.sessionId != session.sessionId) return;
      try {
        final status = await identityClient.fetchExecutionStatus(
          requestId,
          session,
        );
        if (status == 'ACCEPTED') {
          setState(() {
            _operationalStatus =
                'Governed execution accepted; verified delivery ready';
          });
          await _refresh();
          return;
        }
        if (status == 'FAILED' ||
            status == 'DENIED' ||
            status.startsWith('BLOCKED_')) {
          setState(() => _operationalStatus = 'Governed execution: $status');
          await _refresh();
          return;
        }
      } on IdentityClientException catch (error) {
        if (!mounted) return;
        setState(() => _operationalStatus = error.message);
        return;
      }
    }
    if (mounted) {
      setState(() {
        _operationalStatus =
            'Execution is still running; continue tracking it in Live Execution';
      });
      await _refresh();
    }
  }

  @override
  Widget build(BuildContext context) {
    final promptEnabled = _client != null &&
        _identityClient != null &&
        _identityProviders.isNotEmpty &&
        _userSession != null;
    final agentProvisionEnabled = _client != null && _userSession != null;
    final governanceEnabled = _client != null &&
        (widget.config?.approverId != null ||
            (_identityClient != null && _userSession != null));
    return IlaiosDesktopApp(
      projection: _projection,
      operationalSnapshot: _operationalSnapshot,
      operationalStatus: _operationalStatus,
      approverId: widget.config?.approverId,
      identityProviders: _identityProviders,
      userSession: _userSession,
      identityStatus: _identityStatus,
      locale: _locale,
      onLocaleChanged: _changeLocale,
      onSignIn:
          _identityClient == null || _identityProviders.isEmpty ? null : _signIn,
      onLogout: _userSession == null ? null : _logout,
      onPromptSubmit: promptEnabled ? _submitPrompt : null,
      onSaveArtifact: _client == null ? null : _saveArtifact,
      onRefreshRequested: _client == null ? null : _refresh,
      onProvisionAgent: agentProvisionEnabled ? _provisionAgent : null,
      onGovernanceDecision: governanceEnabled ? _decideGovernance : null,
    );
  }
}
