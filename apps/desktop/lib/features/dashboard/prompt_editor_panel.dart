import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/client.dart';

class PromptEditorPanel extends StatefulWidget {
  const PromptEditorPanel({
    required this.controller,
    required this.enabled,
    required this.onRefine,
    super.key,
  });

  final TextEditingController controller;
  final bool enabled;
  final Future<PromptRefinementPreview> Function(
    String prompt,
    PromptRefinementMode mode,
  )? onRefine;

  @override
  State<PromptEditorPanel> createState() => _PromptEditorPanelState();
}

class _PromptEditorPanelState extends State<PromptEditorPanel> {
  PromptRefinementMode _mode = PromptRefinementMode.preserveIntent;
  PromptRefinementPreview? _preview;
  bool _refining = false;
  String? _error;
  int _requestSerial = 0;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onPromptChanged);
  }

  @override
  void didUpdateWidget(covariant PromptEditorPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      oldWidget.controller.removeListener(_onPromptChanged);
      widget.controller.addListener(_onPromptChanged);
      _invalidatePendingRefinement();
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onPromptChanged);
    super.dispose();
  }

  bool get _canApply {
    final preview = _preview;
    return preview != null &&
        preview.originalPrompt == widget.controller.text &&
        preview.riskCuesPreserved != false;
  }

  void _invalidatePendingRefinement() {
    _requestSerial += 1;
    if (!mounted) return;
    setState(() {
      _refining = false;
      _preview = null;
      _error = null;
    });
  }

  void _onPromptChanged() {
    final previewMatchesSource = _preview?.originalPrompt == widget.controller.text;
    if (_refining || (_preview != null && !previewMatchesSource)) {
      _invalidatePendingRefinement();
    }
  }

  Future<void> _refine() async {
    final callback = widget.onRefine;
    final prompt = widget.controller.text;
    if (callback == null || prompt.trim().isEmpty || _refining) return;
    final requestSerial = ++_requestSerial;
    setState(() {
      _refining = true;
      _preview = null;
      _error = null;
    });
    try {
      final result = await callback(prompt, _mode);
      if (!mounted ||
          requestSerial != _requestSerial ||
          widget.controller.text != prompt) {
        return;
      }
      setState(() => _preview = result);
    } on Object {
      if (!mounted || requestSerial != _requestSerial) return;
      setState(() => _error = 'prompt_refinement_failed');
    } finally {
      if (mounted && requestSerial == _requestSerial) {
        setState(() => _refining = false);
      }
    }
  }

  void _apply() {
    final preview = _preview;
    if (preview == null || !_canApply) return;
    widget.controller.value = TextEditingValue(
      text: preview.refinedPrompt,
      selection: TextSelection.collapsed(offset: preview.refinedPrompt.length),
    );
    setState(() => _preview = null);
  }

  void _discard() => setState(() {
        _preview = null;
        _error = null;
      });

  @override
  Widget build(BuildContext context) {
    final tr = IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;
    return Container(
      key: const Key('prompt-editor-panel'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  tr ? 'Prompt Editor' : 'Prompt Editor',
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
                ),
              ),
              Text(
                tr ? 'Danışman katman · yürütme yetkisi yok' : 'Advisory layer · no execution authority',
                style: TextStyle(
                  fontSize: 11,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              for (final mode in PromptRefinementMode.values)
                ChoiceChip(
                  key: ValueKey('prompt-mode-${mode.wireValue}'),
                  label: Text(_modeLabel(mode, tr)),
                  selected: _mode == mode,
                  onSelected: widget.enabled && !_refining
                      ? (_) => setState(() {
                            _mode = mode;
                            _preview = null;
                            _error = null;
                          })
                      : null,
                ),
              OutlinedButton.icon(
                key: const Key('prompt-refine-action'),
                onPressed: widget.enabled && !_refining && widget.onRefine != null
                    ? _refine
                    : null,
                icon: _refining
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.auto_fix_high_outlined, size: 17),
                label: Text(tr ? 'Önizle' : 'Preview'),
              ),
            ],
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(
              tr ? 'Prompt önizlemesi oluşturulamadı.' : 'Prompt preview could not be generated.',
              key: const Key('prompt-refinement-error'),
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          if (_preview != null) ...[
            const SizedBox(height: 10),
            _PromptPreview(
              preview: _preview!,
              turkish: tr,
              canApply: _canApply,
              onApply: _apply,
              onDiscard: _discard,
            ),
          ],
        ],
      ),
    );
  }
}

