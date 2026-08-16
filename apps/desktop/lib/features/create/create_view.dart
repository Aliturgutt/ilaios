import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/client.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';

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

enum _FactoryPreset { web, video, software }

class _CreateViewState extends State<CreateView> {
  final TextEditingController _controller = TextEditingController();
  bool _submitting = false;
  String? _signingInProvider;
  bool _loggingOut = false;
  PromptSubmission? _submission;
  String? _error;
  _FactoryPreset? _selectedPreset;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _signIn(String providerId) async {
    final callback = widget.onSignIn;
    if (callback == null || _signingInProvider != null) return;
    setState(() {
      _signingInProvider = providerId;
      _error = null;
    });
    try {
      await callback(providerId);
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _signingInProvider = null);
    }
  }

  Future<void> _logout() async {
    final callback = widget.onLogout;
    if (callback == null || _loggingOut) return;
    setState(() {
      _loggingOut = true;
      _error = null;
      _submission = null;
    });
    try {
      await callback();
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loggingOut = false);
    }
  }

  String _starterText(BuildContext context, _FactoryPreset preset) {
    final tr = _isTr(context);
    return switch (preset) {
      _FactoryPreset.web => tr
          ? 'Şirketim için premium, responsive bir web sitesi oluştur; test et ve bitmiş ürünü teslim et.'
          : 'Build a premium responsive website for my company, test it, and deliver the finished product.',
      _FactoryPreset.video => tr
          ? '20 saniyelik profesyonel bir ürün videosu oluştur, doğrula ve bitmiş videoyu teslim et.'
          : 'Create a professional 20-second product video, verify it, and deliver the finished video.',
      _FactoryPreset.software => tr
          ? 'İhtiyacımı karşılayan çalışan bir yazılım ürünü oluştur, test et ve doğrulanmış çıktıyı teslim et.'
          : 'Build a working software product for my requirement, test it, and deliver the verified output.',
    };
  }

  String _routePrefix(BuildContext context, _FactoryPreset preset) {
    final tr = _isTr(context);
    return switch (preset) {
      _FactoryPreset.web => tr ? 'Web sitesi oluşturma görevi:' : 'Website build task:',
      _FactoryPreset.video => tr ? 'Video oluşturma görevi:' : 'Video creation task:',
      _FactoryPreset.software => tr ? 'Yazılım oluşturma görevi:' : 'Software build task:',
    };
  }

  String _presetLabel(BuildContext context, _FactoryPreset preset) => switch (preset) {
        _FactoryPreset.web => _isTr(context) ? 'Web Factory' : 'Web Factory',
        _FactoryPreset.video => _isTr(context) ? 'Video Factory' : 'Video Factory',
        _FactoryPreset.software => _isTr(context) ? 'Software Factory' : 'Software Factory',
      };

  void _selectPreset(BuildContext context, _FactoryPreset preset) {
    final current = _controller.text.trim();
    final starterTexts = _FactoryPreset.values.map((item) => _starterText(context, item)).toSet();
    final shouldReplace = current.isEmpty || starterTexts.contains(current);
    setState(() {
      _selectedPreset = preset;
      _submission = null;
      _error = null;
      if (shouldReplace) {
        final text = _starterText(context, preset);
        _controller.text = text;
        _controller.selection = TextSelection.collapsed(offset: text.length);
      }
    });
  }

  Future<void> _submit() async {
    final callback = widget.onSubmit;
    final rawObjective = _controller.text.trim();
    if (callback == null || rawObjective.isEmpty || _submitting) return;
    final preset = _selectedPreset;
    final objective = preset == null
        ? rawObjective
        : '${_routePrefix(context, preset)} $rawObjective';
    setState(() {
      _submitting = true;
      _error = null;
      _submission = null;
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
    final scheme = Theme.of(context).colorScheme;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(
                      color: IlaiosTheme.enterpriseCyan.withValues(alpha: .13),
                      borderRadius: BorderRadius.circular(13),
                    ),
                    child: const Icon(
                      Icons.track_changes_outlined,
                      color: IlaiosTheme.enterpriseCyan,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.tr('goals.title'),
                          style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          context.tr('goals.subtitle'),
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              _IdentityCard(
                providers: widget.identityProviders,
                session: widget.userSession,
                status: widget.identityStatus,
                signingInProvider: _signingInProvider,
                loggingOut: _loggingOut,
                onSignIn: _signIn,
                onLogout: _logout,
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: scheme.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: scheme.outlineVariant),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        const Icon(
                          Icons.auto_awesome_outlined,
                          color: IlaiosTheme.violet,
                          size: 20,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _isTr(context) ? 'Tek prompt çalışma alanı' : 'One-prompt workspace',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w800,
                                ),
                          ),
                        ),
                        if (_selectedPreset case final preset?)
                          Container(
                            key: const Key('selected-factory-route'),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: _presetAccent(preset).withValues(alpha: .10),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(
                                color: _presetAccent(preset).withValues(alpha: .42),
                              ),
                            ),
                            child: Text(
                              _presetLabel(context, preset),
                              style: TextStyle(
                                color: _presetAccent(preset),
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      key: const Key('one-prompt-input'),
                      controller: _controller,
                      enabled: enabled && !_submitting,
                      minLines: 6,
                      maxLines: 10,
                      maxLength: 20000,
                      textInputAction: TextInputAction.newline,
                      onChanged: (_) => setState(() {}),
                      decoration: InputDecoration(
                        hintText: context.tr('goals.example'),
                        alignLabelWithHint: true,
                        border: const OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _isTr(context)
                          ? 'İş türünü seç — seçim yalnızca doğru Factory rotasını açıkça sabitler.'
                          : 'Choose the work type — the selection explicitly pins the intended Factory route.',
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                    const SizedBox(height: 9),
                    LayoutBuilder(
                      builder: (context, constraints) {
                        final width = constraints.maxWidth >= 780
                            ? (constraints.maxWidth - 20) / 3
                            : constraints.maxWidth;
                        return Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: [
                            _FactoryCard(
                              width: width,
                              preset: _FactoryPreset.web,
                              selected: _selectedPreset == _FactoryPreset.web,
                              icon: Icons.language_outlined,
                              accent: IlaiosTheme.enterpriseCyan,
                              title: 'Web Factory',
                              subtitle: _isTr(context)
                                  ? 'Web sitesi oluşturma ve teslim'
                                  : 'Website build and delivery',
                              onTap: () => _selectPreset(context, _FactoryPreset.web),
                            ),
                            _FactoryCard(
                              width: width,
                              preset: _FactoryPreset.video,
                              selected: _selectedPreset == _FactoryPreset.video,
                              icon: Icons.movie_creation_outlined,
                              accent: IlaiosTheme.coreBlue,
                              title: 'Video Factory',
                              subtitle: _isTr(context)
                                  ? 'Video oluşturma ve doğrulama'
                                  : 'Video creation and verification',
                              onTap: () => _selectPreset(context, _FactoryPreset.video),
                            ),
                            _FactoryCard(
                              width: width,
                              preset: _FactoryPreset.software,
                              selected: _selectedPreset == _FactoryPreset.software,
                              icon: Icons.code_outlined,
                              accent: IlaiosTheme.violet,
                              title: 'Software Factory',
                              subtitle: _isTr(context)
                                  ? 'Yazılım ürünü oluşturma ve test'
                                  : 'Software product build and test',
                              onTap: () => _selectPreset(context, _FactoryPreset.software),
                            ),
                          ],
                        );
                      },
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        FilledButton.icon(
                          key: const Key('one-prompt-submit'),
                          onPressed: enabled && !_submitting && _controller.text.trim().isNotEmpty
                              ? _submit
                              : null,
                          icon: _submitting
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.arrow_forward_rounded),
                          label: Text(
                            _submitting
                                ? context.tr('goals.submitting')
                                : context.tr('goals.startPrompt'),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Text(
                            enabled
                                ? _localizedStatus(context, widget.status)
                                : _disabledPromptReason(context, widget),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              if (_submission case final submission?) ...[
                const SizedBox(height: 16),
                Container(
                  key: const Key('one-prompt-accepted'),
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: IlaiosTheme.success.withValues(alpha: .07),
                    borderRadius: BorderRadius.circular(13),
                    border: Border.all(
                      color: IlaiosTheme.success.withValues(alpha: .35),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.check_circle_outline, color: IlaiosTheme.success),
                          const SizedBox(width: 10),
                          Text(
                            context.tr('goals.accepted'),
                            style: const TextStyle(fontWeight: FontWeight.w800),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      SelectableText('${context.tr('goals.goal')}: ${submission.goalId}'),
                      const SizedBox(height: 5),
                      SelectableText('${context.tr('goals.job')}: ${submission.jobId}'),
                      const SizedBox(height: 5),
                      Text('${context.tr('goals.authoritativeState')}: ${submission.state}'),
                      const SizedBox(height: 12),
                      Text(
                        context.tr('goals.submissionNote'),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
              if (_error case final error?) ...[
                const SizedBox(height: 16),
                Container(
                  key: const Key('one-prompt-error'),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: IlaiosTheme.danger.withValues(alpha: .08),
                    borderRadius: BorderRadius.circular(11),
                    border: Border.all(color: IlaiosTheme.danger.withValues(alpha: .35)),
                  ),
                  child: Text(error, style: const TextStyle(color: IlaiosTheme.danger)),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

Color _presetAccent(_FactoryPreset preset) => switch (preset) {
      _FactoryPreset.web => IlaiosTheme.enterpriseCyan,
      _FactoryPreset.video => IlaiosTheme.coreBlue,
      _FactoryPreset.software => IlaiosTheme.violet,
    };

class _FactoryCard extends StatefulWidget {
  const _FactoryCard({
    required this.width,
    required this.preset,
    required this.selected,
    required this.icon,
    required this.accent,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final double width;
  final _FactoryPreset preset;
  final bool selected;
  final IconData icon;
  final Color accent;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  State<_FactoryCard> createState() => _FactoryCardState();
}

class _FactoryCardState extends State<_FactoryCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) => MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: Material(
          color: widget.selected || _hovered
              ? widget.accent.withValues(alpha: .10)
              : Theme.of(context).colorScheme.surfaceContainerLowest,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: widget.selected || _hovered
                  ? widget.accent.withValues(alpha: .72)
                  : Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            key: ValueKey('factory-preset-${widget.preset.name}'),
            onTap: widget.onTap,
            child: SizedBox(
              width: widget.width,
              height: 88,
              child: Padding(
                padding: const EdgeInsets.all(13),
                child: Row(
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: widget.accent.withValues(alpha: .14),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(widget.icon, color: widget.accent, size: 20),
                    ),
                    const SizedBox(width: 11),
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            widget.subtitle,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 6),
                    Icon(
                      widget.selected ? Icons.check_circle : Icons.arrow_forward_ios_rounded,
                      color: widget.selected ? widget.accent : Theme.of(context).colorScheme.outline,
                      size: widget.selected ? 20 : 14,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}

class _IdentityCard extends StatelessWidget {
  const _IdentityCard({
    required this.providers,
    required this.session,
    required this.status,
    required this.signingInProvider,
    required this.loggingOut,
    required this.onSignIn,
    required this.onLogout,
  });

  final List<IdentityProviderOption> providers;
  final DesktopUserSession? session;
  final String status;
  final String? signingInProvider;
  final bool loggingOut;
  final Future<void> Function(String providerId) onSignIn;
  final Future<void> Function() onLogout;

  @override
  Widget build(BuildContext context) {
    final current = session;
    final scheme = Theme.of(context).colorScheme;
    return Container(
      key: const Key('identity-card'),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: IlaiosTheme.enterpriseCyan.withValues(alpha: .28)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: IlaiosTheme.enterpriseCyan.withValues(alpha: .12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.verified_user_outlined,
              color: IlaiosTheme.enterpriseCyan,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.tr('goals.account'),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 8),
                if (current != null) ...[
                  Text(
                    current.displayIdentity ?? current.principalId,
                    key: const Key('identity-signed-in'),
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${context.tr('goals.provider')}: ${current.providerId}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    key: const Key('identity-logout'),
                    onPressed: loggingOut ? null : onLogout,
                    icon: const Icon(Icons.logout),
                    label: Text(
                      loggingOut
                          ? context.tr('goals.signingOut')
                          : context.tr('goals.signOut'),
                    ),
                  ),
                ] else if (providers.isNotEmpty) ...[
                  Text(
                    context.tr('goals.signInNote'),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      for (final provider in providers)
                        OutlinedButton.icon(
                          key: ValueKey('identity-provider-${provider.providerId}'),
                          onPressed: signingInProvider == null
                              ? () => onSignIn(provider.providerId)
                              : null,
                          icon: signingInProvider == provider.providerId
                              ? const SizedBox(
                                  width: 15,
                                  height: 15,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.login),
                          label: Text(
                            signingInProvider == provider.providerId
                                ? context.tr('goals.signingIn')
                                : '${context.tr('goals.continueWith')} ${provider.displayName}',
                          ),
                        ),
                    ],
                  ),
                ] else
                  Text(
                    _localizedIdentity(context, status),
                    key: const Key('identity-not-configured'),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

String _disabledPromptReason(BuildContext context, CreateView widget) {
  if (!widget.projection.connected) return context.tr('goals.controlPlaneUnavailable');
  if (widget.identityProviders.isNotEmpty && widget.userSession == null) {
    return context.tr('goals.signInRequired');
  }
  return _localizedStatus(context, widget.status);
}

String _localizedStatus(BuildContext context, String value) {
  if (!_isTr(context)) return value;
  return switch (value) {
    'Operational APIs connected' => 'Operasyon API’leri bağlı',
    'Connected to authoritative control plane' => 'Yetkili kontrol düzlemine bağlı',
    _ => value,
  };
}

String _localizedIdentity(BuildContext context, String value) {
  if (!_isTr(context)) return value;
  if (value.startsWith('Signed in as ')) {
    return 'Oturum açık: ${value.substring('Signed in as '.length)}';
  }
  return switch (value) {
    'Signed out' => 'Oturum kapalı',
    'Account sign-in is not configured' => 'Hesap girişi yapılandırılmadı',
    _ => value,
  };
}

bool _isTr(BuildContext context) => context.ilaiosLocale.locale == IlaiosLocale.turkish;
