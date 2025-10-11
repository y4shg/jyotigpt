/// Utility class for parsing and extracting reasoning/thinking content from messages.
class ReasoningParser {
  /// Default tag pairs to detect raw reasoning blocks when providers don't emit `<details>`.
  /// This mirrors Open WebUI defaults: `<think>...</think>`, `<reasoning>...</reasoning>`.
  static const List<List<String>> defaultReasoningTagPairs = <List<String>>[
    ['<think>', '</think>'],
    ['<reasoning>', '</reasoning>'],
  ];

  /// Parses a message and extracts reasoning content
  /// Supports:
  /// - `<details type="reasoning" ...>` blocks (server-emitted)
  /// - Raw tag pairs like `<think>...</think>` or `<reasoning>...</reasoning>`
  /// - Optional custom tag pair override
  static ReasoningContent? parseReasoningContent(
    String content, {
    List<String>? customTagPair,
    bool detectDefaultTags = true,
  }) {
    if (content.isEmpty) return null;

    // 1) Prefer server-emitted `<details type="reasoning">` blocks
    final detailsRegex = RegExp(
      r'<details\s+type="reasoning"(?:\s+done="(true|false)")?(?:\s+duration="(\d+)")?[^>]*>\s*<summary>([^<]*)<\/summary>\s*([\s\S]*?)<\/details>',
      multiLine: true,
      dotAll: true,
    );
    final detailsMatch = detailsRegex.firstMatch(content);
    if (detailsMatch != null) {
      final isDone = (detailsMatch.group(1) ?? 'true') == 'true';
      final duration = int.tryParse(detailsMatch.group(2) ?? '0') ?? 0;
      final summary = (detailsMatch.group(3) ?? '').trim();
      final reasoning = (detailsMatch.group(4) ?? '').trim();

      final mainContent = content.replaceAll(detailsRegex, '').trim();

      return ReasoningContent(
        reasoning: reasoning,
        summary: summary,
        duration: duration,
        isDone: isDone,
        mainContent: mainContent,
        originalContent: content,
      );
    }

    // 2) Handle partially streamed `<details>` (opening present, no closing yet)
    final openingIdx = content.indexOf('<details type="reasoning"');
    if (openingIdx >= 0 && !content.contains('</details>')) {
      final after = content.substring(openingIdx);
      // Try to extract optional summary
      final summaryMatch = RegExp(
        r'<summary>([^<]*)<\/summary>',
      ).firstMatch(after);
      final summary = (summaryMatch?.group(1) ?? '').trim();
      final reasoning = after
          .replaceAll(RegExp(r'^<details[^>]*>'), '')
          .replaceAll(RegExp(r'<summary>[\s\S]*?<\/summary>'), '')
          .trim();

      final mainContent = content.substring(0, openingIdx).trim();

      return ReasoningContent(
        reasoning: reasoning,
        summary: summary,
        duration: 0,
        isDone: false,
        mainContent: mainContent,
        originalContent: content,
      );
    }

    // 3) Otherwise, look for raw tag pairs
    List<List<String>> tagPairs = [];
    if (customTagPair != null && customTagPair.length == 2) {
      tagPairs.add(customTagPair);
    }
    if (detectDefaultTags) {
      tagPairs.addAll(defaultReasoningTagPairs);
    }

    for (final pair in tagPairs) {
      final start = RegExp.escape(pair[0]);
      final end = RegExp.escape(pair[1]);
      final tagRegex = RegExp(
        '($start)(.*?)($end)',
        multiLine: true,
        dotAll: true,
      );
      final match = tagRegex.firstMatch(content);
      if (match != null) {
        final reasoning = (match.group(2) ?? '').trim();
        final mainContent = content.replaceAll(tagRegex, '').trim();

        return ReasoningContent(
          reasoning: reasoning,
          summary: '', // no summary available for raw tags
          duration: 0,
          isDone: true,
          mainContent: mainContent,
          originalContent: content,
        );
      }
    }

    return null;
  }

