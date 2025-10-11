import 'dart:io' show Platform;

import 'package:jyotigpt/core/providers/app_providers.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';
import 'package:jyotigpt/shared/theme/theme_extensions.dart';
import 'package:jyotigpt/shared/widgets/jyotigpt_components.dart';
import 'package:jyotigpt/shared/widgets/modal_safe_area.dart';
import 'package:jyotigpt/shared/widgets/sheet_handle.dart';
import 'package:jyotigpt/shared/widgets/themed_dialogs.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:jyotigpt/features/chat/providers/chat_providers.dart' as chat;

class JyotiGPTContextMenuAction {
  final IconData cupertinoIcon;
  final IconData materialIcon;
  final String label;
  final Future<void> Function() onSelected;
  final VoidCallback? onBeforeClose;
  final bool destructive;

  const JyotiGPTContextMenuAction({
    required this.cupertinoIcon,
    required this.materialIcon,
    required this.label,
    required this.onSelected,
    this.onBeforeClose,
    this.destructive = false,
  });
}

Future<void> showJyotiGPTContextMenu({
  required BuildContext context,
  required List<JyotiGPTContextMenuAction> actions,
}) async {
  if (actions.isEmpty) return;

  final theme = context.jyotigptTheme;

  await showModalBottomSheet(
    context: context,
    backgroundColor: Colors.transparent,
    builder: (sheetContext) {
      Future<void> handleAction(JyotiGPTContextMenuAction action) async {
        action.onBeforeClose?.call();
        Navigator.of(sheetContext).pop();
        await Future.microtask(action.onSelected);
      }

      List<Widget> buildActionTiles() {
        return actions
            .map(
              (action) => JyotiGPTListItem(
                isCompact: true,
                leading: Icon(
                  Platform.isIOS ? action.cupertinoIcon : action.materialIcon,
                  color: action.destructive ? theme.error : theme.iconPrimary,
                  size: IconSize.modal,
                ),
                title: Text(
                  action.label,
                  style: AppTypography.standard.copyWith(
                    color: action.destructive ? theme.error : theme.textPrimary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                onTap: () => handleAction(action),
              ),
            )
            .toList();
      }

      final actionTiles = buildActionTiles();

      return ModalSheetSafeArea(
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.screenPadding,
          vertical: Spacing.screenPadding,
        ),
        child: Container(
          decoration: BoxDecoration(
            color: theme.surfaceBackground,
            borderRadius: BorderRadius.circular(AppBorderRadius.lg),
            boxShadow: JyotiGPTShadows.modal(context),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: Spacing.sm),
              const SheetHandle(),
              const SizedBox(height: Spacing.sm),
              for (var i = 0; i < actionTiles.length; i++) ...[
                if (i != 0) const JyotiGPTDivider(isCompact: true),
                actionTiles[i],
              ],
              const SizedBox(height: Spacing.sm),
            ],
          ),
        ),
      );
    },
  );
}

