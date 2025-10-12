import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'color_palettes.dart';

/// Immutable set of semantic color tokens exposed through [ThemeExtension].
///
/// The tokens are derived from the JyotiGPT color specification and provide
/// consistent mappings for light and dark modes. Widgets should prefer using
/// these tokens instead of hard-coded color values to ensure theme parity and
/// accessible contrast levels.
@immutable
class AppColorTokens extends ThemeExtension<AppColorTokens> {
  const AppColorTokens({
    required this.brightness,
    required this.neutralTone00,
    required this.neutralTone10,
    required this.neutralTone20,
    required this.neutralTone40,
    required this.neutralTone60,
    required this.neutralTone80,
    required this.neutralOnSurface,
    required this.brandTone40,
    required this.brandTone60,
    required this.brandOn60,
    required this.brandTone90,
    required this.brandOn90,
    required this.accentIndigo60,
    required this.accentOnIndigo60,
    required this.accentTeal60,
    required this.accentGold60,
    required this.statusSuccess60,
    required this.statusOnSuccess60,
    required this.statusWarning60,
    required this.statusOnWarning60,
    required this.statusError60,
    required this.statusOnError60,
    required this.statusInfo60,
    required this.statusOnInfo60,
    required this.overlayWeak,
    required this.overlayMedium,
    required this.overlayStrong,
    required this.codeBackground,
    required this.codeBorder,
    required this.codeText,
    required this.codeAccent,
  });

  final Brightness brightness;

  // Neutral tokens
  final Color neutralTone00;
  final Color neutralTone10;
  final Color neutralTone20;
  final Color neutralTone40;
  final Color neutralTone60;
  final Color neutralTone80;
  final Color neutralOnSurface;

  // Brand tokens
  final Color brandTone40;
  final Color brandTone60;
  final Color brandOn60;
  final Color brandTone90;
  final Color brandOn90;

  // Accent tokens
  final Color accentIndigo60;
  final Color accentOnIndigo60;
  final Color accentTeal60;
  final Color accentGold60;

  // Status tokens
  final Color statusSuccess60;
  final Color statusOnSuccess60;
  final Color statusWarning60;
  final Color statusOnWarning60;
  final Color statusError60;
  final Color statusOnError60;
  final Color statusInfo60;
  final Color statusOnInfo60;

  // Overlay tokens
  final Color overlayWeak;
  final Color overlayMedium;
  final Color overlayStrong;

  // Markdown/code tokens
  final Color codeBackground;
  final Color codeBorder;
  final Color codeText;
  final Color codeAccent;

  factory AppColorTokens.light({AppColorPalette? palette}) {
    return AppColorTokens._fromPalette(
      palette ?? AppColorPalettes.innerFire,
      Brightness.light,
    );
  }

  factory AppColorTokens.dark({AppColorPalette? palette}) {
    return AppColorTokens._fromPalette(
      palette ?? AppColorPalettes.innerFire,
      Brightness.dark,
    );
  }

