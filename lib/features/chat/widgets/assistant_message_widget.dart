import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'dart:convert';
import 'dart:async';
import 'dart:io' show Platform;
import '../../../shared/theme/theme_extensions.dart';
import '../../../shared/widgets/markdown/streaming_markdown_widget.dart';
import '../../../core/utils/reasoning_parser.dart';
import '../../../core/utils/message_segments.dart';
import '../../../core/utils/tool_calls_parser.dart';
import '../../../core/models/chat_message.dart';
import '../providers/text_to_speech_provider.dart';
import 'enhanced_image_attachment.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';
import 'enhanced_attachment.dart';
import 'package:jyotigpt/shared/widgets/chat_action_button.dart';
import '../../../shared/widgets/model_avatar.dart';
import 'package:url_launcher/url_launcher_string.dart';
import '../providers/chat_providers.dart' show sendMessageWithContainer;
import '../../../core/utils/debug_logger.dart';
import 'sources/openwebui_sources.dart';
import '../providers/assistant_response_builder_provider.dart';

// Pre-compiled regex patterns for TTS sanitization (performance optimization)
final _ttsCodeBlockPattern = RegExp(r'```');
final _ttsInlineCodePattern = RegExp(r'`');
final _ttsImagePattern = RegExp(r'!\[(.*?)\]\((.*?)\)');
final _ttsLinkPattern = RegExp(r'\[(.*?)\]\((.*?)\)');
final _ttsBoldPattern1 = RegExp(r'\*\*');
final _ttsBoldPattern2 = RegExp(r'__');
final _ttsItalicPattern1 = RegExp(r'\*');
final _ttsItalicPattern2 = RegExp(r'_');
final _ttsStrikePattern = RegExp(r'~');
final _ttsListPattern = RegExp(r'^[-*+]\s+', multiLine: true);
final _ttsQuotePattern = RegExp(r'^>\s?', multiLine: true);
final _ttsMultiSpacePattern = RegExp(r'[ \t]{2,}');
final _ttsMultiNewlinePattern = RegExp(r'\n{3,}');

// Pre-compiled regex patterns for image processing (performance optimization)
final _base64ImagePattern = RegExp(r'data:image/[^;]+;base64,[A-Za-z0-9+/]+=*');
final _fileIdPattern = RegExp(r'/api/v1/files/([^/]+)/content');

class AssistantMessageWidget extends ConsumerStatefulWidget {
  final dynamic message;
  final bool isStreaming;
  final String? modelName;
  final String? modelIconUrl;
  final VoidCallback? onCopy;
  final VoidCallback? onRegenerate;
  final VoidCallback? onLike;
  final VoidCallback? onDislike;

  const AssistantMessageWidget({
    super.key,
    required this.message,
    this.isStreaming = false,
    this.modelName,
    this.modelIconUrl,
    this.onCopy,
    this.onRegenerate,
    this.onLike,
    this.onDislike,
  });

  @override
  ConsumerState<AssistantMessageWidget> createState() =>
      _AssistantMessageWidgetState();
}

