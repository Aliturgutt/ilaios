import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../control_plane/client.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../../reference_assets/reference_asset_platform.dart';
import '../../reference_assets/reference_attachment.dart';
import 'create_view_core.dart' as core;

/// Reference-aware wrapper around the canonical Create/Goals surface.
///
/// The original surface remains intact in [core.CreateView]. This wrapper adds
/// governed image selection, native Windows drag/drop, previews, and request-
/// scoped attachment propagation without changing the one-prompt contract.
class CreateView extends StatefulWidget {
  const CreateView({
    required this.projection,
    required this.status,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.onSignIn,
    this.onLogout,
    this.onSubmit,
    super.key,
  });

  final ControlPlaneProjection projection;
  final String status;
  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final String identityStatus;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onSubmit;

  @override
  State<CreateView> createState() => _CreateViewState();
}

class _CreateViewState extends State<CreateView> {
  final List<ReferenceAttachmentDraft> _attachments = <ReferenceAttachmentDraft>[];
  StreamSubscription<List<String>>? _dropSubscription;
  String? _attachmentError;
  bool _readingFiles = false;

  @override
  void initState() {
    super.initState();
    _dropSubscription = ReferenceAssetPlatform.instance.droppedFiles.listen(_addPaths);
  }

  @override
  void dispose() {
    _dropSubscription?.cancel();
    super.dispose();
  }

  bool get _enabled => widget.projection.connected && widget.onSubmit != null;

  Future<void> _pickImages() async {
    if (!_enabled || _readingFiles) return;
    try {
      final paths = await ReferenceAssetPlatform.instance.pickImages();
      await _addPaths(paths);
    } on PlatformException catch (error) {
      if (!mounted) return;
      setState(() => _attachmentError = error.message ?? 'Image picker failed.');
    }
  }

  Future<void> _addPaths(List<String> paths) async {
    if (!_enabled || paths.isEmpty || _readingFiles) return;
    setState(() {
      _readingFiles = true;
      _attachmentError = null;
    });
    var errorMessage = '';
    try {
      for (final path in paths) {
        if (_attachments.length >= maxReferenceAssets) {
          errorMessage = 'A maximum of $maxReferenceAssets reference images is allowed.';
          break;
        }
        try {
          final attachment = await ReferenceAttachmentDraft.fromFilePath(path);
          if (_attachments.any((item) => item.sha256 == attachment.sha256)) {
            continue;
          }
          final total = _attachments.fold<int>(
                0,
                (sum, item) => sum + item.sizeBytes,
              ) +
              attachment.sizeBytes;
          if (total > maxReferenceTotalBytes) {
            errorMessage = 'Combined reference images cannot exceed 24 MB.';
            break;
          }
          _attachments.add(attachment);
        } on Object catch (error) {
          errorMessage = error.toString();
        }
      }
    } finally {
      if (mounted) {
        setState(() {
          _readingFiles = false;
          _attachmentError = errorMessage.isEmpty ? null : errorMessage;
        });
      }
    }
  }

  Future<PromptSubmission> _submitWithReferences(String objective) async {
    final callback = widget.onSubmit;
    if (callback == null) {
      throw StateError('Prompt submission is unavailable.');
    }
    final snapshot = List<ReferenceAttachmentDraft>.unmodifiable(_attachments);
    final result = await withReferenceAttachments(
      snapshot,
      () => callback(objective),
    );
    if (mounted && snapshot.isNotEmpty) {
      setState(() {
        _attachments.clear();
        _attachmentError = null;
      });
    }
    return result;
  }

  void _removeAttachment(String digest) {
    setState(() {
      _attachments.removeWhere((item) => item.sha256 == digest);
      _attachmentError = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _ReferenceAssetBar(
          enabled: _enabled,
          readingFiles: _readingFiles,
          attachments: _attachments,
          error: _attachmentError,
          onPick: _pickImages,
          onRemove: _removeAttachment,
        ),
        Expanded(
          child: core.CreateView(
            projection: widget.projection,
            status: widget.status,
            identityProviders: widget.identityProviders,
            userSession: widget.userSession,
            identityStatus: widget.identityStatus,
            onSignIn: widget.onSignIn,
            onLogout: widget.onLogout,
            onSubmit: widget.onSubmit == null ? null : _submitWithReferences,
          ),
        ),
      ],
    );
  }
}

class _ReferenceAssetBar extends StatelessWidget {
  const _ReferenceAssetBar({
    required this.enabled,
    required this.readingFiles,
    required this.attachments,
    required this.error,
    required this.onPick,
    required this.onRemove,
  });

  final bool enabled;
  final bool readingFiles;
  final List<ReferenceAttachmentDraft> attachments;
  final String? error;
  final VoidCallback onPick;
  final ValueChanged<String> onRemove;

  @override
  Widget build(BuildContext context) {
    final tr = Localizations.localeOf(context).languageCode.toLowerCase() == 'tr';
    return Container(
      key: const Key('reference-image-drop-zone'),
      margin: const EdgeInsets.fromLTRB(18, 10, 18, 0),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.image_outlined, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      tr ? 'Web / Video referans görselleri' : 'Web / Video reference images',
                      style: Theme.of(context).textTheme.labelLarge,
                    ),
                    Text(
                      tr
                          ? 'PNG, JPEG veya WebP sürükleyip bırakın ya da bilgisayarınızdan seçin. En fazla 8 görsel / toplam 24 MB.'
                          : 'Drop PNG, JPEG, or WebP images here, or choose them from your computer. Up to 8 images / 24 MB total.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              FilledButton.tonalIcon(
                key: const Key('reference-image-picker'),
                onPressed: enabled && !readingFiles ? onPick : null,
                icon: readingFiles
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.add_photo_alternate_outlined, size: 17),
                label: Text(tr ? 'Görsel ekle' : 'Add images'),
              ),
            ],
          ),
          if (attachments.isNotEmpty) ...[
            const SizedBox(height: 8),
            SizedBox(
              height: 66,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: attachments.length,
                separatorBuilder: (context, index) => const SizedBox(width: 8),
                itemBuilder: (context, index) {
                  final attachment = attachments[index];
                  return _ReferencePreview(
                    attachment: attachment,
                    index: index,
                    onRemove: () => onRemove(attachment.sha256),
                  );
                },
              ),
            ),
          ],
          if (error != null) ...[
            const SizedBox(height: 5),
            Text(
              error!,
              key: const Key('reference-image-error'),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.error,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ReferencePreview extends StatelessWidget {
  const _ReferencePreview({
    required this.attachment,
    required this.index,
    required this.onRemove,
  });

  final ReferenceAttachmentDraft attachment;
  final int index;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: ValueKey('reference-image-preview-$index'),
      width: 188,
      padding: const EdgeInsets.all(5),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: Image.memory(
              attachment.bytes,
              width: 52,
              height: 52,
              fit: BoxFit.cover,
              gaplessPlayback: true,
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  attachment.originalName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall,
                ),
                Text(
                  '${(attachment.sizeBytes / 1024).ceil()} KB',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          IconButton(
            key: ValueKey('reference-image-remove-$index'),
            tooltip: 'Remove reference image',
            onPressed: onRemove,
            icon: const Icon(Icons.close_rounded, size: 16),
            visualDensity: VisualDensity.compact,
          ),
        ],
      ),
    );
  }
}
