import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import '../../../shared/theme/theme_extensions.dart';
import '../../../shared/widgets/sheet_handle.dart';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'dart:io' show Platform;
import 'dart:async';
import 'dart:ui';
import 'dart:math' as math;
import '../providers/chat_providers.dart';
import '../../tools/providers/tools_providers.dart';
import '../../prompts/providers/prompts_providers.dart';
import '../../../core/models/tool.dart';
import '../../../core/models/prompt.dart';
import '../../../core/providers/app_providers.dart';
import '../../../core/services/settings_service.dart';
import '../../chat/services/voice_input_service.dart';

import '../../../shared/utils/platform_utils.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';
import '../../../shared/widgets/modal_safe_area.dart';

class _SendMessageIntent extends Intent {
  const _SendMessageIntent();
}

class _InsertNewlineIntent extends Intent {
  const _InsertNewlineIntent();
}

class _SelectNextPromptIntent extends Intent {
  const _SelectNextPromptIntent();
}

class _SelectPreviousPromptIntent extends Intent {
  const _SelectPreviousPromptIntent();
}

class _DismissPromptIntent extends Intent {
  const _DismissPromptIntent();
}

class _PromptCommandMatch {
  const _PromptCommandMatch({
    required this.command,
    required this.start,
    required this.end,
  });

  final String command;
  final int start;
  final int end;
}

class ModernChatInput extends ConsumerStatefulWidget {
  final Function(String) onSendMessage;
  final bool enabled;
  final Function()? onVoiceInput;
  final Function()? onVoiceCall;

  const ModernChatInput({
    super.key,
    required this.onSendMessage,
    this.enabled = true,
    this.onVoiceInput,
    this.onVoiceCall,
  });

  @override
  ConsumerState<ModernChatInput> createState() => _ModernChatInputState();
}