  factory AppColorTokens._fromPalette(
    AppColorPalette palette,
    Brightness brightness,
  ) {
    final AppPaletteTone tone = palette.toneFor(brightness);

    final bool isLight = brightness == Brightness.light;

    final Color neutralTone00 = isLight
        ? const Color(0xFFFFFFFF)
        : const Color(0xFF0B0E14);
    final Color neutralTone10 = isLight
        ? const Color(0xFFF5F7FA)
        : const Color(0xFF161B24);
    final Color neutralTone20 = isLight
        ? const Color(0xFFE6EAF1)
        : const Color(0xFF1F2531);
    final Color neutralTone40 = isLight
        ? const Color(0xFFC5CCD9)
        : const Color(0xFF343C4D);
    final Color neutralTone60 = isLight
        ? const Color(0xFF9099AC)
        : const Color(0xFF4C566A);
    final Color neutralTone80 = isLight
        ? const Color(0xFF4A5161)
        : const Color(0xFF8B95AA);
    final Color neutralOnSurface = isLight
        ? const Color(0xFF151920)
        : const Color(0xFFE8ECF5);

    final Color overlayWeak = isLight
        ? const Color.fromRGBO(21, 25, 32, 0.08)
        : const Color.fromRGBO(232, 236, 245, 0.08);
    final Color overlayMedium = isLight
        ? const Color.fromRGBO(21, 25, 32, 0.16)
        : const Color.fromRGBO(232, 236, 245, 0.16);
    final Color overlayStrong = isLight
        ? const Color.fromRGBO(21, 25, 32, 0.32)
        : const Color.fromRGBO(232, 236, 245, 0.48);

    final ColorScheme seedScheme = ColorScheme.fromSeed(
      seedColor: tone.primary,
      brightness: brightness,
    );

    final Color brandTone60 = seedScheme.primary;
    final Color brandOn60 = _preferredOnColor(
      background: brandTone60,
      light: neutralTone00,
      dark: neutralOnSurface,
    );

    final Color brandTone90 = seedScheme.primaryContainer;
    final Color brandOn90 = _preferredOnColor(
      background: brandTone90,
      light: neutralTone00,
      dark: neutralOnSurface,
    );

    final double brandShift = isLight ? 0.18 : -0.14;
    final Color brandTone40 = _shiftLightness(brandTone60, brandShift);

    final Color accentIndigo60 = tone.secondary;
    final Color accentOnIndigo60 = _preferredOnColor(
      background: accentIndigo60,
      light: neutralTone00,
      dark: neutralOnSurface,
    );

    final Color accentTeal60 = tone.accent;
    final Color accentGold60 = isLight
        ? const Color(0xFFFFB54A)
        : const Color(0xFFFFC266);

    final Color statusSuccess60 = isLight
        ? const Color(0xFF0E9D58)
        : const Color(0xFF23C179);
    final Color statusOnSuccess60 = _preferredOnColor(
      background: statusSuccess60,
      light: neutralTone00,
      dark: neutralOnSurface,
    );

    final Color statusWarning60 = isLight
        ? const Color(0xFFDB7900)
        : const Color(0xFFFF9800);
    final Color statusOnWarning60 = _preferredOnColor(
      background: statusWarning60,
      light: neutralTone00,
      dark: neutralOnSurface,
    );

    final Color statusError60 = isLight
        ? const Color(0xFFCE2C31)
        : const Color(0xFFFF5F67);
    final Color statusOnError60 = _preferredOnColor(
      background: statusError60,
      light: neutralTone00,
      dark: neutralOnSurface,
    );

    final Color statusInfo60 = isLight
        ? const Color(0xFF0174D3)
        : const Color(0xFF4CA8FF);
    final Color statusOnInfo60 = _preferredOnColor(
      background: statusInfo60,
      light: neutralTone00,
      dark: neutralOnSurface,
    );

    final Color codeBackground = isLight ? neutralTone10 : neutralTone00;
    final Color codeBorder = isLight ? neutralTone20 : neutralTone40;
    final Color codeText = neutralOnSurface;
    final Color codeAccent = isLight
        ? Color.alphaBlend(brandTone60.withValues(alpha: 0.14), codeBackground)
        : Color.alphaBlend(brandTone40.withValues(alpha: 0.24), codeBackground);

    return AppColorTokens(
      brightness: brightness,
      neutralTone00: neutralTone00,
      neutralTone10: neutralTone10,
      neutralTone20: neutralTone20,
      neutralTone40: neutralTone40,
      neutralTone60: neutralTone60,
      neutralTone80: neutralTone80,
      neutralOnSurface: neutralOnSurface,
      brandTone40: brandTone40,
      brandTone60: brandTone60,
      brandOn60: brandOn60,
      brandTone90: brandTone90,
      brandOn90: brandOn90,
      accentIndigo60: accentIndigo60,
      accentOnIndigo60: accentOnIndigo60,
      accentTeal60: accentTeal60,
      accentGold60: accentGold60,
      statusSuccess60: statusSuccess60,
      statusOnSuccess60: statusOnSuccess60,
      statusWarning60: statusWarning60,
      statusOnWarning60: statusOnWarning60,
      statusError60: statusError60,
      statusOnError60: statusOnError60,
      statusInfo60: statusInfo60,
      statusOnInfo60: statusOnInfo60,
      overlayWeak: overlayWeak,
      overlayMedium: overlayMedium,
      overlayStrong: overlayStrong,
      codeBackground: codeBackground,
      codeBorder: codeBorder,
      codeText: codeText,
      codeAccent: codeAccent,
    );
  }

