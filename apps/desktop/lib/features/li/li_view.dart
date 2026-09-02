import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../identity/identity_client.dart';

class LiView extends StatefulWidget {
  const LiView({
    required this.userSession,
    required this.onFetchState,
    required this.onFetchMemories,
    required this.onRemember,
    super.key,
  });

  final DesktopUserSession? userSession;
  final Future<DesktopLiState> Function()? onFetchState;
  final Future<List<DesktopLiMemory>> Function()? onFetchMemories;
  final Future<DesktopLiMemory> Function(String kind, String content)? onRemember;

  @override
  State<LiView> createState() => _LiViewState();
}

class _LiViewState extends State<LiView> {
  final TextEditingController _memoryController = TextEditingController();
  Future<DesktopLiState>? _state;
  Future<List<DesktopLiMemory>>? _memories;
  String _selectedKind = 'working';
  String? _saveStatus;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void didUpdateWidget(covariant LiView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.userSession?.sessionId != widget.userSession?.sessionId ||
        (oldWidget.onFetchState == null && widget.onFetchState != null) ||
        (oldWidget.onFetchMemories == null && widget.onFetchMemories != null) ||
        (oldWidget.onRemember == null && widget.onRemember != null) ||
        (oldWidget.userSession?.liFounder == true &&
            widget.userSession?.liFounder != true)) {
      _reload();
    }
  }

  @override
  void dispose() {
    _memoryController.dispose();
    super.dispose();
  }

  void _reload() {
    final session = widget.userSession;
    final fetchState = widget.onFetchState;
    final fetchMemories = widget.onFetchMemories;
    if (session == null ||
        !session.liFounder ||
        fetchState == null ||
        fetchMemories == null) {
      _state = null;
      _memories = null;
      return;
    }
    _state = fetchState();
    _memories = fetchMemories();
  }

  Future<void> _remember() async {
    final remember = widget.onRemember;
    final fetchMemories = widget.onFetchMemories;
    final content = _memoryController.text.trim();
    if (remember == null || fetchMemories == null || content.isEmpty || _saving) {
      return;
    }
    setState(() {
      _saving = true;
      _saveStatus = _copy(context, 'Saving...', 'Kaydediliyor...');
    });
    try {
      await remember(_selectedKind, content);
      if (!mounted) return;
      _memoryController.clear();
      setState(() {
        _memories = fetchMemories();
        _saveStatus = _copy(context, 'Saved.', 'Kaydedildi.');
      });
    } on IdentityClientException catch (error) {
      if (!mounted) return;
      setState(() => _saveStatus = error.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = widget.userSession;
    final fetch = _state;
    if (session == null || !session.liFounder || fetch == null) {
      return Center(
        key: const Key('li-access-denied'),
        child: Text(
          _copy(context, 'Li access unavailable.', 'Li erişimi kullanılamıyor.'),
        ),
      );
    }

    return Padding(
      key: const Key('li-founder-view'),
      padding: const EdgeInsets.all(24),
      child: FutureBuilder<DesktopLiState>(
        future: fetch,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final state = snapshot.data;
          if (snapshot.hasError || state == null || !state.founderOperator) {
            return Center(
              child: Text(
                _copy(
                  context,
                  'Li access could not be verified.',
                  'Li erişimi doğrulanamadı.',
                ),
              ),
            );
          }

          return SingleChildScrollView(
            child: Align(
              alignment: Alignment.topLeft,
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Li',
                      style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _copy(context, 'Founder Operator', 'Kurucu Operatör'),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 18),
                    _StateCard(state: state),
                    const SizedBox(height: 18),
                    _MemoryComposer(
                      selectedKind: _selectedKind,
                      controller: _memoryController,
                      saving: _saving,
                      status: _saveStatus,
                      onKindChanged: (value) {
                        if (value != null) {
                          setState(() => _selectedKind = value);
                        }
                      },
                      onSave: _remember,
                    ),
                    const SizedBox(height: 18),
                    _MemoryList(memories: _memories),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _StateCard extends StatelessWidget {
  const _StateCard({required this.state});

  final DesktopLiState state;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _copy(
                context,
                'Server-authoritative founder access verified.',
                'Sunucu tarafından yetkilendirilen kurucu erişimi doğrulandı.',
              ),
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            _StateRow(
              label: _copy(context, 'Principal', 'Kullanıcı'),
              value: state.userId,
            ),
            const SizedBox(height: 10),
            _StateRow(
              label: _copy(context, 'Tenant', 'Tenant'),
              value: state.tenantId,
            ),
            const SizedBox(height: 10),
            _StateRow(
              label: _copy(context, 'Source', 'Kaynak'),
              value: state.source,
            ),
          ],
        ),
      );
}

class _MemoryComposer extends StatelessWidget {
  const _MemoryComposer({
    required this.selectedKind,
    required this.controller,
    required this.saving,
    required this.status,
    required this.onKindChanged,
    required this.onSave,
  });

  final String selectedKind;
  final TextEditingController controller;
  final bool saving;
  final String? status;
  final ValueChanged<String?> onKindChanged;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('li-memory-composer'),
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _copy(context, 'Persistent memory', 'Kalıcı hafıza'),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              key: const Key('li-memory-kind'),
              initialValue: selectedKind,
              items: const <DropdownMenuItem<String>>[
                DropdownMenuItem(value: 'working', child: Text('Working')),
                DropdownMenuItem(value: 'episodic', child: Text('Episodic')),
                DropdownMenuItem(value: 'semantic', child: Text('Semantic')),
              ],
              onChanged: saving ? null : onKindChanged,
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('li-memory-content'),
              controller: controller,
              enabled: !saving,
              maxLength: 8000,
              minLines: 2,
              maxLines: 5,
              decoration: InputDecoration(
                hintText: _copy(
                  context,
                  'What should Li remember?',
                  'Li neyi hatırlamalı?',
                ),
              ),
            ),
            const SizedBox(height: 8),
            FilledButton(
              key: const Key('li-memory-save'),
              onPressed: saving ? null : onSave,
              child: Text(_copy(context, 'Remember', 'Hatırla')),
            ),
            if (status != null) ...[
              const SizedBox(height: 8),
              Text(
                status!,
                key: const Key('li-memory-save-status'),
              ),
            ],
          ],
        ),
      );
}

class _MemoryList extends StatelessWidget {
  const _MemoryList({required this.memories});

  final Future<List<DesktopLiMemory>>? memories;

  @override
  Widget build(BuildContext context) {
    final future = memories;
    if (future == null) {
      return Text(
        _copy(context, 'Memory unavailable.', 'Hafıza kullanılamıyor.'),
      );
    }
    return FutureBuilder<List<DesktopLiMemory>>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Text(
            _copy(
              context,
              'Memory could not be loaded.',
              'Hafıza yüklenemedi.',
            ),
          );
        }
        final items = snapshot.data ?? const <DesktopLiMemory>[];
        return Column(
          key: const Key('li-memory-list'),
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _copy(context, 'Recent memories', 'Son hafızalar'),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 10),
            if (items.isEmpty)
              Text(_copy(context, 'No memories yet.', 'Henüz hafıza yok.'))
            else
              for (final item in items)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      border: Border.all(
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.kind,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 4),
                        SelectableText(item.content),
                        const SizedBox(height: 4),
                        Text(
                          '${item.source} • ${item.createdAt.toLocal()}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ),
          ],
        );
      },
    );
  }
}

class _StateRow extends StatelessWidget {
  const _StateRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: SelectableText(
              value,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      );
}

String _copy(BuildContext context, String english, String turkish) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish
        ? turkish
        : english;
