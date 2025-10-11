import 'package:flutter/material.dart';

import 'package:jyotigpt/l10n/app_localizations.dart';

import '../theme/theme_extensions.dart';

/// Centralized helper for building themed dialogs consistently
class ThemedDialogs {
  ThemedDialogs._();

  /// Build a base themed AlertDialog
  static AlertDialog buildBase({
    required BuildContext context,
    required String title,
    Widget? content,
    List<Widget>? actions,
  }) {
    return AlertDialog(
      backgroundColor: context.jyotigptTheme.surfaceBackground,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppBorderRadius.dialog),
      ),
      title: Text(
        title,
        style: TextStyle(color: context.jyotigptTheme.textPrimary),
      ),
      content: content,
      actions: actions,
    );
  }

  /// Show a simple confirmation dialog with Cancel/Confirm actions
  static Future<bool> confirm(
    BuildContext context, {
    required String title,
    required String message,
    String? confirmText,
    String? cancelText,
    bool isDestructive = false,
    bool barrierDismissible = true,
  }) async {
    final l10n = AppLocalizations.of(context);
    final effectiveConfirmText = confirmText ?? l10n?.confirm ?? 'Confirm';
    final effectiveCancelText = cancelText ?? l10n?.cancel ?? 'Cancel';
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: barrierDismissible,
      builder: (ctx) => buildBase(
        context: ctx,
        title: title,
        content: Text(
          message,
          style: TextStyle(color: ctx.jyotigptTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(
              effectiveCancelText,
              style: TextStyle(color: ctx.jyotigptTheme.textSecondary),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: TextButton.styleFrom(
              foregroundColor: isDestructive
                  ? ctx.jyotigptTheme.error
                  : ctx.jyotigptTheme.buttonPrimary,
            ),
            child: Text(
              effectiveConfirmText,
              style: TextStyle(
                color: isDestructive
                    ? ctx.jyotigptTheme.error
                    : ctx.jyotigptTheme.buttonPrimary,
              ),
            ),
          ),
        ],
      ),
    );

    return result ?? false;
  }

  /// Show a generic themed dialog
  static Future<T?> show<T>(
    BuildContext context, {
    required String title,
    required Widget content,
    List<Widget>? actions,
    bool barrierDismissible = true,
  }) {
    return showDialog<T>(
      context: context,
      barrierDismissible: barrierDismissible,
      builder: (ctx) => buildBase(
        context: ctx,
        title: title,
        content: content,
        actions: actions,
      ),
    );
  }

  /// Cohesive text input dialog used for rename/create flows
  static Future<String?> promptTextInput(
    BuildContext context, {
    required String title,
    required String hintText,
    String? initialValue,
    String? confirmText,
    String? cancelText,
    bool barrierDismissible = true,
    TextInputType? keyboardType,
    TextCapitalization textCapitalization = TextCapitalization.sentences,
    int? maxLength,
  }) async {
    final theme = context.jyotigptTheme;
    final controller = TextEditingController(text: initialValue ?? '');
    final l10n = AppLocalizations.of(context);
    final effectiveConfirmText = confirmText ?? l10n?.save ?? 'Save';
    final effectiveCancelText = cancelText ?? l10n?.cancel ?? 'Cancel';

    String? result = await showDialog<String>(
      context: context,
      barrierDismissible: barrierDismissible,
      builder: (ctx) {
        return buildBase(
          context: ctx,
          title: title,
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: controller,
                autofocus: true,
                keyboardType: keyboardType,
                textCapitalization: textCapitalization,
                maxLength: maxLength,
                style: TextStyle(color: theme.inputText),
                decoration: InputDecoration(
                  hintText: hintText,
                  hintStyle: TextStyle(color: theme.inputPlaceholder),
                  filled: true,
                  fillColor: theme.inputBackground,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppBorderRadius.md),
                    borderSide: BorderSide.none,
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppBorderRadius.md),
                    borderSide: BorderSide(color: theme.inputBorder, width: 1),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppBorderRadius.md),
                    borderSide: BorderSide(
                      color: theme.buttonPrimary,
                      width: 1,
                    ),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: Spacing.md,
                    vertical: Spacing.md,
                  ),
                ),
                onSubmitted: (v) {
                  final trimmed = v.trim();
                  final unchanged =
                      (initialValue != null && trimmed == initialValue.trim());
                  if (trimmed.isEmpty || unchanged) return;
                  Navigator.of(ctx).pop(trimmed);
                },
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(
                effectiveCancelText,
                style: TextStyle(color: theme.textSecondary),
              ),
            ),
            ValueListenableBuilder<TextEditingValue>(
              valueListenable: controller,
              builder: (context, value, _) {
                final trimmed = value.text.trim();
                final unchanged =
                    (initialValue != null && trimmed == initialValue.trim());
                final enabled = trimmed.isNotEmpty && !unchanged;
                return TextButton(
                  onPressed: enabled
                      ? () => Navigator.of(ctx).pop(trimmed)
                      : null,
                  child: Text(
                    effectiveConfirmText,
                    style: TextStyle(
                      color: enabled
                          ? theme.buttonPrimary
                          : theme.textSecondary,
                    ),
                  ),
                );
              },
            ),
          ],
        );
      },
    );

    return result;
  }
}
