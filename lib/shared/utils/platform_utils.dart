import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'dart:io' show Platform;
import '../theme/theme_extensions.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';

/// Platform-specific utilities for enhanced user experience
class PlatformUtils {
  PlatformUtils._();

  /// Check if device supports haptic feedback
  static bool get supportsHaptics => Platform.isIOS || Platform.isAndroid;

  /// Trigger light haptic feedback
  static void lightHaptic() {
    if (supportsHaptics) {
      HapticFeedback.lightImpact();
    }
  }

  /// Trigger medium haptic feedback
  static void mediumHaptic() {
    if (supportsHaptics && Platform.isIOS) {
      HapticFeedback.mediumImpact();
    } else if (Platform.isAndroid) {
      HapticFeedback.lightImpact();
    }
  }

  /// Trigger heavy haptic feedback
  static void heavyHaptic() {
    if (supportsHaptics && Platform.isIOS) {
      HapticFeedback.heavyImpact();
    } else if (Platform.isAndroid) {
      HapticFeedback.vibrate();
    }
  }

  /// Trigger selection haptic feedback
  static void selectionHaptic() {
    if (supportsHaptics) {
      HapticFeedback.selectionClick();
    }
  }

  /// Get platform-appropriate icon
  static IconData getIcon({required IconData ios, required IconData android}) {
    return Platform.isIOS ? ios : android;
  }

  /// Get platform-appropriate text style
  static TextStyle getPlatformTextStyle(BuildContext context) {
    if (Platform.isIOS) {
      return CupertinoTheme.of(context).textTheme.textStyle;
    }
    return Theme.of(context).textTheme.bodyMedium ?? const TextStyle();
  }

  /// Create platform-specific button
  static Widget createButton({
    required String text,
    required VoidCallback? onPressed,
    bool isPrimary = true,
    Color? color,
  }) {
    if (Platform.isIOS) {
      return Builder(
        builder: (context) => CupertinoButton(
          onPressed: onPressed,
          color: isPrimary
              ? (color ?? context.jyotigptTheme.buttonPrimary)
              : null,
          child: Text(text),
        ),
      );
    }

    return isPrimary
        ? FilledButton(
            onPressed: onPressed,
            style: color != null
                ? FilledButton.styleFrom(backgroundColor: color)
                : null,
            child: Text(text),
          )
        : OutlinedButton(onPressed: onPressed, child: Text(text));
  }

  /// Create platform-specific switch
  static Widget createSwitch({
    required bool value,
    required ValueChanged<bool>? onChanged,
    Color? activeColor,
  }) {
    if (Platform.isIOS) {
      return Builder(
        builder: (context) => CupertinoSwitch(
          value: value,
          onChanged: onChanged,
          thumbColor: activeColor ?? context.jyotigptTheme.buttonPrimary,
        ),
      );
    }

    return Switch(
      value: value,
      onChanged: onChanged,
      activeTrackColor: activeColor,
    );
  }

  /// Create platform-specific slider
  static Widget createSlider({
    required double value,
    required ValueChanged<double>? onChanged,
    double min = 0.0,
    double max = 1.0,
    int? divisions,
    Color? activeColor,
  }) {
    if (Platform.isIOS) {
      return Builder(
        builder: (context) => CupertinoSlider(
          value: value,
          onChanged: onChanged,
          min: min,
          max: max,
          divisions: divisions,
          activeColor: activeColor ?? context.jyotigptTheme.buttonPrimary,
        ),
      );
    }

    return Slider(
      value: value,
      onChanged: onChanged,
      min: min,
      max: max,
      divisions: divisions,
      activeColor: activeColor,
    );
  }
}

/// iOS-specific enhancements
class IOSEnhancements {
  /// Create iOS-style navigation bar
  static PreferredSizeWidget createNavigationBar({
    required String title,
    VoidCallback? onBack,
    List<Widget>? actions,
    Color? backgroundColor,
  }) {
    return CupertinoNavigationBar(
      middle: Text(title),
      leading: onBack != null
          ? CupertinoNavigationBarBackButton(onPressed: onBack)
          : null,
      trailing: actions != null && actions.isNotEmpty
          ? Row(mainAxisSize: MainAxisSize.min, children: actions)
          : null,
      backgroundColor: backgroundColor,
    );
  }

  /// Create iOS-style context menu
  static Widget createContextMenu({
    required Widget child,
    required List<ContextMenuAction> actions,
  }) {
    return CupertinoContextMenu(
      actions: actions
          .map(
            (action) => CupertinoContextMenuAction(
              onPressed: action.onPressed,
              isDefaultAction: action.isDefault,
              isDestructiveAction: action.isDestructive,
              child: Text(action.title),
            ),
          )
          .toList(),
      child: child,
    );
  }

  /// Create iOS-style action sheet
  static void showActionSheet({
    required BuildContext context,
    required String title,
    String? message,
    required List<ActionSheetAction> actions,
  }) {
    showCupertinoModalPopup(
      context: context,
      builder: (context) => CupertinoActionSheet(
        title: Text(title),
        message: message != null ? Text(message) : null,
        actions: actions
            .map(
              (action) => CupertinoActionSheetAction(
                onPressed: () {
                  Navigator.pop(context);
                  action.onPressed();
                },
                isDefaultAction: action.isDefault,
                isDestructiveAction: action.isDestructive,
                child: Text(action.title),
              ),
            )
            .toList(),
        cancelButton: CupertinoActionSheetAction(
          onPressed: () => Navigator.pop(context),
          child: Text(AppLocalizations.of(context)!.cancel),
        ),
      ),
    );
  }
}

