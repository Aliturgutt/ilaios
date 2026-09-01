enum DesktopRuntimeStatusKind {
  connected,
  offline,
  unavailable,
  localControlPlaneFailure,
  unknown,
}

class DesktopRuntimeStatusPresentation {
  const DesktopRuntimeStatusPresentation({
    required this.kind,
    required this.label,
    required this.detail,
  });

  final DesktopRuntimeStatusKind kind;
  final String label;
  final String detail;
}

DesktopRuntimeStatusPresentation presentDesktopRuntimeStatus(
  String rawStatus, {
  required bool connected,
  required bool turkish,
}) {
  final raw = rawStatus.trim();
  final normalized = raw.toLowerCase();

  if (normalized.startsWith('bundled local control plane failed to start') ||
      normalized.contains('bundled local control plane did not become identity-ready')) {
    return DesktopRuntimeStatusPresentation(
      kind: DesktopRuntimeStatusKind.localControlPlaneFailure,
      label: turkish
          ? 'Yerel kontrol düzlemine bağlanılamadı.'
          : 'Could not connect to the local control plane.',
      detail: raw,
    );
  }

  if (normalized == 'bundled local control plane started') {
    return DesktopRuntimeStatusPresentation(
      kind: DesktopRuntimeStatusKind.connected,
      label: turkish
          ? 'Yerel kontrol düzlemi bağlı.'
          : 'Local control plane connected.',
      detail: raw,
    );
  }

  if (normalized == 'using trusted externally configured control plane') {
    return DesktopRuntimeStatusPresentation(
      kind: DesktopRuntimeStatusKind.connected,
      label: turkish
          ? 'Güvenilir harici kontrol düzlemi bağlı.'
          : 'Trusted external control plane connected.',
      detail: raw,
    );
  }

  if (normalized == 'operational apis connected') {
    return DesktopRuntimeStatusPresentation(
      kind: DesktopRuntimeStatusKind.connected,
      label: turkish
          ? 'Operasyonel hizmetler bağlı.'
          : 'Operational services connected.',
      detail: raw,
    );
  }

  if (normalized == 'operational apis not connected' ||
      normalized == 'control plane configuration unavailable') {
    return DesktopRuntimeStatusPresentation(
      kind: connected
          ? DesktopRuntimeStatusKind.unavailable
          : DesktopRuntimeStatusKind.offline,
      label: turkish
          ? 'Operasyonel hizmetler kullanılamıyor.'
          : 'Operational services are unavailable.',
      detail: raw,
    );
  }

  if (raw.isEmpty) {
    return DesktopRuntimeStatusPresentation(
      kind: connected
          ? DesktopRuntimeStatusKind.unavailable
          : DesktopRuntimeStatusKind.offline,
      label: turkish ? 'Durum kullanılamıyor.' : 'Status unavailable.',
      detail: raw,
    );
  }

  return DesktopRuntimeStatusPresentation(
    kind: connected
        ? DesktopRuntimeStatusKind.unknown
        : DesktopRuntimeStatusKind.offline,
    label: raw,
    detail: raw,
  );
}
