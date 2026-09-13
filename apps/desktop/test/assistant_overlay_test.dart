import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_app.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

class _ConversationFixture {
  _ConversationFixture({this.founder = false, this.user = 'usr_user',
    this.tenant = 'tnt_user', this.sessionId = 'session'});
  final String user;
  final String tenant;
  final String sessionId;
  final bool founder;
  final Map<String, dynamic> document = {
    'conversation_id': 'conversation-1', 'version': 0,
    'messages': <Map<String, dynamic>>[],
  };
  bool created = false;
  int founderReads = 0;
  final exchanges = <Map<String, dynamic>>[];

  Map<String, dynamic> _record(Map<String, Object?> request,
      Map<String, dynamic> response) {
    // Snapshot transport evidence; later fixture mutations must not change it.
    exchanges.add(jsonDecode(jsonEncode({
      'request': request, 'response': response,
    })) as Map<String, dynamic>);
    return response;
  }

  DesktopUserSession get session => DesktopUserSession(
    sessionId: sessionId, providerId: 'google', principalId: user,
    tenantId: tenant, liFounder: founder,
  );

  Future<Map<String, dynamic>> request(Map<String, Object?> request) async {
    final binding = <String, dynamic>{
      'user_id': user, 'tenant_id': tenant,
      'project_id': null, 'workload_id': null,
      'persona': founder ? 'li' : 'assistant',
    };
    if (request['operation'] == 'list') {
      return _record(request, {'binding': binding, 'conversations': <Map<String, dynamic>>[
        if (created) {'conversation_id': 'conversation-1'},
      ]});
    }
    if (request['operation'] == 'create') created = true;
    document['binding'] = binding;
    if (request['operation'] == 'send') {
      (document['messages'] as List<Map<String, dynamic>>).addAll([
        {'role': 'user', 'text': request['text']},
        {'role': 'assistant', 'text': 'UNKNOWN', 'provenance': []},
      ]);
      document['version'] = (document['version'] as int) + 1;
    }
    return _record(request, {'binding': binding, 'conversation': document});
  }

