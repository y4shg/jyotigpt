import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'theme_extensions.dart';
import 'color_palettes.dart';
import 'color_tokens.dart';

class AppTheme {
  // Enhanced neutral palette for better contrast (WCAG AA compliant)
  static const Color neutral900 = Color(0xFF0B0E14);
  static const Color neutral800 = Color(0xFF161B24);
  static const Color neutral700 = Color(0xFF1F2531);
  static const Color neutral600 = Color(0xFF343C4D);
  static const Color neutral500 = Color(0xFF4A5161);
  static const Color neutral400 = Color(0xFF9099AC);
  static const Color neutral300 = Color(0xFFC5CCD9);
  static const Color neutral200 = Color(0xFFE6EAF1);
  static const Color neutral100 = Color(0xFFF5F7FA);
  static const Color neutral50 = Color(0xFFFFFFFF);

  // Semantic colors derived from the token specification
  static const Color error = Color(0xFFCE2C31);
  static const Color errorDark = Color(0xFFFF5F67);
  static const Color success = Color(0xFF0E9D58);
  static const Color successDark = Color(0xFF23C179);
  static const Color warning = Color(0xFFDB7900);
  static const Color warningDark = Color(0xFFFF9800);
  static const Color info = Color(0xFF0174D3);
  static const Color infoDark = Color(0xFF4CA8FF);

  static ThemeData light(AppColorPalette palette) {
    final lightTone = palette.light;
    final tokens = AppColorTokens.light(palette: palette);
    final colorScheme = tokens.toColorScheme().copyWith(
      primary: lightTone.primary,
      onPrimary: _pickOnColor(lightTone.primary, tokens),
      secondary: lightTone.secondary,
      onSecondary: _pickOnColor(lightTone.secondary, tokens),
      tertiary: lightTone.accent,
      onTertiary: _pickOnColor(lightTone.accent, tokens),
      surfaceTint: lightTone.primary,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: colorScheme,
      pageTransitionsTheme: _pageTransitionsTheme,
      splashFactory: NoSplash.splashFactory,
      scaffoldBackgroundColor: tokens.neutralTone10,
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: Elevation.none,
        backgroundColor: Colors.transparent,
        foregroundColor: tokens.neutralOnSurface,
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: tokens.neutralTone00,
        modalBackgroundColor: tokens.neutralTone00,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.modal),
        ),
        showDragHandle: false,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.lg,
            vertical: Spacing.xs,
          ),
          backgroundColor: lightTone.primary,
          foregroundColor: _pickOnColor(lightTone.primary, tokens),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppBorderRadius.md),
          ),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: Elevation.none,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.lg),
          side: BorderSide(color: tokens.neutralTone20),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: Color.alphaBlend(
          tokens.overlayStrong,
          tokens.neutralOnSurface,
        ),
        contentTextStyle: TextStyle(
          color: tokens.neutralTone00,
          fontSize: AppTypography.bodyMedium,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.snackbar),
        ),
        elevation: Elevation.high,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: tokens.neutralTone00,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          borderSide: BorderSide(color: lightTone.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          borderSide: BorderSide(color: tokens.statusError60, width: 1),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: Spacing.md,
          vertical: Spacing.sm,
        ),
      ),
      textTheme: ThemeData.light().textTheme,
      extensions: <ThemeExtension<dynamic>>[
        tokens,
        JyotiGPTThemeExtension.lightPalette(palette: palette, tokens: tokens),
        AppPaletteThemeExtension(palette: palette),
      ],
    );
  }

  static ThemeData dark(AppColorPalette palette) {
    final darkTone = palette.dark;
    final tokens = AppColorTokens.dark(palette: palette);
    final colorScheme = tokens.toColorScheme().copyWith(
      primary: darkTone.primary,
      onPrimary: _pickOnColor(darkTone.primary, tokens),
      secondary: darkTone.secondary,
      onSecondary: _pickOnColor(darkTone.secondary, tokens),
      tertiary: darkTone.accent,
      onTertiary: _pickOnColor(darkTone.accent, tokens),
      surfaceTint: darkTone.primary,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: tokens.neutralTone10,
      pageTransitionsTheme: _pageTransitionsTheme,
      splashFactory: NoSplash.splashFactory,
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: Elevation.none,
        backgroundColor: Colors.transparent,
        foregroundColor: tokens.neutralOnSurface,
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: tokens.neutralTone00,
        modalBackgroundColor: tokens.neutralTone00,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.modal),
        ),
        showDragHandle: false,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.lg,
            vertical: Spacing.xs,
          ),
          backgroundColor: darkTone.primary,
          foregroundColor: _pickOnColor(darkTone.primary, tokens),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppBorderRadius.md),
          ),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: Elevation.none,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.lg),
          side: BorderSide(color: tokens.neutralTone40),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: Color.alphaBlend(
          tokens.overlayStrong,
          tokens.neutralTone20,
        ),
        contentTextStyle: TextStyle(
          color: tokens.neutralOnSurface,
          fontSize: AppTypography.bodyMedium,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.snackbar),
        ),
        elevation: Elevation.high,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: tokens.neutralTone20,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          borderSide: BorderSide(color: tokens.neutralTone40, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          borderSide: BorderSide(color: tokens.neutralTone40, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          borderSide: BorderSide(color: darkTone.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
          borderSide: BorderSide(color: tokens.statusError60, width: 1),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: Spacing.md,
          vertical: Spacing.sm,
        ),
      ),
      textTheme: ThemeData.dark().textTheme,
      extensions: <ThemeExtension<dynamic>>[
        tokens,
        JyotiGPTThemeExtension.darkPalette(palette: palette, tokens: tokens),
        AppPaletteThemeExtension(palette: palette),
      ],
    );
  }

  static CupertinoThemeData cupertinoTheme(
    BuildContext context,
    AppColorPalette palette,
  ) {
    final brightness = Theme.of(context).brightness;
    final tone = palette.toneFor(brightness);
    final tokens = brightness == Brightness.dark
        ? AppColorTokens.dark(palette: palette)
        : AppColorTokens.light(palette: palette);
    return CupertinoThemeData(
      brightness: brightness,
      primaryColor: tone.primary,
      scaffoldBackgroundColor: tokens.neutralTone10,
      barBackgroundColor: tokens.neutralTone10,
    );
  }

  static Color _pickOnColor(Color background, AppColorTokens tokens) {
    final contrastOnLight = _contrastRatio(background, tokens.neutralTone00);
    final contrastOnDark = _contrastRatio(background, tokens.neutralOnSurface);
    return contrastOnLight >= contrastOnDark
        ? tokens.neutralTone00
        : tokens.neutralOnSurface;
  }

  static double _contrastRatio(Color a, Color b) {
    final luminanceA = a.computeLuminance();
    final luminanceB = b.computeLuminance();
    final lighter = math.max(luminanceA, luminanceB);
    final darker = math.min(luminanceA, luminanceB);
    return (lighter + 0.05) / (darker + 0.05);
  }

  static const PageTransitionsTheme _pageTransitionsTheme =
      PageTransitionsTheme(
        builders: <TargetPlatform, PageTransitionsBuilder>{
          TargetPlatform.android: ZoomPageTransitionsBuilder(),
          TargetPlatform.iOS: ZoomPageTransitionsBuilder(),
          TargetPlatform.linux: ZoomPageTransitionsBuilder(),
          TargetPlatform.macOS: ZoomPageTransitionsBuilder(),
          TargetPlatform.windows: ZoomPageTransitionsBuilder(),
        },
      );
}

