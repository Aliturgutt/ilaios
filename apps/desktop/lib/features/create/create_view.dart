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
              Text(
                context.tr('goals.title'),
                style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(
                context.tr('goals.subtitle'),
                style: const TextStyle(color: IlaiosTheme.muted, height: 1.5),
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
              const SizedBox(height: 18),
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
                        decoration: InputDecoration(
                          hintText: context.tr('goals.example'),
                          border: const OutlineInputBorder(),
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
                                  ? widget.status
                                  : _disabledPromptReason(context, widget),
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
                        Row(
                          children: [
                            const Icon(
                              Icons.check_circle_outline,
                              color: IlaiosTheme.success,
                            ),
                            const SizedBox(width: 10),
                            Text(
                              context.tr('goals.accepted'),
                              style: const TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        SelectableText('${context.tr('goals.goal')}: ${submission.goalId}'),
                        const SizedBox(height: 5),
                        SelectableText('${context.tr('goals.job')}: ${submission.jobId}'),
                        const SizedBox(height: 5),
                        Text(
                          '${context.tr('goals.authoritativeState')}: ${submission.state}',
                        ),
                        const SizedBox(height: 12),
                        Text(
                          context.tr('goals.submissionNote'),
                          style: const TextStyle(
                            color: IlaiosTheme.muted,
                            height: 1.45,
                          ),
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
    return Card(
      key: const Key('identity-card'),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.verified_user_outlined, color: IlaiosTheme.cyan),
                const SizedBox(width: 10),
                Text(
                  context.tr('goals.account'),
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (current != null) ...[
              Text(
                current.displayIdentity ?? current.principalId,
                key: const Key('identity-signed-in'),
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 5),
              Text(
                '${context.tr('goals.provider')}: ${current.providerId}',
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12),
              ),
              const SizedBox(height: 12),
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
                style: const TextStyle(color: IlaiosTheme.muted, height: 1.45),
              ),
              const SizedBox(height: 14),
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
                status,
                key: const Key('identity-not-configured'),
                style: const TextStyle(color: IlaiosTheme.muted, height: 1.45),
              ),
          ],
        ),
      ),
    );
  }
}

String _disabledPromptReason(BuildContext context, CreateView widget) {
  if (!widget.projection.connected) {
    return context.tr('goals.controlPlaneUnavailable');
  }
  if (widget.identityProviders.isNotEmpty && widget.userSession == null) {
    return context.tr('goals.signInRequired');
  }
  return widget.status;
}
