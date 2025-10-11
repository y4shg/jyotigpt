import 'dart:async';
import 'dart:convert';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:flutter_math_fork/flutter_math.dart';
import 'package:markdown/markdown.dart' as md;
import 'package:webview_flutter/webview_flutter.dart';

import 'package:jyotigpt/l10n/app_localizations.dart';

import '../../theme/color_tokens.dart';
import '../../theme/theme_extensions.dart';
import 'code_block_header.dart';

typedef MarkdownLinkTapCallback = void Function(String url, String title);

class JyotiGPTMarkdown {
  const JyotiGPTMarkdown._();

  static Widget build({
    required BuildContext context,
    required String data,
    MarkdownLinkTapCallback? onTapLink,
    bool selectable = true,
    bool shrinkWrap = false,
    ScrollPhysics? physics,
    Widget Function(Uri uri, String? title, String? alt)? imageBuilderOverride,
  }) {
    return MarkdownBody(
      data: data,
      selectable: selectable,
      shrinkWrap: shrinkWrap,
      styleSheet: _buildStyleSheet(context),
      builders: _buildCustomBuilders(context, onTapLink),
      // Allow callers to override how markdown images render (e.g., to use
      // EnhancedImageAttachment in assistant views). Fallback to default.
      imageBuilder: (uri, title, alt) => imageBuilderOverride != null
          ? imageBuilderOverride(uri, title, alt)
          : _ImageBuilder(context).buildFromUri(uri),
      extensionSet: md.ExtensionSet.gitHubFlavored,
      onTapLink: onTapLink != null
          ? (text, href, title) => onTapLink(href ?? '', title)
          : null,
      syntaxHighlighter: _CodeSyntaxHighlighter(context),
      inlineSyntaxes: _buildInlineSyntaxes(),
      blockSyntaxes: _buildBlockSyntaxes(),
    );
  }

  static Widget buildBlock({
    required BuildContext context,
    required String data,
    MarkdownLinkTapCallback? onTapLink,
    bool selectable = true,
    Widget Function(Uri uri, String? title, String? alt)? imageBuilderOverride,
  }) {
    return build(
      context: context,
      data: data,
      onTapLink: onTapLink,
      selectable: selectable,
      shrinkWrap: true,
      imageBuilderOverride: imageBuilderOverride,
    );
  }