/// Animated theme wrapper for smooth theme transitions
class AnimatedThemeWrapper extends StatefulWidget {
  final Widget child;
  final ThemeData theme;
  final Duration duration;

  const AnimatedThemeWrapper({
    super.key,
    required this.child,
    required this.theme,
    this.duration = const Duration(milliseconds: 250),
  });

  @override
  State<AnimatedThemeWrapper> createState() => _AnimatedThemeWrapperState();
}

class _AnimatedThemeWrapperState extends State<AnimatedThemeWrapper>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;
  ThemeData? _previousTheme;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(duration: widget.duration, vsync: this);
    _animation = CurvedAnimation(parent: _controller, curve: Curves.easeInOut);
    _previousTheme = widget.theme;
  }

  @override
  void didUpdateWidget(AnimatedThemeWrapper oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.theme != widget.theme) {
      _previousTheme = oldWidget.theme;
      _controller.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  void deactivate() {
    // Pause animations during deactivation to avoid rebuilds in wrong build scope
    _controller.stop();
    super.deactivate();
  }

  @override
  void activate() {
    super.activate();
    // If a theme transition was in progress, resume it
    if (_controller.value < 1.0 && !_controller.isAnimating) {
      _controller.forward();
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Theme(
          data: ThemeData.lerp(
            _previousTheme ?? widget.theme,
            widget.theme,
            _animation.value,
          ),
          child: widget.child,
        );
      },
    );
  }
}

/// Theme transition widget for individual components
class ThemeTransition extends StatelessWidget {
  final Widget child;
  final Duration duration;

  const ThemeTransition({
    super.key,
    required this.child,
    this.duration = const Duration(milliseconds: 200),
  });

  @override
  Widget build(BuildContext context) {
    return child.animate().fadeIn(duration: duration);
  }
}

// Typography, spacing, and design token classes are now in theme_extensions.dart for consistency
