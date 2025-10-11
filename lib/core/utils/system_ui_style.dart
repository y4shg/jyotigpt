import 'package:flutter/services.dart';

/// Applies a single System UI overlay style after first frame to avoid flicker
/// at startup and to align with the active theme brightness.
void applySystemUiOverlayStyleOnce({required Brightness brightness}) {
  // On Android 15+, avoid setting bar colors; only control icon brightness.
  final isDark = brightness == Brightness.dark;
  SystemChrome.setSystemUIOverlayStyle(
    SystemUiOverlayStyle(
      statusBarIconBrightness: isDark ? Brightness.light : Brightness.dark,
      systemNavigationBarIconBrightness: isDark
          ? Brightness.light
          : Brightness.dark,
    ),
  );
}