class _ModernChatInputState extends ConsumerState<ModernChatInput>
    with TickerProviderStateMixin {
  static const double _composerRadius = AppBorderRadius.card;

  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _pendingFocus = false;
  bool _isRecording = false;
  bool _hasText = false;
  StreamSubscription<String>? _voiceStreamSubscription;
  late VoiceInputService _voiceService;
  StreamSubscription<int>? _intensitySub;
  StreamSubscription<String>? _textSub;
  String _baseTextAtStart = '';
  bool _isDeactivated = false;
  int _lastHandledFocusTick = 0;
  bool _showPromptOverlay = false;
  String _currentPromptCommand = '';
  TextRange? _currentPromptRange;
  int _promptSelectionIndex = 0;

  @override
  void initState() {
    super.initState();
    _voiceService = ref.read(voiceInputServiceProvider);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || _isDeactivated) return;
      final text = ref.read(prefilledInputTextProvider);
      if (text != null && text.isNotEmpty) {
        _controller.text = text;
        _controller.selection = TextSelection.collapsed(offset: text.length);
        ref.read(prefilledInputTextProvider.notifier).clear();
      }
    });

    _controller.addListener(_handleComposerChanged);

    _focusNode.addListener(() {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || _isDeactivated) return;
        final hasFocus = _focusNode.hasFocus;
        try {
          ref.read(composerHasFocusProvider.notifier).set(hasFocus);
        } catch (_) {}
      });
    });
  }

  @override
  void dispose() {
    _controller.removeListener(_handleComposerChanged);
    _controller.dispose();
    _focusNode.dispose();
    _pendingFocus = false;
    _voiceStreamSubscription?.cancel();
    _intensitySub?.cancel();
    _textSub?.cancel();
    _voiceService.stopListening();
    super.dispose();
  }

  void _ensureFocusedIfEnabled() {
    final autofocusEnabled = ref.read(composerAutofocusEnabledProvider);
    if (!widget.enabled ||
        _focusNode.hasFocus ||
        _pendingFocus ||
        !autofocusEnabled) {
      return;
    }

    _pendingFocus = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _pendingFocus = false;
      if (widget.enabled && !_focusNode.hasFocus) {
        _focusNode.requestFocus();
      }
    });
  }

  @override
  void deactivate() {
    _isDeactivated = true;
    super.deactivate();
  }

  @override
  void activate() {
    super.activate();
    _isDeactivated = false;
  }

  @override
  void didUpdateWidget(covariant ModernChatInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.enabled && oldWidget.enabled) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || _isDeactivated) return;
        if (_focusNode.hasFocus) {
          _focusNode.unfocus();
        }
      });
    }
  }

  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isEmpty || !widget.enabled) return;

    PlatformUtils.lightHaptic();
    widget.onSendMessage(text);
    _controller.clear();
  }

  void _insertNewline() {
    final text = _controller.text;
    TextSelection sel = _controller.selection;
    final int start = sel.isValid ? sel.start : text.length;
    final int end = sel.isValid ? sel.end : text.length;
    final String before = text.substring(0, start);
    final String after = text.substring(end);
    final String updated = '$before\n$after';
    _controller.value = TextEditingValue(
      text: updated,
      selection: TextSelection.collapsed(offset: before.length + 1),
      composing: TextRange.empty,
    );
    _ensureFocusedIfEnabled();
  }

  static final RegExp _promptCommandBoundary = RegExp(r'\s');

  void _handleComposerChanged() {
    if (!mounted || _isDeactivated) return;

    final String text = _controller.text;
    final TextSelection selection = _controller.selection;
    final bool hasText = text.trim().isNotEmpty;
    final _PromptCommandMatch? match = _resolvePromptCommand(
      text,
      selection,
      widget.enabled,
    );
    final bool shouldShow = match != null;
    final bool wasShowing = _showPromptOverlay;
    final String previousCommand = _currentPromptCommand;

    bool needsUpdate = hasText != _hasText || shouldShow != _showPromptOverlay;

    if (!needsUpdate) {
      if (match != null) {
        final TextRange? range = _currentPromptRange;
        needsUpdate =
            previousCommand != match.command ||
            range == null ||
            range.start != match.start ||
            range.end != match.end;
      } else {
        needsUpdate =
            _currentPromptCommand.isNotEmpty || _currentPromptRange != null;
      }
    }

    if (!needsUpdate) return;

    setState(() {
      _hasText = hasText;
      if (match != null) {
        if (previousCommand != match.command) {
          _promptSelectionIndex = 0;
        }
        _currentPromptCommand = match.command;
        _currentPromptRange = TextRange(start: match.start, end: match.end);
        _showPromptOverlay = true;
      } else {
        _currentPromptCommand = '';
        _currentPromptRange = null;
        _promptSelectionIndex = 0;
        _showPromptOverlay = false;
      }
    });

    if (!wasShowing && shouldShow) {
      ref.read(promptsListProvider.future);
    }
  }

  _PromptCommandMatch? _resolvePromptCommand(
    String text,
    TextSelection selection,
    bool enabled,
  ) {
    if (!enabled) return null;
    if (!selection.isValid || !selection.isCollapsed) return null;

    final int cursor = selection.start;
    if (cursor < 0 || cursor > text.length) return null;
    if (cursor == 0) return null;

    int start = cursor;
    while (start > 0) {
      final String previous = text.substring(start - 1, start);
      if (_promptCommandBoundary.hasMatch(previous)) {
        break;
      }
      start--;
    }

    final String candidate = text.substring(start, cursor);
    if (candidate.isEmpty || !candidate.startsWith('/')) {
      return null;
    }

    return _PromptCommandMatch(command: candidate, start: start, end: cursor);
  }

  List<Prompt> _filterPrompts(List<Prompt> prompts) {
    if (prompts.isEmpty) return const <Prompt>[];
    final String query = _currentPromptCommand.toLowerCase();

    final List<Prompt> filtered =
        prompts
            .where(
              (prompt) =>
                  prompt.command.toLowerCase().contains(query.trim()) &&
                  prompt.content.isNotEmpty,
            )
            .toList()
          ..sort((a, b) {
            final int titleCompare = a.title.toLowerCase().compareTo(
              b.title.toLowerCase(),
            );
            if (titleCompare != 0) return titleCompare;
            return a.command.toLowerCase().compareTo(b.command.toLowerCase());
          });

    return filtered;
  }

  void _movePromptSelection(int delta) {
    final AsyncValue<List<Prompt>> promptsAsync = ref.read(promptsListProvider);
    final List<Prompt>? prompts = promptsAsync.value;
    if (prompts == null || prompts.isEmpty) return;

    final List<Prompt> filtered = _filterPrompts(prompts);
    if (filtered.isEmpty) return;

    int newIndex = _promptSelectionIndex + delta;
    if (newIndex < 0) {
      newIndex = 0;
    } else if (newIndex >= filtered.length) {
      newIndex = filtered.length - 1;
    }
    if (newIndex == _promptSelectionIndex) return;

    setState(() {
      _promptSelectionIndex = newIndex;
    });
  }

  void _confirmPromptSelection() {
    final AsyncValue<List<Prompt>> promptsAsync = ref.read(promptsListProvider);
    final List<Prompt>? prompts = promptsAsync.value;
    if (prompts == null || prompts.isEmpty) return;

    final List<Prompt> filtered = _filterPrompts(prompts);
    if (filtered.isEmpty) return;

    int index = _promptSelectionIndex;
    if (index < 0) {
      index = 0;
    } else if (index >= filtered.length) {
      index = filtered.length - 1;
    }
    _applyPrompt(filtered[index]);
  }

  void _applyPrompt(Prompt prompt) {
    final TextRange? range = _currentPromptRange;
    if (range == null) return;

    final String text = _controller.text;
    final String before = text.substring(0, range.start);
    final String after = text.substring(range.end);
    final String content = prompt.content;
    final int caret = before.length + content.length;

    _controller.value = TextEditingValue(
      text: '$before$content$after',
      selection: TextSelection.collapsed(offset: caret),
      composing: TextRange.empty,
    );

    _ensureFocusedIfEnabled();

    setState(() {
      _showPromptOverlay = false;
      _currentPromptCommand = '';
      _currentPromptRange = null;
      _promptSelectionIndex = 0;
    });
  }

  void _hidePromptOverlay() {
    if (!_showPromptOverlay) return;
    setState(() {
      _showPromptOverlay = false;
      _currentPromptCommand = '';
      _currentPromptRange = null;
      _promptSelectionIndex = 0;
    });
  }

  Widget _buildPromptOverlay(BuildContext context) {
    final Brightness brightness = Theme.of(context).brightness;
    final overlayColor = context.jyotigptTheme.cardBackground;
    final borderColor = context.jyotigptTheme.cardBorder.withValues(
      alpha: brightness == Brightness.dark ? 0.6 : 0.4,
    );

    final AsyncValue<List<Prompt>> promptsAsync = ref.watch(
      promptsListProvider,
    );

    return Container(
      decoration: BoxDecoration(
        color: overlayColor,
        borderRadius: BorderRadius.circular(AppBorderRadius.card),
        border: Border.all(color: borderColor, width: BorderWidth.thin),
        boxShadow: [
          BoxShadow(
            color: context.jyotigptTheme.cardShadow.withValues(
              alpha: brightness == Brightness.dark ? 0.28 : 0.16,
            ),
            blurRadius: 22,
            offset: const Offset(0, 8),
            spreadRadius: -4,
          ),
        ],
      ),
      child: promptsAsync.when(
        data: (prompts) {
          final List<Prompt> filtered = _filterPrompts(prompts);
          if (filtered.isEmpty) {
            return _buildPromptOverlayPlaceholder(
              context,
              Icon(
                Icons.inbox_outlined,
                size: IconSize.medium,
                color: context.jyotigptTheme.textSecondary.withValues(
                  alpha: Alpha.medium,
                ),
              ),
              AppLocalizations.of(context)!.noResults,
            );
          }

          int activeIndex = _promptSelectionIndex;
          if (activeIndex < 0) {
            activeIndex = 0;
          } else if (activeIndex >= filtered.length) {
            activeIndex = filtered.length - 1;
          }

          return ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 240),
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: Spacing.xs),
              shrinkWrap: true,
              physics: const ClampingScrollPhysics(),
              itemCount: filtered.length,
              separatorBuilder: (context, index) =>
                  const SizedBox(height: Spacing.xxs),
              itemBuilder: (context, index) {
                final prompt = filtered[index];
                final bool isSelected = index == activeIndex;
                final Color highlight = isSelected
                    ? context.jyotigptTheme.navigationSelectedBackground
                          .withValues(alpha: 0.4)
                    : Colors.transparent;

                return Material(
                  color: Colors.transparent,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(AppBorderRadius.card),
                    onTap: () => _applyPrompt(prompt),
                    child: Container(
                      decoration: BoxDecoration(
                        color: highlight,
                        borderRadius: BorderRadius.circular(
                          AppBorderRadius.card,
                        ),
                      ),
                      padding: const EdgeInsets.symmetric(
                        horizontal: Spacing.sm,
                        vertical: Spacing.xs,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            prompt.command,
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(
                                  fontWeight: FontWeight.w600,
                                  color: context.jyotigptTheme.textPrimary,
                                ),
                          ),
                          if (prompt.title.trim().isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: Spacing.xxs),
                              child: Text(
                                prompt.title,
                                style: Theme.of(context).textTheme.bodySmall
                                    ?.copyWith(
                                      color: context.jyotigptTheme.textSecondary,
                                    ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          );
        },
        loading: () => _buildPromptOverlayPlaceholder(
          context,
          SizedBox(
            width: IconSize.large,
            height: IconSize.large,
            child: CircularProgressIndicator(
              strokeWidth: BorderWidth.regular,
              valueColor: AlwaysStoppedAnimation<Color>(
                context.jyotigptTheme.loadingIndicator,
              ),
            ),
          ),
          null,
        ),
        error: (error, stackTrace) => _buildPromptOverlayPlaceholder(
          context,
          Icon(
            Icons.error_outline,
            size: IconSize.medium,
            color: context.jyotigptTheme.error,
          ),
          null,
        ),
      ),
    );
  }

  Widget _buildPromptOverlayPlaceholder(
    BuildContext context,
    Widget leading,
    String? message,
  ) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.sm,
        vertical: Spacing.md,
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          leading,
          if (message != null) ...[
            const SizedBox(width: Spacing.sm),
            Flexible(
              child: Text(
                message,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: context.jyotigptTheme.textSecondary,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<String?>(prefilledInputTextProvider, (previous, next) {
      final incoming = next?.trim();
      if (incoming == null || incoming.isEmpty) return;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || _isDeactivated) return;
        _controller.text = incoming;
        _controller.selection = TextSelection.collapsed(
          offset: incoming.length,
        );
        try {
          ref.read(prefilledInputTextProvider.notifier).clear();
        } catch (_) {}
      });
    });

    final messages = ref.watch(chatMessagesProvider);
    final isGenerating =
        messages.isNotEmpty &&
        messages.last.role == 'assistant' &&
        messages.last.isStreaming;
    final stopGeneration = ref.read(stopGenerationProvider);

    final selectedQuickPills = ref.watch(
      appSettingsProvider.select((s) => s.quickPills),
    );
    final sendOnEnter = ref.watch(
      appSettingsProvider.select((s) => s.sendOnEnter),
    );
    final toolsAsync = ref.watch(toolsListProvider);
    final List<Tool> availableTools = toolsAsync.maybeWhen<List<Tool>>(
      data: (t) => t,
      orElse: () => const <Tool>[],
    );
    final voiceAvailableAsync = ref.watch(voiceInputAvailableProvider);
    final bool voiceAvailable = voiceAvailableAsync.maybeWhen(
      data: (v) => v,
      orElse: () => false,
    );
    final selectedToolIds = ref.watch(selectedToolIdsProvider);

    final focusTick = ref.watch(inputFocusTriggerProvider);
    final autofocusEnabled = ref.watch(composerAutofocusEnabledProvider);
    if (autofocusEnabled && focusTick != _lastHandledFocusTick) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || _isDeactivated) return;
        _ensureFocusedIfEnabled();
        _lastHandledFocusTick = focusTick;
      });
    }

    final Brightness brightness = Theme.of(context).brightness;
    final bool isActive = _focusNode.hasFocus || _hasText;
    final Color composerSurface = context.jyotigptTheme.inputBackground;
    final Color composerBackground = brightness == Brightness.dark
        ? composerSurface.withValues(alpha: 0.78)
        : context.jyotigptTheme.surfaceContainerHighest;
    final Color placeholderBase = context.jyotigptTheme.inputPlaceholder;
    final Color placeholderFocused = context.jyotigptTheme.inputText.withValues(
      alpha: 0.64,
    );
    final Color outlineColor = Color.lerp(
      context.jyotigptTheme.inputBorder,
      context.jyotigptTheme.inputBorderFocused,
      isActive ? 1.0 : 0.0,
    )!.withValues(alpha: brightness == Brightness.dark ? 0.55 : 0.45);
    final Color shellShadowColor = context.jyotigptTheme.cardShadow.withValues(
      alpha: brightness == Brightness.dark
          ? 0.22 + (isActive ? 0.08 : 0.0)
          : 0.12 + (isActive ? 0.06 : 0.0),
    );

    final List<Widget> quickPills = <Widget>[];

    for (final id in selectedQuickPills) {
      Tool? tool;
      for (final t in availableTools) {
        if (t.id == id) {
          tool = t;
          break;
        }
      }
      if (tool != null) {
        final bool isSelected = selectedToolIds.contains(id);
        final String label = tool.name;
        final IconData icon = Platform.isIOS
            ? CupertinoIcons.wrench
            : Icons.build;

        void handleTap() {
          final current = List<String>.from(selectedToolIds);
          if (current.contains(id)) {
            current.remove(id);
          } else {
            current.add(id);
          }
          ref.read(selectedToolIdsProvider.notifier).set(current);
        }

        quickPills.add(
          _buildPillButton(
            icon: icon,
            label: label,
            isActive: isSelected,
            onTap: widget.enabled && !_isRecording ? handleTap : null,
          ),
        );
      }
    }

    final bool showCompactComposer = quickPills.isEmpty;

    final BorderRadius shellRadius = BorderRadius.circular(
      showCompactComposer ? AppBorderRadius.round : _composerRadius,
    );

    final BoxDecoration shellDecoration = BoxDecoration(
      color: showCompactComposer ? Colors.transparent : composerBackground,
      borderRadius: shellRadius,
      border: showCompactComposer
          ? null
          : Border.all(color: outlineColor, width: BorderWidth.thin),
      boxShadow: showCompactComposer
          ? const <BoxShadow>[]
          : <BoxShadow>[
              BoxShadow(
                color: shellShadowColor,
                blurRadius: 12 + (isActive ? 4 : 0),
                spreadRadius: -2,
                offset: const Offset(0, -2),
              ),
            ],
    );

    final List<Widget> composerChildren = <Widget>[
      if (_showPromptOverlay)
        Padding(
          padding: const EdgeInsets.fromLTRB(
            Spacing.sm,
            0,
            Spacing.sm,
            Spacing.xs,
          ),
          child: _buildPromptOverlay(context),
        ),
      if (showCompactComposer)
        Padding(
          padding: const EdgeInsets.fromLTRB(
            Spacing.screenPadding,
            Spacing.xs,
            Spacing.screenPadding,
            Spacing.sm,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              _buildOverflowButton(
                tooltip: AppLocalizations.of(context)!.more,
                toolsActive: selectedToolIds.isNotEmpty,
              ),
              const SizedBox(width: Spacing.sm),
              Expanded(
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  curve: Curves.easeOutCubic,
                  padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
                  constraints: const BoxConstraints(
                    minHeight: TouchTarget.input,
                  ),
                  decoration: BoxDecoration(
                    color: brightness == Brightness.dark
                        ? composerSurface.withValues(alpha: 0.9)
                        : context.jyotigptTheme.surfaceContainer,
                    borderRadius: BorderRadius.circular(AppBorderRadius.round),
                    border: Border.all(
                      color: outlineColor.withValues(
                        alpha: brightness == Brightness.dark ? 0.32 : 0.2,
                      ),
                      width: BorderWidth.micro,
                    ),
                    boxShadow: <BoxShadow>[
                      BoxShadow(
                        color: shellShadowColor.withValues(
                          alpha: brightness == Brightness.dark ? 0.4 : 0.22,
                        ),
                        blurRadius: 24,
                        spreadRadius: -6,
                        offset: const Offset(0, 12),
                      ),
                    ],
                  ),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: _buildComposerTextField(
                      brightness: brightness,
                      sendOnEnter: sendOnEnter,
                      placeholderBase: placeholderBase,
                      placeholderFocused: placeholderFocused,
                      contentPadding: const EdgeInsets.symmetric(
                        vertical: Spacing.xs,
                      ),
                      isActive: isActive,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: Spacing.sm),
              if (!_hasText && voiceAvailable && !isGenerating)
                _buildMicButton(voiceAvailable),
              if (!_hasText && voiceAvailable && !isGenerating)
                const SizedBox(width: Spacing.sm),
              _buildPrimaryButton(
                _hasText,
                isGenerating,
                stopGeneration,
                voiceAvailable,
              ),
            ],
          ),
        )
      else ...[
        Padding(
          padding: const EdgeInsets.fromLTRB(
            Spacing.sm,
            Spacing.xs,
            Spacing.sm,
            Spacing.xs,
          ),
          child: Container(
            padding: const EdgeInsets.fromLTRB(
              Spacing.sm,
              Spacing.xs,
              Spacing.sm,
              Spacing.xs,
            ),
            decoration: BoxDecoration(
              color: Colors.transparent,
              borderRadius: BorderRadius.circular(_composerRadius),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(
                  child: _buildComposerTextField(
                    brightness: brightness,
                    sendOnEnter: sendOnEnter,
                    placeholderBase: placeholderBase,
                    placeholderFocused: placeholderFocused,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: Spacing.sm,
                      vertical: Spacing.xs,
                    ),
                    isActive: isActive,
                  ),
                ),
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            Spacing.inputPadding,
            0,
            Spacing.inputPadding,
            0,
          ),
          child: Row(
            children: [
              _buildOverflowButton(
                tooltip: AppLocalizations.of(context)!.more,
                toolsActive: selectedToolIds.isNotEmpty,
              ),
              const SizedBox(width: Spacing.xs),
              Expanded(
                child: ClipRect(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    physics: const BouncingScrollPhysics(),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: _withHorizontalSpacing(quickPills, Spacing.xxs),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: Spacing.sm),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (!_hasText && voiceAvailable && !isGenerating) ...[
                    _buildMicButton(voiceAvailable),
                    const SizedBox(width: Spacing.sm),
                  ],
                  _buildPrimaryButton(
                    _hasText,
                    isGenerating,
                    stopGeneration,
                    voiceAvailable,
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    ];

    Widget shell = AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
      decoration: shellDecoration,
      width: double.infinity,
      child: SafeArea(
        top: false,
        bottom: true,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(context).size.height * 0.4,
          ),
          child: AnimatedSize(
            duration: const Duration(milliseconds: 160),
            curve: Curves.easeOutCubic,
            alignment: Alignment.topCenter,
            child: SingleChildScrollView(
              physics: const ClampingScrollPhysics(),
              child: RepaintBoundary(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: composerChildren,
                ),
              ),
            ),
          ),
        ),
      ),
    );

    if (brightness == Brightness.dark && !showCompactComposer) {
      shell = ClipRRect(
        borderRadius: shellRadius,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: shell,
        ),
      );
    }

    return Container(
      color: Colors.transparent,
      padding: EdgeInsets.zero,
      child: Column(mainAxisSize: MainAxisSize.min, children: [shell]),
    );
  }

  List<Widget> _withHorizontalSpacing(List<Widget> children, double gap) {
    if (children.length <= 1) {
      return List<Widget>.from(children);
    }
    final result = <Widget>[];
    for (var i = 0; i < children.length; i++) {
      result.add(children[i]);
      if (i != children.length - 1) {
        result.add(SizedBox(width: gap));
      }
    }
    return result;
  }

  Widget _buildComposerTextField({
    required Brightness brightness,
    required bool sendOnEnter,
    required Color placeholderBase,
    required Color placeholderFocused,
    required EdgeInsetsGeometry contentPadding,
    required bool isActive,
  }) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () {
        if (!widget.enabled) return;
        try {
          ref.read(composerAutofocusEnabledProvider.notifier).set(true);
        } catch (_) {}
        _ensureFocusedIfEnabled();
      },
      child: Semantics(
        textField: true,
        label: AppLocalizations.of(context)!.messageInputLabel,
        hint: AppLocalizations.of(context)!.messageInputHint,
        child: Shortcuts(
          shortcuts: () {
            final map = <LogicalKeySet, Intent>{
              LogicalKeySet(LogicalKeyboardKey.meta, LogicalKeyboardKey.enter):
                  const _SendMessageIntent(),
              LogicalKeySet(
                LogicalKeyboardKey.control,
                LogicalKeyboardKey.enter,
              ): const _SendMessageIntent(),
            };
            if (sendOnEnter) {
              map[LogicalKeySet(LogicalKeyboardKey.enter)] =
                  const _SendMessageIntent();
              map[LogicalKeySet(
                    LogicalKeyboardKey.shift,
                    LogicalKeyboardKey.enter,
                  )] =
                  const _InsertNewlineIntent();
            }
            if (_showPromptOverlay) {
              map[LogicalKeySet(LogicalKeyboardKey.arrowDown)] =
                  const _SelectNextPromptIntent();
              map[LogicalKeySet(LogicalKeyboardKey.arrowUp)] =
                  const _SelectPreviousPromptIntent();
              map[LogicalKeySet(LogicalKeyboardKey.escape)] =
                  const _DismissPromptIntent();
            }
            return map;
          }(),
          child: Actions(
            actions: <Type, Action<Intent>>{
              _SendMessageIntent: CallbackAction<_SendMessageIntent>(
                onInvoke: (intent) {
                  if (_showPromptOverlay) {
                    _confirmPromptSelection();
                    return null;
                  }
                  _sendMessage();
                  return null;
                },
              ),
              _InsertNewlineIntent: CallbackAction<_InsertNewlineIntent>(
                onInvoke: (intent) {
                  _insertNewline();
                  return null;
                },
              ),
              _SelectNextPromptIntent: CallbackAction<_SelectNextPromptIntent>(
                onInvoke: (intent) {
                  _movePromptSelection(1);
                  return null;
                },
              ),
              _SelectPreviousPromptIntent:
                  CallbackAction<_SelectPreviousPromptIntent>(
                    onInvoke: (intent) {
                      _movePromptSelection(-1);
                      return null;
                    },
                  ),
              _DismissPromptIntent: CallbackAction<_DismissPromptIntent>(
                onInvoke: (intent) {
                  _hidePromptOverlay();
                  return null;
                },
              ),
            },
            child: Builder(
              builder: (context) {
                final double factor = isActive ? 1.0 : 0.0;
                final Color animatedPlaceholder = Color.lerp(
                  placeholderBase,
                  placeholderFocused,
                  factor,
                )!;
                final Color animatedTextColor = Color.lerp(
                  context.jyotigptTheme.inputText.withValues(alpha: 0.88),
                  context.jyotigptTheme.inputText,
                  factor,
                )!;

                final FontWeight recordingWeight = _isRecording
                    ? FontWeight.w500
                    : FontWeight.w400;
                final TextStyle baseChatStyle = AppTypography.chatMessageStyle;

                return TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  enabled: widget.enabled,
                  autofocus: false,
                  minLines: 1,
                  maxLines: null,
                  keyboardType: TextInputType.multiline,
                  textCapitalization: TextCapitalization.sentences,
                  textInputAction: sendOnEnter
                      ? TextInputAction.send
                      : TextInputAction.newline,
                  autofillHints: const <String>[],
                  showCursor: true,
                  scrollPadding: const EdgeInsets.only(bottom: 80),
                  keyboardAppearance: brightness,
                  cursorColor: animatedTextColor,
                  style: baseChatStyle.copyWith(
                    color: animatedTextColor,
                    fontStyle: _isRecording
                        ? FontStyle.italic
                        : FontStyle.normal,
                    fontWeight: recordingWeight,
                  ),
                  decoration: InputDecoration(
                    hintText: AppLocalizations.of(context)!.messageHintText,
                    hintStyle: baseChatStyle.copyWith(
                      color: animatedPlaceholder,
                      fontWeight: recordingWeight,
                      fontStyle: _isRecording
                          ? FontStyle.italic
                          : FontStyle.normal,
                    ),
                    filled: false,
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    errorBorder: InputBorder.none,
                    disabledBorder: InputBorder.none,
                    contentPadding: contentPadding,
                    isDense: true,
                    alignLabelWithHint: true,
                  ),
                  onSubmitted: (_) {
                    if (sendOnEnter) {
                      _sendMessage();
                    }
                  },
                  onTap: () {
                    if (!widget.enabled) return;
                    _ensureFocusedIfEnabled();
                  },
                );
              },
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildOverflowButton({
    required String tooltip,
    required bool toolsActive,
  }) {
    final bool enabled = widget.enabled && !_isRecording;

    IconData icon;
    Color? activeColor;
    if (toolsActive) {
      icon = Platform.isIOS ? CupertinoIcons.wrench : Icons.build;
      activeColor = context.jyotigptTheme.buttonPrimary;
    } else {
      icon = Platform.isIOS ? CupertinoIcons.add : Icons.add;
      activeColor = null;
    }

    const double iconSize = IconSize.large;
    const double buttonSize = TouchTarget.minimum;
    final Brightness brightness = Theme.of(context).brightness;
    final bool isActive = activeColor != null;

    final Color iconColor = !enabled
        ? context.jyotigptTheme.textPrimary.withValues(alpha: Alpha.disabled)
        : (activeColor ??
              context.jyotigptTheme.textPrimary.withValues(alpha: Alpha.strong));

    final Color baseBackground = brightness == Brightness.dark
        ? context.jyotigptTheme.surfaceContainerHighest.withValues(alpha: 0.7)
        : context.jyotigptTheme.surfaceContainerHighest;
    final Color backgroundColor = !enabled
        ? baseBackground.withValues(alpha: Alpha.disabled)
        : isActive
        ? context.jyotigptTheme.buttonPrimary.withValues(alpha: 0.16)
        : baseBackground;
    final Color borderColor = isActive
        ? context.jyotigptTheme.buttonPrimary.withValues(alpha: 0.6)
        : context.jyotigptTheme.cardBorder.withValues(alpha: 0.45);
    final BoxShadow buttonShadow = BoxShadow(
      color: context.jyotigptTheme.cardShadow.withValues(
        alpha: brightness == Brightness.dark ? 0.36 : 0.18,
      ),
      blurRadius: 18,
      spreadRadius: -6,
      offset: const Offset(0, 8),
    );

    return Tooltip(
      message: tooltip,
      child: Opacity(
        opacity: enabled ? 1.0 : Alpha.disabled,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(AppBorderRadius.round),
            onTap: enabled
                ? () {
                    HapticFeedback.selectionClick();
                    _showOverflowSheet();
                  }
                : null,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              curve: Curves.easeOutCubic,
              width: buttonSize,
              height: buttonSize,
              decoration: BoxDecoration(
                color: backgroundColor,
                borderRadius: BorderRadius.circular(AppBorderRadius.round),
                border: Border.all(color: borderColor, width: BorderWidth.thin),
                boxShadow: enabled ? <BoxShadow>[buttonShadow] : const [],
              ),
              child: Center(
                child: Icon(icon, size: iconSize, color: iconColor),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMicButton(bool voiceAvailable) {
    final bool enabledMic = widget.enabled && voiceAvailable;
    return Tooltip(
      message: AppLocalizations.of(context)!.voiceInput,
      child: Opacity(
        opacity: enabledMic ? Alpha.primary : Alpha.disabled,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(AppBorderRadius.circular),
            onTap: enabledMic
                ? () {
                    HapticFeedback.selectionClick();
                    _toggleVoice();
                  }
                : null,
            child: SizedBox(
              width: TouchTarget.minimum,
              height: TouchTarget.minimum,
              child: Icon(
                Platform.isIOS ? CupertinoIcons.mic : Icons.mic,
                size: IconSize.large,
                color: _isRecording
                    ? context.jyotigptTheme.buttonPrimary
                    : (enabledMic
                          ? context.jyotigptTheme.textPrimary.withValues(
                              alpha: Alpha.strong,
                            )
                          : context.jyotigptTheme.textPrimary.withValues(
                              alpha: Alpha.disabled,
                            )),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPrimaryButton(
    bool hasText,
    bool isGenerating,
    void Function() stopGeneration,
    bool voiceAvailable,
  ) {
    const double buttonSize = TouchTarget.minimum;
    const double radius = AppBorderRadius.round;

    final enabled = !isGenerating && hasText && widget.enabled;

    if (isGenerating) {
      return Tooltip(
        message: AppLocalizations.of(context)!.stopGenerating,
        child: Material(
          color: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radius),
            side: BorderSide(
              color: context.jyotigptTheme.error,
              width: BorderWidth.regular,
            ),
          ),
          child: InkWell(
            borderRadius: BorderRadius.circular(radius),
            onTap: () {
              HapticFeedback.lightImpact();
              stopGeneration();
            },
            child: Container(
              width: buttonSize,
              height: buttonSize,
              decoration: BoxDecoration(
                color: context.jyotigptTheme.error.withValues(
                  alpha: Alpha.buttonPressed,
                ),
                borderRadius: BorderRadius.circular(radius),
                boxShadow: JyotiGPTShadows.button(context),
              ),
              child: Center(
                child: Icon(
                  Platform.isIOS ? CupertinoIcons.stop_fill : Icons.stop,
                  size: IconSize.large,
                  color: context.jyotigptTheme.error,
                ),
              ),
            ),
          ),
        ),
      );
    }

    if (hasText) {
      return Tooltip(
        message: enabled
            ? AppLocalizations.of(context)!.sendMessage
            : AppLocalizations.of(context)!.send,
        child: Opacity(
          opacity: enabled ? Alpha.primary : Alpha.disabled,
          child: IgnorePointer(
            ignoring: !enabled,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(radius),
                onTap: enabled
                    ? () {
                        PlatformUtils.lightHaptic();
                        _sendMessage();
                      }
                    : null,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 160),
                  curve: Curves.easeOutCubic,
                  width: buttonSize,
                  height: buttonSize,
                  decoration: BoxDecoration(
                    color: enabled
                        ? context.jyotigptTheme.buttonPrimary
                        : context.jyotigptTheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(radius),
                    border: Border.all(
                      color: enabled
                          ? context.jyotigptTheme.buttonPrimary.withValues(
                              alpha: 0.8,
                            )
                          : context.jyotigptTheme.cardBorder.withValues(
                              alpha: 0.45,
                            ),
                      width: BorderWidth.thin,
                    ),
                    boxShadow: enabled
                        ? <BoxShadow>[
                            BoxShadow(
                              color: context.jyotigptTheme.cardShadow.withValues(
                                alpha:
                                    Theme.of(context).brightness ==
                                        Brightness.dark
                                    ? 0.36
                                    : 0.18,
                              ),
                              blurRadius: 18,
                              spreadRadius: -6,
                              offset: const Offset(0, 8),
                            ),
                          ]
                        : const [],
                  ),
                  child: Center(
                    child: Icon(
                      Platform.isIOS
                          ? CupertinoIcons.arrow_up
                          : Icons.arrow_upward,
                      size: IconSize.large,
                      color: enabled
                          ? context.jyotigptTheme.buttonPrimaryText
                          : context.jyotigptTheme.textPrimary.withValues(
                              alpha: Alpha.disabled,
                            ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    }

    final bool enabledVoiceCall = widget.enabled && widget.onVoiceCall != null;
    return Tooltip(
      message: 'Voice Call',
      child: Opacity(
        opacity: enabledVoiceCall ? Alpha.primary : Alpha.disabled,
        child: IgnorePointer(
          ignoring: !enabledVoiceCall,
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(radius),
              onTap: enabledVoiceCall
                  ? () {
                      PlatformUtils.lightHaptic();
                      widget.onVoiceCall!();
                    }
                  : null,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                curve: Curves.easeOutCubic,
                width: buttonSize,
                height: buttonSize,
                decoration: BoxDecoration(
                  color: enabledVoiceCall
                      ? context.jyotigptTheme.buttonPrimary
                      : context.jyotigptTheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(radius),
                  border: Border.all(
                    color: enabledVoiceCall
                        ? context.jyotigptTheme.buttonPrimary.withValues(
                            alpha: 0.8,
                          )
                        : context.jyotigptTheme.cardBorder.withValues(
                            alpha: 0.45,
                          ),
                    width: BorderWidth.thin,
                  ),
                  boxShadow: enabledVoiceCall
                      ? <BoxShadow>[
                          BoxShadow(
                            color: context.jyotigptTheme.cardShadow.withValues(
                              alpha:
                                  Theme.of(context).brightness ==
                                      Brightness.dark
                                  ? 0.36
                                  : 0.18,
                            ),
                            blurRadius: 18,
                            spreadRadius: -6,
                            offset: const Offset(0, 8),
                          ),
                        ]
                      : const [],
                ),
                child: Center(
                  child: Icon(
                    Platform.isIOS ? CupertinoIcons.waveform : Icons.graphic_eq,
                    size: IconSize.large,
                    color: enabledVoiceCall
                        ? context.jyotigptTheme.buttonPrimaryText
                        : context.jyotigptTheme.textPrimary.withValues(
                            alpha: Alpha.disabled,
                          ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPillButton({
    required IconData icon,
    required String label,
    required bool isActive,
    VoidCallback? onTap,
  }) {
    final bool enabled = onTap != null;
    final Brightness brightness = Theme.of(context).brightness;
    final Color baseBackground = context.jyotigptTheme.cardBackground;
    final Color background = isActive
        ? context.jyotigptTheme.buttonPrimary.withValues(alpha: 0.16)
        : baseBackground.withValues(
            alpha: brightness == Brightness.dark ? 0.18 : 0.12,
          );
    final Color outline = isActive
        ? context.jyotigptTheme.buttonPrimary.withValues(alpha: 0.8)
        : context.jyotigptTheme.cardBorder.withValues(alpha: 0.6);
    final Color contentColor = isActive
        ? context.jyotigptTheme.buttonPrimary
        : context.jyotigptTheme.textPrimary.withValues(
            alpha: enabled ? Alpha.strong : Alpha.disabled,
          );

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(AppBorderRadius.input),
        onTap: onTap == null
            ? null
            : () {
                HapticFeedback.selectionClick();
                onTap();
              },
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.sm,
            vertical: Spacing.xs,
          ),
          decoration: BoxDecoration(
            color: background,
            borderRadius: BorderRadius.circular(AppBorderRadius.input),
            border: Border.all(color: outline, width: BorderWidth.thin),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: IconSize.medium, color: contentColor),
              const SizedBox(width: Spacing.xs),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.labelStyle.copyWith(color: contentColor),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showOverflowSheet() {
    HapticFeedback.selectionClick();
    final prevCanRequest = _focusNode.canRequestFocus;
    final wasFocused = _focusNode.hasFocus;
    _focusNode.canRequestFocus = false;
    try {
      FocusScope.of(context).unfocus();
      SystemChannels.textInput.invokeMethod('TextInput.hide');
    } catch (_) {}

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (modalContext) => Consumer(
        builder: (innerContext, modalRef, _) {
          final l10n = AppLocalizations.of(innerContext)!;
          final theme = innerContext.jyotigptTheme;

          final selectedToolIds = modalRef.watch(selectedToolIdsProvider);
          final toolsAsync = modalRef.watch(toolsListProvider);
          final Widget toolsSection = toolsAsync.when(
            data: (tools) {
              if (tools.isEmpty) {
                return _buildInfoCard('No tools available');
              }
              final tiles = tools.map((tool) {
                final isSelected = selectedToolIds.contains(tool.id);
                return _buildToolTile(
                  tool: tool,
                  selected: isSelected,
                  onToggle: () {
                    final current = List<String>.from(
                      modalRef.read(selectedToolIdsProvider),
                    );
                    if (isSelected) {
                      current.remove(tool.id);
                    } else {
                      current.add(tool.id);
                    }
                    modalRef
                        .read(selectedToolIdsProvider.notifier)
                        .set(current);
                  },
                );
              }).toList();
              return Column(children: _withVerticalSpacing(tiles, Spacing.xxs));
            },
            loading: () => Center(
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: BorderWidth.thin),
              ),
            ),
            error: (error, stack) => _buildInfoCard('Failed to load tools'),
          );

          final bodyChildren = <Widget>[
            const SheetHandle(),
            const SizedBox(height: Spacing.sm),
            _buildSectionLabel(l10n.tools),
            toolsSection,
          ];

          final GlobalKey sheetContentKey = GlobalKey();
          double? measuredContentHeight;

          return StatefulBuilder(
            builder: (context, setModalState) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                final ctx = sheetContentKey.currentContext;
                if (ctx != null) {
                  final renderObject = ctx.findRenderObject();
                  if (renderObject is RenderBox) {
                    final double h = renderObject.size.height;
                    if (h > 0 && h != measuredContentHeight) {
                      measuredContentHeight = h;
                      setModalState(() {});
                    }
                  }
                }
              });

              final media = MediaQuery.of(modalContext);
              final double availableHeight =
                  media.size.height - media.padding.top;

              double computedMax = 0.9;
              if (measuredContentHeight != null && availableHeight > 0) {
                computedMax = (measuredContentHeight! / availableHeight).clamp(
                  0.1,
                  0.9,
                );
              }
              final double computedMin = math.min(0.2, computedMax);
              final double computedInitial = math.min(0.34, computedMax);

              return Stack(
                children: [
                  Positioned.fill(
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: () => Navigator.of(modalContext).maybePop(),
                      child: const SizedBox.shrink(),
                    ),
                  ),
                  DraggableScrollableSheet(
                    expand: false,
                    initialChildSize: computedInitial,
                    minChildSize: computedMin,
                    maxChildSize: computedMax,
                    snap: true,
                    snapSizes: [computedMax],
                    builder: (sheetContext, scrollController) {
                      return Container(
                        decoration: BoxDecoration(
                          color: theme.surfaceBackground,
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(AppBorderRadius.bottomSheet),
                          ),
                          border: Border.all(
                            color: theme.dividerColor,
                            width: BorderWidth.thin,
                          ),
                          boxShadow: JyotiGPTShadows.modal(context),
                        ),
                        child: ModalSheetSafeArea(
                          padding: const EdgeInsets.fromLTRB(
                            Spacing.md,
                            Spacing.xs,
                            Spacing.md,
                            Spacing.md,
                          ),
                          child: SingleChildScrollView(
                            controller: scrollController,
                            padding: EdgeInsets.zero,
                            child: Column(
                              key: sheetContentKey,
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: bodyChildren,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ],
              );
            },
          );
        },
      ),
    ).whenComplete(() {
      if (mounted) {
        _focusNode.canRequestFocus = prevCanRequest;
        if (wasFocused && widget.enabled) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted) return;
            _ensureFocusedIfEnabled();
          });
        }
      }
    });
  }

  List<Widget> _withVerticalSpacing(List<Widget> children, double gap) {
    if (children.length <= 1) {
      return List<Widget>.from(children);
    }
    final spaced = <Widget>[];
    for (var i = 0; i < children.length; i++) {
      spaced.add(children[i]);
      if (i != children.length - 1) {
        spaced.add(SizedBox(height: gap));
      }
    }
    return spaced;
  }

  Widget _buildSectionLabel(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.xxs),
      child: Text(
        text,
        style: AppTypography.labelStyle.copyWith(
          color: context.jyotigptTheme.textSecondary.withValues(
            alpha: Alpha.strong,
          ),
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildToolTile({
    required Tool tool,
    required bool selected,
    required VoidCallback onToggle,
  }) {
    final theme = context.jyotigptTheme;
    final brightness = Theme.of(context).brightness;
    final description = _toolDescriptionFor(tool);
    final Color background = selected
        ? theme.buttonPrimary.withValues(
            alpha: brightness == Brightness.dark ? 0.28 : 0.16,
          )
        : theme.surfaceContainer.withValues(
            alpha: brightness == Brightness.dark ? 0.32 : 0.12,
          );
    final Color borderColor = selected
        ? theme.buttonPrimary.withValues(alpha: 0.7)
        : theme.cardBorder.withValues(alpha: 0.55);

    return Semantics(
      button: true,
      toggled: selected,
      label: tool.name,
      hint: description.isEmpty ? null : description,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(AppBorderRadius.input),
          onTap: () {
            HapticFeedback.selectionClick();
            onToggle();
          },
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOutCubic,
            margin: const EdgeInsets.symmetric(vertical: Spacing.xxs),
            padding: const EdgeInsets.all(Spacing.sm),
            decoration: BoxDecoration(
              color: background,
              borderRadius: BorderRadius.circular(AppBorderRadius.input),
              border: Border.all(color: borderColor, width: BorderWidth.thin),
              boxShadow: selected ? JyotiGPTShadows.low(context) : const [],
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                _buildToolGlyph(
                  icon: _toolIconFor(tool),
                  selected: selected,
                  theme: theme,
                ),
                const SizedBox(width: Spacing.xs),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        tool.name,
                        style: AppTypography.bodySmallStyle.copyWith(
                          color: theme.textPrimary,
                          fontWeight: selected
                              ? FontWeight.w600
                              : FontWeight.w500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (description.isNotEmpty) ...[
                        const SizedBox(height: Spacing.xs),
                        Text(
                          description,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: AppTypography.captionStyle.copyWith(
                            color: theme.textSecondary.withValues(
                              alpha: Alpha.strong,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: Spacing.xs),
                _buildTogglePill(isOn: selected, theme: theme),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildToolGlyph({
    required IconData icon,
    required bool selected,
    required JyotiGPTThemeExtension theme,
  }) {
    final Color accentStart = theme.buttonPrimary.withValues(
      alpha: selected ? Alpha.active : Alpha.hover,
    );
    final Color accentEnd = theme.buttonPrimary.withValues(
      alpha: selected ? Alpha.highlight : Alpha.focus,
    );
    final Color iconColor = selected
        ? theme.buttonPrimaryText
        : theme.iconPrimary.withValues(alpha: Alpha.strong);

    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [accentStart, accentEnd],
        ),
      ),
      child: Icon(icon, color: iconColor, size: IconSize.modal),
    );
  }

  String _toolDescriptionFor(Tool tool) {
    final metaDescription = _extractMetaDescription(tool.meta);
    if (metaDescription != null && metaDescription.isNotEmpty) {
      return metaDescription;
    }

    final custom = tool.description?.trim();
    if (custom != null && custom.isNotEmpty) {
      return custom;
    }

    final name = tool.name.toLowerCase();
    if (name.contains('search') || name.contains('browse')) {
      return 'Search the web for fresh context to improve answers.';
    }
    if (name.contains('image') ||
        name.contains('vision') ||
        name.contains('media')) {
      return 'Understand or generate imagery alongside your conversation.';
    }
    if (name.contains('code') ||
        name.contains('python') ||
        name.contains('notebook')) {
      return 'Execute code snippets and return computed results inline.';
    }
    if (name.contains('calc') || name.contains('math')) {
      return 'Perform precise math and calculations on demand.';
    }
    if (name.contains('file') || name.contains('document')) {
      return 'Access and summarize your uploaded files during chat.';
    }
    if (name.contains('api') || name.contains('request')) {
      return 'Trigger API requests and bring external data into the chat.';
    }
    return 'Enhance responses with specialized capabilities from this tool.';
  }

  String? _extractMetaDescription(Map<String, dynamic>? meta) {
    if (meta == null || meta.isEmpty) return null;
    final value = meta['description'];
    if (value is String) {
      final trimmed = value.trim();
      if (trimmed.isNotEmpty) return trimmed;
    }
    return null;
  }

  Widget _buildTogglePill({
    required bool isOn,
    required JyotiGPTThemeExtension theme,
  }) {
    final Color trackColor = isOn
        ? theme.buttonPrimary.withValues(alpha: 0.9)
        : theme.cardBorder.withValues(alpha: 0.5);
    final Color thumbColor = isOn
        ? theme.buttonPrimaryText
        : theme.surfaceBackground.withValues(alpha: 0.9);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
      width: 42,
      height: 22,
      padding: const EdgeInsets.symmetric(horizontal: 2),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppBorderRadius.round),
        color: trackColor,
      ),
      alignment: isOn ? Alignment.centerRight : Alignment.centerLeft,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        width: 18,
        height: 18,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: thumbColor,
          boxShadow: [
            BoxShadow(
              color: theme.buttonPrimary.withValues(alpha: 0.25),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
      ),
    );
  }

  IconData _toolIconFor(Tool tool) {
    final name = tool.name.toLowerCase();
    if (name.contains('image') || name.contains('vision')) {
      return Platform.isIOS ? CupertinoIcons.photo : Icons.image;
    }
    if (name.contains('code') || name.contains('python')) {
      return Platform.isIOS
          ? CupertinoIcons.chevron_left_slash_chevron_right
          : Icons.code;
    }
    if (name.contains('calculator') || name.contains('math')) {
      return Icons.calculate;
    }
    if (name.contains('file') || name.contains('document')) {
      return Platform.isIOS ? CupertinoIcons.doc : Icons.description;
    }
    if (name.contains('api') || name.contains('request')) {
      return Icons.cloud;
    }
    if (name.contains('search')) {
      return Platform.isIOS ? CupertinoIcons.search : Icons.search;
    }
    return Platform.isIOS ? CupertinoIcons.square_grid_2x2 : Icons.extension;
  }

  Widget _buildInfoCard(String message) {
    final theme = context.jyotigptTheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(Spacing.md),
      decoration: BoxDecoration(
        color: theme.cardBackground,
        borderRadius: BorderRadius.circular(AppBorderRadius.input),
        border: Border.all(
          color: theme.cardBorder.withValues(alpha: 0.6),
          width: BorderWidth.thin,
        ),
      ),
      child: Text(
        message,
        style: AppTypography.bodyMediumStyle.copyWith(
          color: theme.textSecondary,
        ),
      ),
    );
  }

  Future<void> _toggleVoice() async {
    if (_isRecording) {
      await _stopVoice();
    } else {
      await _startVoice();
    }
  }

  Future<void> _startVoice() async {
    if (!widget.enabled) return;
    try {
      final ok = await _voiceService.initialize();
      if (!mounted) return;
      if (!ok) {
        _showVoiceUnavailable(
          AppLocalizations.of(context)?.errorMessage ??
              'Voice input unavailable',
        );
        return;
      }
      final stream = await _voiceService.beginListening();
      if (!mounted) return;
      setState(() {
        _isRecording = true;
        _baseTextAtStart = _controller.text;
      });
      _intensitySub?.cancel();
      _textSub?.cancel();
      _textSub = stream.listen(
        (text) async {
          final updated = _baseTextAtStart.isEmpty
              ? text
              : '${_baseTextAtStart.trimRight()} $text';
          _controller.value = TextEditingValue(
            text: updated,
            selection: TextSelection.collapsed(offset: updated.length),
          );
        },
        onDone: () {
          if (!mounted) return;
          setState(() => _isRecording = false);
          _intensitySub?.cancel();
          _intensitySub = null;
        },
        onError: (_) {
          if (!mounted) return;
          setState(() => _isRecording = false);
          _intensitySub?.cancel();
          _intensitySub = null;
        },
      );
      _ensureFocusedIfEnabled();
    } catch (_) {
      _showVoiceUnavailable(
        AppLocalizations.of(context)?.errorMessage ??
            'Failed to start voice input',
      );
      if (!mounted) return;
      setState(() => _isRecording = false);
    }
  }

  Future<void> _stopVoice() async {
    _intensitySub?.cancel();
    _intensitySub = null;
    await _voiceService.stopListening();
    if (!mounted) return;
    setState(() => _isRecording = false);
    HapticFeedback.selectionClick();
  }

  void _showVoiceUnavailable(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }
}