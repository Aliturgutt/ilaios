import '../../app/desktop_page_heading.dart';
import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/client.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../create/reference_asset_picker.dart';
import '../navigation/desktop_section.dart';
import 'pixel_agent_presentation.dart';

/// Canonical 7-page Home surface.
///
/// Geometry follows the user-approved 1536x1024 Home reference. Runtime values
/// remain authority-derived; screenshot example counts are never copied into
/// application state.
class ReferenceHomeDashboardV3 extends StatefulWidget {
  const ReferenceHomeDashboardV3({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.onNavigate,
    this.userSession,
    this.onPromptSubmit,
    this.onPromptRefine,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final DesktopUserSession? userSession;
  final ValueChanged<DesktopSection> onNavigate;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final Future<PromptRefinementPreview> Function(
    String prompt,
    PromptRefinementMode mode,
  )?
  onPromptRefine;
  final VoidCallback? onRefreshRequested;

  @override
  State<ReferenceHomeDashboardV3> createState() =>
      _ReferenceHomeDashboardV3State();
}

class _ReferenceHomeDashboardV3State extends State<ReferenceHomeDashboardV3> {
  final TextEditingController _promptController = TextEditingController();
  bool _submitting = false;
  String _objective = '';

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  Future<void> _startWork() async {
    final callback = widget.onPromptSubmit;
    final objective = _promptController.text.trim();
    if (callback == null || objective.isEmpty || _submitting) return;

    setState(() => _submitting = true);
    try {
      final submission = await callback(objective);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _t(
              context,
              'Work accepted · ${submission.state}',
              'İş kabul edildi · ${submission.state}',
            ),
          ),
        ),
      );
      _promptController.clear();
      setState(() => _objective = '');
    } on Object catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _t(
              context,
              'Work could not be started: $error',
              'İş başlatılamadı: $error',
            ),
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final referenceAssets = ReferenceAssetPickerScope.maybeOf(context);
    final operator = desktopOperatorLabel(widget.userSession);

    return LayoutBuilder(
      builder: (context, viewport) {
        final compactHome = viewport.maxHeight < 800;
        return ColoredBox(
          color: Theme.of(context).scaffoldBackgroundColor,
          child: SingleChildScrollView(
            key: const Key('command-center-short-viewport-scroll'),
            primary: false,
            child: Column(
              key: const Key('command-center-home'),
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  padding: compactHome
                      ? const EdgeInsets.fromLTRB(24, 10, 27, 7)
                      : const EdgeInsets.fromLTRB(24, 20, 27, 14),
                  decoration: BoxDecoration(
                    border: Border(
                      bottom: BorderSide(
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              _t(context, 'Start work', 'İş başlat'),
                              style: DesktopPageHeading.style(context),
                            ),
                          ),
                          Text(
                            _t(
                              context,
                              'Operator · $operator',
                              'Operatör · $operator',
                            ),
                            key: const Key('home-operator-identity'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: Theme.of(
                                context,
                              ).colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: compactHome ? 8 : 16),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: SizedBox(
                              height: compactHome ? 48 : 60,
                              child: TextField(
                                key: const Key('home-command-prompt'),
                                controller: _promptController,
                                minLines: 1,
                                maxLines: 1,
                                textAlignVertical: TextAlignVertical.center,
                                onChanged: (value) =>
                                    setState(() => _objective = value.trim()),
                                decoration: InputDecoration(
                                  hintText: _t(
                                    context,
                                    'Website, video, software or research — describe the result and criteria…',
                                    'Web sitesi, video, yazılım veya araştırma — sonucu ve kriterleri yaz...',
                                  ),
                                  hintStyle: const TextStyle(fontSize: 14),
                                  contentPadding: const EdgeInsets.symmetric(
                                    horizontal: 16,
                                    vertical: 18,
                                  ),
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 16),
                          SizedBox(
                            width: 162,
                            height: compactHome ? 48 : 60,
                            child: FilledButton.icon(
                              key: const Key('home-new-work'),
                              onPressed:
                                  _objective.isNotEmpty &&
                                      widget.onPromptSubmit != null &&
                                      !_submitting
                                  ? _startWork
                                  : null,
                              icon: _submitting
                                  ? const SizedBox(
                                      width: 18,
                                      height: 18,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Icon(
                                      Icons.play_arrow_outlined,
                                      size: 24,
                                    ),
                              label: Text(
                                _submitting
                                    ? _t(context, 'Starting…', 'Başlatılıyor…')
                                    : _t(context, 'Start', 'Başlat'),
                                style: const TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              style: FilledButton.styleFrom(
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(8),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: compactHome ? 5 : 12),
                      if (referenceAssets != null) ...[
                        SizedBox(height: compactHome ? 5 : 13),
                        ReferenceAssetPicker(
                          key: const Key('home-prompt-attachments'),
                          controller: referenceAssets,
                          enabled: !_submitting,
                          compact: true,
                          factoryCardHeight: 138,
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

String _t(BuildContext context, String english, String turkish) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish
    ? turkish
    : english;
