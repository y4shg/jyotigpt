import 'package:flutter/material.dart';
import '../../theme/theme_extensions.dart';

class CodeBlockHeader extends StatelessWidget {
  const CodeBlockHeader({
    super.key,
    required this.language,
    required this.onCopy,
  });

  final String language;
  final VoidCallback onCopy;

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;
    final materialTheme = Theme.of(context);
    final isDark = materialTheme.brightness == Brightness.dark;
    final label = language.isEmpty ? 'plaintext' : language;

    // Match GitHub/Atom theme colors
    final backgroundColor = isDark
        ? const Color(0xFF282c34) // Atom One Dark header
        : const Color(0xFFf6f8fa); // GitHub light header
    final textColor = isDark
        ? const Color(0xFF9da5b4) // Muted text for dark
        : const Color(0xFF57606a); // GitHub gray for light

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.xs,
      ),
      decoration: BoxDecoration(
        color: backgroundColor,
        border: Border(
          bottom: BorderSide(
            color: theme.cardBorder.withValues(alpha: 0.15),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          Text(
            label,
            style: AppTypography.codeStyle.copyWith(
              color: textColor,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
          const Spacer(),
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onCopy,
              borderRadius: BorderRadius.circular(4),
              child: Padding(
                padding: const EdgeInsets.all(6),
                child: Icon(
                  Icons.content_copy_rounded,
                  size: 16,
                  color: textColor,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