Future<void> showConversationContextMenu({
  required BuildContext context,
  required WidgetRef ref,
  required dynamic conversation,
}) async {
  if (conversation == null) return;

  final l10n = AppLocalizations.of(context)!;
  final bool isPinned = conversation.pinned == true;
  final bool isArchived = conversation.archived == true;

  Future<void> togglePin() async {
    final errorMessage = l10n.failedToUpdatePin;
    try {
      await chat.pinConversation(ref, conversation.id, !isPinned);
    } catch (_) {
      if (!context.mounted) return;
      await _showConversationError(context, errorMessage);
    }
  }

  Future<void> toggleArchive() async {
    final errorMessage = l10n.failedToUpdateArchive;
    try {
      await chat.archiveConversation(ref, conversation.id, !isArchived);
    } catch (_) {
      if (!context.mounted) return;
      await _showConversationError(context, errorMessage);
    }
  }

  Future<void> rename() async {
    await _renameConversation(
      context,
      ref,
      conversation.id,
      conversation.title ?? '',
    );
  }

  Future<void> deleteConversation() async {
    await _confirmAndDeleteConversation(context, ref, conversation.id);
  }

  HapticFeedback.selectionClick();
  await showJyotiGPTContextMenu(
    context: context,
    actions: [
      JyotiGPTContextMenuAction(
        cupertinoIcon: isPinned
            ? CupertinoIcons.pin_slash
            : CupertinoIcons.pin_fill,
        materialIcon: isPinned
            ? Icons.push_pin_outlined
            : Icons.push_pin_rounded,
        label: isPinned ? l10n.unpin : l10n.pin,
        onBeforeClose: () => HapticFeedback.lightImpact(),
        onSelected: togglePin,
      ),
      JyotiGPTContextMenuAction(
        cupertinoIcon: isArchived
            ? CupertinoIcons.archivebox_fill
            : CupertinoIcons.archivebox,
        materialIcon: isArchived
            ? Icons.unarchive_rounded
            : Icons.archive_rounded,
        label: isArchived ? l10n.unarchive : l10n.archive,
        onBeforeClose: () => HapticFeedback.lightImpact(),
        onSelected: toggleArchive,
      ),
      JyotiGPTContextMenuAction(
        cupertinoIcon: CupertinoIcons.pencil,
        materialIcon: Icons.edit_rounded,
        label: l10n.rename,
        onBeforeClose: () => HapticFeedback.selectionClick(),
        onSelected: rename,
      ),
      JyotiGPTContextMenuAction(
        cupertinoIcon: CupertinoIcons.delete,
        materialIcon: Icons.delete_rounded,
        label: l10n.delete,
        destructive: true,
        onBeforeClose: () => HapticFeedback.mediumImpact(),
        onSelected: deleteConversation,
      ),
    ],
  );
}

Future<void> _renameConversation(
  BuildContext context,
  WidgetRef ref,
  String conversationId,
  String currentTitle,
) async {
  final l10n = AppLocalizations.of(context)!;
  final newName = await ThemedDialogs.promptTextInput(
    context,
    title: l10n.renameChat,
    hintText: l10n.enterChatName,
    initialValue: currentTitle,
    confirmText: l10n.save,
    cancelText: l10n.cancel,
  );

  if (!context.mounted) return;
  if (newName == null) return;
  if (newName.isEmpty || newName == currentTitle) return;

  final renameError = l10n.failedToRenameChat;
  try {
    final api = ref.read(apiServiceProvider);
    if (api == null) throw Exception('No API service');
    await api.updateConversation(conversationId, title: newName);
    HapticFeedback.selectionClick();
    refreshConversationsCache(ref);
    final active = ref.read(activeConversationProvider);
    if (active?.id == conversationId) {
      ref
          .read(activeConversationProvider.notifier)
          .set(active!.copyWith(title: newName));
    }
  } catch (_) {
    if (!context.mounted) return;
    await _showConversationError(context, renameError);
  }
}

Future<void> _confirmAndDeleteConversation(
  BuildContext context,
  WidgetRef ref,
  String conversationId,
) async {
  final l10n = AppLocalizations.of(context)!;
  final confirmed = await ThemedDialogs.confirm(
    context,
    title: l10n.deleteChatTitle,
    message: l10n.deleteChatMessage,
    confirmText: l10n.delete,
    isDestructive: true,
  );

  if (!context.mounted) return;
  if (!confirmed) return;

  final deleteError = l10n.failedToDeleteChat;
  try {
    final api = ref.read(apiServiceProvider);
    if (api == null) throw Exception('No API service');
    await api.deleteConversation(conversationId);
    HapticFeedback.mediumImpact();
    final active = ref.read(activeConversationProvider);
    if (active?.id == conversationId) {
      ref.read(activeConversationProvider.notifier).clear();
      ref.read(chat.chatMessagesProvider.notifier).clearMessages();
    }
    refreshConversationsCache(ref);
  } catch (_) {
    if (!context.mounted) return;
    await _showConversationError(context, deleteError);
  }
}

Future<void> _showConversationError(
  BuildContext context,
  String message,
) async {
  if (!context.mounted) return;
  final l10n = AppLocalizations.of(context)!;
  final theme = context.jyotigptTheme;
  await ThemedDialogs.show<void>(
    context,
    title: l10n.errorMessage,
    content: Text(message, style: TextStyle(color: theme.textSecondary)),
    actions: [
      TextButton(
        onPressed: () => Navigator.of(context).pop(),
        child: Text(l10n.ok),
      ),
    ],
  );
}
