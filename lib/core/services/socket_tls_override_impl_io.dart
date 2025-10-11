import 'dart:io'
    show HttpOverrides, SecurityContext, HttpClient, X509Certificate;
import 'package:socket_io_client/socket_io_client.dart' as io;

import '../models/server_config.dart';

io.Socket createSocketWithOptionalBadCertOverride(
  String base,
  io.OptionBuilder builder,
  ServerConfig serverConfig,
) {
  if (!serverConfig.allowSelfSignedCertificates) {
    return io.io(base, builder.build());
  }

  final target = _tryParseUri(base);
  if (target == null || !(target.scheme == 'https' || target.scheme == 'wss')) {
    return io.io(base, builder.build());
  }

  final host = target.host.toLowerCase();
  final port = target.hasPort ? target.port : null;
  return HttpOverrides.runWithHttpOverrides<io.Socket>(
    () => io.io(base, builder.build()),
    _ScopedBadCertOverrides(host: host, port: port),
  );
}

Uri? _tryParseUri(String url) {
  try {
    final parsed = Uri.parse(url);
    if (parsed.hasScheme) return parsed;
  } catch (_) {}
  return null;
}

class _ScopedBadCertOverrides extends HttpOverrides {
  _ScopedBadCertOverrides({required this.host, this.port});

  final String host;
  final int? port;

  @override
  HttpClient createHttpClient(SecurityContext? context) {
    final client = super.createHttpClient(context);
    client.badCertificateCallback =
        (X509Certificate cert, String requestHost, int requestPort) {
          if (requestHost.toLowerCase() != host) return false;
          if (port == null) return true;
          return requestPort == port;
        };
    return client;
  }
}
