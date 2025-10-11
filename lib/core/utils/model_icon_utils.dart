import '../models/model.dart';
import '../services/api_service.dart';

String? deriveModelIcon(Model? model) {
  if (model == null) return null;

  String? pick(Map<String, dynamic>? source) {
    if (source == null) return null;
    for (final key in const [
      'profile_image_url',
      'profileImageUrl',
      'profileImage',
      'icon_url',
      'icon',
      'image',
      'avatar',
    ]) {
      final value = source[key];
      if (value is String && value.trim().isNotEmpty) {
        return value.trim();
      }
    }
    return null;
  }

  final metadata = model.metadata ?? const <String, dynamic>{};
  final capabilities = model.capabilities ?? const <String, dynamic>{};
  final info = metadata['info'] as Map<String, dynamic>?;
  final infoMeta = info?['meta'] as Map<String, dynamic>?;
  final nestedMeta = metadata['meta'] as Map<String, dynamic>?;

  final candidates = <String?>[
    pick(metadata),
    pick(nestedMeta),
    pick(info),
    pick(infoMeta),
    pick(capabilities),
    pick(capabilities['meta'] as Map<String, dynamic>?),
  ];

  for (final candidate in candidates) {
    if (candidate != null && candidate.isNotEmpty) {
      return candidate;
    }
  }

  return null;
}

String? resolveModelIconUrl(ApiService? api, String? rawUrl) {
  final value = rawUrl?.trim();
  if (value == null || value.isEmpty) {
    return null;
  }

  if (value.startsWith('data:image')) {
    return value;
  }

  if (value.startsWith('http://') || value.startsWith('https://')) {
    return value;
  }

  if (value.startsWith('//')) {
    final base = api?.baseUrl;
    if (base != null && base.isNotEmpty) {
      try {
        final baseUri = Uri.parse(base);
        final scheme = baseUri.scheme.isNotEmpty ? baseUri.scheme : 'https';
        return '$scheme:$value';
      } catch (_) {
        return 'https:$value';
      }
    }
    return 'https:$value';
  }

  if (api == null || api.baseUrl.isEmpty) {
    return value.startsWith('/') ? value : '/$value';
  }

  try {
    final baseUri = Uri.parse(api.baseUrl);
    final resolved = baseUri.resolve(value);
    return resolved.toString();
  } catch (_) {
    final normalizedBase = api.baseUrl.endsWith('/')
        ? api.baseUrl.substring(0, api.baseUrl.length - 1)
        : api.baseUrl;
    if (value.startsWith('/')) {
      return '$normalizedBase$value';
    }
    return '$normalizedBase/$value';
  }
}

String? resolveModelIconUrlForModel(ApiService? api, Model? model) {
  final raw = deriveModelIcon(model);
  return resolveModelIconUrl(api, raw);
}