  @override
  AppColorTokens copyWith({
    Brightness? brightness,
    Color? neutralTone00,
    Color? neutralTone10,
    Color? neutralTone20,
    Color? neutralTone40,
    Color? neutralTone60,
    Color? neutralTone80,
    Color? neutralOnSurface,
    Color? brandTone40,
    Color? brandTone60,
    Color? brandOn60,
    Color? brandTone90,
    Color? brandOn90,
    Color? accentIndigo60,
    Color? accentOnIndigo60,
    Color? accentTeal60,
    Color? accentGold60,
    Color? statusSuccess60,
    Color? statusOnSuccess60,
    Color? statusWarning60,
    Color? statusOnWarning60,
    Color? statusError60,
    Color? statusOnError60,
    Color? statusInfo60,
    Color? statusOnInfo60,
    Color? overlayWeak,
    Color? overlayMedium,
    Color? overlayStrong,
    Color? codeBackground,
    Color? codeBorder,
    Color? codeText,
    Color? codeAccent,
  }) {
    return AppColorTokens(
      brightness: brightness ?? this.brightness,
      neutralTone00: neutralTone00 ?? this.neutralTone00,
      neutralTone10: neutralTone10 ?? this.neutralTone10,
      neutralTone20: neutralTone20 ?? this.neutralTone20,
      neutralTone40: neutralTone40 ?? this.neutralTone40,
      neutralTone60: neutralTone60 ?? this.neutralTone60,
      neutralTone80: neutralTone80 ?? this.neutralTone80,
      neutralOnSurface: neutralOnSurface ?? this.neutralOnSurface,
      brandTone40: brandTone40 ?? this.brandTone40,
      brandTone60: brandTone60 ?? this.brandTone60,
      brandOn60: brandOn60 ?? this.brandOn60,
      brandTone90: brandTone90 ?? this.brandTone90,
      brandOn90: brandOn90 ?? this.brandOn90,
      accentIndigo60: accentIndigo60 ?? this.accentIndigo60,
      accentOnIndigo60: accentOnIndigo60 ?? this.accentOnIndigo60,
      accentTeal60: accentTeal60 ?? this.accentTeal60,
      accentGold60: accentGold60 ?? this.accentGold60,
      statusSuccess60: statusSuccess60 ?? this.statusSuccess60,
      statusOnSuccess60: statusOnSuccess60 ?? this.statusOnSuccess60,
      statusWarning60: statusWarning60 ?? this.statusWarning60,
      statusOnWarning60: statusOnWarning60 ?? this.statusOnWarning60,
      statusError60: statusError60 ?? this.statusError60,
      statusOnError60: statusOnError60 ?? this.statusOnError60,
      statusInfo60: statusInfo60 ?? this.statusInfo60,
      statusOnInfo60: statusOnInfo60 ?? this.statusOnInfo60,
      overlayWeak: overlayWeak ?? this.overlayWeak,
      overlayMedium: overlayMedium ?? this.overlayMedium,
      overlayStrong: overlayStrong ?? this.overlayStrong,
      codeBackground: codeBackground ?? this.codeBackground,
      codeBorder: codeBorder ?? this.codeBorder,
      codeText: codeText ?? this.codeText,
      codeAccent: codeAccent ?? this.codeAccent,
    );
  }