  static MarkdownStyleSheet _buildStyleSheet(BuildContext context) {
    final theme = context.jyotigptTheme;
    final material = Theme.of(context);

    final baseBody = AppTypography.bodyMediumStyle.copyWith(
      color: theme.textPrimary,
      height: 1.45,
    );
    final secondaryBody = AppTypography.bodySmallStyle.copyWith(
      color: theme.textSecondary,
      height: 1.45,
    );

    final codeBackground = theme.surfaceContainer.withValues(alpha: 0.55);
    final borderColor = theme.cardBorder.withValues(alpha: 0.25);

    return MarkdownStyleSheet(
      p: baseBody,
      h1: AppTypography.headlineLargeStyle.copyWith(color: theme.textPrimary),
      h2: AppTypography.headlineMediumStyle.copyWith(color: theme.textPrimary),
      h3: AppTypography.headlineSmallStyle.copyWith(color: theme.textPrimary),
      h4: AppTypography.bodyLargeStyle.copyWith(color: theme.textPrimary),
      h5: baseBody.copyWith(fontWeight: FontWeight.w600),
      h6: secondaryBody,
      a: baseBody.copyWith(
        color: material.colorScheme.primary,
        decoration: TextDecoration.underline,
        decorationColor: material.colorScheme.primary,
      ),
      code: AppTypography.codeStyle.copyWith(
        color: theme.codeText,
        backgroundColor: codeBackground,
      ),
      codeblockDecoration: BoxDecoration(
        color: codeBackground,
        borderRadius: BorderRadius.circular(AppBorderRadius.sm),
        border: Border.all(color: borderColor, width: BorderWidth.micro),
      ),
      codeblockPadding: const EdgeInsets.all(Spacing.sm),
      blockquoteDecoration: BoxDecoration(
        border: Border(
          left: BorderSide(
            color: material.colorScheme.primary.withValues(alpha: 0.35),
            width: BorderWidth.small,
          ),
        ),
      ),
      blockquotePadding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.sm,
      ),
      blockquote: secondaryBody,
      listBullet: baseBody,
      listIndent: Spacing.lg,
      tableHead: secondaryBody.copyWith(fontWeight: FontWeight.w600),
      tableBody: secondaryBody,
      tableBorder: TableBorder.all(
        color: borderColor,
        width: BorderWidth.micro,
      ),
      tableHeadAlign: TextAlign.start,
      tableColumnWidth: const FlexColumnWidth(),
      tableCellsPadding: const EdgeInsets.symmetric(
        horizontal: Spacing.sm,
        vertical: Spacing.xs,
      ),
      horizontalRuleDecoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: theme.dividerColor, width: BorderWidth.small),
        ),
      ),
    );
  }

  static Map<String, MarkdownElementBuilder> _buildCustomBuilders(
    BuildContext context,
    MarkdownLinkTapCallback? onTapLink,
  ) {
    return {
      'code': _CodeBlockBuilder(context),
      'mermaid': _MermaidBuilder(context),
      'latex': _LatexBuilder(context),
      'details': _DetailsBuilder(context),
    };
  }

  static List<md.InlineSyntax> _buildInlineSyntaxes() {
    return [_LatexInlineSyntax()];
  }

  static List<md.BlockSyntax> _buildBlockSyntaxes() {
    return [_DetailsBlockSyntax()];
  }

  static Widget buildMermaidBlock(BuildContext context, String code) {
    final jyotigptTheme = context.jyotigptTheme;
    final materialTheme = Theme.of(context);

    if (MermaidDiagram.isSupported) {
      return _buildMermaidContainer(
        context: context,
        jyotigptTheme: jyotigptTheme,
        materialTheme: materialTheme,
        code: code,
      );
    }

    return _buildUnsupportedMermaidContainer(
      context: context,
      jyotigptTheme: jyotigptTheme,
      code: code,
    );
  }

  static Widget _buildMermaidContainer({
    required BuildContext context,
    required JyotiGPTThemeExtension jyotigptTheme,
    required ThemeData materialTheme,
    required String code,
  }) {
    final tokens = context.colorTokens;
    return Container(
      margin: const EdgeInsets.symmetric(vertical: Spacing.sm),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppBorderRadius.sm),
        border: Border.all(
          color: jyotigptTheme.cardBorder.withValues(alpha: 0.4),
          width: BorderWidth.micro,
        ),
      ),
      height: 360,
      width: double.infinity,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppBorderRadius.sm),
        child: MermaidDiagram(
          code: code,
          brightness: materialTheme.brightness,
          colorScheme: materialTheme.colorScheme,
          tokens: tokens,
        ),
      ),
    );
  }

  static Widget _buildUnsupportedMermaidContainer({
    required BuildContext context,
    required JyotiGPTThemeExtension jyotigptTheme,
    required String code,
  }) {
    final textStyle = AppTypography.bodySmallStyle.copyWith(
      color: jyotigptTheme.codeText.withValues(alpha: 0.7),
    );

    return Container(
      margin: const EdgeInsets.symmetric(vertical: Spacing.sm),
      padding: const EdgeInsets.all(Spacing.sm),
      decoration: BoxDecoration(
        color: jyotigptTheme.surfaceContainer.withValues(alpha: 0.35),
        borderRadius: BorderRadius.circular(AppBorderRadius.sm),
        border: Border.all(
          color: jyotigptTheme.cardBorder.withValues(alpha: 0.4),
          width: BorderWidth.micro,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Mermaid preview is not available on this platform.',
            style: textStyle,
          ),
          const SizedBox(height: Spacing.xs),
          SelectableText(
            code,
            maxLines: null,
            textAlign: TextAlign.left,
            textDirection: TextDirection.ltr,
            textWidthBasis: TextWidthBasis.parent,
            style: AppTypography.codeStyle.copyWith(
              color: jyotigptTheme.codeText,
            ),
          ),
        ],
      ),
    );
  }
}

// Code syntax highlighting
class _CodeSyntaxHighlighter extends SyntaxHighlighter {
  _CodeSyntaxHighlighter(this.context);

  final BuildContext context;

  @override
  TextSpan format(String source) {
    final theme = context.jyotigptTheme;

    return TextSpan(
      style: AppTypography.codeStyle.copyWith(color: theme.codeText),
      children: [TextSpan(text: source)],
    );
  }
}

