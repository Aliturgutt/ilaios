import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_app.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

class _ConversationFixture {
  _ConversationFixture({this.founder = false});
  final bool founder;
  final Map<String, dynamic> document = {
    'conversation_id': 'conversation-1', 'version': 0,
    'messages': <Map<String, dynamic>>[],
  };
  bool created = false;
  int founderReads = 0;

  DesktopUserSession get session => DesktopUserSession(
    sessionId: 'session', providerId: 'google', principalId: 'usr_user',
    tenantId: 'tnt_user', liFounder: founder,
  );

  Future<Map<String, dynamic>> request(Map<String, Object?> request) async {
    final binding = <String, dynamic>{
      'user_id': 'usr_user', 'tenant_id': 'tnt_user',
      'project_id': null, 'workload_id': null,
      'persona': founder ? 'li' : 'assistant',
    };
    if (request['operation'] == 'list') {
      return {'binding': binding, 'conversations': <Map<String, dynamic>>[
        if (created) {'conversation_id': 'conversation-1'},
      ]};
    }
    if (request['operation'] == 'create') created = true;
    document['binding'] = binding;
    if (request['operation'] == 'send') {
      (document['messages'] as List).addAll([
        {'role': 'user', 'text': request['text']},
        {'role': 'assistant', 'text': 'UNKNOWN', 'provenance': []},
      ]);
      document['version'] = (document['version'] as int) + 1;
    }
    return {'binding': binding, 'conversation': document};
  }

  Future<DesktopLiState> verify() async {
    founderReads++;
    return const DesktopLiState(name: 'Li', founderOperator: true,
        userId: 'usr_user', tenantId: 'tnt_user', source: 'canonical_desktop_session');
  }

  Widget app({IlaiosLocale locale = IlaiosLocale.english, ThemeMode theme = ThemeMode.light}) =>
      IlaiosDesktopApp(locale: locale, themeMode: theme, userSession: session,
          onAssistantRequest: request, onFetchLiState: verify);
}

void main() {
  for (final locale in IlaiosLocale.values) {
    for (final founder in [false, true]) {
      for (final theme in [ThemeMode.light, ThemeMode.dark]) {
      testWidgets('shared sidebar / authorized persona $locale $theme founder=$founder', (tester) async {
        await tester.binding.setSurfaceSize(const Size(1536, 1024));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        final fixture = _ConversationFixture(founder: founder);
        await tester.pumpWidget(fixture.app(locale: locale, theme: theme));
        await tester.pumpAndSettle();
        final trigger = find.byKey(const Key('nav-assistant'));
        expect(find.descendant(of: trigger, matching: find.text(
            locale == IlaiosLocale.turkish ? 'Asistan' : 'Assistant')), findsOneWidget);
        expect(find.descendant(of: trigger, matching: find.textContaining('Li')), findsNothing);
        final home = tester.element(find.byKey(const Key('command-center-home')));
        final promptRect = tester.getRect(find.byKey(const Key('home-command-prompt')));
        final startRect = tester.getRect(find.byKey(const Key('home-new-work')));
        final attachmentRect = tester.getRect(find.byKey(const Key('home-prompt-attachments')));
        await tester.tap(trigger);
        await tester.pumpAndSettle();
        expect(find.text(founder ? 'Li — Founder Intelligence' : 'ILAIOS Assistant'), findsOneWidget);
        expect(fixture.founderReads, founder ? 1 : 0);
        if (!founder) {
          expect(find.textContaining('Li'), findsNothing);
          expect(find.byKey(const Key('assistant-memory')), findsNothing);
        }
        expect(identical(home, tester.element(find.byKey(const Key('command-center-home')))), isTrue);
        expect(tester.getRect(find.byKey(const Key('home-command-prompt'))), promptRect);
        expect(tester.getRect(find.byKey(const Key('home-new-work'))), startRect);
        expect(tester.getRect(find.byKey(const Key('home-prompt-attachments'))), attachmentRect);
        final left = tester.getRect(find.byKey(const Key('assistant-history-arm')));
        final lower = tester.getRect(find.byKey(const Key('assistant-conversation-arm')));
        expect(left.width, 290);
        expect(left.top, greaterThanOrEqualTo(tester.getRect(trigger).bottom));
        expect(left.top, lessThan(lower.top));
        expect(lower.top, closeTo(637, 1));
        expect(lower.bottom, closeTo(995, 1));
        expect(tester.getSize(find.byKey(const Key('canonical-7-page-sidebar'))).width, 219);
        await tester.tap(find.byKey(const Key('assistant-close')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('assistant-conversation-arm')), findsNothing);
        expect(tester.getRect(find.byKey(const Key('home-new-work'))), startRect);
        expect(tester.takeException(), isNull);
      });
      }
    }
  }

  testWidgets('conversation survives close, navigation and UI restart', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final fixture = _ConversationFixture();
    await tester.pumpWidget(fixture.app());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('assistant-composer')), 'My task');
    await tester.tap(find.byKey(const Key('assistant-send')));
    await tester.pumpAndSettle();
    expect(find.text('My task'), findsOneWidget);
    await tester.tap(find.byKey(const Key('assistant-close')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-settings')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pumpAndSettle();
    expect(find.text('My task'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpWidget(fixture.app());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pumpAndSettle();
    expect(find.text('My task'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('forged founder response is rejected before presentation', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final fixture = _ConversationFixture();
    await tester.pumpWidget(IlaiosDesktopApp(userSession: fixture.session,
      onAssistantRequest: (_) async => {'binding': {
        'user_id': 'usr_user', 'tenant_id': 'tnt_user', 'project_id': null,
        'workload_id': null, 'persona': 'li'}, 'conversations': []},
      onFetchLiState: fixture.verify));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pumpAndSettle();
    expect(find.text('Li — Founder Intelligence'), findsNothing);
    expect(find.byKey(const Key('assistant-memory')), findsNothing);
    expect(fixture.founderReads, 0);
    expect(find.byKey(const Key('assistant-error')), findsOneWidget);
  });

  testWidgets('chat does not submit work; explicit confirmed handoff reuses callback', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final fixture = _ConversationFixture();
    var submissions = 0;
    await tester.pumpWidget(IlaiosDesktopApp(userSession: fixture.session,
      onAssistantRequest: fixture.request,
      onPromptSubmit: (_) async {
        submissions++;
        return const PromptSubmission(goalId: 'goal', jobId: 'job', state: 'pending');
      }));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('assistant-composer')), 'Make a website');
    await tester.tap(find.byKey(const Key('assistant-send')));
    await tester.pumpAndSettle();
    expect(submissions, 0);
    await tester.enterText(find.byKey(const Key('assistant-composer')), 'Make a website');
    await tester.tap(find.byKey(const Key('assistant-submit-work')));
    await tester.pumpAndSettle();
    expect(submissions, 0);
    await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
    await tester.pumpAndSettle();
    expect(submissions, 1);
    expect(tester.takeException(), isNull);
  });
}
