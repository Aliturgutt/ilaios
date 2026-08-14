import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/client.dart';
import '../../control_plane/projection.dart';

class CreateView extends StatefulWidget {
  const CreateView({
    required this.projection,
    required this.status,
    this.onSubmit,
    super.key,
  });

  final ControlPlaneProjection projection;
  final String status;
  final Future<PromptSubmission> Function(String objective)? onSubmit;

  @override
  State<CreateView> createState() => _CreateViewState();
}

class _CreateViewState extends State<CreateView> {
  final TextEditingController _controller = TextEditingController();
  bool _submitting = false;
  PromptSubmission? _submission;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final callback = widget.onSubmit;
    final objective = _controller.text.trim();
    if (callback == null || objective.isEmpty || _submitting) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final submission = await callback(objective);
      if (!mounted) return;
      setState(() => _submission = submission);
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final enabled = widget.projection.connected && widget.onSubmit != null;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(28),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1050),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'What do you want ILAIOS to build?',
                style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              const Text(
                'Describe the finished outcome. ILAIOS records the intent as an authoritative goal and durable job; provider, worker and privileged execution authority remain server-controlled.',
                style: TextStyle(color: IlaiosTheme.muted, height: 1.5),
              ),
              const SizedBox(height: 24),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        key: const Key('one-prompt-input'),
                        controller: _controller,
                        enabled: enabled && !_submitting,
                        minLines: 5,
                        maxLines: 10,
                        maxLength: 20000,
                        textInputAction: TextInputAction.newline,
                        decoration: const InputDecoration(
                          hintText:
                              'Example: Build a premium website for my furniture company and deliver the finished result.',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          FilledButton.icon(
                            key: const Key('one-prompt-submit'),
                            onPressed: enabled && !_submitting ? _submit : null,
                            icon: _submitting
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.arrow_forward),
                            label: Text(_submitting ? 'Submitting…' : 'Start with one prompt'),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Text(
                              enabled ? widget.status : 'Authoritative control plane is unavailable',
                              style: const TextStyle(
                                color: IlaiosTheme.muted,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              if (_submission case final submission?) ...[
                const SizedBox(height: 18),
                Card(
                  key: const Key('one-prompt-accepted'),
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.check_circle_outline, color: IlaiosTheme.success),
                            SizedBox(width: 10),
                            Text(
                              'Accepted by the control plane',
                              style: TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        SelectableText('Goal: ${submission.goalId}'),
                        const SizedBox(height: 5),
                        SelectableText('Job: ${submission.jobId}'),
                        const SizedBox(height: 5),
                        Text('Authoritative state: ${submission.state}'),
                        const SizedBox(height: 12),
                        const Text(
                          'Desktop does not treat submission as completion. Progress, governance, evidence and final artifacts must be proven by the authoritative runtime.',
                          style: TextStyle(color: IlaiosTheme.muted, height: 1.45),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (_error case final error?) ...[
                const SizedBox(height: 18),
                Text(
                  error,
                  key: const Key('one-prompt-error'),
                  style: const TextStyle(color: Colors.redAccent),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