  @override
  AppColorTokens lerp(
    covariant ThemeExtension<AppColorTokens>? other,
    double t,
  ) {
    if (other is! AppColorTokens) {
      return this;
    }

    return AppColorTokens(
      brightness: t < 0.5 ? brightness : other.brightness,
      neutralTone00: Color.lerp(neutralTone00, other.neutralTone00, t)!,
      neutralTone10: Color.lerp(neutralTone10, other.neutralTone10, t)!,
      neutralTone20: Color.lerp(neutralTone20, other.neutralTone20, t)!,
      neutralTone40: Color.lerp(neutralTone40, other.neutralTone40, t)!,
      neutralTone60: Color.lerp(neutralTone60, other.neutralTone60, t)!,
      neutralTone80: Color.lerp(neutralTone80, other.neutralTone80, t)!,
      neutralOnSurface: Color.lerp(
        neutralOnSurface,
        other.neutralOnSurface,
        t,
      )!,
      brandTone40: Color.lerp(brandTone40, other.brandTone40, t)!,
      brandTone60: Color.lerp(brandTone60, other.brandTone60, t)!,
      brandOn60: Color.lerp(brandOn60, other.brandOn60, t)!,
      brandTone90: Color.lerp(brandTone90, other.brandTone90, t)!,
      brandOn90: Color.lerp(brandOn90, other.brandOn90, t)!,
      accentIndigo60: Color.lerp(accentIndigo60, other.accentIndigo60, t)!,
      accentOnIndigo60: Color.lerp(
        accentOnIndigo60,
        other.accentOnIndigo60,
        t,
      )!,
      accentTeal60: Color.lerp(accentTeal60, other.accentTeal60, t)!,
      accentGold60: Color.lerp(accentGold60, other.accentGold60, t)!,
      statusSuccess60: Color.lerp(statusSuccess60, other.statusSuccess60, t)!,
      statusOnSuccess60: Color.lerp(
        statusOnSuccess60,
        other.statusOnSuccess60,
        t,
      )!,
      statusWarning60: Color.lerp(statusWarning60, other.statusWarning60, t)!,
      statusOnWarning60: Color.lerp(
        statusOnWarning60,
        other.statusOnWarning60,
        t,
      )!,
      statusError60: Color.lerp(statusError60, other.statusError60, t)!,
      statusOnError60: Color.lerp(statusOnError60, other.statusOnError60, t)!,
      statusInfo60: Color.lerp(statusInfo60, other.statusInfo60, t)!,
      statusOnInfo60: Color.lerp(statusOnInfo60, other.statusOnInfo60, t)!,
      overlayWeak: Color.lerp(overlayWeak, other.overlayWeak, t)!,
      overlayMedium: Color.lerp(overlayMedium, other.overlayMedium, t)!,
      overlayStrong: Color.lerp(overlayStrong, other.overlayStrong, t)!,
      codeBackground: Color.lerp(codeBackground, other.codeBackground, t)!,
      codeBorder: Color.lerp(codeBorder, other.codeBorder, t)!,
      codeText: Color.lerp(codeText, other.codeText, t)!,
      codeAccent: Color.lerp(codeAccent, other.codeAccent, t)!,
    );
  }

  /// Generates a Material [ColorScheme] that aligns with the defined tokens.
  ColorScheme toColorScheme() {
    final base = ColorScheme.fromSeed(
      seedColor: brandTone60,
      brightness: brightness,
    );

    return base.copyWith(
      primary: brandTone60,
      onPrimary: brandOn60,
      primaryContainer: brandTone90,
      onPrimaryContainer: brandOn90,
      secondary: accentIndigo60,
      onSecondary: accentOnIndigo60,
      tertiary: accentTeal60,
      onTertiary: neutralTone00,
      surface: neutralTone00,
      surfaceContainerLow: neutralTone10,
      surfaceContainerHighest: neutralTone20,
      onSurface: neutralOnSurface,
      onSurfaceVariant: neutralTone80,
      outline: neutralTone60,
      outlineVariant: neutralTone40,
      error: statusError60,
      onError: statusOnError60,
      surfaceTint: brandTone40,
      scrim: overlayStrong,
    );
  }

  /// Convenience helper to composite an overlay on top of the correct surface.
  Color overlayOnSurface(Color overlay, {Color? surface}) {
    final baseSurface = surface ?? neutralTone00;
    return Color.alphaBlend(overlay, baseSurface);
  }

  static AppColorTokens fallback({Brightness brightness = Brightness.light}) {
    return brightness == Brightness.dark
        ? AppColorTokens.dark()
        : AppColorTokens.light();
  }

  static Color _shiftLightness(Color color, double amount) {
    final HSLColor hsl = HSLColor.fromColor(color);
    final double lightness = (hsl.lightness + amount).clamp(0.0, 1.0);
    return hsl.withLightness(lightness).toColor();
  }

  static Color _preferredOnColor({
    required Color background,
    required Color light,
    required Color dark,
  }) {
    final double lightContrast = _contrastRatio(background, light);
    final double darkContrast = _contrastRatio(background, dark);
    return lightContrast >= darkContrast ? light : dark;
  }

  static double _contrastRatio(Color a, Color b) {
    final double luminanceA = a.computeLuminance();
    final double luminanceB = b.computeLuminance();
    final double lighter = math.max(luminanceA, luminanceB);
    final double darker = math.min(luminanceA, luminanceB);
    return (lighter + 0.05) / (darker + 0.05);
  }
}
