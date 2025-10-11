/// Converts markdown text to plain text suitable for text-to-speech.
///
/// Strips formatting while preserving the semantic meaning and readability
/// of the content for audio consumption.
class MarkdownToText {
  const MarkdownToText._();

  static final _codeBlockRegex = RegExp(
    r'```[^\n]*\n(.*?)```',
    multiLine: true,
    dotAll: true,
  );
  static final _inlineCodeRegex = RegExp(r'`([^`]+)`');
  static final _boldItalicRegex = RegExp(r'\*\*\*([^*]+)\*\*\*');
  static final _boldRegex = RegExp(r'\*\*([^*]+)\*\*');
  static final _italicRegex = RegExp(r'\*([^*]+)\*|_([^_]+)_');
  static final _strikethroughRegex = RegExp(r'~~([^~]+)~~');
  static final _linkRegex = RegExp(r'\[([^\]]+)\]\([^)]+\)');
  static final _imageRegex = RegExp(r'!\[([^\]]*)\]\([^)]+\)');
  static final _headingRegex = RegExp(r'^#{1,6}\s+(.+)$', multiLine: true);
  static final _listItemRegex = RegExp(r'^[\s]*[-*+]\s+(.+)$', multiLine: true);
  static final _orderedListRegex = RegExp(
    r'^[\s]*\d+\.\s+(.+)$',
    multiLine: true,
  );
  static final _blockquoteRegex = RegExp(r'^>\s*(.+)$', multiLine: true);
  static final _horizontalRuleRegex = RegExp(
    r'^[\s]*[-*_]{3,}[\s]*$',
    multiLine: true,
  );
  static final _htmlTagRegex = RegExp(r'<[^>]+>');
  static final _multipleNewlinesRegex = RegExp(r'\n{3,}');
  static final _multipleSpacesRegex = RegExp(r' {2,}');

  /// Converts markdown text to plain text suitable for TTS.
  ///
  /// - Removes code blocks (replaces with descriptive text)
  /// - Strips all formatting (bold, italic, strikethrough)
  /// - Converts links to just their text
  /// - Removes images (or converts to alt text)
  /// - Simplifies headings
  /// - Preserves list structure with natural pauses
  /// - Removes HTML tags
  /// - Normalizes whitespace
  static String convert(String markdown) {
    if (markdown.trim().isEmpty) {
      return '';
    }

    var text = markdown;

    // Remove or replace code blocks with descriptive text
    text = text.replaceAllMapped(_codeBlockRegex, (match) {
      final code = match[1]?.trim() ?? '';
      if (code.isEmpty) {
        return '';
      }
      // For TTS, skip code blocks or use a brief description
      return ' (code block) ';
    });

    // Remove inline code backticks but keep the content
    text = text.replaceAllMapped(_inlineCodeRegex, (match) => match[1] ?? '');

    // Strip bold/italic/strikethrough formatting
    text = text.replaceAllMapped(_boldItalicRegex, (match) => match[1] ?? '');
    text = text.replaceAllMapped(_boldRegex, (match) => match[1] ?? '');
    text = text.replaceAllMapped(
      _italicRegex,
      (match) => match[1] ?? match[2] ?? '',
    );
    text = text.replaceAllMapped(
      _strikethroughRegex,
      (match) => match[1] ?? '',
    );

    // Convert links to just their text
    text = text.replaceAllMapped(_linkRegex, (match) => match[1] ?? '');

    // Remove images (or use alt text if available)
    text = text.replaceAllMapped(_imageRegex, (match) {
      final alt = match[1]?.trim() ?? '';
      return alt.isNotEmpty ? ' ($alt image) ' : '';
    });

    // Simplify headings (remove # symbols)
    text = text.replaceAllMapped(_headingRegex, (match) {
      final heading = match[1] ?? '';
      // Add a pause after headings for natural speech flow
      return '$heading.\n';
    });

    // Preserve list items with natural pauses
    text = text.replaceAllMapped(_listItemRegex, (match) => '${match[1]}. ');
    text = text.replaceAllMapped(_orderedListRegex, (match) => '${match[1]}. ');

    // Remove blockquote markers
    text = text.replaceAllMapped(_blockquoteRegex, (match) => match[1] ?? '');

    // Remove horizontal rules
    text = text.replaceAll(_horizontalRuleRegex, '');

    // Remove HTML tags
    text = text.replaceAll(_htmlTagRegex, '');

    // Normalize whitespace
    text = text.replaceAll(_multipleNewlinesRegex, '\n\n');
    text = text.replaceAll(_multipleSpacesRegex, ' ');

    // Convert newlines to spaces for natural speech flow
    text = text.replaceAll('\n', ' ');

    // Final cleanup
    text = text.trim();

    return text;
  }
}
