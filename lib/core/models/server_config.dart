import 'package:freezed_annotation/freezed_annotation.dart';

part 'server_config.freezed.dart';
part 'server_config.g.dart';

@freezed
sealed class ServerConfig with _$ServerConfig {
  const factory ServerConfig({
    required String id,
    required String name,
    required String url,
    String? apiKey,
    @Default({}) Map<String, String> customHeaders,
    DateTime? lastConnected,
    @Default(false) bool isActive,

    /// Whether to trust self-signed TLS certificates for this server.
    @Default(false) bool allowSelfSignedCertificates,
  }) = _ServerConfig;

  factory ServerConfig.fromJson(Map<String, dynamic> json) =>
      _$ServerConfigFromJson(json);
}