/// Android-specific enhancements
class AndroidEnhancements {
  /// Create Material You themed button
  static Widget createMaterial3Button({
    required String text,
    required VoidCallback? onPressed,
    ButtonType type = ButtonType.filled,
    IconData? icon,
  }) {
    Widget button;

    switch (type) {
      case ButtonType.filled:
        button = icon != null
            ? FilledButton.icon(
                onPressed: onPressed,
                icon: Icon(icon),
                label: Text(text),
              )
            : FilledButton(onPressed: onPressed, child: Text(text));
        break;
      case ButtonType.outlined:
        button = icon != null
            ? OutlinedButton.icon(
                onPressed: onPressed,
                icon: Icon(icon),
                label: Text(text),
              )
            : OutlinedButton(onPressed: onPressed, child: Text(text));
        break;
      case ButtonType.text:
        button = icon != null
            ? TextButton.icon(
                onPressed: onPressed,
                icon: Icon(icon),
                label: Text(text),
              )
            : TextButton(onPressed: onPressed, child: Text(text));
        break;
    }

    return button;
  }

  /// Create Material 3 card
  static Widget createCard({
    required Widget child,
    VoidCallback? onTap,
    EdgeInsetsGeometry? padding,
    CardType type = CardType.filled,
  }) {
    Widget card;

    switch (type) {
      case CardType.filled:
        card = Card.filled(
          child: padding != null
              ? Padding(padding: padding, child: child)
              : child,
        );
        break;
      case CardType.outlined:
        card = Card.outlined(
          child: padding != null
              ? Padding(padding: padding, child: child)
              : child,
        );
        break;
      case CardType.elevated:
        card = Card(
          child: padding != null
              ? Padding(padding: padding, child: child)
              : child,
        );
        break;
    }

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppBorderRadius.md),
        child: card,
      );
    }

    return card;
  }

  /// Create floating action button with Material 3 styling
  static Widget createFAB({
    required VoidCallback onPressed,
    required Widget child,
    bool isExtended = false,
    String? label,
  }) {
    if (isExtended && label != null) {
      return FloatingActionButton.extended(
        onPressed: onPressed,
        icon: child,
        label: Text(label),
      );
    }

    return FloatingActionButton(onPressed: onPressed, child: child);
  }
}

/// Platform-aware widget that provides different implementations
class PlatformWidget extends StatelessWidget {
  final Widget ios;
  final Widget android;
  final Widget? fallback;

  const PlatformWidget({
    super.key,
    required this.ios,
    required this.android,
    this.fallback,
  });

  @override
  Widget build(BuildContext context) {
    if (Platform.isIOS) {
      return ios;
    } else if (Platform.isAndroid) {
      return android;
    } else {
      return fallback ?? android;
    }
  }
}

/// Enhanced button with platform-specific haptics
class HapticButton extends StatelessWidget {
  final Widget child;
  final VoidCallback? onPressed;
  final HapticType hapticType;
  final ButtonStyle? style;

  const HapticButton({
    super.key,
    required this.child,
    required this.onPressed,
    this.hapticType = HapticType.light,
    this.style,
  });

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: onPressed != null
          ? () {
              _triggerHaptic();
              onPressed!();
            }
          : null,
      style: style,
      child: child,
    );
  }

  void _triggerHaptic() {
    switch (hapticType) {
      case HapticType.light:
        PlatformUtils.lightHaptic();
        break;
      case HapticType.medium:
        PlatformUtils.mediumHaptic();
        break;
      case HapticType.heavy:
        PlatformUtils.heavyHaptic();
        break;
      case HapticType.selection:
        PlatformUtils.selectionHaptic();
        break;
    }
  }
}

/// Enhanced list tile with platform-specific styling
class PlatformListTile extends StatelessWidget {
  final Widget? leading;
  final Widget? title;
  final Widget? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final bool enableHaptic;

  const PlatformListTile({
    super.key,
    this.leading,
    this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.enableHaptic = true,
  });

  @override
  Widget build(BuildContext context) {
    final tile = ListTile(
      leading: leading,
      title: title,
      subtitle: subtitle,
      trailing: trailing,
      onTap: onTap != null && enableHaptic
          ? () {
              PlatformUtils.selectionHaptic();
              onTap!();
            }
          : onTap,
    );

    if (Platform.isIOS) {
      return Builder(
        builder: (context) => Container(
          decoration: BoxDecoration(
            color: context.jyotigptTheme.surfaceBackground,
            border: Border(
              bottom: BorderSide(
                color: context.jyotigptTheme.dividerColor,
                width: 0.5,
              ),
            ),
          ),
          child: tile,
        ),
      );
    }

    return tile;
  }
}

// Enums and supporting classes
enum HapticType { light, medium, heavy, selection }

enum ButtonType { filled, outlined, text }

enum CardType { filled, outlined, elevated }

class ContextMenuAction {
  final String title;
  final VoidCallback onPressed;
  final bool isDefault;
  final bool isDestructive;

  const ContextMenuAction({
    required this.title,
    required this.onPressed,
    this.isDefault = false,
    this.isDestructive = false,
  });
}

class ActionSheetAction {
  final String title;
  final VoidCallback onPressed;
  final bool isDefault;
  final bool isDestructive;

  const ActionSheetAction({
    required this.title,
    required this.onPressed,
    this.isDefault = false,
    this.isDestructive = false,
  });
}
