String artifactFileExtension(String action) {
  final normalized = action.toLowerCase();
  if (normalized.contains('video')) return '.mp4';
  if (normalized.contains('software')) return '.zip';
  return '.bin';
}
