import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('MSIX manifest advertises final Desktop identity and EN/TR resources', () {
    final manifest = File('packaging/msix/AppxManifest.template.xml').readAsStringSync();

    expect(manifest, contains('<DisplayName>ILAIOS Desktop</DisplayName>'));
    expect(manifest, contains('<PublisherDisplayName>ILAIOS</PublisherDisplayName>'));
    expect(manifest, contains('Executable="ilaios_desktop.exe"'));
    expect(manifest, contains('Language="en-us"'));
    expect(manifest, contains('Language="tr-tr"'));
    expect(manifest, contains('Assets\\StoreLogo.png'));
    expect(manifest, contains('Assets\\Square44x44Logo.png'));
    expect(manifest, contains('Assets\\Square150x150Logo.png'));
    expect(manifest, contains('Assets\\Wide310x150Logo.png'));
    expect(manifest, contains('<rescap:Capability Name="runFullTrust" />'));
  });
}
