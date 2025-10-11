import 'package:flutter/material.dart';
import '../../../shared/theme/theme_extensions.dart';
import 'enhanced_image_attachment.dart';
import 'enhanced_attachment.dart';

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:io' show Platform;
import 'package:jyotigpt/l10n/app_localizations.dart';
import 'package:jyotigpt/shared/widgets/chat_action_button.dart';
import '../../../core/providers/app_providers.dart';
import '../providers/chat_providers.dart';
import '../../../shared/services/tasks/task_queue.dart';
import '../../tools/providers/tools_providers.dart';

class UserMessageBubble extends ConsumerStatefulWidget {
  final dynamic message;
  final bool isUser;
  final bool isStreaming;
  final String? modelName;
  final VoidCallback? onCopy;
  final VoidCallback? onEdit;
  final VoidCallback? onRegenerate;
  final VoidCallback? onLike;
  final VoidCallback? onDislike;

  const UserMessageBubble({
    super.key,
    required this.message,
    required this.isUser,
    this.isStreaming = false,
    this.modelName,
    this.onCopy,
    this.onEdit,
    this.onRegenerate,
    this.onLike,
    this.onDislike,
  });

  @override
  ConsumerState<UserMessageBubble> createState() => _UserMessageBubbleState();
}

class _UserMessageBubbleState extends ConsumerState<UserMessageBubble>
    with TickerProviderStateMixin {
  bool _showActions = false;
  late AnimationController _fadeController;
  late AnimationController _slideController;
  // press state handled by shared ChatActionButton

  bool _isEditing = false;
  late final TextEditingController _editController;
  final FocusNode _editFocusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      duration: AnimationDuration.microInteraction,
      vsync: this,
    );
    _slideController = AnimationController(
      duration: AnimationDuration.messageSlide,
      vsync: this,
    );
    _editController = TextEditingController(
      text: widget.message?.content ?? '',
    );
  }

  Widget _buildUserAttachmentImages() {
    if (widget.message.attachmentIds == null ||
        widget.message.attachmentIds!.isEmpty) {
      return const SizedBox.shrink();
    }

    final imageCount = widget.message.attachmentIds!.length;

    // iMessage-style image layout with AnimatedSwitcher for smooth transitions
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      switchInCurve: Curves.easeInOut,
      child: _buildImageLayout(imageCount),
    );
  }

  Widget _buildUserFileImages() {
    if (widget.message.files == null || widget.message.files!.isEmpty) {
      return const SizedBox.shrink();
    }

    final allFiles = widget.message.files!;

    // Separate images and non-image files
    final imageFiles = allFiles
        .where(
          (file) =>
              file is Map && file['type'] == 'image' && file['url'] != null,
        )
        .toList();
    final nonImageFiles = allFiles
        .where(
          (file) =>
              file is Map && file['type'] != 'image' && file['url'] != null,
        )
        .toList();

    final widgets = <Widget>[];

    // Add images first
    if (imageFiles.isNotEmpty) {
      widgets.add(
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          switchInCurve: Curves.easeInOut,
          child: _buildFileImageLayout(imageFiles, imageFiles.length),
        ),
      );
    }

    // Add non-image files
    if (nonImageFiles.isNotEmpty) {
      if (widgets.isNotEmpty) {
        widgets.add(const SizedBox(height: Spacing.xs));
      }
      widgets.add(_buildUserNonImageFiles(nonImageFiles));
    }

    if (widgets.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: widgets,
    );
  }

  Widget _buildFileImageLayout(List<dynamic> imageFiles, int imageCount) {
    if (imageCount == 1) {
      final String imageUrl = imageFiles[0]['url'] as String;
      return Row(
        key: ValueKey('user_file_single_$imageUrl'),
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(
                AppBorderRadius.messageBubble,
              ),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(
                AppBorderRadius.messageBubble,
              ),
              child: EnhancedImageAttachment(
                attachmentId: imageUrl,
                isUserMessage: true,
                isMarkdownFormat: false,
                constraints: const BoxConstraints(
                  maxWidth: 280,
                  maxHeight: 350,
                ),
                disableAnimation: widget.isStreaming,
              ),
            ),
          ),
        ],
      );
    } else if (imageCount == 2) {
      return Row(
        key: ValueKey(
          'user_file_double_${imageFiles.map((e) => e['url']).join('_')}',
        ),
        mainAxisAlignment: MainAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: imageFiles.asMap().entries.map((entry) {
                final index = entry.key;
                final String imageUrl = entry.value['url'] as String;
                return Padding(
                  padding: EdgeInsets.only(left: index == 0 ? 0 : Spacing.xs),
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(
                        AppBorderRadius.messageBubble,
                      ),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(
                        AppBorderRadius.messageBubble,
                      ),
                      child: EnhancedImageAttachment(
                        key: ValueKey('user_file_attachment_$imageUrl'),
                        attachmentId: imageUrl,
                        isUserMessage: true,
                        isMarkdownFormat: false,
                        constraints: const BoxConstraints(
                          maxWidth: 135,
                          maxHeight: 180,
                        ),
                        disableAnimation: widget.isStreaming,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      );
    } else {
      return Row(
        key: ValueKey(
          'user_file_grid_${imageFiles.map((e) => e['url']).join('_')}',
        ),
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Flexible(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 280),
              child: Wrap(
                alignment: WrapAlignment.end,
                spacing: Spacing.xs,
                runSpacing: Spacing.xs,
                children: imageFiles.map((file) {
                  final String imageUrl = file['url'] as String;
                  return Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(AppBorderRadius.md),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(AppBorderRadius.md),
                      child: EnhancedImageAttachment(
                        key: ValueKey('user_file_grid_attachment_$imageUrl'),
                        attachmentId: imageUrl,
                        isUserMessage: true,
                        isMarkdownFormat: false,
                        constraints: BoxConstraints(
                          maxWidth: imageCount == 3 ? 135 : 90,
                          maxHeight: imageCount == 3 ? 135 : 90,
                        ),
                        disableAnimation: widget.isStreaming,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
        ],
      );
    }
  }

  Widget _buildImageLayout(int imageCount) {
    if (imageCount == 1) {
      // Single image - larger display
      return Row(
        key: ValueKey('user_single_${widget.message.attachmentIds![0]}'),
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(
                AppBorderRadius.messageBubble,
              ),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(
                AppBorderRadius.messageBubble,
              ),
              child: EnhancedAttachment(
                attachmentId: widget.message.attachmentIds![0],
                isUserMessage: true,
                constraints: const BoxConstraints(
                  maxWidth: 280,
                  maxHeight: 350,
                ),
                disableAnimation: widget.isStreaming,
              ),
            ),
          ),
        ],
      );
    } else if (imageCount == 2) {
      // Two images side by side
      return Row(
        key: ValueKey('user_double_${widget.message.attachmentIds!.join('_')}'),
        mainAxisAlignment: MainAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: widget.message.attachmentIds!.asMap().entries.map((
                entry,
              ) {
                final index = entry.key;
                final attachmentId = entry.value;
                return Padding(
                  padding: EdgeInsets.only(left: index == 0 ? 0 : Spacing.xs),
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(
                        AppBorderRadius.messageBubble,
                      ),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(
                        AppBorderRadius.messageBubble,
                      ),
                      child: EnhancedAttachment(
                        key: ValueKey('user_attachment_$attachmentId'),
                        attachmentId: attachmentId,
                        isUserMessage: true,
                        constraints: const BoxConstraints(
                          maxWidth: 135,
                          maxHeight: 180,
                        ),
                        disableAnimation: widget.isStreaming,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      );
    } else {
      // Grid layout for 3+ images
      return Row(
        key: ValueKey('user_grid_${widget.message.attachmentIds!.join('_')}'),
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Flexible(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 280),
              child: Wrap(
                alignment: WrapAlignment.end,
                spacing: Spacing.xs,
                runSpacing: Spacing.xs,
                children: widget.message.attachmentIds!.map((attachmentId) {
                  return Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(AppBorderRadius.md),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(AppBorderRadius.md),
                      child: EnhancedAttachment(
                        key: ValueKey('user_grid_attachment_$attachmentId'),
                        attachmentId: attachmentId,
                        isUserMessage: true,
                        constraints: BoxConstraints(
                          maxWidth: imageCount == 3 ? 135 : 90,
                          maxHeight: imageCount == 3 ? 135 : 90,
                        ),
                        disableAnimation: widget.isStreaming,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
        ],
      );
    }
  }

  Widget _buildUserNonImageFiles(List<dynamic> nonImageFiles) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        Flexible(
          child: Wrap(
            alignment: WrapAlignment.end,
            spacing: Spacing.xs,
            runSpacing: Spacing.xs,
            children: nonImageFiles.map<Widget>((file) {
              final fileUrl = file['url'] as String?;

              if (fileUrl == null) return const SizedBox.shrink();

              // Extract file ID from URL if it's in the format /api/v1/files/{id}/content
              String attachmentId = fileUrl;
              if (fileUrl.contains('/api/v1/files/') &&
                  fileUrl.contains('/content')) {
                final fileIdMatch = RegExp(
                  r'/api/v1/files/([^/]+)/content',
                ).firstMatch(fileUrl);
                if (fileIdMatch != null) {
                  attachmentId = fileIdMatch.group(1)!;
                }
              }

              return EnhancedAttachment(
                key: ValueKey('user_file_attachment_$attachmentId'),
                attachmentId: attachmentId,
                isMarkdownFormat: false,
                isUserMessage: true,
                constraints: const BoxConstraints(maxWidth: 280, maxHeight: 80),
                disableAnimation: widget.isStreaming,
              );
            }).toList(),
          ),
        ),
      ],
    );
  }

  // Assistant-only helpers removed; this widget renders only user bubbles.

  @override
  void dispose() {
    _fadeController.dispose();
    _slideController.dispose();
    _editController.dispose();
    _editFocusNode.dispose();
    super.dispose();
  }

  void _toggleActions() {
    setState(() {
      _showActions = !_showActions;
    });

    if (_showActions) {
      _fadeController.forward();
      _slideController.forward();
    } else {
      _fadeController.reverse();
      _slideController.reverse();
    }
  }

  @override
  Widget build(BuildContext context) {
    return _buildUserMessage();
  }

  Widget _buildUserMessage() {
    final hasImages =
        widget.message.attachmentIds != null &&
        widget.message.attachmentIds!.isNotEmpty;
    final hasText = widget.message.content.isNotEmpty;
    final hasFilesFromArray =
        widget.message.files != null &&
        (widget.message.files as List).any((f) => f is Map && f['url'] != null);
    // Prefer input/textPrimary colors during inline editing to avoid low contrast
    final inlineEditTextColor = context.jyotigptTheme.textPrimary;
    final inlineEditFill = context.jyotigptTheme.surfaceContainer.withValues(
      alpha: 0.92,
    );

    return GestureDetector(
      onLongPress: () => _toggleActions(),
      behavior: HitTestBehavior.translucent,
      child: Container(
        width: double.infinity,
        margin: const EdgeInsets.only(
          bottom: Spacing.md,
          left: Spacing.xxxl,
          right: Spacing.xs,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            // Display images outside and above the text bubble (iMessage style)
            // Prioritize files array over attachmentIds to avoid duplication
            if (hasFilesFromArray) ...[
              _buildUserFileImages(),
            ] else if (hasImages) ...[
              _buildUserAttachmentImages(),
            ],

            // Display text bubble if there's text content
            if (hasText) const SizedBox(height: Spacing.xs),
            if (hasText)
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Flexible(
                    child: ConstrainedBox(
                      constraints: BoxConstraints(
                        maxWidth: MediaQuery.of(context).size.width * 0.82,
                      ),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: Spacing.chatBubblePadding,
                          vertical: Spacing.sm,
                        ),
                        decoration: BoxDecoration(
                          color: context.jyotigptTheme.chatBubbleUser,
                          borderRadius: BorderRadius.circular(
                            AppBorderRadius.messageBubble,
                          ),
                          border: Border.all(
                            color: context.jyotigptTheme.chatBubbleUserBorder
                                .withValues(alpha: 0.5),
                            width: BorderWidth.standard,
                          ),
                        ),
                        child: _isEditing
                            ? Focus(
                                focusNode: _editFocusNode,
                                autofocus: true,
                                child: DecoratedBox(
                                  decoration: BoxDecoration(
                                    color: inlineEditFill,
                                    borderRadius: BorderRadius.circular(
                                      AppBorderRadius.small,
                                    ),
                                    border: Border.all(
                                      color: context
                                          .jyotigptTheme
                                          .inputBorderFocused
                                          .withValues(alpha: 0.5),
                                      width: BorderWidth.thin,
                                    ),
                                  ),
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: Spacing.xs,
                                      vertical: Spacing.xxs,
                                    ),
                                    child: Platform.isIOS
                                        ? CupertinoTextField(
                                            controller: _editController,
                                            maxLines: null,
                                            padding: EdgeInsets.zero,
                                            autofillHints: const <String>[],
                                            style: AppTypography
                                                .chatMessageStyle
                                                .copyWith(
                                                  color: inlineEditTextColor,
                                                ),
                                            decoration: const BoxDecoration(),
                                            cursorColor: context
                                                .jyotigptTheme
                                                .buttonPrimary,
                                            onSubmitted: (_) =>
                                                _saveInlineEdit(),
                                          )
                                        : TextField(
                                            controller: _editController,
                                            maxLines: null,
                                            autofillHints: const <String>[],
                                            style: AppTypography
                                                .chatMessageStyle
                                                .copyWith(
                                                  color: inlineEditTextColor,
                                                ),
                                            decoration: const InputDecoration(
                                              isCollapsed: true,
                                              border: InputBorder.none,
                                              contentPadding: EdgeInsets.zero,
                                            ),
                                            cursorColor: context
                                                .jyotigptTheme
                                                .buttonPrimary,
                                            onSubmitted: (_) =>
                                                _saveInlineEdit(),
                                          ),
                                  ),
                                ),
                              )
                            : Text(
                                widget.message.content,
                                style: AppTypography.chatMessageStyle.copyWith(
                                  color:
                                      context.jyotigptTheme.chatBubbleUserText,
                                ),
                                softWrap: true,
                                textAlign: TextAlign.left,
                                textHeightBehavior: const TextHeightBehavior(
                                  applyHeightToFirstAscent: false,
                                  applyHeightToLastDescent: false,
                                  leadingDistribution:
                                      TextLeadingDistribution.even,
                                ),
                              ),
                      ),
                    ),
                  ),
                ],
              ),
            if (hasText) const SizedBox(height: Spacing.xs),

            // Action buttons below the message
            if (_showActions) ...[
              const SizedBox(height: Spacing.sm),
              _buildUserActionButtons(),
            ],
          ],
        ),
      ),
    );
  }

  // Assistant-only message renderer removed.

  // Markdown rendering and typing indicator helpers removed.

  // Removed unused assistant action buttons builder.

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    VoidCallback? onTap,
  }) {
    return ChatActionButton(icon: icon, label: label, onTap: onTap);
  }

  Widget _buildUserActionButtons() {
    return Wrap(
      spacing: Spacing.sm,
      runSpacing: Spacing.sm,
      children: [
        if (_isEditing) ...[
          _buildActionButton(
            icon: Platform.isIOS ? CupertinoIcons.check_mark : Icons.check,
            label: AppLocalizations.of(context)!.save,
            onTap: _saveInlineEdit,
          ),
          _buildActionButton(
            icon: Platform.isIOS ? CupertinoIcons.xmark : Icons.close,
            label: AppLocalizations.of(context)!.cancel,
            onTap: _cancelInlineEdit,
          ),
        ] else ...[
          _buildActionButton(
            icon: Platform.isIOS ? CupertinoIcons.pencil : Icons.edit_outlined,
            label: AppLocalizations.of(context)!.edit,
            onTap: widget.onEdit ?? _startInlineEdit,
          ),
          _buildActionButton(
            icon: Platform.isIOS
                ? CupertinoIcons.doc_on_clipboard
                : Icons.content_copy,
            label: AppLocalizations.of(context)!.copy,
            onTap: widget.onCopy,
          ),
        ],
      ],
    );
  }

  void _startInlineEdit() {
    if (_isEditing) return;
    setState(() {
      _isEditing = true;
      _showActions = true; // ensure actions visible for Save/Cancel
      _editController.text = widget.message.content ?? '';
    });
    // Request focus after frame to show keyboard
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _editFocusNode.requestFocus();
      }
    });
  }

  void _cancelInlineEdit() {
    if (!_isEditing) return;
    setState(() {
      _isEditing = false;
      // keep actions panel open; user can close with long-press
      _editController.text = widget.message.content ?? '';
    });
    _editFocusNode.unfocus();
  }

  Future<void> _saveInlineEdit() async {
    final newText = _editController.text.trim();
    final oldText = (widget.message.content ?? '').toString();
    if (newText.isEmpty || newText == oldText) {
      _cancelInlineEdit();
      return;
    }

    try {
      // Remove messages after this one
      final messages = ref.read(chatMessagesProvider);
      final idx = messages.indexOf(widget.message);
      if (idx >= 0) {
        final keep = messages.take(idx).toList(growable: false);
        ref.read(chatMessagesProvider.notifier).setMessages(keep);

        // Enqueue edited text as a new message
        final activeConv = ref.read(activeConversationProvider);
        final List<String>? attachments =
            (widget.message.attachmentIds != null &&
                (widget.message.attachmentIds as List).isNotEmpty)
            ? List<String>.from(widget.message.attachmentIds as List)
            : null;
        final toolIds = ref.read(selectedToolIdsProvider);
        await ref
            .read(taskQueueProvider.notifier)
            .enqueueSendText(
              conversationId: activeConv?.id,
              text: newText,
              attachments: attachments,
              toolIds: toolIds.isNotEmpty ? toolIds : null,
            );
      }
    } catch (_) {
      // Swallow errors; upstream error handling will surface if needed
    } finally {
      if (mounted) {
        setState(() {
          _isEditing = false;
        });
        _editFocusNode.unfocus();
      }
    }
  }
}
