import 'dart:async';

import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../create/video_reference_picker.dart';
import 'reference_desktop_shell_v11.dart';

typedef VideoPromptSubmit = Future<PromptSubmission> Function(
  String objective,
  List<VideoReferenceDraft> references,
);

/// Adds bounded Video Factory reference-image UX without changing the approved
/// Desktop layout or the canonical one-prompt routing surface.
class ReferenceDesktopShellV12 extends StatefulWidget {
  const ReferenceDesktopShellV12({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.approverId,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.themeMode = ThemeMode.dark,
    this.onThemeModeChanged,
    this.onSignIn,
    this.onLogout,
    this.onPromptSubmit,
    this.onVideoPromptSubmit,
    this.onSaveArtifact,
    this.onRefreshRequested,
    this.onGovernanceDecision,
    this.referencePicker = const WindowsVideoReferenceFilePicker(),
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final String? approverId;
  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final String identityStatus;
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final VideoPromptSubmit? onVideoPromptSubmit;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;
  final VideoReferenceFilePicker referencePicker;

  @override
  State<ReferenceDesktopShellV12> createState() =>
      _ReferenceDesktopShellV12State();
}

class _ReferenceDesktopShellV12State extends State<ReferenceDesktopShellV12> {
  final List<VideoReferenceDraft> _references = <VideoReferenceDraft>[];
  bool _trayVisible = false;
  bool _picking = false;

  bool _isVideoObjective(String objective) {
    final normalized = objective.trimLeft();
    return normalized.startsWith('Video creation task:') ||
        normalized.startsWith('Video oluşturma görevi:');
  }

  Future<PromptSubmission> _submit(String objective) async {
    final ordinary = widget.onPromptSubmit;
    if (_isVideoObjective(objective) && _references.isNotEmpty) {
      final video = widget.onVideoPromptSubmit;
      if (video == null) {
        throw StateError(
          'Video reference upload is unavailable; generation was not started.',
        );
      }
      final snapshot = List<VideoReferenceDraft>.unmodifiable(_references);
      final result = await video(objective, snapshot);
      if (mounted) {
        setState(() {
          _references.clear();
          _trayVisible = false;
        });
      }
      return result;
    }
    if (ordinary == null) {
      throw StateError('Governed prompt submission is unavailable.');
    }
    return ordinary(objective);
  }

  Future<void> _pickReferences() async {
    if (_picking || _references.length >= maxVideoReferenceImages) return;
    setState(() => _picking = true);
    try {
      final picked = await widget.referencePicker.pick();
      if (!mounted || picked.isEmpty) return;
      final byDigest = <String, VideoReferenceDraft>{
        for (final reference in _references) reference.sha256Digest: reference,
      };
      for (final reference in picked) {
        byDigest.putIfAbsent(reference.sha256Digest, () => reference);
      }
      final merged = byDigest.values.toList(growable: false);
      if (merged.length > maxVideoReferenceImages) {
        throw const VideoReferencePickerException(
          'You can attach at most 8 video reference images.',
        );
      }
      final total = merged.fold<int>(0, (sum, item) => sum + item.sizeBytes);
      if (total > maxVideoReferencePoolBytes) {
        throw const VideoReferencePickerException(
          'Reference images exceed the 40 MiB total upload limit.',
        );
      }
      setState(() {
        _references
          ..clear()
          ..addAll(merged);
        _trayVisible = true;
      });
    } on VideoReferencePickerException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    } finally {
      if (mounted) setState(() => _picking = false);
    }
  }

  void _removeReference(int index) {
    if (index < 0 || index >= _references.length) return;
    setState(() {
      _references.removeAt(index);
      if (_references.isEmpty) _trayVisible = false;
    });
  }

  void _changeRole(int index, VideoReferenceRole role) {
    if (index < 0 || index >= _references.length) return;
    setState(() => _references[index] = _references[index].copyWith(role: role));
  }

  @override
  Widget build(BuildContext context) => Stack(
        children: [
          ReferenceDesktopShellV11(
            projection: widget.projection,
            operationalSnapshot: widget.operationalSnapshot,
            operationalStatus: widget.operationalStatus,
            approverId: widget.approverId,
            identityProviders: widget.identityProviders,
            userSession: widget.userSession,
            identityStatus: widget.identityStatus,
            themeMode: widget.themeMode,
            onThemeModeChanged: widget.onThemeModeChanged,
            onSignIn: widget.onSignIn,
            onLogout: widget.onLogout,
            onPromptSubmit: _submit,
            onSaveArtifact: widget.onSaveArtifact,
            onRefreshRequested: widget.onRefreshRequested,
            onGovernanceDecision: widget.onGovernanceDecision,
          ),
          Positioned(
            right: 16,
            bottom: 54,
            child: Semantics(
              button: true,
              label: 'Video reference images',
              child: FilledButton.tonalIcon(
                key: const Key('video-reference-toggle'),
                onPressed: _picking
                    ? null
                    : () {
                        if (_references.isEmpty) {
                          unawaited(_pickReferences());
                        } else {
                          setState(() => _trayVisible = !_trayVisible);
                        }
                      },
                icon: _picking
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.add_photo_alternate_outlined, size: 17),
                label: Text(
                  _references.isEmpty
                      ? 'Video references'
                      : 'Video references ${_references.length}/$maxVideoReferenceImages',
                ),
              ),
            ),
          ),
          if (_trayVisible)
            Positioned(
              right: 16,
              bottom: 102,
              child: VideoReferenceTray(
                references: _references,
                onAdd: () => unawaited(_pickReferences()),
                onRemove: _removeReference,
                onRoleChanged: _changeRole,
                busy: _picking,
              ),
            ),
        ],
      );
}
