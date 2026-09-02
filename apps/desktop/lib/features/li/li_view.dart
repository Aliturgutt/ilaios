import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../identity/identity_client.dart';

class LiView extends StatefulWidget {
  const LiView({
    required this.userSession,
    required this.onFetchState,
    super.key,
  });

  final DesktopUserSession? userSession;
  final Future<DesktopLiState> Function()? onFetchState;

  @override
  State<LiView> createState() => _LiViewState();
}

class _LiViewState extends State<LiView> {
  Future<DesktopLiState>? _state;

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
        (oldWidget.userSession?.liFounder == true &&
            widget.userSession?.liFounder != true)) {
      _reload();
    }
  }

  void _reload() {
    final session = widget.userSession;
    final fetch = widget.onFetchState;
    if (session == null || !session.liFounder || fetch == null) {
      _state = null;
      return;
    }
    _state = fetch();
  }

  @override
  Widget build(BuildContext context) {
    final session = widget.userSession;
    final fetch = _state;
    if (session == null || !session.liFounder || fetch == null) {
      return Center(
        key: const Key('li-access-denied'),
        child: Text(_copy(context, 'Li access unavailable.', 'Li erişimi kullanılamıyor.')),
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

          return Align(
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
                  Container(
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
                  ),
                ],
              ),
            ),
          );
        },
      ),
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
