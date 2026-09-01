import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/config.dart';

void main() {
  test('explicit loopback HTTP endpoint validator accepts only local endpoints', () {
    expect(
      isExplicitLoopbackHttpEndpoint(Uri.parse('http://127.0.0.1:4123')),
      isTrue,
    );
    expect(
      isExplicitLoopbackHttpEndpoint(Uri.parse('http://localhost:4123')),
      isTrue,
    );
    expect(
      isExplicitLoopbackHttpEndpoint(Uri.parse('http://[::1]:4123')),
      isTrue,
    );

    expect(
      isExplicitLoopbackHttpEndpoint(Uri.parse('http://example.com:4123')),
      isFalse,
    );
    expect(
      isExplicitLoopbackHttpEndpoint(Uri.parse('https://127.0.0.1:4123')),
      isFalse,
    );
    expect(
      isExplicitLoopbackHttpEndpoint(Uri.parse('http://127.0.0.1')),
      isFalse,
    );
  });
}
