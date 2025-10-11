import 'package:flutter/material.dart';

import '../theme/theme_extensions.dart';
import 'user_avatar.dart';

class ModelAvatar extends StatelessWidget {
  final double size;
  final String? imageUrl;
  final String? label;

  const ModelAvatar({super.key, required this.size, this.imageUrl, this.label});

  @override
  Widget build(BuildContext context) {
    return AvatarImage(
      size: size,
      imageUrl: imageUrl,
      borderRadius: BorderRadius.circular(AppBorderRadius.small),
      fallbackBuilder: (context, size) {
        final theme = context.jyotigptTheme;
        String? uppercase;
        final trimmed = label?.trim();
        if (trimmed != null && trimmed.isNotEmpty) {
          uppercase = trimmed.substring(0, 1).toUpperCase();
        }

        return Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: theme.buttonPrimary.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(AppBorderRadius.small),
            border: Border.all(
              color: theme.buttonPrimary.withValues(alpha: 0.25),
              width: BorderWidth.thin,
            ),
          ),
          alignment: Alignment.center,
          child: uppercase != null
              ? Text(
                  uppercase,
                  style: AppTypography.small.copyWith(
                    color: theme.buttonPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                )
              : Icon(
                  Icons.psychology,
                  color: theme.buttonPrimary,
                  size: size * 0.5,
                ),
        );
      },
    );
  }
}
