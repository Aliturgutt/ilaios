/// Canonical factory IDs from services/capability_registry.py.
abstract final class DesktopFactorySelection {
  static const ids = <String>[
    'ilaios.capability.web-factory',
    'ilaios.capability.video-media-factory',
    'ilaios.capability.software-factory',
    'ilaios.capability.app-factory',
    'ilaios.capability.research-data',
    'ilaios.capability.security-factory',
    'ilaios.capability.creative-document',
    'ilaios.capability.commerce-growth',
    'ilaios.capability.personal-operations',
  ];
  static bool valid(String id) => ids.contains(id);
}

/// One-shot UI-to-authenticated-transport selection, cleared after each attempt.
abstract final class FactorySelectionSubmissionBus {
  static String? _pending;
  static void stage(String? id) {
    if (id != null && !DesktopFactorySelection.valid(id)) {
      throw ArgumentError.value(id, 'id', 'Unknown factory');
    }
    _pending = id;
  }

  static String? take() {
    final id = _pending;
    _pending = null;
    return id;
  }

  static void clear() => _pending = null;
}
