// Pre-compiled regex patterns for markdown syntax detection (performance optimization)
final _boldPattern = RegExp(r'\*\*');
final _italicPattern = RegExp(r'(?<!\*)\*(?!\*)');

/// Maintains a raw markdown buffer for streaming content and generates
/// preview-safe output by appending synthetic closing tokens when necessary.
class MarkdownStreamFormatter {
  StringBuffer _raw = StringBuffer();

  /// Seeds the formatter with existing markdown content.
  void seed(String content) {
    _raw = StringBuffer(content);
  }

  /// Adds a streaming chunk to the internal buffer and returns a preview-ready
  /// string with any required synthetic closing markers.
  String ingest(String chunk) {
    if (chunk.isNotEmpty) {
      _raw.write(chunk);
    }
    return preview();
  }

  /// Replaces the current buffer with the provided [content].
  String replace(String content) {
    seed(content);
    return preview();
  }

  /// Returns the preview-safe markdown string.
  String preview() {
    final raw = _raw.toString();
    return raw + _syntheticClosures(raw);
  }

  /// Returns the raw markdown accumulated so far.
  String finalize() => _raw.toString();

  String _syntheticClosures(String content) {
    final buffer = StringBuffer();

    final fenceCount = '```'.allMatches(content).length;
    if (fenceCount.isOdd) {
      buffer.writeln('```');
    }

    final boldCount = _boldPattern.allMatches(content).length;
    if (boldCount.isOdd) {
      buffer.write('**');
    }

    final italicCount = _italicPattern.allMatches(content).length;
    if (italicCount.isOdd) {
      buffer.write('*');
    }

    final openBrackets = '['.allMatches(content).length;
    final closeBrackets = ']'.allMatches(content).length;
    if (openBrackets > closeBrackets) {
      buffer.write(List.filled(openBrackets - closeBrackets, ']').join());
    }

    final openParens = '('.allMatches(content).length;
    final closeParens = ')'.allMatches(content).length;
    if (openParens > closeParens) {
      buffer.write(List.filled(openParens - closeParens, ')').join());
    }

    return buffer.toString();
  }
}
