/// Utility helpers for normalising markdown content before handing it to
/// [JyotiGPTMarkdown]. The goal is to keep streaming responsive while smoothing
/// out troublesome edge-cases (e.g. nested fences inside lists).
class JyotiGPTMarkdownPreprocessor {
  const JyotiGPTMarkdownPreprocessor._();

  // Pre-compile regex patterns for better performance during streaming
  static final _bulletFenceRegex = RegExp(
    r'^(\s*(?:[*+-]|\d+\.)\s+)```([^\s`]*)\s*$',
    multiLine: true,
  );
  static final _dedentOpenRegex = RegExp(
    r'^[ \t]+```([^\n`]*)\s*$',
    multiLine: true,
  );
  static final _dedentCloseRegex = RegExp(r'^[ \t]+```\s*$', multiLine: true);
  static final _inlineClosingRegex = RegExp(r'([^\r\n`])```(?=\s*(?:\r?\n|$))');
  static final _labelThenDashRegex = RegExp(
    r'^(\*\*[^\n*]+\*\*.*)\n(\s*-{3,}\s*$)',
    multiLine: true,
  );
  static final _atxEnumRegex = RegExp(
    r'^(\s{0,3}#{1,6}\s+\d+)\.(\s*)(\S)',
    multiLine: true,
  );
  static final _fenceAtBolRegex = RegExp(r'^\s*```', multiLine: true);

  /// Normalises common fence and hard-break issues produced by LLMs.
  static String normalize(String input) {
    if (input.isEmpty) {
      return input;
    }

    var output = input.replaceAll('\r\n', '\n');

    // Move fenced code blocks that start on the same line as a list item onto
    // their own line so the parser does not treat them as list text.
    output = output.replaceAllMapped(
      _bulletFenceRegex,
      (match) => '${match[1]}\n```${match[2]}',
    );

    // Dedent opening fences to avoid partial code-block detection when the
    // model indents fences by accident.
    output = output.replaceAllMapped(
      _dedentOpenRegex,
      (match) => '```${match[1]}',
    );

    // Dedent closing fences for the same reason as the opening fences.
    output = output.replaceAllMapped(_dedentCloseRegex, (_) => '```');

    // Ensure closing fences stand alone. Prevents situations like `}\n```foo`
    // from keeping trailing braces inside the code block.
    output = output.replaceAllMapped(
      _inlineClosingRegex,
      (match) => '${match[1]}\n```',
    );

    // Insert a blank line when a "label: value" line is followed by a
    // horizontal rule so it is not treated as a Setext heading underline.
    output = output.replaceAllMapped(
      _labelThenDashRegex,
      (match) => '${match[1]}\n\n${match[2]}',
    );

    // Allow headings like "## 1. Summary" without triggering ordered-list
    // parsing by inserting a zero-width joiner after the numeric marker.
    output = output.replaceAllMapped(
      _atxEnumRegex,
      (match) => '${match[1]}.\u200C${match[2]}${match[3]}',
    );

    // Auto-close an unmatched opening fence at EOF to avoid the entire tail
    // of the message rendering as code.
    final fenceCount = _fenceAtBolRegex.allMatches(output).length;
    if (fenceCount.isOdd) {
      if (!output.endsWith('\n')) {
        output += '\n';
      }
      output += '```';
    }

    // Convert Markdown links followed by two trailing spaces into separate
    // paragraphs so that consecutive links do not collapse into a single
    // paragraph at render time.
    final linkWithTrailingSpaces = RegExp(r'\[[^\]]+\]\([^\)]+\)\s{2,}$');
    final lines = output.split('\n');
    if (lines.length > 1) {
      final buffer = StringBuffer();
      for (var i = 0; i < lines.length; i++) {
        final line = lines[i];
        buffer.write(line);
        if (i < lines.length - 1) {
          buffer.write('\n');
        }
        if (linkWithTrailingSpaces.hasMatch(line)) {
          buffer.write('\n');
        }
      }
      output = buffer.toString();
    }

    return output;
  }

  /// Inserts zero-width break characters into long inline code spans so they
  /// remain readable and do not overflow narrow layouts.
  static String softenInlineCode(String input, {int chunkSize = 24}) {
    if (input.length <= chunkSize) {
      return input;
    }
    final buffer = StringBuffer();
    for (var i = 0; i < input.length; i++) {
      buffer.write(input[i]);
      if ((i + 1) % chunkSize == 0) {
        buffer.write('\u200B');
      }
    }
    return buffer.toString();
  }
}
