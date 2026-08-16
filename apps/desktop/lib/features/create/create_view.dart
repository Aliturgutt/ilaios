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

class _CreateViewState extends State<CreateView> {
  final TextEditingController _controller = TextEditingController();
  bool _submitting = false;
  String? _signingInProvider;
  bool _loggingOut = false;
  PromptSubmission? _submission;
  String? _error;

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

  void _useStarter(String value) {
    _controller.text = value;
    _controller.selection = TextSelection.collapsed(offset: value.length);
    setState(() {});
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
                        Text(
                          _isTr(context) ? 'Tek prompt çalışma alanı' : 'One-prompt workspace',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.w800,
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
                    const SizedBox(height: 4),
                    Text(
                      _isTr(context) ? 'Hızlı başlangıç' : 'Quick start',
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                    const SizedBox(height: 7),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _StarterChip(
                          icon: Icons.language_outlined,
                          accent: IlaiosTheme.enterpriseCyan,
                          label: _isTr(context) ? 'Web sitesi' : 'Website',
                          onTap: () => _useStarter(
                            _isTr(context)
                                ? 'Şirketim için premium, responsive bir web sitesi oluştur; test et ve bitmiş ürünü teslim et.'
                                : 'Build a premium responsive website for my company, test it, and deliver the finished product.',
                          ),
                        ),
                        _StarterChip(
                          icon: Icons.movie_creation_outlined,
                          accent: IlaiosTheme.coreBlue,
                          label: _isTr(context) ? 'Video' : 'Video',
                          onTap: () => _useStarter(
                            _isTr(context)
                                ? '20 saniyelik profesyonel bir ürün videosu oluştur, doğrula ve bitmiş videoyu teslim et.'
                                : 'Create a professional 20-second product video, verify it, and deliver the finished video.',
                          ),
                        ),
                        _StarterChip(
                          icon: Icons.code_outlined,
                          accent: IlaiosTheme.violet,
                          label: _isTr(context) ? 'Yazılım' : 'Software',
                          onTap: () => _useStarter(
                            _isTr(context)
                                ? 'İhtiyacımı karşılayan çalışan bir yazılım ürünü oluştur, test et ve doğrulanmış çıktıyı teslim et.'
                                : 'Build a working software product for my requirement, test it, and deliver the verified output.',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
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

class _StarterChip extends StatelessWidget {
  const _StarterChip({
    required this.icon,
    required this.accent,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final Color accent;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ActionChip(
        onPressed: onTap,
        avatar: Icon(icon, color: accent, size: 17),
        label: Text(label),
        side: BorderSide(color: accent.withValues(alpha: .35)),
        backgroundColor: accent.withValues(alpha: .06),
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