// Custom code block builder with header
class _CodeBlockBuilder extends MarkdownElementBuilder {
  _CodeBlockBuilder(this.context);

  final BuildContext context;

  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final theme = context.jyotigptTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final code = element.textContent;
    final language =
        element.attributes['class']?.replaceFirst('language-', '') ??
        'plaintext';
    final normalizedLanguage = language.trim().isEmpty
        ? 'plaintext'
        : language.trim();

    // Match GitHub/Atom theme colors for code block container
    final codeBackground = isDark
        ? const Color(0xFF282c34) // Atom One Dark background
        : const Color(0xFFfafbfc); // GitHub light background

    return Container(
      margin: const EdgeInsets.symmetric(vertical: Spacing.sm),
      decoration: BoxDecoration(
        color: codeBackground,
        borderRadius: BorderRadius.circular(6),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CodeBlockHeader(
            language: normalizedLanguage,
            onCopy: () async {
              await Clipboard.setData(ClipboardData(text: code));
              if (!context.mounted) {
                return;
              }
              ScaffoldMessenger.of(context).hideCurrentSnackBar();
              final l10n = AppLocalizations.of(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    l10n?.codeCopiedToClipboard ?? 'Code copied to clipboard.',
                  ),
                ),
              );
            },
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.all(Spacing.md),
            child: SelectableText(
              code,
              style: AppTypography.codeStyle.copyWith(
                color: theme.codeText,
                fontFamily: AppTypography.monospaceFontFamily,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Custom image builder
class _ImageBuilder extends MarkdownElementBuilder {
  _ImageBuilder(this.context);

  final BuildContext context;

  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final url = element.attributes['src'] ?? '';
    final uri = Uri.tryParse(url);
    if (uri == null) {
      return _buildImageError(context, context.jyotigptTheme);
    }
    return buildFromUri(uri);
  }

  /// Public helper used by the Markdown `imageBuilder` callback.
  Widget buildFromUri(Uri uri) {
    final theme = context.jyotigptTheme;
    if (uri.scheme == 'data') {
      return _buildBase64Image(uri.toString(), context, theme);
    }
    if (uri.scheme.isEmpty || uri.scheme == 'http' || uri.scheme == 'https') {
      return _buildNetworkImage(uri.toString(), context, theme);
    }
    return _buildImageError(context, theme);
  }

  Widget _buildBase64Image(
    String dataUrl,
    BuildContext context,
    JyotiGPTThemeExtension theme,
  ) {
    try {
      final commaIndex = dataUrl.indexOf(',');
      if (commaIndex == -1) {
        throw FormatException(
          AppLocalizations.of(context)?.invalidDataUrl ??
              'Invalid data URL format',
        );
      }

      final base64String = dataUrl.substring(commaIndex + 1);
      final imageBytes = base64.decode(base64String);

      return Container(
        margin: const EdgeInsets.symmetric(vertical: Spacing.sm),
        constraints: const BoxConstraints(maxWidth: 480, maxHeight: 480),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          child: Image.memory(
            imageBytes,
            fit: BoxFit.contain,
            errorBuilder: (context, error, stackTrace) {
              return _buildImageError(context, theme);
            },
          ),
        ),
      );
    } catch (_) {
      return _buildImageError(context, theme);
    }
  }

  Widget _buildNetworkImage(
    String url,
    BuildContext context,
    JyotiGPTThemeExtension theme,
  ) {
    return CachedNetworkImage(
      imageUrl: url,
      placeholder: (context, _) => Container(
        height: 200,
        decoration: BoxDecoration(
          color: theme.surfaceBackground.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
        ),
        child: Center(
          child: CircularProgressIndicator(
            color: theme.loadingIndicator,
            strokeWidth: 2,
          ),
        ),
      ),
      errorWidget: (context, url, error) => _buildImageError(context, theme),
      imageBuilder: (context, imageProvider) => Container(
        margin: const EdgeInsets.symmetric(vertical: Spacing.sm),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          image: DecorationImage(image: imageProvider, fit: BoxFit.contain),
        ),
      ),
    );
  }

  Widget _buildImageError(BuildContext context, JyotiGPTThemeExtension theme) {
    return Container(
      height: 120,
      decoration: BoxDecoration(
        color: theme.surfaceBackground.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(AppBorderRadius.md),
        border: Border.all(
          color: theme.cardBorder.withValues(alpha: 0.4),
          width: BorderWidth.micro,
        ),
      ),
      child: Center(
        child: Icon(Icons.broken_image_outlined, color: theme.iconSecondary),
      ),
    );
  }
}

// Mermaid diagram builder
class _MermaidBuilder extends MarkdownElementBuilder {
  _MermaidBuilder(this.context);