class _AssistantMessageWidgetState extends ConsumerState<AssistantMessageWidget>
    with TickerProviderStateMixin {
  late AnimationController _fadeController;
  late AnimationController _slideController;
  // Unified content segments (text, tool-calls, reasoning)
  List<MessageSegment> _segments = const [];
  final Set<String> _expandedToolIds = {};
  final Set<int> _expandedReasoning = {};
  Widget? _cachedAvatar;
  bool _allowTypingIndicator = false;
  Timer? _typingGateTimer;
  String _ttsPlainText = '';
  // press state handled by shared ChatActionButton

  Future<void> _handleFollowUpTap(String suggestion) async {
    final trimmed = suggestion.trim();
    if (trimmed.isEmpty || widget.isStreaming) {
      return;
    }
    try {
      final container = ProviderScope.containerOf(context, listen: false);
      await sendMessageWithContainer(container, trimmed, null);
    } catch (err, stack) {
      DebugLogger.log(
        'Failed to send follow-up: $err',
        scope: 'chat/assistant',
      );
      debugPrintStack(stackTrace: stack);
    }
  }

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _slideController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );

    // Parse reasoning and tool-calls sections
    _reparseSections();
    _updateTypingIndicatorGate();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Build cached avatar when theme context is available
    _buildCachedAvatar();
  }

  @override
  void didUpdateWidget(AssistantMessageWidget oldWidget) {
    super.didUpdateWidget(oldWidget);

    // Re-parse sections when message content changes
    if (oldWidget.message.content != widget.message.content) {
      _reparseSections();
      _updateTypingIndicatorGate();
    }

    // Update typing indicator gate when message properties that affect emptiness change
    if (oldWidget.message.statusHistory != widget.message.statusHistory ||
        oldWidget.message.files != widget.message.files ||
        oldWidget.message.attachmentIds != widget.message.attachmentIds ||
        oldWidget.message.followUps != widget.message.followUps ||
        oldWidget.message.codeExecutions != widget.message.codeExecutions) {
      _updateTypingIndicatorGate();
    }

    // Rebuild cached avatar if model name or icon changes
    if (oldWidget.modelName != widget.modelName ||
        oldWidget.modelIconUrl != widget.modelIconUrl) {
      _buildCachedAvatar();
    }
  }

  void _reparseSections() {
    final raw0 = widget.message.content ?? '';
    // Strip any leftover placeholders from content before parsing
    const ti = '[TYPING_INDICATOR]';
    const searchBanner = '🔍 Searching the web...';
    String raw = raw0;
    if (raw.startsWith(ti)) {
      raw = raw.substring(ti.length);
    }
    if (raw.startsWith(searchBanner)) {
      raw = raw.substring(searchBanner.length);
    }
    // Do not truncate content during streaming; segmented parser skips
    // incomplete details blocks and tiles will render once complete.
    final rSegs = ReasoningParser.segments(raw);

    final out = <MessageSegment>[];
    final textBuf = StringBuffer();
    if (rSegs == null || rSegs.isEmpty) {
      final tSegs = ToolCallsParser.segments(raw);
      if (tSegs == null || tSegs.isEmpty) {
        out.add(MessageSegment.text(raw));
        textBuf.write(raw);
      } else {
        for (final s in tSegs) {
          if (s.isToolCall && s.entry != null) {
            out.add(MessageSegment.tool(s.entry!));
          } else if ((s.text ?? '').isNotEmpty) {
            out.add(MessageSegment.text(s.text!));
            textBuf.write(s.text);
          }
        }
      }
    } else {
      for (final rs in rSegs) {
        if (rs.isReasoning && rs.entry != null) {
          out.add(MessageSegment.reason(rs.entry!));
        } else if ((rs.text ?? '').isNotEmpty) {
          final t = rs.text!;
          final tSegs = ToolCallsParser.segments(t);
          if (tSegs == null || tSegs.isEmpty) {
            out.add(MessageSegment.text(t));
            textBuf.write(t);
          } else {
            for (final s in tSegs) {
              if (s.isToolCall && s.entry != null) {
                out.add(MessageSegment.tool(s.entry!));
              } else if ((s.text ?? '').isNotEmpty) {
                out.add(MessageSegment.text(s.text!));
                textBuf.write(s.text);
              }
            }
          }
        }
      }
    }

    final segments = out.isEmpty ? [MessageSegment.text(raw)] : out;
    final speechText = _buildTtsPlainText(segments, raw);

    setState(() {
      _segments = segments;
      _ttsPlainText = speechText;
    });
    _updateTypingIndicatorGate();
  }

  void _updateTypingIndicatorGate() {
    _typingGateTimer?.cancel();
    if (_shouldShowTypingIndicator) {
      if (_allowTypingIndicator) {
        return;
      }
      _typingGateTimer = Timer(const Duration(milliseconds: 150), () {
        if (!mounted || !_shouldShowTypingIndicator) {
          return;
        }
        setState(() {
          _allowTypingIndicator = true;
        });
      });
    } else if (_allowTypingIndicator) {
      if (mounted) {
        setState(() {
          _allowTypingIndicator = false;
        });
      } else {
        _allowTypingIndicator = false;
      }
    }
  }

  String get _messageId {
    try {
      final dynamic idValue = widget.message.id;
      if (idValue == null) {
        return '';
      }
      return idValue.toString();
    } catch (_) {
      return '';
    }
  }

  String _buildTtsPlainText(List<MessageSegment> segments, String fallback) {
    if (segments.isEmpty) {
      return _sanitizeForSpeech(fallback);
    }

    final buffer = StringBuffer();
    for (final segment in segments) {
      if (!segment.isText) {
        continue;
      }
      final text = segment.text ?? '';
      final sanitized = _sanitizeForSpeech(text);
      if (sanitized.isEmpty) {
        continue;
      }
      if (buffer.isNotEmpty) {
        buffer.writeln();
        buffer.writeln();
      }
      buffer.write(sanitized);
    }

    final result = buffer.toString().trim();
    if (result.isEmpty) {
      return _sanitizeForSpeech(fallback);
    }
    return result;
  }

  String _sanitizeForSpeech(String input) {
    if (input.isEmpty) {
      return '';
    }

    var text = input;
    // Use pre-compiled regex patterns for better performance
    text = text.replaceAll(_ttsCodeBlockPattern, ' ');
    text = text.replaceAll(_ttsInlineCodePattern, '');
    text = text.replaceAll(_ttsImagePattern, r'$1');
    text = text.replaceAll(_ttsLinkPattern, r'$1');
    text = text.replaceAll(_ttsBoldPattern1, '');
    text = text.replaceAll(_ttsBoldPattern2, '');
    text = text.replaceAll(_ttsItalicPattern1, '');
    text = text.replaceAll(_ttsItalicPattern2, '');
    text = text.replaceAll(_ttsStrikePattern, '');
    text = text.replaceAll(_ttsListPattern, '');
    text = text.replaceAll(_ttsQuotePattern, '');
    text = text.replaceAll('&nbsp;', ' ');
    text = text.replaceAll('&amp;', '&');
    text = text.replaceAll('&lt;', '<');
    text = text.replaceAll('&gt;', '>');
    text = text.replaceAll(_ttsMultiSpacePattern, ' ');
    text = text.replaceAll(_ttsMultiNewlinePattern, '\n\n');
    return text.trim();
  }

  // No streaming-specific markdown fixes needed here; handled by Markdown widget

  Widget _buildToolCallTile(ToolCallEntry tc) {
    final isExpanded = _expandedToolIds.contains(tc.id);
    final theme = context.jyotigptTheme;

    String pretty(dynamic v, {int max = 1200}) {
      try {
        final formatted = const JsonEncoder.withIndent('  ').convert(v);
        return formatted.length > max
            ? '${formatted.substring(0, max)}\n…'
            : formatted;
      } catch (_) {
        final s = v?.toString() ?? '';
        return s.length > max ? '${s.substring(0, max)}…' : s;
      }
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.xs),
      child: InkWell(
        onTap: () {
          setState(() {
            if (isExpanded) {
              _expandedToolIds.remove(tc.id);
            } else {
              _expandedToolIds.add(tc.id);
            }
          });
        },
        borderRadius: BorderRadius.circular(AppBorderRadius.small),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.sm,
            vertical: Spacing.xs,
          ),
          decoration: BoxDecoration(
            color: theme.surfaceContainer.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(AppBorderRadius.small),
            border: Border.all(
              color: theme.dividerColor.withValues(alpha: 0.5),
              width: BorderWidth.thin,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isExpanded
                        ? Icons.expand_less_rounded
                        : Icons.expand_more_rounded,
                    size: 16,
                    color: theme.textSecondary,
                  ),
                  const SizedBox(width: Spacing.xs),
                  Icon(
                    tc.done
                        ? Icons.build_circle_outlined
                        : Icons.play_circle_outline,
                    size: 14,
                    color: theme.buttonPrimary,
                  ),
                  const SizedBox(width: Spacing.xs),
                  Flexible(
                    child: Text(
                      tc.done
                          ? 'Tool Executed: ${tc.name}'
                          : 'Running tool: ${tc.name}…',
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: AppTypography.bodySmall,
                        color: theme.textSecondary,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),

              AnimatedCrossFade(
                firstChild: const SizedBox.shrink(),
                secondChild: Container(
                  margin: const EdgeInsets.only(top: Spacing.sm),
                  padding: const EdgeInsets.all(Spacing.sm),
                  decoration: BoxDecoration(
                    color: theme.surfaceContainer.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(AppBorderRadius.small),
                    border: Border.all(
                      color: theme.dividerColor.withValues(alpha: 0.5),
                      width: BorderWidth.thin,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (tc.arguments != null) ...[
                        Text(
                          'Arguments',
                          style: TextStyle(
                            fontSize: AppTypography.bodySmall,
                            color: theme.textSecondary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: Spacing.xxs),
                        SelectableText(
                          pretty(tc.arguments),
                          style: TextStyle(
                            fontSize: AppTypography.bodySmall,
                            color: theme.textSecondary,
                            fontFamily: 'monospace',
                            height: 1.35,
                          ),
                        ),
                        const SizedBox(height: Spacing.sm),
                      ],

                      if (tc.result != null) ...[
                        Text(
                          'Result',
                          style: TextStyle(
                            fontSize: AppTypography.bodySmall,
                            color: theme.textSecondary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: Spacing.xxs),
                        SelectableText(
                          pretty(tc.result),
                          style: TextStyle(
                            fontSize: AppTypography.bodySmall,
                            color: theme.textSecondary,
                            fontFamily: 'monospace',
                            height: 1.35,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                crossFadeState: isExpanded
                    ? CrossFadeState.showSecond
                    : CrossFadeState.showFirst,
                duration: const Duration(milliseconds: 200),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSegmentedContent() {
    final children = <Widget>[];
    // Determine if media (attachments or generated images) is rendered above.
    final hasMediaAbove =
        (widget.message.attachmentIds?.isNotEmpty ?? false) ||
        (widget.message.files?.isNotEmpty ?? false);
    bool firstToolSpacerAdded = false;
    int idx = 0;
    for (final seg in _segments) {
      if (seg.isTool && seg.toolCall != null) {
        // Add top spacing before the first tool block for clarity
        if (!firstToolSpacerAdded) {
          children.add(const SizedBox(height: Spacing.sm));
          firstToolSpacerAdded = true;
        }
        children.add(_buildToolCallTile(seg.toolCall!));
      } else if (seg.isReasoning && seg.reasoning != null) {
        // If a reasoning tile is the very first content and sits at the top,
        // add a small spacer above it for breathing room.
        if (children.isEmpty && !hasMediaAbove) {
          children.add(const SizedBox(height: Spacing.sm));
        }
        children.add(_buildReasoningTile(seg.reasoning!, idx));
      } else if ((seg.text ?? '').trim().isNotEmpty) {
        children.add(_buildEnhancedMarkdownContent(seg.text!));
      }
      idx++;
    }

    if (children.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: children,
    );
  }

  bool get _shouldShowTypingIndicator =>
      widget.isStreaming && _isAssistantResponseEmpty;

  bool get _isAssistantResponseEmpty {
    final content = widget.message.content.trim();
    if (content.isNotEmpty) {
      return false;
    }

    final hasFiles = widget.message.files?.isNotEmpty ?? false;
    if (hasFiles) {
      return false;
    }

    final hasAttachments = widget.message.attachmentIds?.isNotEmpty ?? false;
    if (hasAttachments) {
      return false;
    }

    final hasVisibleStatus = widget.message.statusHistory
        .where((status) => status.hidden != true)
        .isNotEmpty;
    if (hasVisibleStatus) {
      return false;
    }

    final hasFollowUps = widget.message.followUps.isNotEmpty;
    if (hasFollowUps) {
      return false;
    }

    final hasCodeExecutions = widget.message.codeExecutions.isNotEmpty;
    if (hasCodeExecutions) {
      return false;
    }

    // Check for tool calls in the content using ToolCallsParser
    final hasToolCalls =
        ToolCallsParser.segments(
          content,
        )?.any((segment) => segment.isToolCall) ??
        false;
    return !hasToolCalls;
  }

  void _buildCachedAvatar() {
    final theme = context.jyotigptTheme;
    final iconUrl = widget.modelIconUrl?.trim();
    final hasIcon = iconUrl != null && iconUrl.isNotEmpty;

    final Widget leading = hasIcon
        ? ModelAvatar(size: 20, imageUrl: iconUrl, label: widget.modelName)
        : Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(
              color: theme.buttonPrimary,
              borderRadius: BorderRadius.circular(AppBorderRadius.small),
            ),
            child: Icon(
              Icons.auto_awesome,
              color: theme.buttonPrimaryText,
              size: 12,
            ),
          );

    _cachedAvatar = Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          leading,
          const SizedBox(width: Spacing.xs),
          Text(
            widget.modelName ?? 'Assistant',
            style: TextStyle(
              color: theme.textSecondary,
              fontSize: AppTypography.bodySmall,
              fontWeight: FontWeight.w500,
              letterSpacing: 0.1,
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _typingGateTimer?.cancel();
    _fadeController.dispose();
    _slideController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _buildDocumentationMessage();
  }

  Widget _buildDocumentationMessage() {
    final visibleStatusHistory = widget.message.statusHistory
        .where((status) => status.hidden != true)
        .toList(growable: false);
    final hasStatusTimeline = visibleStatusHistory.isNotEmpty;
    final hasCodeExecutions = widget.message.codeExecutions.isNotEmpty;
    final hasFollowUps =
        widget.message.followUps.isNotEmpty && !widget.isStreaming;
    final hasSources = widget.message.sources.isNotEmpty;

    return Container(
          width: double.infinity,
          margin: const EdgeInsets.only(
            bottom: 16,
            left: Spacing.xs,
            right: Spacing.xs,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Cached AI Name and Avatar to prevent flashing
              _cachedAvatar ?? const SizedBox.shrink(),

              // Reasoning blocks are now rendered inline where they appear

              // Documentation-style content without heavy bubble; premium markdown
              SizedBox(
                width: double.infinity,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Display attachments - prioritize files array over attachmentIds to avoid duplication
                    if (widget.message.files != null &&
                        widget.message.files!.isNotEmpty) ...[
                      _buildFilesFromArray(),
                      const SizedBox(height: Spacing.md),
                    ] else if (widget.message.attachmentIds != null &&
                        widget.message.attachmentIds!.isNotEmpty) ...[
                      _buildAttachmentItems(),
                      const SizedBox(height: Spacing.md),
                    ],

                    if (hasStatusTimeline) ...[
                      StatusHistoryTimeline(
                        updates: visibleStatusHistory,
                        initiallyExpanded: widget.message.content
                            .trim()
                            .isEmpty,
                      ),
                      const SizedBox(height: Spacing.xs),
                    ],

                    // Tool calls are rendered inline via segmented content
                    // Smoothly crossfade between typing indicator and content
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 220),
                      switchInCurve: Curves.easeOutCubic,
                      switchOutCurve: Curves.easeInCubic,
                      transitionBuilder: (child, anim) {
                        final fade = CurvedAnimation(
                          parent: anim,
                          curve: Curves.easeOutCubic,
                          reverseCurve: Curves.easeInCubic,
                        );
                        final size = CurvedAnimation(
                          parent: anim,
                          curve: Curves.easeOutCubic,
                          reverseCurve: Curves.easeInCubic,
                        );
                        return FadeTransition(
                          opacity: fade,
                          child: SizeTransition(
                            sizeFactor: size,
                            axisAlignment: -1.0, // collapse/expand from top
                            child: child,
                          ),
                        );
                      },
                      child:
                          (_allowTypingIndicator && _shouldShowTypingIndicator)
                          ? KeyedSubtree(
                              key: const ValueKey('typing'),
                              child: _buildTypingIndicator(),
                            )
                          : KeyedSubtree(
                              key: const ValueKey('content'),
                              child: _buildSegmentedContent(),
                            ),
                    ),

                    if (hasCodeExecutions) ...[
                      const SizedBox(height: Spacing.md),
                      CodeExecutionListView(
                        executions: widget.message.codeExecutions,
                      ),
                    ],

                    if (hasSources) ...[
                      const SizedBox(height: Spacing.xs),
                      OpenWebUISourcesWidget(
                        sources: widget.message.sources,
                        messageId: widget.message.id,
                      ),
                    ],
                  ],
                ),
              ),

              // Action buttons below the message content (only after streaming completes)
              if (!widget.isStreaming) ...[
                const SizedBox(height: Spacing.sm),
                _buildActionButtons(),
                if (hasFollowUps) ...[
                  const SizedBox(height: Spacing.md),
                  FollowUpSuggestionBar(
                    suggestions: widget.message.followUps,
                    onSelected: _handleFollowUpTap,
                    isBusy: widget.isStreaming,
                  ),
                ],
              ],
            ],
          ),
        )
        .animate()
        .fadeIn(duration: const Duration(milliseconds: 300))
        .slideY(
          begin: 0.1,
          end: 0,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutCubic,
        );
  }

  Widget _buildEnhancedMarkdownContent(String content) {
    if (content.trim().isEmpty) {
      return const SizedBox.shrink();
    }

    // Note: The markdown parser now handles <details> tags (including type="reasoning"
    // and type="tool_calls") via a custom block syntax, so they won't be rendered as
    // plain text during streaming. This prevents character flashing.

    // Quick check: only run cleanup if raw tags might exist (rare case)
    String cleaned = content;
    if (content.contains('<think>') || content.contains('<reasoning>')) {
      // Clean raw reasoning tags as a fallback for raw mode or direct API responses.
      // The server normally converts these to <details> format.
      cleaned = content
          .replaceAll(
            RegExp(r'<think>[\s\S]*?<\/think>', multiLine: true, dotAll: true),
            '',
          )
          .replaceAll(
            RegExp(
              r'<reasoning>[\s\S]*?<\/reasoning>',
              multiLine: true,
              dotAll: true,
            ),
            '',
          );
    }

    // Process images in the remaining text
    final processedContent = _processContentForImages(cleaned);

    Widget buildDefault(BuildContext context) => StreamingMarkdownWidget(
      content: processedContent,
      isStreaming: widget.isStreaming,
      onTapLink: (url, _) => _launchUri(url),
      imageBuilderOverride: (uri, title, alt) {
        // Route markdown images through the enhanced image widget so they
        // get caching, auth headers, fullscreen viewer, and sharing.
        return EnhancedImageAttachment(
          attachmentId: uri.toString(),
          isMarkdownFormat: true,
          constraints: const BoxConstraints(maxWidth: 500, maxHeight: 400),
          disableAnimation: widget.isStreaming,
        );
      },
    );

    final responseBuilder = ref.watch(assistantResponseBuilderProvider);
    if (responseBuilder != null) {
      final contextData = AssistantResponseContext(
        message: widget.message,
        markdown: processedContent,
        isStreaming: widget.isStreaming,
        buildDefault: buildDefault,
      );
      return responseBuilder(context, contextData);
    }

    return buildDefault(context);
  }

  String _processContentForImages(String content) {
    // Check if content contains image markdown or base64 data URLs
    // This ensures images generated by AI are properly formatted

    // Quick check: only process if we have base64 images and no markdown
    if (!content.contains('data:image/') || content.contains('![')) {
      return content;
    }

    // If we find base64 images not wrapped in markdown, wrap them
    if (_base64ImagePattern.hasMatch(content)) {
      content = content.replaceAllMapped(_base64ImagePattern, (match) {
        final imageData = match.group(0)!;
        // Check if this image is already in markdown format (simple string check)
        if (!content.contains('![$imageData)')) {
          return '\n![Generated Image]($imageData)\n';
        }
        return imageData;
      });
    }

    return content;
  }

  Widget _buildAttachmentItems() {
    if (widget.message.attachmentIds == null ||
        widget.message.attachmentIds!.isEmpty) {
      return const SizedBox.shrink();
    }

    final imageCount = widget.message.attachmentIds!.length;

    // Display images in a clean, modern layout for assistant messages
    // Use AnimatedSwitcher for smooth transitions when loading
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      switchInCurve: Curves.easeInOut,
      child: imageCount == 1
          ? Container(
              key: ValueKey('single_item_${widget.message.attachmentIds![0]}'),
              child: EnhancedAttachment(
                attachmentId: widget.message.attachmentIds![0],
                isMarkdownFormat: true,
                constraints: const BoxConstraints(
                  maxWidth: 500,
                  maxHeight: 400,
                ),
                disableAnimation: widget.isStreaming,
              ),
            )
          : Wrap(
              key: ValueKey(
                'multi_items_${widget.message.attachmentIds!.join('_')}',
              ),
              spacing: Spacing.sm,
              runSpacing: Spacing.sm,
              children: widget.message.attachmentIds!.map<Widget>((
                attachmentId,
              ) {
                return EnhancedAttachment(
                  key: ValueKey('attachment_$attachmentId'),
                  attachmentId: attachmentId,
                  isMarkdownFormat: true,
                  constraints: BoxConstraints(
                    maxWidth: imageCount == 2 ? 245 : 160,
                    maxHeight: imageCount == 2 ? 245 : 160,
                  ),
                  disableAnimation: widget.isStreaming,
                );
              }).toList(),
            ),
    );
  }

  Widget _buildFilesFromArray() {
    if (widget.message.files == null || widget.message.files!.isEmpty) {
      return const SizedBox.shrink();
    }

    final allFiles = widget.message.files!;

    // Separate images and non-image files
    final imageFiles = allFiles
        .where((file) => file['type'] == 'image')
        .toList();
    final nonImageFiles = allFiles
        .where((file) => file['type'] != 'image')
        .toList();

    final widgets = <Widget>[];

    // Add images first
    if (imageFiles.isNotEmpty) {
      widgets.add(_buildImagesFromFiles(imageFiles));
    }

    // Add non-image files
    if (nonImageFiles.isNotEmpty) {
      if (widgets.isNotEmpty) {
        widgets.add(const SizedBox(height: Spacing.sm));
      }
      widgets.add(_buildNonImageFiles(nonImageFiles));
    }

    if (widgets.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  Widget _buildImagesFromFiles(List<dynamic> imageFiles) {
    final imageCount = imageFiles.length;

    // Display images using EnhancedImageAttachment for consistency
    // Use AnimatedSwitcher for smooth transitions
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      switchInCurve: Curves.easeInOut,
      child: imageCount == 1
          ? Container(
              key: ValueKey('file_single_${imageFiles[0]['url']}'),
              child: Builder(
                builder: (context) {
                  final imageUrl = imageFiles[0]['url'] as String?;
                  if (imageUrl == null) return const SizedBox.shrink();

                  return EnhancedImageAttachment(
                    attachmentId:
                        imageUrl, // Pass URL directly as it handles URLs
                    isMarkdownFormat: true,
                    constraints: const BoxConstraints(
                      maxWidth: 500,
                      maxHeight: 400,
                    ),
                    disableAnimation:
                        false, // Keep animations enabled to prevent black display
                  );
                },
              ),
            )
          : Wrap(
              key: ValueKey(
                'file_multi_${imageFiles.map((f) => f['url']).join('_')}',
              ),
              spacing: Spacing.sm,
              runSpacing: Spacing.sm,
              children: imageFiles.map<Widget>((file) {
                final imageUrl = file['url'] as String?;
                if (imageUrl == null) return const SizedBox.shrink();

                return EnhancedImageAttachment(
                  key: ValueKey('gen_attachment_$imageUrl'),
                  attachmentId: imageUrl, // Pass URL directly
                  isMarkdownFormat: true,
                  constraints: BoxConstraints(
                    maxWidth: imageCount == 2 ? 245 : 160,
                    maxHeight: imageCount == 2 ? 245 : 160,
                  ),
                  disableAnimation:
                      false, // Keep animations enabled to prevent black display
                );
              }).toList(),
            ),
    );
  }

  Widget _buildNonImageFiles(List<dynamic> nonImageFiles) {
    return Wrap(
      spacing: Spacing.sm,
      runSpacing: Spacing.sm,
      children: nonImageFiles.map<Widget>((file) {
        final fileUrl = file['url'] as String?;

        if (fileUrl == null) return const SizedBox.shrink();

        // Extract file ID from URL if it's in the format /api/v1/files/{id}/content
        String attachmentId = fileUrl;
        if (fileUrl.contains('/api/v1/files/') &&
            fileUrl.contains('/content')) {
          final fileIdMatch = _fileIdPattern.firstMatch(fileUrl);
          if (fileIdMatch != null) {
            attachmentId = fileIdMatch.group(1)!;
          }
        }

        return EnhancedAttachment(
          key: ValueKey('file_attachment_$attachmentId'),
          attachmentId: attachmentId,
          isMarkdownFormat: true,
          constraints: const BoxConstraints(maxWidth: 300, maxHeight: 100),
          disableAnimation: widget.isStreaming,
        );
      }).toList(),
    );
  }

  Widget _buildTypingIndicator() {
    final theme = context.jyotigptTheme;
    final dotColor = theme.textSecondary.withValues(alpha: 0.75);

    const double dotSize = 8.0;
    const double dotSpacing = 6.0;
    const int numberOfDots = 3;

    // Create three dots with staggered animations
    final dots = List.generate(numberOfDots, (index) {
      final delay = Duration(milliseconds: 150 * index);

      return Container(
            width: dotSize,
            height: dotSize,
            decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle),
          )
          .animate(onPlay: (controller) => controller.repeat())
          .then(delay: delay)
          .fadeIn(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          )
          .scale(
            duration: const Duration(milliseconds: 600),
            curve: Curves.easeInOut,
            begin: const Offset(0.4, 0.4),
            end: const Offset(1, 1),
          )
          .then()
          .scale(
            duration: const Duration(milliseconds: 600),
            curve: Curves.easeInOut,
            begin: const Offset(1.2, 1.2),
            end: const Offset(0.5, 0.5),
          );
    });

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: Spacing.sm),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Add left padding to prevent clipping when dots scale up
          const SizedBox(width: dotSize * 0.2),
          for (int i = 0; i < numberOfDots; i++) ...[
            dots[i],
            if (i < numberOfDots - 1) const SizedBox(width: dotSpacing),
          ],
          // Add right padding to prevent clipping when dots scale up
          const SizedBox(width: dotSize * 0.2),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    final l10n = AppLocalizations.of(context)!;
    final ttsState = ref.watch(textToSpeechControllerProvider);
    final messageId = _messageId;
    final hasSpeechText = _ttsPlainText.trim().isNotEmpty;
    final isErrorMessage =
        widget.message.content.contains('⚠️') ||
        widget.message.content.contains('Error') ||
        widget.message.content.contains('timeout') ||
        widget.message.content.contains('retry options');

    final isActiveMessage = ttsState.activeMessageId == messageId;
    final isSpeaking =
        isActiveMessage && ttsState.status == TtsPlaybackStatus.speaking;
    final isPaused =
        isActiveMessage && ttsState.status == TtsPlaybackStatus.paused;
    final isBusy =
        isActiveMessage &&
        (ttsState.status == TtsPlaybackStatus.loading ||
            ttsState.status == TtsPlaybackStatus.initializing);
    final bool disableDueToStreaming = widget.isStreaming && !isActiveMessage;
    final bool ttsAvailable = !ttsState.initialized || ttsState.available;
    final bool showStopState =
        isActiveMessage && (isSpeaking || isPaused || isBusy);
    final bool shouldShowTtsButton = hasSpeechText && messageId.isNotEmpty;
    final bool canStartTts =
        shouldShowTtsButton && !disableDueToStreaming && ttsAvailable;

    VoidCallback? ttsOnTap;
    if (showStopState || canStartTts) {
      ttsOnTap = () {
        if (messageId.isEmpty) {
          return;
        }
        ref
            .read(textToSpeechControllerProvider.notifier)
            .toggleForMessage(messageId: messageId, text: _ttsPlainText);
      };
    }

    final IconData listenIcon = Platform.isIOS
        ? CupertinoIcons.speaker_2_fill
        : Icons.volume_up;
    final IconData stopIcon = Platform.isIOS
        ? CupertinoIcons.stop_fill
        : Icons.stop;
    final IconData ttsIcon = showStopState ? stopIcon : listenIcon;
    final String ttsLabel = showStopState ? l10n.ttsStop : l10n.ttsListen;

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        if (shouldShowTtsButton)
          _buildActionButton(icon: ttsIcon, label: ttsLabel, onTap: ttsOnTap),
        _buildActionButton(
          icon: Platform.isIOS
              ? CupertinoIcons.doc_on_clipboard
              : Icons.content_copy,
          label: l10n.copy,
          onTap: widget.onCopy,
        ),
        if (isErrorMessage) ...[
          _buildActionButton(
            icon: Platform.isIOS
                ? CupertinoIcons.arrow_clockwise
                : Icons.refresh,
            label: l10n.retry,
            onTap: widget.onRegenerate,
          ),
        ] else ...[
          _buildActionButton(
            icon: Platform.isIOS ? CupertinoIcons.refresh : Icons.refresh,
            label: l10n.regenerate,
            onTap: widget.onRegenerate,
          ),
        ],
      ],
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    VoidCallback? onTap,
  }) {
    return ChatActionButton(icon: icon, label: label, onTap: onTap);
  }

  // Reasoning tile rendered inline at the position it appears
  Widget _buildReasoningTile(ReasoningEntry rc, int index) {
    final isExpanded = _expandedReasoning.contains(index);
    final theme = context.jyotigptTheme;

    String headerText() {
      final l10n = AppLocalizations.of(context)!;
      final hasSummary = rc.summary.isNotEmpty;
      final isThinkingSummary =
          rc.summary.trim().toLowerCase() == 'thinking…' ||
          rc.summary.trim().toLowerCase() == 'thinking...';
      if (widget.isStreaming) {
        return hasSummary ? rc.summary : l10n.thinking;
      }
      if (rc.duration > 0) {
        return l10n.thoughtForDuration(rc.formattedDuration);
      }
      if (!hasSummary || isThinkingSummary) {
        return l10n.thoughts;
      }
      return rc.summary;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.xs),
      child: InkWell(
        onTap: () {
          setState(() {
            if (isExpanded) {
              _expandedReasoning.remove(index);
            } else {
              _expandedReasoning.add(index);
            }
          });
        },
        borderRadius: BorderRadius.circular(AppBorderRadius.small),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.sm,
            vertical: Spacing.xs,
          ),
          decoration: BoxDecoration(
            color: theme.surfaceContainer.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(AppBorderRadius.small),
            border: Border.all(
              color: theme.dividerColor.withValues(alpha: 0.5),
              width: BorderWidth.thin,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isExpanded
                        ? Icons.expand_less_rounded
                        : Icons.expand_more_rounded,
                    size: 16,
                    color: theme.textSecondary,
                  ),
                  const SizedBox(width: Spacing.xs),
                  Icon(
                    Icons.psychology_outlined,
                    size: 14,
                    color: theme.buttonPrimary,
                  ),
                  const SizedBox(width: Spacing.xs),
                  Flexible(
                    child: Text(
                      headerText(),
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: AppTypography.bodySmall,
                        color: theme.textSecondary,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),

              AnimatedCrossFade(
                firstChild: const SizedBox.shrink(),
                secondChild: Container(
                  margin: const EdgeInsets.only(top: Spacing.sm),
                  padding: const EdgeInsets.all(Spacing.sm),
                  decoration: BoxDecoration(
                    color: theme.surfaceContainer.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(AppBorderRadius.small),
                    border: Border.all(
                      color: theme.dividerColor.withValues(alpha: 0.5),
                      width: BorderWidth.thin,
                    ),
                  ),
                  child: SelectableText(
                    rc.cleanedReasoning,
                    style: TextStyle(
                      fontSize: AppTypography.bodySmall,
                      color: theme.textSecondary,
                      fontFamily: 'monospace',
                      height: 1.4,
                    ),
                  ),
                ),
                crossFadeState: isExpanded
                    ? CrossFadeState.showSecond
                    : CrossFadeState.showFirst,
                duration: const Duration(milliseconds: 200),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class StatusHistoryTimeline extends StatefulWidget {
  const StatusHistoryTimeline({
    super.key,
    required this.updates,
    this.initiallyExpanded = false,
  });

  final List<ChatStatusUpdate> updates;
  final bool initiallyExpanded;

  @override
  State<StatusHistoryTimeline> createState() => _StatusHistoryTimelineState();
}

class _StatusHistoryTimelineState extends State<StatusHistoryTimeline> {
  late bool _expanded;

  @override
  void initState() {
    super.initState();
    _expanded = widget.initiallyExpanded;
  }

  @override
  void didUpdateWidget(covariant StatusHistoryTimeline oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initiallyExpanded != oldWidget.initiallyExpanded) {
      _expanded = widget.initiallyExpanded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;
    final visible = widget.updates
        .where((update) => update.hidden != true)
        .toList();
    if (visible.isEmpty) {
      return const SizedBox.shrink();
    }

    final previous = visible.length > 1
        ? visible.sublist(0, visible.length - 1)
        : const [];
    final current = visible.last;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AnimatedSize(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          child: !_expanded || previous.isEmpty
              ? const SizedBox.shrink()
              : Column(
                  children: previous
                      .map(
                        (update) => _TimelineRow(
                          update: update,
                          theme: theme,
                          showTail: true,
                          forceDone: true,
                        ),
                      )
                      .toList(growable: false),
                ),
        ),
        _TimelineRow(
          update: current,
          theme: theme,
          showTail: false,
          forceDone: current.done == true ? true : null,
          onTap: previous.isNotEmpty
              ? () => setState(() => _expanded = !_expanded)
              : null,
          showChevron: previous.isNotEmpty,
          expanded: _expanded,
        ),
      ],
    );
  }
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({
    required this.update,
    required this.theme,
    required this.showTail,
    this.forceDone,
    this.onTap,
    this.showChevron = false,
    this.expanded = false,
  });

  final ChatStatusUpdate update;
  final JyotiGPTThemeExtension theme;
  final bool showTail;
  final bool? forceDone;
  final VoidCallback? onTap;
  final bool showChevron;
  final bool expanded;

  bool get _isPending {
    final resolved = forceDone ?? update.done;
    return resolved != true;
  }

  @override
  Widget build(BuildContext context) {
    final resolved = forceDone ?? update.done;
    final dotColor = _indicatorColor(theme, resolved);
    final content = _StatusHistoryContent(
      update: update,
      theme: theme,
      isPending: _isPending,
    );

    final row = IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _TimelineIndicator(
            color: dotColor,
            showTail: showTail,
            animatePulse: _isPending,
            theme: theme,
          ),
          const SizedBox(width: Spacing.xs),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: content),
                if (showChevron)
                  Padding(
                    padding: const EdgeInsets.only(left: Spacing.xs, top: 4),
                    child: AnimatedRotation(
                      turns: expanded ? 0.5 : 0.0,
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.easeOutCubic,
                      child: Icon(
                        Icons.expand_more,
                        size: 16,
                        color: theme.textSecondary.withValues(alpha: 0.6),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );

    final wrapped = Padding(
      padding: const EdgeInsets.symmetric(vertical: Spacing.xxs),
      child: row,
    );

    if (onTap == null) {
      return wrapped;
    }

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppBorderRadius.small),
      child: wrapped,
    );
  }

  Color _indicatorColor(JyotiGPTThemeExtension theme, bool? done) {
    if (done == false) {
      return theme.iconPrimary;
    }
    if (done == true) {
      return theme.success;
    }
    return theme.iconSecondary.withValues(alpha: 0.7);
  }
}

class _TimelineIndicator extends StatefulWidget {
  const _TimelineIndicator({
    required this.color,
    required this.showTail,
    required this.animatePulse,
    required this.theme,
  });

  final Color color;
  final bool showTail;
  final bool animatePulse;
  final JyotiGPTThemeExtension theme;

  @override
  State<_TimelineIndicator> createState() => _TimelineIndicatorState();
}

class _TimelineIndicatorState extends State<_TimelineIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    if (widget.animatePulse) {
      _controller.repeat();
    }
  }

  @override
  void didUpdateWidget(covariant _TimelineIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.animatePulse && !_controller.isAnimating) {
      _controller.repeat();
    } else if (!widget.animatePulse && _controller.isAnimating) {
      _controller.stop();
      _controller.reset();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final lineColor = widget.theme.dividerColor.withValues(alpha: 0.5);

    return SizedBox(
      width: 18,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.start,
        children: [
          SizedBox(
            height: 16,
            width: 16,
            child: Stack(
              alignment: Alignment.center,
              children: [
                if (widget.animatePulse)
                  FadeTransition(
                    opacity: _controller.drive(
                      Tween<double>(begin: 0.45, end: 0.0),
                    ),
                    child: ScaleTransition(
                      scale: _controller.drive(
                        Tween<double>(
                          begin: 1.0,
                          end: 2.2,
                        ).chain(CurveTween(curve: Curves.easeOutCubic)),
                      ),
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: widget.color.withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                DecoratedBox(
                  decoration: BoxDecoration(
                    color: widget.color,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const SizedBox.square(dimension: 8),
                ),
              ],
            ),
          ),
          if (widget.showTail)
            Expanded(
              child: Align(
                alignment: Alignment.topCenter,
                child: Container(
                  margin: const EdgeInsets.only(top: Spacing.xxs),
                  width: 1,
                  color: lineColor,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _StatusHistoryContent extends StatelessWidget {
  const _StatusHistoryContent({
    required this.update,
    required this.theme,
    required this.isPending,
  });

  final ChatStatusUpdate update;
  final JyotiGPTThemeExtension theme;
  final bool isPending;

  @override
  Widget build(BuildContext context) {
    final description = _resolveStatusDescription(update);
    final queries = _collectQueries(update);
    final linkChips = _buildLinkChips(update);

    final headlineStyle = TextStyle(
      fontSize: AppTypography.bodySmall,
      fontWeight: FontWeight.w600,
      height: 1.3,
      color: isPending ? theme.textPrimary : theme.textSecondary,
    );

    final content = <Widget>[Text(description, style: headlineStyle)];

    if (update.count != null && update.action != 'sources_retrieved') {
      content.add(
        Text(
          update.count == 1
              ? 'Retrieved 1 source'
              : 'Retrieved ${update.count} sources',
          style: TextStyle(
            fontSize: AppTypography.labelSmall,
            color: theme.textSecondary.withValues(alpha: 0.75),
          ),
        ),
      );
    }

    if (queries.isNotEmpty) {
      content.add(_QueryPills(queries: queries, theme: theme));
    }

    if (linkChips.isNotEmpty) {
      content.add(_LinkPills(items: linkChips, theme: theme));
    }

    final timestamp = update.occurredAt;
    if (timestamp != null) {
      content.add(
        Text(
          _relativeTime(timestamp),
          style: TextStyle(
            fontSize: AppTypography.labelSmall,
            color: theme.textSecondary.withValues(alpha: 0.55),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < content.length; i++)
          Padding(
            padding: EdgeInsets.only(top: i == 0 ? 0 : Spacing.xxs),
            child: content[i],
          ),
      ],
    );
  }
}

class _QueryPills extends StatelessWidget {
  const _QueryPills({required this.queries, required this.theme});

  final List<String> queries;
  final JyotiGPTThemeExtension theme;

  @override
  Widget build(BuildContext context) {
    final iconColor = theme.iconSecondary;
    final textStyle = TextStyle(
      fontSize: AppTypography.labelSmall,
      color: theme.textSecondary,
    );

    return Wrap(
      spacing: Spacing.xs,
      runSpacing: Spacing.xs,
      children: queries
          .map(
            (query) => InkWell(
              onTap: () => _launchUri(
                'https://www.google.com/search?q=${Uri.encodeComponent(query)}',
              ),
              borderRadius: BorderRadius.circular(AppBorderRadius.small),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: Spacing.sm,
                  vertical: Spacing.xs,
                ),
                decoration: BoxDecoration(
                  color: theme.surfaceContainer.withValues(alpha: 0.25),
                  borderRadius: BorderRadius.circular(AppBorderRadius.small),
                  border: Border.all(
                    color: theme.dividerColor.withValues(alpha: 0.3),
                    width: BorderWidth.thin,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.search,
                      size: AppTypography.labelSmall + 2,
                      color: iconColor,
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        query,
                        style: textStyle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _LinkPills extends StatelessWidget {
  const _LinkPills({required this.items, required this.theme});

  final List<_LinkChipData> items;
  final JyotiGPTThemeExtension theme;

  @override
  Widget build(BuildContext context) {
    final iconColor = theme.iconPrimary;
    final textStyle = TextStyle(
      fontSize: AppTypography.labelSmall,
      color: theme.buttonPrimary,
      fontWeight: FontWeight.w600,
    );

    return Wrap(
      spacing: Spacing.xs,
      runSpacing: Spacing.xs,
      children: items
          .map(
            (item) => InkWell(
              onTap: item.url != null ? () => _launchUri(item.url!) : null,
              borderRadius: BorderRadius.circular(AppBorderRadius.small),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: Spacing.sm,
                  vertical: Spacing.xs,
                ),
                decoration: BoxDecoration(
                  color: theme.surfaceContainer.withValues(alpha: 0.25),
                  borderRadius: BorderRadius.circular(AppBorderRadius.small),
                  border: Border.all(
                    color: theme.dividerColor.withValues(alpha: 0.3),
                    width: BorderWidth.thin,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Icon(
                      item.icon,
                      size: AppTypography.labelSmall + 2,
                      color: iconColor,
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        item.label,
                        style: textStyle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (item.url != null) ...[
                      const SizedBox(width: 4),
                      Icon(
                        Icons.open_in_new,
                        size: 11,
                        color: iconColor.withValues(alpha: 0.7),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _LinkChipData {
  const _LinkChipData({required this.label, required this.icon, this.url});

  final String label;
  final IconData icon;
  final String? url;
}

List<String> _collectQueries(ChatStatusUpdate update) {
  final merged = <String>[];
  for (final query in update.queries) {
    final trimmed = query.trim();
    if (trimmed.isNotEmpty) {
      merged.add(trimmed);
    }
  }
  final single = update.query?.trim();
  if (single != null && single.isNotEmpty && !merged.contains(single)) {
    merged.add(single);
  }
  return merged;
}

List<_LinkChipData> _buildLinkChips(ChatStatusUpdate update) {
  final chips = <_LinkChipData>[];
  if (update.items.isNotEmpty) {
    for (final item in update.items) {
      final title = item.title?.trim();
      final label = (title != null && title.isNotEmpty)
          ? title
          : (item.link != null ? _extractHost(item.link!) : 'Result');
      chips.add(
        _LinkChipData(label: label, icon: Icons.public, url: item.link),
      );
    }
  } else if (update.urls.isNotEmpty) {
    for (final url in update.urls) {
      chips.add(
        _LinkChipData(label: _extractHost(url), icon: Icons.public, url: url),
      );
    }
  }
  return chips;
}

String _resolveStatusDescription(ChatStatusUpdate update) {
  final description = update.description?.trim();
  final action = update.action?.trim();

  if (action == 'knowledge_search' && update.query?.isNotEmpty == true) {
    return 'Searching knowledge for "${update.query}"';
  }

  if (action == 'web_search_queries_generated' ||
      action == 'queries_generated') {
    return 'Searching';
  }

  if (action == 'sources_retrieved') {
    final count = update.count;
    if (count == null) {
      return 'Retrieved sources';
    }
    if (count == 0) {
      return 'No sources found';
    }
    if (count == 1) {
      return 'Retrieved 1 source';
    }
    return 'Retrieved $count sources';
  }

  if (description != null && description.isNotEmpty) {
    return _replaceStatusPlaceholders(description, update);
  }

  if (action != null && action.isNotEmpty) {
    return action.replaceAll('_', ' ');
  }

  return 'Processing';
}

String _replaceStatusPlaceholders(String template, ChatStatusUpdate update) {
  var result = template;

  if (result.contains('{{count}}')) {
    final fallback = update.count ?? _inferCount(update);
    result = result.replaceAll(
      '{{count}}',
      fallback != null ? fallback.toString() : 'multiple',
    );
  }

  if (result.contains('{{searchQuery}}')) {
    final query = update.query?.trim();
    if (query != null && query.isNotEmpty) {
      result = result.replaceAll('{{searchQuery}}', query);
    }
  }

  return result;
}

int? _inferCount(ChatStatusUpdate update) {
  if (update.urls.isNotEmpty) {
    return update.urls.length;
  }
  if (update.items.isNotEmpty) {
    return update.items.length;
  }
  if (update.queries.isNotEmpty) {
    return update.queries.length;
  }
  return null;
}

String _relativeTime(DateTime timestamp) {
  final local = timestamp.toLocal();
  final now = DateTime.now();
  final difference = now.difference(local);
  if (difference.inMinutes < 1) {
    return 'Just now';
  }
  if (difference.inHours < 1) {
    final minutes = difference.inMinutes;
    return minutes == 1 ? '1 minute ago' : '$minutes minutes ago';
  }
  return '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
}

String _extractHost(String url) {
  final uri = Uri.tryParse(url);
  if (uri == null || uri.host.isEmpty) {
    return url;
  }
  return uri.host;
}

class CodeExecutionListView extends StatelessWidget {
  const CodeExecutionListView({super.key, required this.executions});

  final List<ChatCodeExecution> executions;

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;
    if (executions.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Code executions',
          style: TextStyle(
            color: theme.textPrimary,
            fontWeight: FontWeight.w600,
            fontSize: AppTypography.bodyLarge,
          ),
        ),
        const SizedBox(height: Spacing.xs),
        Wrap(
          spacing: Spacing.xs,
          runSpacing: Spacing.xs,
          children: executions.map((execution) {
            final hasError = execution.result?.error != null;
            final hasOutput = execution.result?.output != null;
            IconData icon;
            Color iconColor;
            if (hasError) {
              icon = Icons.error_outline;
              iconColor = theme.error;
            } else if (hasOutput) {
              icon = Icons.check_circle_outline;
              iconColor = theme.success;
            } else {
              icon = Icons.sync;
              iconColor = theme.textSecondary;
            }
            final label = execution.name?.isNotEmpty == true
                ? execution.name!
                : 'Execution';
            return ActionChip(
              avatar: Icon(icon, size: 16, color: iconColor),
              label: Text(label),
              onPressed: () => _showCodeExecutionDetails(context, execution),
            );
          }).toList(),
        ),
      ],
    );
  }

  Future<void> _showCodeExecutionDetails(
    BuildContext context,
    ChatCodeExecution execution,
  ) async {
    final theme = context.jyotigptTheme;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: theme.surfaceBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(AppBorderRadius.dialog),
        ),
      ),
      builder: (ctx) {
        final result = execution.result;
        return DraggableScrollableSheet(
          initialChildSize: 0.6,
          maxChildSize: 0.95,
          expand: false,
          builder: (_, controller) {
            return Padding(
              padding: const EdgeInsets.all(Spacing.lg),
              child: ListView(
                controller: controller,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          execution.name ?? 'Code execution',
                          style: TextStyle(
                            fontSize: AppTypography.bodyLarge,
                            fontWeight: FontWeight.w600,
                            color: theme.textPrimary,
                          ),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () => Navigator.of(ctx).pop(),
                      ),
                    ],
                  ),
                  const SizedBox(height: Spacing.sm),
                  if (execution.language != null)
                    Text(
                      'Language: ${execution.language}',
                      style: TextStyle(color: theme.textSecondary),
                    ),
                  const SizedBox(height: Spacing.sm),
                  if (execution.code != null && execution.code!.isNotEmpty) ...[
                    Text(
                      'Code',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: theme.textPrimary,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    Container(
                      padding: const EdgeInsets.all(Spacing.sm),
                      decoration: BoxDecoration(
                        color: theme.surfaceContainer,
                        borderRadius: BorderRadius.circular(AppBorderRadius.md),
                      ),
                      child: SelectableText(
                        execution.code!,
                        style: const TextStyle(
                          fontFamily: 'monospace',
                          height: 1.4,
                        ),
                      ),
                    ),
                    const SizedBox(height: Spacing.md),
                  ],
                  if (result?.error != null) ...[
                    Text(
                      'Error',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: theme.error,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    SelectableText(result!.error!),
                    const SizedBox(height: Spacing.md),
                  ],
                  if (result?.output != null) ...[
                    Text(
                      'Output',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: theme.textPrimary,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    SelectableText(result!.output!),
                    const SizedBox(height: Spacing.md),
                  ],
                  if (result?.files.isNotEmpty == true) ...[
                    Text(
                      'Files',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: theme.textPrimary,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    ...result!.files.map((file) {
                      final name = file.name ?? file.url ?? 'Download';
                      return ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.insert_drive_file_outlined),
                        title: Text(name),
                        onTap: file.url != null
                            ? () => _launchUri(file.url!)
                            : null,
                        trailing: file.url != null
                            ? const Icon(Icons.open_in_new)
                            : null,
                      );
                    }),
                  ],
                ],
              ),
            );
          },
        );
      },
    );
  }
}

// Legacy CitationListView - replaced with OpenWebUISourcesWidget
// Keeping for reference, can be removed after testing
/*
class CitationListView extends StatelessWidget {
  const CitationListView({super.key, required this.sources});

  final List<ChatSourceReference> sources;

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;
    if (sources.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          sources.length == 1 ? 'Source' : 'Sources',
          style: TextStyle(
            color: theme.textPrimary,
            fontWeight: FontWeight.w600,
            fontSize: AppTypography.bodyLarge,
          ),
        ),
        const SizedBox(height: Spacing.xs),
        ...sources.map((source) {
          final title = source.title?.isNotEmpty == true
              ? source.title!
              : source.url ?? 'Citation';
          final subtitle = source.snippet?.isNotEmpty == true
              ? source.snippet!
              : source.url;

          return Card(
            margin: const EdgeInsets.only(bottom: Spacing.xs),
            color: theme.surfaceContainer,
            child: ListTile(
              onTap: source.url != null ? () => _launchUri(source.url!) : null,
              title: Text(title, style: TextStyle(color: theme.textPrimary)),
              subtitle: subtitle != null
                  ? Text(subtitle, style: TextStyle(color: theme.textSecondary))
                  : null,
              trailing: source.url != null
                  ? const Icon(Icons.open_in_new, size: 18)
                  : null,
            ),
          );
        }),
      ],
    );
  }
}
*/

class FollowUpSuggestionBar extends StatelessWidget {
  const FollowUpSuggestionBar({
    super.key,
    required this.suggestions,
    required this.onSelected,
    required this.isBusy,
  });

  final List<String> suggestions;
  final ValueChanged<String> onSelected;
  final bool isBusy;

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;
    final trimmedSuggestions = suggestions
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList(growable: false);

    if (trimmedSuggestions.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Subtle header
        Row(
          children: [
            Icon(
              Icons.lightbulb_outline,
              size: 12,
              color: theme.textSecondary.withValues(alpha: 0.7),
            ),
            const SizedBox(width: Spacing.xxs),
            Text(
              'Continue with',
              style: TextStyle(
                fontSize: AppTypography.labelSmall,
                color: theme.textSecondary.withValues(alpha: 0.7),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        const SizedBox(height: Spacing.xs),
        Wrap(
          spacing: Spacing.xs,
          runSpacing: Spacing.xs,
          children: [
            for (final suggestion in trimmedSuggestions)
              _MinimalFollowUpButton(
                label: suggestion,
                onPressed: isBusy ? null : () => onSelected(suggestion),
                enabled: !isBusy,
              ),
          ],
        ),
      ],
    );
  }
}

class _MinimalFollowUpButton extends StatelessWidget {
  const _MinimalFollowUpButton({
    required this.label,
    this.onPressed,
    this.enabled = true,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;

    return InkWell(
      onTap: enabled ? onPressed : null,
      borderRadius: BorderRadius.circular(AppBorderRadius.small),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.sm,
          vertical: Spacing.xs,
        ),
        decoration: BoxDecoration(
          color: enabled
              ? theme.surfaceContainer.withValues(alpha: 0.2)
              : theme.surfaceContainer.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(AppBorderRadius.small),
          border: Border.all(
            color: enabled
                ? theme.buttonPrimary.withValues(alpha: 0.15)
                : theme.dividerColor.withValues(alpha: 0.2),
            width: BorderWidth.thin,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.arrow_forward,
              size: 11,
              color: enabled
                  ? theme.buttonPrimary.withValues(alpha: 0.7)
                  : theme.textSecondary.withValues(alpha: 0.4),
            ),
            const SizedBox(width: Spacing.xxs),
            Flexible(
              child: Text(
                label,
                style: TextStyle(
                  color: enabled
                      ? theme.buttonPrimary.withValues(alpha: 0.9)
                      : theme.textSecondary.withValues(alpha: 0.5),
                  fontSize: AppTypography.bodySmall,
                  fontWeight: FontWeight.w500,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> _launchUri(String url) async {
  if (url.isEmpty) return;
  try {
    await launchUrlString(url, mode: LaunchMode.externalApplication);
  } catch (err) {
    DebugLogger.log('Unable to open url $url: $err', scope: 'chat/assistant');
  }
}
