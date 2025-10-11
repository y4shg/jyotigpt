import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'dart:io' show Platform;
import '../theme/theme_extensions.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';

/// Utility functions for common UI patterns and helpers
/// Following JyotiGPT design principles

class UiUtils {
  static bool get isIOS => Platform.isIOS;

  /// Returns platform-appropriate icon
  static IconData platformIcon({
    required IconData ios,
    required IconData android,
  }) {
    return isIOS ? ios : android;
  }

  /// Common platform icons used throughout the app
  static IconData get chatIcon =>
      platformIcon(ios: CupertinoIcons.chat_bubble_2, android: Icons.chat);

  static IconData get searchIcon =>
      platformIcon(ios: CupertinoIcons.search, android: Icons.search);

  static IconData get deleteIcon =>
      platformIcon(ios: CupertinoIcons.delete, android: Icons.delete);

  static IconData get archiveIcon =>
      platformIcon(ios: CupertinoIcons.archivebox, android: Icons.archive);

  static IconData get shareIcon =>
      platformIcon(ios: CupertinoIcons.share, android: Icons.share);

  static IconData get settingsIcon =>
      platformIcon(ios: CupertinoIcons.gear, android: Icons.settings);

  static IconData get editIcon =>
      platformIcon(ios: CupertinoIcons.pencil, android: Icons.edit_outlined);

  static IconData get menuIcon =>
      platformIcon(ios: CupertinoIcons.line_horizontal_3, android: Icons.menu);

  static IconData get addIcon =>
      platformIcon(ios: CupertinoIcons.plus_circle, android: Icons.add);

  static IconData get attachIcon =>
      platformIcon(ios: CupertinoIcons.paperclip, android: Icons.attach_file);

  static IconData get micIcon =>
      platformIcon(ios: CupertinoIcons.mic, android: Icons.mic);

  static IconData get sendIcon => platformIcon(
    ios: CupertinoIcons.arrow_up_circle_fill,
    android: Icons.send,
  );

  static IconData get moreIcon => platformIcon(
    ios: CupertinoIcons.ellipsis_vertical,
    android: Icons.more_vert,
  );

  static IconData get closeIcon =>
      platformIcon(ios: CupertinoIcons.xmark, android: Icons.close);

  static IconData get checkIcon =>
      platformIcon(ios: CupertinoIcons.check_mark, android: Icons.check);

  static IconData get globeIcon =>
      platformIcon(ios: CupertinoIcons.globe, android: Icons.public);

  static IconData get folderIcon =>
      platformIcon(ios: CupertinoIcons.folder, android: Icons.folder);

  static IconData get tagIcon =>
      platformIcon(ios: CupertinoIcons.tag, android: Icons.label);

  static IconData get copyIcon =>
      platformIcon(ios: CupertinoIcons.doc_on_doc, android: Icons.copy);

  static IconData get pinIcon =>
      platformIcon(ios: CupertinoIcons.pin_fill, android: Icons.push_pin);

  static IconData get unpinIcon => platformIcon(
    ios: CupertinoIcons.pin_slash,
    android: Icons.push_pin_outlined,
  );

  /// Shows a JyotiGPT-styled snackbar with conversational messaging
  static void showMessage(
    BuildContext context,
    String message, {
    bool isError = false,
    VoidCallback? onRetry,
    Duration? duration,
  }) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError
            ? context.jyotigptTheme.error
            : context.jyotigptTheme.buttonPrimary,
        behavior: SnackBarBehavior.floating,
        action: onRetry != null
            ? SnackBarAction(
                label: AppLocalizations.of(context)!.retry,
                textColor: context.jyotigptTheme.textInverse,
                onPressed: onRetry,
              )
            : null,
        duration: duration ?? const Duration(seconds: 3),
      ),
    );
  }

  // Confirmation dialog moved to shared ThemedDialogs.confirm for cohesion

  /// Formats dates in a conversational way following JyotiGPT patterns
  static String formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);

    if (difference.inDays == 0) {
      if (difference.inHours == 0) {
        if (difference.inMinutes == 0) {
          return 'Just now';
        }
        return '${difference.inMinutes}m ago';
      }
      return '${difference.inHours}h ago';
    } else if (difference.inDays == 1) {
      return 'Yesterday';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} days ago';
    } else if (difference.inDays < 30) {
      final weeks = (difference.inDays / 7).floor();
      return weeks == 1 ? '1 week ago' : '$weeks weeks ago';
    } else if (difference.inDays < 365) {
      final months = (difference.inDays / 30).floor();
      return months == 1 ? '1 month ago' : '$months months ago';
    } else {
      return '${date.month}/${date.day}/${date.year}';
    }
  }

  /// Creates a smooth haptic feedback on iOS
  static void hapticFeedback() {
    if (isIOS) {
      // iOS haptic feedback would be implemented here
      // For now, we'll leave this as a placeholder
    }
  }

  /// Safe area padding helper
  static EdgeInsets safeAreaPadding(BuildContext context) {
    return MediaQuery.of(context).padding;
  }

  /// Screen size helpers
  static Size screenSize(BuildContext context) {
    return MediaQuery.of(context).size;
  }

  static bool isSmallScreen(BuildContext context) {
    return screenSize(context).width < 375;
  }

  static bool isLargeScreen(BuildContext context) {
    return screenSize(context).width > 414;
  }

  /// Keyboard handling
  static bool isKeyboardOpen(BuildContext context) {
    return MediaQuery.of(context).viewInsets.bottom > 0;
  }

  /// Focus management
  static void unfocus(BuildContext context) {
    FocusScope.of(context).unfocus();
  }
}