  final BuildContext context;

  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final code = element.textContent;
    return JyotiGPTMarkdown.buildMermaidBlock(context, code);
  }
}

// LaTeX builder
class _LatexBuilder extends MarkdownElementBuilder {
  _LatexBuilder(this.context);

  final BuildContext context;

  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final content = element.textContent.trim();
    final isInline = element.attributes['isInline'] == 'true';

    final baseStyle = (preferredStyle ?? AppTypography.bodyMediumStyle)
        .copyWith(color: isDark ? Colors.white : Colors.black);

    if (content.isEmpty) {
      return Text(element.textContent, style: baseStyle);
    }

    final mathWidget = Math.tex(
      content,
      mathStyle: MathStyle.text,
      textStyle: baseStyle,
      textScaleFactor: 1,
      onErrorFallback: (error) {
        return Text(content, style: baseStyle.copyWith(color: Colors.red));
      },
    );

    if (isInline) {
      return mathWidget;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: Spacing.xs),
      child: Center(child: mathWidget),
    );
  }
}

// LaTeX inline syntax
class _LatexInlineSyntax extends md.InlineSyntax {
  _LatexInlineSyntax()
    : super(
        r'(\$\$[\s\S]+?\$\$)|(\$[^\n]+?\$)|(\\\([\s\S]+?\\\))|(\\\[[\s\S]+?\\\])',
      );

  @override
  bool onMatch(md.InlineParser parser, Match match) {
    final raw = match.group(0) ?? '';
    String content = raw;
    bool isInline = true;

    if (raw.startsWith(r'$$') && raw.endsWith(r'$$') && raw.length > 4) {
      content = raw.substring(2, raw.length - 2);
      isInline = false;
    } else if (raw.startsWith(r'$') && raw.endsWith(r'$') && raw.length > 2) {
      content = raw.substring(1, raw.length - 1);
      isInline = true;
    } else if (raw.startsWith(r'\(') && raw.endsWith(r'\)') && raw.length > 4) {
      content = raw.substring(2, raw.length - 2);
      isInline = true;
    } else if (raw.startsWith(r'\[') && raw.endsWith(r'\]') && raw.length > 4) {
      content = raw.substring(2, raw.length - 2);
      isInline = false;
    }

    final element = md.Element.text('latex', content);
    element.attributes['isInline'] = isInline.toString();
    parser.addNode(element);
    return true;
  }
}

// Mermaid diagram WebView widget
class MermaidDiagram extends StatefulWidget {
  const MermaidDiagram({
    super.key,
    required this.code,
    required this.brightness,
    required this.colorScheme,
    required this.tokens,
  });

  final String code;
  final Brightness brightness;
  final ColorScheme colorScheme;
  final AppColorTokens tokens;

  static bool get isSupported => !kIsWeb;

  static Future<String> _loadScript() {
    return _scriptFuture ??= rootBundle.loadString('assets/mermaid.min.js');
  }

  static Future<String>? _scriptFuture;

  @override
  State<MermaidDiagram> createState() => _MermaidDiagramState();
}

class _MermaidDiagramState extends State<MermaidDiagram> {
  WebViewController? _controller;
  String? _script;
  final Set<Factory<OneSequenceGestureRecognizer>> _gestureRecognizers =
      <Factory<OneSequenceGestureRecognizer>>{
        Factory<OneSequenceGestureRecognizer>(() => EagerGestureRecognizer()),
      };

  @override
  void initState() {
    super.initState();
    if (!MermaidDiagram.isSupported) {
      return;
    }
    MermaidDiagram._loadScript().then((value) {
      if (!mounted) {
        return;
      }
      _script = value;
      _controller = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(Colors.transparent);
      _loadHtml();
      setState(() {});
    });
  }

