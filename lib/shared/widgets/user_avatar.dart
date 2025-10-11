import 'dart:convert';
import 'dart:typed_data';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../services/brand_service.dart';
import '../theme/theme_extensions.dart';

typedef AvatarWidgetBuilder =
    Widget Function(BuildContext context, double size);

class AvatarImage extends StatelessWidget {
  final double size;
  final String? imageUrl;
  final BorderRadius? borderRadius;
  final AvatarWidgetBuilder fallbackBuilder;
  final AvatarWidgetBuilder? placeholderBuilder;

  const AvatarImage({
    super.key,
    required this.size,
    required this.fallbackBuilder,
    this.imageUrl,
    this.borderRadius,
    this.placeholderBuilder,
  });

  BorderRadius get _radius => borderRadius ?? BorderRadius.circular(size / 2);

  @override
  Widget build(BuildContext context) {
    final url = imageUrl?.trim();
    if (url == null || url.isEmpty) {
      return fallbackBuilder(context, size);
    }

    if (url.startsWith('data:image')) {
      final content = _decodeDataImage(url);
      if (content != null) {
        return ClipRRect(
          borderRadius: _radius,
          child: Image.memory(
            content,
            width: size,
            height: size,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) =>
                fallbackBuilder(context, size),
          ),
        );
      }
      return fallbackBuilder(context, size);
    }

    return ClipRRect(
      borderRadius: _radius,
      child: CachedNetworkImage(
        imageUrl: url,
        width: size,
        height: size,
        fit: BoxFit.cover,
        placeholder: (context, _) =>
            (placeholderBuilder ?? _defaultPlaceholder)(context, size),
        errorWidget: (context, url, error) => fallbackBuilder(context, size),
      ),
    );
  }

  AvatarWidgetBuilder get _defaultPlaceholder => (context, size) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      color: context.jyotigptTheme.surfaceContainer.withValues(alpha: 0.35),
      child: SizedBox(
        width: size * 0.35,
        height: size * 0.35,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          valueColor: AlwaysStoppedAnimation(
            context.jyotigptTheme.buttonPrimary,
          ),
        ),
      ),
    );
  };

  Uint8List? _decodeDataImage(String dataUrl) {
    try {
      final commaIndex = dataUrl.indexOf(',');
      if (commaIndex == -1) return null;
      final base64Data = dataUrl.substring(commaIndex + 1);
      return base64Decode(base64Data);
    } catch (_) {
      return null;
    }
  }
}

class UserAvatar extends StatelessWidget {
  final double size;
  final String? imageUrl;
  final String? fallbackText;

  const UserAvatar({
    super.key,
    required this.size,
    this.imageUrl,
    this.fallbackText,
  });

  @override
  Widget build(BuildContext context) {
    return AvatarImage(
      size: size,
      imageUrl: imageUrl,
      fallbackBuilder: (context, size) => BrandService.createBrandAvatar(
        size: size,
        fallbackText: fallbackText,
        context: context,
      ),
    );
  }
}
