import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../control_plane/client.dart';
import '../control_plane/evidence_record.dart';
import '../control_plane/operational_snapshot.dart';
import '../control_plane/projection.dart';
import '../features/create/reference_asset_picker.dart';
import '../features/dashboard/reference_desktop_shell_v11.dart';
import '../identity/identity_client.dart';
import 'ilaios_locale.dart';
import 'ilaios_theme.dart';
import 'ilaios_theme_mode.dart';

class IlaiosDesktopApp extends StatefulWidget {
  const IlaiosDesktopApp({
    super.key,
    this.projection = const ControlPlaneProjection.unavailable(),
    this.operationalSnapshot = const OperationalSnapshot.unavailable(),
    this.operationalStatus = 'Operational APIs not connected',
    this.approverId,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.locale = IlaiosLocale.english,
    this.themeMode = ThemeMode.dark,
    this.onLocaleChanged,
    this.onThemeModeChanged,
    this.onSignIn,
    this.onLogout,
    this.onPromptSubmit,
    this.onSaveArtifact,
    this.onFetchLiState,
    this.onFetchLiMemories,
    this.onRememberLiMemory,
    this.onRefreshRequested,
    this.onProvisionAgent,
    this.onGovernanceDecision,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final String? approverId;
  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final String identityStatus;
  final IlaiosLocale locale;
  final ThemeMode themeMode;
  final ValueChanged<IlaiosLocale>? onLocaleChanged;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;
  final Future<DesktopLiState> Function()? onFetchLiState;
  final Future<List<DesktopLiMemory>> Function()? onFetchLiMemories;
  final Future<DesktopLiMemory> Function(String kind, String content)?
      onRememberLiMemory;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String agentId)? onProvisionAgent;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

  @override
  State<IlaiosDesktopApp> createState() => _IlaiosDesktopAppState();
}

class _IlaiosDesktopAppState extends State<IlaiosDesktopApp>
    with WidgetsBindingObserver {
  static const Duration _operationalRefreshInterval = Duration(seconds: 2);

  late ThemeMode _localThemeMode = widget.themeMode;
  final ReferenceAssetPickerController _referenceAssets =
      ReferenceAssetPickerController();
  Timer? _operationalRefreshTimer;
  AppLifecycleState _lifecycleState = AppLifecycleState.resumed;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _lifecycleState =
        WidgetsBinding.instance.lifecycleState ?? AppLifecycleState.resumed;
    _restartOperationalRefresh();
    if (kReleaseMode && widget.onThemeModeChanged == null) {
      unawaited(_loadTheme());
    }
  }

  @override
  void didUpdateWidget(covariant IlaiosDesktopApp oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.themeMode != oldWidget.themeMode &&
        widget.onThemeModeChanged != null) {
      _localThemeMode = widget.themeMode;
    }
    if (widget.onRefreshRequested != oldWidget.onRefreshRequested) {
      _restartOperationalRefresh();
    }
    if (oldWidget.userSession != null && widget.userSession == null) {
      _referenceAssets.clear();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _lifecycleState = state;
    if (state == AppLifecycleState.resumed) {
      widget.onRefreshRequested?.call();
    }
  }