  @override
  void didUpdateWidget(MermaidDiagram oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_controller == null || _script == null) {
      return;
    }
    final codeChanged = oldWidget.code != widget.code;
    final themeChanged =
        oldWidget.brightness != widget.brightness ||
        oldWidget.colorScheme != widget.colorScheme ||
        oldWidget.tokens != widget.tokens;
    if (codeChanged || themeChanged) {
      _loadHtml();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_controller == null) {
      return const Center(child: CircularProgressIndicator());
    }
    return SizedBox.expand(
      child: WebViewWidget(
        controller: _controller!,
        gestureRecognizers: _gestureRecognizers,
      ),
    );
  }

  void _loadHtml() {
    if (_controller == null || _script == null) {
      return;
    }
    _controller!.loadHtmlString(_buildHtml(widget.code, _script!));
  }

  String _buildHtml(String code, String script) {
    final theme = widget.brightness == Brightness.dark ? 'dark' : 'default';
    final primary = _toHex(widget.tokens.brandTone60);
    final secondary = _toHex(widget.tokens.accentTeal60);
    final background = _toHex(widget.tokens.codeBackground);
    final onBackground = _toHex(widget.tokens.codeText);

    return '''
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  body {
    margin: 0;
    background-color: transparent;
  }
  #container {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: transparent;
  }
</style>
</head>
<body>
<div id="container">
  <div class="mermaid">$code</div>
</div>
<script>$script</script>
<script>
  mermaid.initialize({
    theme: '$theme',
    themeVariables: {
      primaryColor: '$primary',
      primaryTextColor: '$onBackground',
      primaryBorderColor: '$secondary',
      background: '$background'
    },
  });
  mermaid.contentLoaded();
</script>
</body>
</html>
''';
  }

  String _toHex(Color color) {
    int channel(double value) {
      final scaled = (value * 255).round();
      if (scaled < 0) {
        return 0;
      }
      if (scaled > 255) {
        return 255;
      }
      return scaled;
    }

    final argb =
        (channel(color.a) << 24) |
        (channel(color.r) << 16) |
        (channel(color.g) << 8) |
        channel(color.b);
    return '#${argb.toRadixString(16).padLeft(8, '0')}';
  }
}

// Details block syntax for parsing <details> tags
class _DetailsBlockSyntax extends md.BlockSyntax {
  @override
  RegExp get pattern => RegExp(r'^<details(\s+[^>]*)?>$');

  @override
  md.Node? parse(md.BlockParser parser) {
    final match = pattern.firstMatch(parser.current.content);
    if (match == null) {
      return null;
    }

    // Parse attributes from the opening tag
    final attributesString = match.group(1) ?? '';
    final attributes = _parseAttributes(attributesString);

    parser.advance();

    // Find the matching closing tag
    String summary = '';
    final contentLines = <String>[];
    while (!parser.isDone) {
      final line = parser.current.content;

      // Check for closing tag
      if (line.trim() == '</details>') {
        parser.advance();
        break;
      }

      // Check for summary tag
      final summaryMatch = RegExp(
        r'^<summary>(.*?)<\/summary>$',
      ).firstMatch(line);
      if (summaryMatch != null) {
        summary = summaryMatch.group(1) ?? '';
        parser.advance();
        continue;
      }

      contentLines.add(line);
      parser.advance();
    }

    final element = md.Element('details', [md.Text(contentLines.join('\n'))]);
    element.attributes['summary'] = summary;
    element.attributes.addAll(attributes);

    return element;
  }

  Map<String, String> _parseAttributes(String attributesString) {
    final attributes = <String, String>{};
    final attrRegex = RegExp(r'(\w+)="([^"]*)"');
    for (final match in attrRegex.allMatches(attributesString)) {
      attributes[match.group(1)!] = match.group(2) ?? '';
    }
    return attributes;
  }
}

// Details builder for rendering <details> elements
class _DetailsBuilder extends MarkdownElementBuilder {
  _DetailsBuilder(this.context);

  final BuildContext context;

  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    // Details elements with type="reasoning" or type="tool_calls" should not be
    // rendered as markdown during streaming. They are handled by:
    // - ReasoningParser for reasoning blocks (creates thinking tiles)
    // - ToolCallsParser for tool_calls blocks (creates tool execution tiles)
    // Return empty widget to prevent character flashing during streaming.
    return const SizedBox.shrink();
  }
}
