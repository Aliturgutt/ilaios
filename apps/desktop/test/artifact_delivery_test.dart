import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/artifact_delivery.dart';

void main() {
  test('maps verified finished-product actions to usable file extensions', () {
    expect(artifactFileExtension('video.local.rendered'), '.mp4');
    expect(artifactFileExtension('software.local.finished-product'), '.zip');
    expect(artifactFileExtension('unknown.artifact'), '.bin');
  });
}