  /// Splits content into ordered segments of plain text and reasoning entries
  /// (in the order they appear). Supports multiple reasoning blocks.
  /// - Handles `<details type="reasoning" ...>` with optional summary/duration/done
  /// - Handles raw tag pairs like `<think>...</think>` and `<reasoning>...</reasoning>`
  /// - Handles incomplete/streaming cases by emitting a partial reasoning entry
  static List<ReasoningSegment>? segments(
    String content, {
    List<String>? customTagPair,
    bool detectDefaultTags = true,
  }) {
    if (content.isEmpty) return null;

    // Build raw tag pairs to check
    final tagPairs = <List<String>>[];
    if (customTagPair != null && customTagPair.length == 2) {
      tagPairs.add(customTagPair);
    }
    if (detectDefaultTags) {
      tagPairs.addAll(defaultReasoningTagPairs);
    }

    final segs = <ReasoningSegment>[];
    int index = 0;

    while (index < content.length) {
      final nextDetails = content.indexOf('<details', index);

      // Find earliest raw tag start among known pairs
      int nextRawStart = -1;
      List<String>? rawPair; // [start, end]
      for (final pair in tagPairs) {
        final s = content.indexOf(pair[0], index);
        if (s != -1 && (nextRawStart == -1 || s < nextRawStart)) {
          nextRawStart = s;
          rawPair = pair;
        }
      }

      // Determine which comes first: reasoning <details> or raw tag
      int nextIdx;
      String kind; // 'details' or 'raw' or 'none'
      if (nextDetails == -1 && nextRawStart == -1) {
        nextIdx = -1;
        kind = 'none';
      } else if (nextDetails != -1 &&
          (nextRawStart == -1 || nextDetails < nextRawStart)) {
        nextIdx = nextDetails;
        kind = 'details';
      } else {
        nextIdx = nextRawStart;
        kind = 'raw';
      }

      if (kind == 'none') {
        if (index < content.length) {
          segs.add(ReasoningSegment.text(content.substring(index)));
        }
        break;
      }

      // Add text before the next block
      if (nextIdx > index) {
        segs.add(ReasoningSegment.text(content.substring(index, nextIdx)));
      }

      if (kind == 'details') {
        // Try to parse the opening <details ...>
        final openEnd = content.indexOf('>', nextIdx);
        if (openEnd == -1) {
          // Malformed tag; treat rest as text and stop
          segs.add(ReasoningSegment.text(content.substring(nextIdx)));
          break;
        }
        final openTag = content.substring(nextIdx, openEnd + 1);

        // Parse attributes
        final attrs = <String, String>{};
        final attrRegex = RegExp(r'(\w+)="(.*?)"');
        for (final m in attrRegex.allMatches(openTag)) {
          attrs[m.group(1)!] = m.group(2) ?? '';
        }
        final isReasoning = (attrs['type'] ?? '') == 'reasoning';

        // Find matching closing tag with nesting awareness
        int depth = 1;
        int i = openEnd + 1;
        while (i < content.length && depth > 0) {
          final nextOpen = content.indexOf('<details', i);
          final nextClose = content.indexOf('</details>', i);
          if (nextClose == -1 && nextOpen == -1) break;
          if (nextOpen != -1 && (nextClose == -1 || nextOpen < nextClose)) {
            depth++;
            i = nextOpen + 8; // '<details'
          } else {
            depth--;
            i = (nextClose != -1) ? nextClose + 10 : content.length;
          }
        }

        if (!isReasoning) {
          // Not a reasoning block; keep entire block as text if closed,
          // else append remainder and stop (streaming/malformed)
          if (depth != 0) {
            segs.add(ReasoningSegment.text(content.substring(nextIdx)));
            break;
          } else {
            final full = content.substring(nextIdx, i);
            segs.add(ReasoningSegment.text(full));
            index = i;
            continue;
          }
        }

        // Reasoning block
        final done = (attrs['done'] ?? 'true') == 'true';
        final duration = int.tryParse(attrs['duration'] ?? '0') ?? 0;

        if (depth != 0) {
          // Unclosed; treat as streaming partial
          final after = content.substring(openEnd + 1);
          final summaryMatch = RegExp(
            r'<summary>([^<]*)<\/summary>',
          ).firstMatch(after);
          final summary = (summaryMatch?.group(1) ?? '').trim();
          final reasoning = after
              .replaceAll(RegExp(r'^\s*<summary>[\s\S]*?<\/summary>'), '')
              .trim();
          segs.add(
            ReasoningSegment.entry(
              ReasoningEntry(
                reasoning: reasoning,
                summary: summary,
                duration: duration,
                isDone: false,
              ),
            ),
          );
          // No more content after partial block
          break;
        } else {
          // Closed block: extract inner content
          final inner = content.substring(
            openEnd + 1,
            i - 10,
          ); // without </details>
          final sumMatch = RegExp(
            r'<summary>([^<]*)<\/summary>',
          ).firstMatch(inner);
          final summary = (sumMatch?.group(1) ?? '').trim();
          final reasoning = inner
              .replaceAll(RegExp(r'<summary>[\s\S]*?<\/summary>'), '')
              .trim();
          segs.add(
            ReasoningSegment.entry(
              ReasoningEntry(
                reasoning: reasoning,
                summary: summary,
                duration: duration,
                isDone: done,
              ),
            ),
          );
          index = i;
          continue;
        }
      } else if (kind == 'raw' && rawPair != null) {
        final startTag = rawPair[0];
        final endTag = rawPair[1];
        final start = nextIdx;
        final end = content.indexOf(endTag, start + startTag.length);
        if (end == -1) {
          // Unclosed raw tag => streaming partial
          final inner = content.substring(start + startTag.length);
          segs.add(
            ReasoningSegment.entry(
              ReasoningEntry(
                reasoning: inner.trim(),
                summary: '',
                duration: 0,
                isDone: false,
              ),
            ),
          );
          break;
        } else {
          final inner = content.substring(start + startTag.length, end);
          segs.add(
            ReasoningSegment.entry(
              ReasoningEntry(
                reasoning: inner.trim(),
                summary: '',
                duration: 0,
                isDone: true,
              ),
            ),
          );
          index = end + endTag.length;
          continue;
        }
      }
    }

    return segs.isEmpty ? null : segs;
  }