  Future<DesktopLiState> verify() async {
    founderReads++;
    return DesktopLiState(name: 'Li', founderOperator: true,
        userId: user, tenantId: tenant, source: 'canonical_desktop_session');
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
        final topBar = tester.getRect(find.byKey(const Key('canonical-7-page-topbar')));
        final home = tester.element(find.byKey(const Key('command-center-home')));
        final promptRect = tester.getRect(find.byKey(const Key('home-command-prompt')));
        final startRect = tester.getRect(find.byKey(const Key('home-new-work')));
        final attachmentRect = tester.getRect(find.byKey(const Key('home-prompt-attachments')));
        await tester.tap(trigger);
        await tester.pumpAndSettle();
        expect(find.text(founder ? 'Li — Founder Intelligence' : 'ILAIOS Assistant'), findsOneWidget);
        expect(fixture.founderReads, founder ? 1 : 0);
        final symbolPath = theme == ThemeMode.dark
            ? '../../brand/assets/05-ilaios-app-icon.jpg'
            : '../../brand/assets/04-ilaios-symbol-light.jpg';
        for (final surface in [trigger,
          find.byKey(const Key('assistant-history-arm')),
          find.byKey(const Key('assistant-conversation-arm'))]) {
          final symbols = tester.widgetList<Image>(find.descendant(
              of: surface, matching: find.byType(Image)));
          expect(symbols.any((image) => image.image is AssetImage &&
              (image.image as AssetImage).assetName == symbolPath &&
              image.fit == BoxFit.contain && image.color == null), isTrue);
        }
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
        expect(tester.getRect(find.byKey(const Key('canonical-7-page-topbar'))), topBar);
        expect(left.width, 290);
        expect(left, const Rect.fromLTRB(0, 482, 290, 995));
        expect(lower, const Rect.fromLTRB(290, 637, 1524, 995));
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

  for (final change in ['user', 'tenant', 'session', 'logout']) {
    testWidgets('session boundary clears history and draft: $change', (tester) async {
      await tester.binding.setSurfaceSize(const Size(1536, 1024));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final first = _ConversationFixture(founder: true);
      await tester.pumpWidget(first.app());
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('nav-assistant')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('assistant-composer')), 'Private history');
      await tester.tap(find.byKey(const Key('assistant-send')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('assistant-composer')), 'Private draft');
      final next = _ConversationFixture(
        user: change == 'user' ? 'usr_other' : 'usr_user',
        tenant: change == 'tenant' ? 'tnt_other' : 'tnt_user',
        sessionId: change == 'session' ? 'new-session' : 'session',
        founder: true,
      );
      await tester.pumpWidget(change == 'logout'
          ? const IlaiosDesktopApp() : next.app());
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('assistant-composer'), skipOffstage: false), findsNothing);
      expect(find.text('Private history', skipOffstage: false), findsNothing);
      expect(find.text('Private draft', skipOffstage: false), findsNothing);
      if (change != 'logout') {
        await tester.tap(find.byKey(const Key('nav-assistant')));
        await tester.pumpAndSettle();
        expect(find.text('Private history'), findsNothing);
        expect(find.text('Private draft'), findsNothing);
      }
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('late old-session response cannot restore private state', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final old = _ConversationFixture();
    final pending = Completer<Map<String, dynamic>>();
    var oldRequests = 0;
    await tester.pumpWidget(IlaiosDesktopApp(userSession: old.session,
        onAssistantRequest: (_) { oldRequests++; return pending.future; }));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pump();
    final next = _ConversationFixture(user: 'usr_other', sessionId: 'other-session');
    await tester.pumpWidget(next.app());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pumpAndSettle();
    pending.complete({'binding': {
      'user_id': 'usr_user', 'tenant_id': 'tnt_user', 'project_id': null,
      'workload_id': null, 'persona': 'assistant'},
      'conversations': [{'conversation_id': 'private-old-history'}]});
    await tester.pumpAndSettle();
    expect(oldRequests, 1);
    expect(find.text('private-old-history', skipOffstage: false), findsNothing);
    expect(find.byKey(const Key('assistant-error')), findsNothing);
    expect(find.byKey(const Key('assistant-composer')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('opening over Agents preserves page and pixel workspace', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_ConversationFixture().app());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-agents')));
    await tester.pumpAndSettle();
    final workspace = find.byKey(const Key('agents-pixel-workspace'));
    final element = tester.element(workspace);
    final rect = tester.getRect(workspace);
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pumpAndSettle();
    expect(identical(element, tester.element(workspace)), isTrue);
    expect(tester.getRect(workspace), rect);
    expect(tester.getRect(find.byKey(const Key('assistant-history-arm'))),
        const Rect.fromLTRB(0, 482, 290, 995));
    await tester.tap(find.byKey(const Key('assistant-close')));
    await tester.pumpAndSettle();
    expect(identical(element, tester.element(workspace)), isTrue);
    expect(tester.getRect(workspace), rect);
    expect(tester.takeException(), isNull);
  });

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
    expect(fixture.document['version'], 1,
        reason: 'Initial send must persist: ${jsonEncode(fixture.exchanges)}');
    expect(tester.widget<TextField>(find.byKey(const Key('assistant-composer')))
        .controller!.text, isEmpty);
    expect(find.text('My task'), findsOneWidget);
    await tester.tap(find.byKey(const Key('assistant-close')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-settings')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pumpAndSettle();
    expect(find.text('My task'), findsOneWidget);
    fixture.exchanges.clear();
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpWidget(fixture.app());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nav-assistant')));
    await tester.pumpAndSettle();
    final trace = jsonEncode(fixture.exchanges);
    expect(fixture.exchanges.map((entry) => entry['request']['operation']),
        ['list', 'get'], reason: 'Restart request sequence: $trace');
    final listed = fixture.exchanges[0]['response'];
    expect(listed['conversations'], [{'conversation_id': 'conversation-1'}],
        reason: 'Restart list response: $trace');
    expect(fixture.exchanges[1]['request']['conversation_id'], 'conversation-1',
        reason: 'Restart get target: $trace');
    final restored = fixture.exchanges[1]['response']['conversation'];
    expect(restored['messages'], contains({'role': 'user', 'text': 'My task'}),
        reason: 'Restart get payload: $trace');
    expect(find.byKey(const Key('assistant-error')), findsNothing,
        reason: 'Restart load/accept rejected transport: $trace');
    expect(find.byWidgetPredicate((widget) => widget is ListTile && widget.selected),
        findsOneWidget, reason: 'Restored conversation was not selected: $trace');
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
