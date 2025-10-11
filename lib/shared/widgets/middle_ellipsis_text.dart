import 'package:flutter/widgets.dart';

/// A single-line text widget that truncates the middle of long strings
/// with an ellipsis (e.g., "prefix…suffix") so both ends remain visible.
class MiddleEllipsisText extends StatelessWidget {
  final String text;
  final TextStyle? style;
  final TextAlign? textAlign;
  final String ellipsis;
  final String? semanticsLabel;

  const MiddleEllipsisText(
    this.text, {
    super.key,
    this.style,
    this.textAlign,
    this.ellipsis = '…',
    this.semanticsLabel,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final TextStyle effectiveStyle = DefaultTextStyle.of(
          context,
        ).style.merge(style);
        final TextDirection direction = Directionality.of(context);
        final double maxWidth = constraints.maxWidth;

        // Measure full text width first.
        final fullSpan = TextSpan(text: text, style: effectiveStyle);
        final fullPainter = TextPainter(
          text: fullSpan,
          textDirection: direction,
          maxLines: 1,
        )..layout(minWidth: 0, maxWidth: double.infinity);

        if (fullPainter.width <= maxWidth) {
          return Text(
            text,
            style: effectiveStyle,
            maxLines: 1,
            overflow: TextOverflow.clip,
            textAlign: textAlign,
            semanticsLabel: semanticsLabel,
          );
        }

        // Pre-measure ellipsis width (used implicitly during search).
        final ellipsisSpan = TextSpan(text: ellipsis, style: effectiveStyle);
        final ellipsisPainter = TextPainter(
          text: ellipsisSpan,
          textDirection: direction,
          maxLines: 1,
        )..layout(minWidth: 0, maxWidth: double.infinity);
        final double _ = ellipsisPainter.width; // hint width; not used directly

        // Binary search the maximum number of visible characters (k), split
        // between start and end. For a given k, we use ceil(k/2) from start
        // and floor(k/2) from end.
        int low = 0;
        int high = text.length; // exclusive upper bound in practice
        int bestK = 0;
        String bestStart = '';
        String bestEnd = '';

        while (low <= high) {
          final int k = (low + high) >> 1; // candidate visible char count
          final int leftCount = (k + 1) >> 1; // ceil(k/2)
          final int rightCount = k - leftCount; // floor(k/2)

          final String start = text.substring(0, leftCount);
          final String end = rightCount == 0
              ? ''
              : text.substring(text.length - rightCount);

          final trialSpan = TextSpan(
            text: '$start$ellipsis$end',
            style: effectiveStyle,
          );
          final trialPainter = TextPainter(
            text: trialSpan,
            textDirection: direction,
            maxLines: 1,
          )..layout(minWidth: 0, maxWidth: double.infinity);

          if (trialPainter.width <= maxWidth) {
            bestK = k;
            bestStart = start;
            bestEnd = end;
            low = k + 1; // try to fit more
          } else {
            high = k - 1; // need fewer characters
          }
        }

        if (bestK == 0) {
          return Text(
            ellipsis,
            style: effectiveStyle,
            maxLines: 1,
            overflow: TextOverflow.clip,
            textAlign: textAlign,
            semanticsLabel: semanticsLabel ?? text,
          );
        }

        final String display = '$bestStart$ellipsis$bestEnd';
        return Text(
          display,
          style: effectiveStyle,
          maxLines: 1,
          overflow: TextOverflow.clip,
          textAlign: textAlign,
          semanticsLabel: semanticsLabel ?? text,
        );
      },
    );
  }
}
