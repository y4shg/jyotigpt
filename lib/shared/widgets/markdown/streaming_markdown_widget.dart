import 'package:flutter/material.dart';

import '../../theme/theme_extensions.dart';
import 'markdown_config.dart';
import 'markdown_preprocessor.dart';

// Pre-compiled regex for mermaid diagram detection (performance optimization)
final _mermaidRegex = RegExp(r'```mermaid\s*([\s\S]*?)```', multiLine: true);

class StreamingMarkdownWidget extends StatelessWidget {
  const StreamingMarkdownWidget({
    super.key,
    required this.content,
    required this.isStreaming,
    this.onTapLink,
    this.imageBuilderOverride,
  });

  final String content;
  final bool isStreaming;
  final MarkdownLinkTapCallback? onTapLink;
  final Widget Function(Uri uri, String? title, String? alt)?
  imageBuilderOverride;

  @override
  Widget build(BuildContext context) {
    if (content.trim().isEmpty) {
      return const SizedBox.shrink();
    }

    final normalized = JyotiGPTMarkdownPreprocessor.normalize(content);
    final matches = _mermaidRegex.allMatches(normalized).toList();

    Widget buildMarkdown(String data) {
      return JyotiGPTMarkdown.buildBlock(
        context: context,
        data: data,
        onTapLink: onTapLink,
        selectable: false,
        imageBuilderOverride: imageBuilderOverride,
      );
    }

    if (matches.isEmpty) {
      return SelectionArea(
        child: Theme(
          data: Theme.of(context).copyWith(
            textSelectionTheme: TextSelectionThemeData(
              cursorColor: context.jyotigptTheme.buttonPrimary,
            ),
          ),
          child: buildMarkdown(normalized),
        ),
      );
    }

    final children = <Widget>[];
    var currentIndex = 0;
    for (final match in matches) {
      final before = normalized.substring(currentIndex, match.start);
      if (before.trim().isNotEmpty) {
        children.add(buildMarkdown(before));
      }

      final code = match.group(1)?.trim() ?? '';
      if (code.isNotEmpty) {
        children.add(JyotiGPTMarkdown.buildMermaidBlock(context, code));
      }

      currentIndex = match.end;
    }

    final tail = normalized.substring(currentIndex);
    if (tail.trim().isNotEmpty) {
      children.add(buildMarkdown(tail));
    }

    return SelectionArea(
      child: Theme(
        data: Theme.of(context).copyWith(
          textSelectionTheme: TextSelectionThemeData(
            cursorColor: context.jyotigptTheme.buttonPrimary,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: children,
        ),
      ),
    );
  }
}

extension StreamingMarkdownExtension on String {
  Widget toMarkdown({
    required BuildContext context,
    bool isStreaming = false,
    MarkdownLinkTapCallback? onTapLink,
  }) {
    return StreamingMarkdownWidget(
      content: this,
      isStreaming: isStreaming,
      onTapLink: onTapLink,
    );
  }
}

class MarkdownWithLoading extends StatelessWidget {
  const MarkdownWithLoading({super.key, this.content, required this.isLoading});

  final String? content;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    final value = content ?? '';
    if (isLoading && value.trim().isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    return StreamingMarkdownWidget(content: value, isStreaming: isLoading);
  }
}