class _PromptPreview extends StatelessWidget {
  const _PromptPreview({
    required this.preview,
    required this.turkish,
    required this.canApply,
    required this.onApply,
    required this.onDiscard,
  });

  final PromptRefinementPreview preview;
  final bool turkish;
  final bool canApply;
  final VoidCallback onApply;
  final VoidCallback onDiscard;

  @override
  Widget build(BuildContext context) {
    final riskLabel = preview.riskCues.isEmpty
        ? (turkish ? 'Risk ifadesi yok' : 'No risk cues')
        : preview.riskCuesPreserved == true
            ? (turkish ? 'Risk ifadeleri korundu' : 'Risk cues preserved')
            : (turkish ? 'Risk ifadesi korunumu doğrulanamadı' : 'Risk cue preservation failed');
    final constraintLabel = preview.constraintsDetected
        ? (turkish
            ? '${preview.preservedConstraints.length} kısıt korundu'
            : '${preview.preservedConstraints.length} constraints preserved')
        : (turkish ? 'Kısıt algılanmadı' : 'No constraints detected');

    return Column(
      key: const Key('prompt-before-after'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final cards = <Widget>[
              _PromptTextCard(
                title: turkish ? 'Önce' : 'Before',
                text: preview.originalPrompt,
                widgetKey: const Key('prompt-before'),
              ),
              _PromptTextCard(
                title: turkish ? 'Sonra' : 'After',
                text: preview.refinedPrompt,
                widgetKey: const Key('prompt-after'),
              ),
            ];
            if (constraints.maxWidth < 760) {
              return Column(
                children: [cards[0], const SizedBox(height: 8), cards[1]],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: cards[0]),
                const SizedBox(width: 8),
                Expanded(child: cards[1]),
              ],
            );
          },
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          children: [
            Text(
              preview.transformed
                  ? (turkish ? 'Değişiklik var' : 'Changed')
                  : (turkish ? 'Metin değişmedi' : 'No text change'),
              key: const Key('prompt-change-status'),
            ),
            Text(constraintLabel, key: const Key('prompt-constraint-status')),
            Text(riskLabel, key: const Key('prompt-risk-status')),
          ],
        ),
        if (preview.unresolvedAmbiguities.isNotEmpty || preview.warnings.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(
            <String>[...preview.unresolvedAmbiguities, ...preview.warnings].join(' · '),
            key: const Key('prompt-refinement-warnings'),
            style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
          ),
        ],
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
              key: const Key('prompt-keep-original'),
              onPressed: onDiscard,
              child: Text(turkish ? 'Orijinali koru' : 'Keep original'),
            ),
            const SizedBox(width: 8),
            FilledButton(
              key: const Key('prompt-use-refined'),
              onPressed: canApply ? onApply : null,
              child: Text(turkish ? 'Düzenlenmiş metni kullan' : 'Use refined'),
            ),
          ],
        ),
      ],
    );
  }
}

class _PromptTextCard extends StatelessWidget {
  const _PromptTextCard({
    required this.title,
    required this.text,
    required this.widgetKey,
  });

  final String title;
  final String text;
  final Key widgetKey;

  @override
  Widget build(BuildContext context) => Container(
        key: widgetKey,
        constraints: const BoxConstraints(minHeight: 92),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 5),
            SelectableText(text),
          ],
        ),
      );
}

String _modeLabel(PromptRefinementMode mode, bool tr) => switch (mode) {
      PromptRefinementMode.improve => tr ? 'İyileştir' : 'Improve',
      PromptRefinementMode.clarify => tr ? 'Netleştir' : 'Clarify',
      PromptRefinementMode.structure => tr ? 'Yapılandır' : 'Structure',
      PromptRefinementMode.preserveIntent => tr ? 'Niyeti Koru' : 'Preserve Intent',
      PromptRefinementMode.compress => tr ? 'Sıkıştır' : 'Compress',
      PromptRefinementMode.evaluate => tr ? 'Değerlendir' : 'Evaluate',
    };
