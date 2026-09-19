import 'dart:io';

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';

typedef SubscriptionOpener = Future<void> Function(Uri uri);

/// Open the shared account surface without copying credentials or plan state.
class SubscriptionEntry extends StatefulWidget {
  const SubscriptionEntry({this.opener, super.key});

  final SubscriptionOpener? opener;

  @override
  State<SubscriptionEntry> createState() => _SubscriptionEntryState();
}

class _SubscriptionEntryState extends State<SubscriptionEntry> {
  bool _opening = false;

  Future<void> _open() async {
    final tr = context.ilaiosLocale.locale == IlaiosLocale.turkish;
    final uri = Uri.https('app.ilaios.com', '/subscription', {
      'lang': tr ? 'tr' : 'en',
    });
    setState(() => _opening = true);
    try {
      final opener = widget.opener;
      if (opener != null) {
        await opener(uri);
      } else {
        if (!Platform.isWindows) {
          throw UnsupportedError('Windows browser launcher required');
        }
        await Process.start(
          'rundll32.exe',
          ['url.dll,FileProtocolHandler', uri.toString()],
          mode: ProcessStartMode.detached,
        );
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr
            ? 'Aboneliğinizi görmek için tarayıcıda aynı ILAIOS hesabıyla giriş yapın.'
            : 'Sign in with the same ILAIOS account in your browser to view your subscription.'),
      ));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr
            ? 'Abonelik sayfası açılamadı. app.ilaios.com/subscription adresini açın.'
            : 'Could not open subscription. Visit app.ilaios.com/subscription.'),
      ));
    } finally {
      if (mounted) setState(() => _opening = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final tr = context.ilaiosLocale.locale == IlaiosLocale.turkish;
    return TextButton.icon(
      key: const Key('subscription-entry'),
      onPressed: _opening ? null : _open,
      icon: const Icon(Icons.open_in_new, size: 16),
      label: Text(tr ? 'Planlar ve abonelik' : 'Plans & subscription'),
      style: TextButton.styleFrom(
        foregroundColor: Theme.of(context).colorScheme.onSurface,
      ),
    );
  }
}