  @override
  void dispose() {
    _operationalRefreshTimer?.cancel();
    _referenceAssets.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  void _restartOperationalRefresh() {
    _operationalRefreshTimer?.cancel();
    if (widget.onRefreshRequested == null) return;
    _operationalRefreshTimer = Timer.periodic(
      _operationalRefreshInterval,
      (_) {
        if (!mounted || _lifecycleState != AppLifecycleState.resumed) return;
        widget.onRefreshRequested?.call();
      },
    );
  }

  Future<void> _loadTheme() async {
    final mode = await IlaiosThemeModeStore.load();
    if (!mounted || widget.onThemeModeChanged != null || mode == _localThemeMode) {
      return;
    }
    setState(() => _localThemeMode = mode);
  }

  void _changeTheme(ThemeMode mode) {
    if (widget.onThemeModeChanged != null) {
      widget.onThemeModeChanged!(mode);
      return;
    }
    if (_localThemeMode != mode) setState(() => _localThemeMode = mode);
    if (kReleaseMode) unawaited(IlaiosThemeModeStore.save(mode));
  }

  String _localeText(String english, String turkish) =>
      widget.locale == IlaiosLocale.turkish ? turkish : english;

  Future<PromptSubmission> _submitPrompt(String objective) async {
    final callback = widget.onPromptSubmit;
    if (callback == null) {
      throw StateError(
        _localeText(
          'Desktop prompt submission is unavailable.',
          'Desktop prompt gönderimi kullanılamıyor.',
        ),
      );
    }
    final hasReferences = _referenceAssets.assets.isNotEmpty;
    final hasSourceVideo = _referenceAssets.sourceVideo.source != null;
    final referenceFactoryCount = _referenceFactoryCount(objective);
    final videoFactory = _isVideoFactoryObjective(objective);
    if (hasReferences && referenceFactoryCount == 0) {
      throw StateError(
        _localeText(
          'Reference images can only be attached to Web Factory or Video Factory goals.',
          'Referans görseller yalnızca Web Factory veya Video Factory hedeflerine eklenebilir.',
        ),
      );
    }
    if (hasReferences && referenceFactoryCount != 1) {
      throw StateError(
        _localeText(
          'A reference-image goal must target exactly one of Web Factory or Video Factory.',
          'Referans görselli bir hedef tam olarak Web Factory veya Video Factory’den birini hedeflemelidir.',
        ),
      );
    }
    if (hasSourceVideo && !videoFactory) {
      throw StateError(
        _localeText(
          'Source video can only be attached to a Video Factory goal.',
          'Kaynak video yalnızca Video Factory hedefine eklenebilir.',
        ),
      );
    }
    if (hasSourceVideo && hasReferences) {
      throw StateError(
        _localeText(
          'Source video and reference images cannot be combined until that exact revision contract is verified.',
          'Bu birleşik revizyon sözleşmesi doğrulanana kadar kaynak video ile referans görseller birlikte kullanılamaz.',
        ),
      );
    }
    final result = await callback(objective);
    if ((hasReferences && referenceFactoryCount == 1) || hasSourceVideo) {
      _referenceAssets.clear();
      if (mounted) setState(() {});
    }
    return result;
  }

  @override
  Widget build(BuildContext context) {
    final effectiveTheme =
        widget.onThemeModeChanged == null ? _localThemeMode : widget.themeMode;
    final darkDesktopTheme = IlaiosTheme.dark;
    return MaterialApp(
      title: 'ILAIOS Desktop',
      debugShowCheckedModeBanner: false,
      theme: IlaiosTheme.light,
      darkTheme: darkDesktopTheme,
      themeMode: effectiveTheme,
      home: IlaiosLocaleScope(
        locale: widget.locale,
        onChanged: (value) => widget.onLocaleChanged?.call(value),
        child: Builder(
          builder: (context) => ReferenceDesktopShellV11(
            projection: widget.projection,
            operationalSnapshot: widget.operationalSnapshot,
            operationalStatus: widget.operationalStatus,
            approverId: widget.approverId,
            identityProviders: widget.identityProviders,
            userSession: widget.userSession,
            identityStatus: widget.identityStatus,
            themeMode: effectiveTheme,
            referenceAssets: _referenceAssets,
            onThemeModeChanged: _changeTheme,
            onSignIn: widget.onSignIn,
            onLogout: widget.onLogout,
            onPromptSubmit:
                widget.onPromptSubmit == null ? null : _submitPrompt,
            onSaveArtifact: widget.onSaveArtifact,
            onFetchLiState: widget.onFetchLiState,
            onFetchLiMemories: widget.onFetchLiMemories,
            onRememberLiMemory: widget.onRememberLiMemory,
            onRefreshRequested: widget.onRefreshRequested,
            onProvisionAgent: widget.onProvisionAgent,
            onGovernanceDecision: widget.onGovernanceDecision,
          ),
        ),
      ),
    );
  }
}

bool _isVideoFactoryObjective(String objective) {
  final normalized = objective.trimLeft().toLowerCase();
  return normalized.startsWith('video creation task:') ||
      normalized.startsWith('video oluşturma görevi:');
}

int _referenceFactoryCount(String objective) {
  final normalized = objective.trimLeft().toLowerCase();
  final video = _isVideoFactoryObjective(normalized);
  const webTerms = <String>{
    'website',
    'web site',
    'web sitesi',
    'landing page',
    'internet sitesi',
  };
  final web = webTerms.any(normalized.contains);
  return (video ? 1 : 0) + (web ? 1 : 0);
}