  /// Checks if a message contains reasoning content
  static bool hasReasoningContent(String content) {
    if (content.contains('<details type="reasoning"')) return true;
    for (final pair in defaultReasoningTagPairs) {
      if (content.contains(pair[0]) && content.contains(pair[1])) return true;
    }
    return false;
  }

  /// Formats the duration for display
  static String formatDuration(int seconds) {
    if (seconds == 0) return 'instant';
    if (seconds < 60) return '$seconds second${seconds == 1 ? '' : 's'}';

    final minutes = seconds ~/ 60;
    final remainingSeconds = seconds % 60;

    if (remainingSeconds == 0) {
      return '$minutes minute${minutes == 1 ? '' : 's'}';
    }

    return '$minutes min ${remainingSeconds}s';
  }
}

/// Model class for reasoning content
class ReasoningContent {
  final String reasoning;
  final String summary;
  final int duration;
  final bool isDone;
  final String mainContent;
  final String originalContent;

  const ReasoningContent({
    required this.reasoning,
    required this.summary,
    required this.duration,
    required this.isDone,
    required this.mainContent,
    required this.originalContent,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ReasoningContent &&
          runtimeType == other.runtimeType &&
          reasoning == other.reasoning &&
          summary == other.summary &&
          duration == other.duration &&
          isDone == other.isDone &&
          mainContent == other.mainContent &&
          originalContent == other.originalContent;

  @override
  int get hashCode =>
      reasoning.hashCode ^
      summary.hashCode ^
      duration.hashCode ^
      isDone.hashCode ^
      mainContent.hashCode ^
      originalContent.hashCode;

  String get formattedDuration => ReasoningParser.formatDuration(duration);

  /// Gets the cleaned reasoning text (removes leading '>')
  String get cleanedReasoning {
    // Split by lines and clean each line
    return reasoning
        .split('\n')
        .map((line) => line.startsWith('>') ? line.substring(1).trim() : line)
        .join('\n')
        .trim();
  }
}

/// Lightweight reasoning block for segmented rendering
class ReasoningEntry {
  final String reasoning;
  final String summary;
  final int duration;
  final bool isDone;

  const ReasoningEntry({
    required this.reasoning,
    required this.summary,
    required this.duration,
    required this.isDone,
  });

  String get formattedDuration => ReasoningParser.formatDuration(duration);

  String get cleanedReasoning {
    return reasoning
        .split('\n')
        .map((line) => line.startsWith('>') ? line.substring(1).trim() : line)
        .join('\n')
        .trim();
  }
}

/// Ordered segment that is either plain text or a reasoning entry
class ReasoningSegment {
  final String? text;
  final ReasoningEntry? entry;

  const ReasoningSegment._({this.text, this.entry});
  factory ReasoningSegment.text(String text) => ReasoningSegment._(text: text);
  factory ReasoningSegment.entry(ReasoningEntry entry) =>
      ReasoningSegment._(entry: entry);

  bool get isReasoning => entry != null;
}
