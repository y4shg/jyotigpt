import 'dart:math' as math;

import 'package:flutter/material.dart';
// Using system fonts; no GoogleFonts dependency required
import 'color_palettes.dart';
import 'color_tokens.dart';

/// Extended theme data for consistent styling across the app
@immutable
class JyotiGPTThemeExtension extends ThemeExtension<JyotiGPTThemeExtension> {
  // Chat-specific colors
  final Color chatBubbleUser;
  final Color chatBubbleAssistant;
  final Color chatBubbleUserText;
  final Color chatBubbleAssistantText;
  final Color chatBubbleUserBorder;
  final Color chatBubbleAssistantBorder;

  // Input and form colors
  final Color inputBackground;
  final Color inputBorder;
  final Color inputBorderFocused;
  final Color inputText;
  final Color inputPlaceholder;
  final Color inputError;

  // Card and surface colors
  final Color cardBackground;
  final Color cardBorder;
  final Color cardShadow;
  final Color surfaceBackground;
  final Color surfaceContainer;
  final Color surfaceContainerHighest;

  // Interactive element colors
  final Color buttonPrimary;
  final Color buttonPrimaryText;
  final Color buttonSecondary;
  final Color buttonSecondaryText;
  final Color buttonDisabled;
  final Color buttonDisabledText;

  // Status and feedback colors
  final Color success;
  final Color successBackground;
  final Color error;
  final Color errorBackground;
  final Color warning;
  final Color warningBackground;
  final Color info;
  final Color infoBackground;

  // Navigation and UI element colors
  final Color dividerColor;
  final Color navigationBackground;
  final Color navigationSelected;
  final Color navigationUnselected;
  final Color navigationSelectedBackground;

  // Loading and animation colors
  final Color shimmerBase;
  final Color shimmerHighlight;
  final Color loadingIndicator;

  // Markdown/code colors
  final Color codeBackground;
  final Color codeBorder;
  final Color codeText;
  final Color codeAccent;

  // Text colors
  final Color textPrimary;
  final Color textSecondary;
  final Color textTertiary;
  final Color textInverse;
  final Color textDisabled;

  // Icon colors
  final Color iconPrimary;
  final Color iconSecondary;
  final Color iconDisabled;
  final Color iconInverse;

  // Typography styles
  final TextStyle? headingLarge;
  final TextStyle? headingMedium;
  final TextStyle? headingSmall;
  final TextStyle? bodyLarge;
  final TextStyle? bodyMedium;
  final TextStyle? bodySmall;
  final TextStyle? caption;
  final TextStyle? label;
  final TextStyle? code;

  const JyotiGPTThemeExtension({
    // Chat-specific colors
    required this.chatBubbleUser,
    required this.chatBubbleAssistant,
    required this.chatBubbleUserText,
    required this.chatBubbleAssistantText,
    required this.chatBubbleUserBorder,
    required this.chatBubbleAssistantBorder,

    // Input and form colors
    required this.inputBackground,
    required this.inputBorder,
    required this.inputBorderFocused,
    required this.inputText,
    required this.inputPlaceholder,
    required this.inputError,

    // Card and surface colors
    required this.cardBackground,
    required this.cardBorder,
    required this.cardShadow,
    required this.surfaceBackground,
    required this.surfaceContainer,
    required this.surfaceContainerHighest,

    // Interactive element colors
    required this.buttonPrimary,
    required this.buttonPrimaryText,
    required this.buttonSecondary,
    required this.buttonSecondaryText,
    required this.buttonDisabled,
    required this.buttonDisabledText,

    // Status and feedback colors
    required this.success,
    required this.successBackground,
    required this.error,
    required this.errorBackground,
    required this.warning,
    required this.warningBackground,
    required this.info,
    required this.infoBackground,

    // Navigation and UI element colors
    required this.dividerColor,
    required this.navigationBackground,
    required this.navigationSelected,
    required this.navigationUnselected,
    required this.navigationSelectedBackground,

    // Loading and animation colors
    required this.shimmerBase,
    required this.shimmerHighlight,
    required this.loadingIndicator,

    // Markdown/code colors
    required this.codeBackground,
    required this.codeBorder,
    required this.codeText,
    required this.codeAccent,

    // Text colors
    required this.textPrimary,
    required this.textSecondary,
    required this.textTertiary,
    required this.textInverse,
    required this.textDisabled,

    // Icon colors
    required this.iconPrimary,
    required this.iconSecondary,
    required this.iconDisabled,
    required this.iconInverse,

    // Typography styles
    this.headingLarge,
    this.headingMedium,
    this.headingSmall,
    this.bodyLarge,
    this.bodyMedium,
    this.bodySmall,
    this.caption,
    this.label,
    this.code,
  });

  @override
  JyotiGPTThemeExtension copyWith({
    // Chat-specific colors
    Color? chatBubbleUser,
    Color? chatBubbleAssistant,
    Color? chatBubbleUserText,
    Color? chatBubbleAssistantText,
    Color? chatBubbleUserBorder,
    Color? chatBubbleAssistantBorder,

    // Input and form colors
    Color? inputBackground,
    Color? inputBorder,
    Color? inputBorderFocused,
    Color? inputText,
    Color? inputPlaceholder,
    Color? inputError,

    // Card and surface colors
    Color? cardBackground,
    Color? cardBorder,
    Color? cardShadow,
    Color? surfaceBackground,
    Color? surfaceContainer,
    Color? surfaceContainerHighest,

    // Interactive element colors
    Color? buttonPrimary,
    Color? buttonPrimaryText,
    Color? buttonSecondary,
    Color? buttonSecondaryText,
    Color? buttonDisabled,
    Color? buttonDisabledText,

    // Status and feedback colors
    Color? success,
    Color? successBackground,
    Color? error,
    Color? errorBackground,
    Color? warning,
    Color? warningBackground,
    Color? info,
    Color? infoBackground,

    // Navigation and UI element colors
    Color? dividerColor,
    Color? navigationBackground,
    Color? navigationSelected,
    Color? navigationUnselected,
    Color? navigationSelectedBackground,

    // Loading and animation colors
    Color? shimmerBase,
    Color? shimmerHighlight,
    Color? loadingIndicator,

    // Markdown/code colors
    Color? codeBackground,
    Color? codeBorder,
    Color? codeText,
    Color? codeAccent,

    // Text colors
    Color? textPrimary,
    Color? textSecondary,
    Color? textTertiary,
    Color? textInverse,
    Color? textDisabled,

    // Icon colors
    Color? iconPrimary,
    Color? iconSecondary,
    Color? iconDisabled,
    Color? iconInverse,

    // Typography styles
    TextStyle? headingLarge,
    TextStyle? headingMedium,
    TextStyle? headingSmall,
    TextStyle? bodyLarge,
    TextStyle? bodyMedium,
    TextStyle? bodySmall,
    TextStyle? caption,
    TextStyle? label,
    TextStyle? code,
  }) {
    return JyotiGPTThemeExtension(
      // Chat-specific colors
      chatBubbleUser: chatBubbleUser ?? this.chatBubbleUser,
      chatBubbleAssistant: chatBubbleAssistant ?? this.chatBubbleAssistant,
      chatBubbleUserText: chatBubbleUserText ?? this.chatBubbleUserText,
      chatBubbleAssistantText:
          chatBubbleAssistantText ?? this.chatBubbleAssistantText,
      chatBubbleUserBorder: chatBubbleUserBorder ?? this.chatBubbleUserBorder,
      chatBubbleAssistantBorder:
          chatBubbleAssistantBorder ?? this.chatBubbleAssistantBorder,

      // Input and form colors
      inputBackground: inputBackground ?? this.inputBackground,
      inputBorder: inputBorder ?? this.inputBorder,
      inputBorderFocused: inputBorderFocused ?? this.inputBorderFocused,
      inputText: inputText ?? this.inputText,
      inputPlaceholder: inputPlaceholder ?? this.inputPlaceholder,
      inputError: inputError ?? this.inputError,

      // Card and surface colors
      cardBackground: cardBackground ?? this.cardBackground,
      cardBorder: cardBorder ?? this.cardBorder,
      cardShadow: cardShadow ?? this.cardShadow,
      surfaceBackground: surfaceBackground ?? this.surfaceBackground,
      surfaceContainer: surfaceContainer ?? this.surfaceContainer,
      surfaceContainerHighest:
          surfaceContainerHighest ?? this.surfaceContainerHighest,

      // Interactive element colors
      buttonPrimary: buttonPrimary ?? this.buttonPrimary,
      buttonPrimaryText: buttonPrimaryText ?? this.buttonPrimaryText,
      buttonSecondary: buttonSecondary ?? this.buttonSecondary,
      buttonSecondaryText: buttonSecondaryText ?? this.buttonSecondaryText,
      buttonDisabled: buttonDisabled ?? this.buttonDisabled,
      buttonDisabledText: buttonDisabledText ?? this.buttonDisabledText,

      // Status and feedback colors
      success: success ?? this.success,
      successBackground: successBackground ?? this.successBackground,
      error: error ?? this.error,
      errorBackground: errorBackground ?? this.errorBackground,
      warning: warning ?? this.warning,
      warningBackground: warningBackground ?? this.warningBackground,
      info: info ?? this.info,
      infoBackground: infoBackground ?? this.infoBackground,

      // Navigation and UI element colors
      dividerColor: dividerColor ?? this.dividerColor,
      navigationBackground: navigationBackground ?? this.navigationBackground,
      navigationSelected: navigationSelected ?? this.navigationSelected,
      navigationUnselected: navigationUnselected ?? this.navigationUnselected,
      navigationSelectedBackground:
          navigationSelectedBackground ?? this.navigationSelectedBackground,

      // Loading and animation colors
      shimmerBase: shimmerBase ?? this.shimmerBase,
      shimmerHighlight: shimmerHighlight ?? this.shimmerHighlight,
      loadingIndicator: loadingIndicator ?? this.loadingIndicator,

      // Markdown/code colors
      codeBackground: codeBackground ?? this.codeBackground,
      codeBorder: codeBorder ?? this.codeBorder,
      codeText: codeText ?? this.codeText,
      codeAccent: codeAccent ?? this.codeAccent,

      // Text colors
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textTertiary: textTertiary ?? this.textTertiary,
      textInverse: textInverse ?? this.textInverse,
      textDisabled: textDisabled ?? this.textDisabled,

      // Icon colors
      iconPrimary: iconPrimary ?? this.iconPrimary,
      iconSecondary: iconSecondary ?? this.iconSecondary,
      iconDisabled: iconDisabled ?? this.iconDisabled,
      iconInverse: iconInverse ?? this.iconInverse,

      // Typography styles
      headingLarge: headingLarge ?? this.headingLarge,
      headingMedium: headingMedium ?? this.headingMedium,
      headingSmall: headingSmall ?? this.headingSmall,
      bodyLarge: bodyLarge ?? this.bodyLarge,
      bodyMedium: bodyMedium ?? this.bodyMedium,
      bodySmall: bodySmall ?? this.bodySmall,
      caption: caption ?? this.caption,
      label: label ?? this.label,
      code: code ?? this.code,
    );
  }

  @override
  JyotiGPTThemeExtension lerp(
    ThemeExtension<JyotiGPTThemeExtension>? other,
    double t,
  ) {
    if (other is! JyotiGPTThemeExtension) {
      return this;
    }
    return JyotiGPTThemeExtension(
      // Chat-specific colors
      chatBubbleUser: Color.lerp(chatBubbleUser, other.chatBubbleUser, t)!,
      chatBubbleAssistant: Color.lerp(
        chatBubbleAssistant,
        other.chatBubbleAssistant,
        t,
      )!,
      chatBubbleUserText: Color.lerp(
        chatBubbleUserText,
        other.chatBubbleUserText,
        t,
      )!,
      chatBubbleAssistantText: Color.lerp(
        chatBubbleAssistantText,
        other.chatBubbleAssistantText,
        t,
      )!,
      chatBubbleUserBorder: Color.lerp(
        chatBubbleUserBorder,
        other.chatBubbleUserBorder,
        t,
      )!,
      chatBubbleAssistantBorder: Color.lerp(
        chatBubbleAssistantBorder,
        other.chatBubbleAssistantBorder,
        t,
      )!,

      // Input and form colors
      inputBackground: Color.lerp(inputBackground, other.inputBackground, t)!,
      inputBorder: Color.lerp(inputBorder, other.inputBorder, t)!,
      inputBorderFocused: Color.lerp(
        inputBorderFocused,
        other.inputBorderFocused,
        t,
      )!,
      inputText: Color.lerp(inputText, other.inputText, t)!,
      inputPlaceholder: Color.lerp(
        inputPlaceholder,
        other.inputPlaceholder,
        t,
      )!,
      inputError: Color.lerp(inputError, other.inputError, t)!,

      // Card and surface colors
      cardBackground: Color.lerp(cardBackground, other.cardBackground, t)!,
      cardBorder: Color.lerp(cardBorder, other.cardBorder, t)!,
      cardShadow: Color.lerp(cardShadow, other.cardShadow, t)!,
      surfaceBackground: Color.lerp(
        surfaceBackground,
        other.surfaceBackground,
        t,
      )!,
      surfaceContainer: Color.lerp(
        surfaceContainer,
        other.surfaceContainer,
        t,
      )!,
      surfaceContainerHighest: Color.lerp(
        surfaceContainerHighest,
        other.surfaceContainerHighest,
        t,
      )!,

      // Interactive element colors
      buttonPrimary: Color.lerp(buttonPrimary, other.buttonPrimary, t)!,
      buttonPrimaryText: Color.lerp(
        buttonPrimaryText,
        other.buttonPrimaryText,
        t,
      )!,
      buttonSecondary: Color.lerp(buttonSecondary, other.buttonSecondary, t)!,
      buttonSecondaryText: Color.lerp(
        buttonSecondaryText,
        other.buttonSecondaryText,
        t,
      )!,
      buttonDisabled: Color.lerp(buttonDisabled, other.buttonDisabled, t)!,
      buttonDisabledText: Color.lerp(
        buttonDisabledText,
        other.buttonDisabledText,
        t,
      )!,

      // Status and feedback colors
      success: Color.lerp(success, other.success, t)!,
      successBackground: Color.lerp(
        successBackground,
        other.successBackground,
        t,
      )!,
      error: Color.lerp(error, other.error, t)!,
      errorBackground: Color.lerp(errorBackground, other.errorBackground, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      warningBackground: Color.lerp(
        warningBackground,
        other.warningBackground,
        t,
      )!,
      info: Color.lerp(info, other.info, t)!,
      infoBackground: Color.lerp(infoBackground, other.infoBackground, t)!,

      // Navigation and UI element colors
      dividerColor: Color.lerp(dividerColor, other.dividerColor, t)!,
      navigationBackground: Color.lerp(
        navigationBackground,
        other.navigationBackground,
        t,
      )!,
      navigationSelected: Color.lerp(
        navigationSelected,
        other.navigationSelected,
        t,
      )!,
      navigationUnselected: Color.lerp(
        navigationUnselected,
        other.navigationUnselected,
        t,
      )!,
      navigationSelectedBackground: Color.lerp(
        navigationSelectedBackground,
        other.navigationSelectedBackground,
        t,
      )!,

      // Loading and animation colors
      shimmerBase: Color.lerp(shimmerBase, other.shimmerBase, t)!,
      shimmerHighlight: Color.lerp(
        shimmerHighlight,
        other.shimmerHighlight,
        t,
      )!,
      loadingIndicator: Color.lerp(
        loadingIndicator,
        other.loadingIndicator,
        t,
      )!,
      codeBackground: Color.lerp(codeBackground, other.codeBackground, t)!,
      codeBorder: Color.lerp(codeBorder, other.codeBorder, t)!,
      codeText: Color.lerp(codeText, other.codeText, t)!,
      codeAccent: Color.lerp(codeAccent, other.codeAccent, t)!,

      // Text colors
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textTertiary: Color.lerp(textTertiary, other.textTertiary, t)!,
      textInverse: Color.lerp(textInverse, other.textInverse, t)!,
      textDisabled: Color.lerp(textDisabled, other.textDisabled, t)!,

      // Icon colors
      iconPrimary: Color.lerp(iconPrimary, other.iconPrimary, t)!,
      iconSecondary: Color.lerp(iconSecondary, other.iconSecondary, t)!,
      iconDisabled: Color.lerp(iconDisabled, other.iconDisabled, t)!,
      iconInverse: Color.lerp(iconInverse, other.iconInverse, t)!,

      // Typography styles
      headingLarge: TextStyle.lerp(headingLarge, other.headingLarge, t),
      headingMedium: TextStyle.lerp(headingMedium, other.headingMedium, t),
      headingSmall: TextStyle.lerp(headingSmall, other.headingSmall, t),
      bodyLarge: TextStyle.lerp(bodyLarge, other.bodyLarge, t),
      bodyMedium: TextStyle.lerp(bodyMedium, other.bodyMedium, t),
      bodySmall: TextStyle.lerp(bodySmall, other.bodySmall, t),
      caption: TextStyle.lerp(caption, other.caption, t),
      label: TextStyle.lerp(label, other.label, t),
      code: TextStyle.lerp(code, other.code, t),
    );
  }

  /// Dark theme extension derived from the active color palette.
  static JyotiGPTThemeExtension darkPalette({
    required AppColorPalette palette,
    required AppColorTokens tokens,
  }) {
    final darkTone = palette.dark;
    final onPrimary = _onSurfaceColor(darkTone.primary, tokens);
    Color blend(Color overlay, {Color? surface}) {
      return Color.alphaBlend(overlay, surface ?? tokens.neutralTone10);
    }

    Color toneBackground(Color tone, {double opacity = 0.24}) {
      return Color.alphaBlend(
        tone.withValues(alpha: opacity),
        tokens.neutralTone10,
      );
    }

    return JyotiGPTThemeExtension(
      chatBubbleUser: darkTone.primary,
      chatBubbleAssistant: tokens.neutralTone20,
      chatBubbleUserText: onPrimary,
      chatBubbleAssistantText: tokens.neutralOnSurface,
      chatBubbleUserBorder: darkTone.secondary,
      chatBubbleAssistantBorder: tokens.neutralTone40,
      inputBackground: tokens.neutralTone20,
      inputBorder: tokens.neutralTone40,
      inputBorderFocused: darkTone.primary,
      inputText: tokens.neutralOnSurface,
      inputPlaceholder: tokens.neutralTone80,
      inputError: tokens.statusError60,
      cardBackground: tokens.neutralTone00,
      cardBorder: tokens.neutralTone40,
      cardShadow: blend(tokens.overlayWeak, surface: tokens.neutralTone00),
      surfaceBackground: tokens.neutralTone10,
      surfaceContainer: tokens.neutralTone00,
      surfaceContainerHighest: tokens.neutralTone20,
      buttonPrimary: darkTone.primary,
      buttonPrimaryText: onPrimary,
      buttonSecondary: tokens.neutralTone20,
      buttonSecondaryText: tokens.neutralOnSurface,
      buttonDisabled: tokens.neutralTone40,
      buttonDisabledText: tokens.neutralTone80,
      success: tokens.statusSuccess60,
      successBackground: toneBackground(tokens.statusSuccess60),
      error: tokens.statusError60,
      errorBackground: toneBackground(tokens.statusError60),
      warning: tokens.statusWarning60,
      warningBackground: toneBackground(tokens.statusWarning60),
      info: tokens.statusInfo60,
      infoBackground: toneBackground(tokens.statusInfo60),
      dividerColor: tokens.neutralTone40,
      navigationBackground: tokens.neutralTone10,
      navigationSelected: darkTone.primary,
      navigationUnselected: tokens.neutralTone80,
      navigationSelectedBackground: blend(
        tokens.overlayMedium,
        surface: tokens.neutralTone10,
      ),
      shimmerBase: blend(tokens.overlayWeak, surface: tokens.neutralTone10),
      shimmerHighlight: blend(
        tokens.overlayMedium,
        surface: tokens.neutralTone20,
      ),
      loadingIndicator: darkTone.primary,
      codeBackground: tokens.codeBackground,
      codeBorder: tokens.codeBorder,
      codeText: tokens.codeText,
      codeAccent: tokens.codeAccent,
      textPrimary: tokens.neutralOnSurface,
      textSecondary: tokens.neutralTone80,
      textTertiary: tokens.neutralTone60,
      textInverse: tokens.neutralTone00,
      textDisabled: tokens.neutralTone40,
      iconPrimary: tokens.neutralOnSurface,
      iconSecondary: tokens.neutralTone80,
      iconDisabled: tokens.neutralTone40,
      iconInverse: tokens.neutralTone00,
      headingLarge: TextStyle(
        fontSize: AppTypography.displaySmall,
        fontWeight: FontWeight.w700,
        color: tokens.neutralOnSurface,
        height: 1.2,
      ),
      headingMedium: TextStyle(
        fontSize: AppTypography.headlineLarge,
        fontWeight: FontWeight.w600,
        color: tokens.neutralOnSurface,
        height: 1.3,
      ),
      headingSmall: TextStyle(
        fontSize: AppTypography.headlineSmall,
        fontWeight: FontWeight.w600,
        color: tokens.neutralOnSurface,
        height: 1.4,
      ),
      bodyLarge: TextStyle(
        fontSize: AppTypography.bodyLarge,
        fontWeight: FontWeight.w400,
        color: tokens.neutralOnSurface,
        height: 1.5,
      ),
      bodyMedium: TextStyle(
        fontSize: AppTypography.bodyMedium,
        fontWeight: FontWeight.w400,
        color: tokens.neutralOnSurface,
        height: 1.5,
      ),
      bodySmall: TextStyle(
        fontSize: AppTypography.bodySmall,
        fontWeight: FontWeight.w400,
        color: tokens.neutralTone80,
        height: 1.4,
      ),
      caption: TextStyle(
        fontSize: AppTypography.labelMedium,
        fontWeight: FontWeight.w500,
        color: tokens.neutralTone80,
        height: 1.3,
        letterSpacing: 0.5,
      ),
      label: TextStyle(
        fontSize: AppTypography.labelLarge,
        fontWeight: FontWeight.w500,
        color: tokens.neutralOnSurface,
        height: 1.3,
      ),
      code: TextStyle(
        fontSize: AppTypography.bodySmall,
        fontWeight: FontWeight.w400,
        color: tokens.neutralOnSurface,
        height: 1.4,
        fontFamily: AppTypography.monospaceFontFamily,
      ),
    );
  }

  /// Light theme extension derived from the active color palette.
  static JyotiGPTThemeExtension lightPalette({
    required AppColorPalette palette,
    required AppColorTokens tokens,
  }) {
    final lightTone = palette.light;
    final darkTone = palette.dark;
    final onPrimary = _onSurfaceColor(lightTone.primary, tokens);
    Color blend(Color overlay, {Color? surface}) {
      return Color.alphaBlend(overlay, surface ?? tokens.neutralTone00);
    }

    Color toneBackground(Color tone, {double opacity = 0.12}) {
      return Color.alphaBlend(
        tone.withValues(alpha: opacity),
        tokens.neutralTone00,
      );
    }

    return JyotiGPTThemeExtension(
      chatBubbleUser: lightTone.primary,
      chatBubbleAssistant: tokens.neutralTone00,
      chatBubbleUserText: onPrimary,
      chatBubbleAssistantText: tokens.neutralOnSurface,
      chatBubbleUserBorder: darkTone.primary,
      chatBubbleAssistantBorder: tokens.neutralTone20,
      inputBackground: tokens.neutralTone00,
      inputBorder: tokens.neutralTone20,
      inputBorderFocused: lightTone.primary,
      inputText: tokens.neutralOnSurface,
      inputPlaceholder: tokens.neutralTone60,
      inputError: tokens.statusError60,
      cardBackground: tokens.neutralTone00,
      cardBorder: tokens.neutralTone20,
      cardShadow: blend(tokens.overlayWeak),
      surfaceBackground: tokens.neutralTone10,
      surfaceContainer: tokens.neutralTone00,
      surfaceContainerHighest: tokens.neutralTone20,
      buttonPrimary: lightTone.primary,
      buttonPrimaryText: onPrimary,
      buttonSecondary: tokens.neutralTone20,
      buttonSecondaryText: tokens.neutralOnSurface,
      buttonDisabled: tokens.neutralTone40,
      buttonDisabledText: tokens.neutralTone60,
      success: tokens.statusSuccess60,
      successBackground: toneBackground(tokens.statusSuccess60),
      error: tokens.statusError60,
      errorBackground: toneBackground(tokens.statusError60),
      warning: tokens.statusWarning60,
      warningBackground: toneBackground(tokens.statusWarning60),
      info: tokens.statusInfo60,
      infoBackground: toneBackground(tokens.statusInfo60),
      dividerColor: tokens.neutralTone20,
      navigationBackground: tokens.neutralTone00,
      navigationSelected: lightTone.primary,
      navigationUnselected: tokens.neutralTone60,
      navigationSelectedBackground: blend(tokens.overlayMedium),
      shimmerBase: blend(tokens.overlayWeak, surface: tokens.neutralTone10),
      shimmerHighlight: tokens.neutralTone00,
      loadingIndicator: lightTone.primary,
      codeBackground: tokens.codeBackground,
      codeBorder: tokens.codeBorder,
      codeText: tokens.codeText,
      codeAccent: tokens.codeAccent,
      textPrimary: tokens.neutralOnSurface,
      textSecondary: tokens.neutralTone80,
      textTertiary: tokens.neutralTone60,
      textInverse: tokens.neutralTone00,
      textDisabled: tokens.neutralTone60,
      iconPrimary: tokens.neutralOnSurface,
      iconSecondary: tokens.neutralTone80,
      iconDisabled: tokens.neutralTone60,
      iconInverse: tokens.neutralTone00,
      headingLarge: TextStyle(
        fontSize: AppTypography.displaySmall,
        fontWeight: FontWeight.w700,
        color: tokens.neutralOnSurface,
        height: 1.2,
      ),
      headingMedium: TextStyle(
        fontSize: AppTypography.headlineLarge,
        fontWeight: FontWeight.w600,
        color: tokens.neutralOnSurface,
        height: 1.3,
      ),
      headingSmall: TextStyle(
        fontSize: AppTypography.headlineSmall,
        fontWeight: FontWeight.w600,
        color: tokens.neutralOnSurface,
        height: 1.4,
      ),
      bodyLarge: TextStyle(
        fontSize: AppTypography.bodyLarge,
        fontWeight: FontWeight.w400,
        color: tokens.neutralOnSurface,
        height: 1.5,
      ),
      bodyMedium: TextStyle(
        fontSize: AppTypography.bodyMedium,
        fontWeight: FontWeight.w400,
        color: tokens.neutralOnSurface,
        height: 1.5,
      ),
      bodySmall: TextStyle(
        fontSize: AppTypography.bodySmall,
        fontWeight: FontWeight.w400,
        color: tokens.neutralTone60,
        height: 1.4,
      ),
      caption: TextStyle(
        fontSize: AppTypography.labelMedium,
        fontWeight: FontWeight.w500,
        color: tokens.neutralTone60,
        height: 1.3,
        letterSpacing: 0.5,
      ),
      label: TextStyle(
        fontSize: AppTypography.labelLarge,
        fontWeight: FontWeight.w500,
        color: tokens.neutralTone80,
        height: 1.3,
      ),
      code: TextStyle(
        fontSize: AppTypography.bodySmall,
        fontWeight: FontWeight.w400,
        color: tokens.neutralOnSurface,
        height: 1.4,
        fontFamily: AppTypography.monospaceFontFamily,
      ),
    );
  }

  static Color _onSurfaceColor(Color background, AppColorTokens tokens) {
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
}

/// Extension method to easily access JyotiGPT theme from BuildContext
extension JyotiGPTThemeContext on BuildContext {
  JyotiGPTThemeExtension get jyotigptTheme {
    final theme = Theme.of(this);
    final extension = theme.extension<JyotiGPTThemeExtension>();
    if (extension != null) return extension;
    final palette =
        theme.extension<AppPaletteThemeExtension>()?.palette ??
        AppColorPalettes.innerFire;
    final tokens = theme.brightness == Brightness.dark
        ? AppColorTokens.dark(palette: palette)
        : AppColorTokens.light(palette: palette);
    return theme.brightness == Brightness.dark
        ? JyotiGPTThemeExtension.darkPalette(palette: palette, tokens: tokens)
        : JyotiGPTThemeExtension.lightPalette(palette: palette, tokens: tokens);
  }
}

extension JyotiGPTColorTokensContext on BuildContext {
  AppColorTokens get colorTokens {
    final theme = Theme.of(this);
    final tokens = theme.extension<AppColorTokens>();
    if (tokens != null) return tokens;
    final palette =
        theme.extension<AppPaletteThemeExtension>()?.palette ??
        AppColorPalettes.innerFire;
    return theme.brightness == Brightness.dark
        ? AppColorTokens.dark(palette: palette)
        : AppColorTokens.light(palette: palette);
  }
}

extension JyotiGPTPaletteContext on BuildContext {
  AppColorPalette get jyotigptPalette {
    return Theme.of(this).extension<AppPaletteThemeExtension>()?.palette ??
        AppColorPalettes.innerFire;
  }
}

/// Consistent spacing values - Enhanced for production with better hierarchy
class Spacing {
  // Base spacing scale (8pt grid system)
  static const double xxs = 2.0;
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;
  static const double xxxl = 64.0;

  // Enhanced spacing for specific components with better hierarchy
  static const double buttonPadding = 16.0;
  static const double cardPadding = 20.0;
  static const double inputPadding = 16.0;
  static const double modalPadding = 24.0;
  static const double messagePadding = 16.0;
  static const double navigationPadding = 12.0;
  static const double listItemPadding = 16.0;
  static const double sectionPadding = 24.0;
  static const double pagePadding = 20.0;
  static const double screenPadding = 16.0;

  // Spacing for different densities with improved hierarchy
  static const double compact = 8.0;
  static const double comfortable = 16.0;
  static const double spacious = 24.0;
  static const double extraSpacious = 32.0;

  // Specific component spacing with better consistency
  static const double chatBubblePadding = 16.0;
  static const double actionButtonPadding = 12.0;
  static const double floatingButtonPadding = 16.0;
  static const double bottomSheetPadding = 24.0;
  static const double dialogPadding = 20.0;
  static const double snackbarPadding = 16.0;

  // Layout spacing with improved hierarchy
  static const double gridGap = 16.0;
  static const double listGap = 12.0;
  static const double sectionGap = 32.0;
  static const double contentGap = 24.0;

  // Enhanced spacing for better visual hierarchy
  static const double micro = 4.0;
  static const double small = 8.0;
  static const double medium = 16.0;
  static const double large = 24.0;
  static const double extraLarge = 32.0;
  static const double huge = 48.0;
  static const double massive = 64.0;

  // Component-specific spacing
  static const double iconSpacing = 8.0;
  static const double textSpacing = 4.0;
  static const double borderSpacing = 1.0;
  static const double shadowSpacing = 2.0;
}

/// Consistent border radius values - Enhanced for production with better hierarchy
class AppBorderRadius {
  // Base radius scale
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double xl = 24.0;
  static const double round = 999.0;

  // Enhanced radius values for specific components with better hierarchy
  static const double button = 12.0;
  static const double card = 16.0;
  static const double input = 12.0;
  static const double modal = 20.0;
  static const double messageBubble = 18.0;
  static const double navigation = 12.0;
  static const double avatar = 50.0;
  static const double badge = 20.0;
  static const double chip = 16.0;
  static const double tooltip = 8.0;

  // Border radius for different sizes with improved hierarchy
  static const double small = 6.0;
  static const double medium = 12.0;
  static const double large = 18.0;
  static const double extraLarge = 24.0;
  static const double pill = 999.0;

  // Specific component radius with better consistency
  static const double chatBubble = 20.0;
  static const double actionButton = 14.0;
  static const double floatingButton = 28.0;
  static const double bottomSheet = 24.0;
  static const double dialog = 16.0;
  static const double snackbar = 8.0;

  // Enhanced radius values for better visual hierarchy
  static const double micro = 2.0;
  static const double tiny = 4.0;
  static const double standard = 8.0;
  static const double comfortable = 12.0;
  static const double spacious = 16.0;
  static const double extraSpacious = 24.0;
  static const double circular = 999.0;
}

/// Consistent border width values - Enhanced for production
class BorderWidth {
  static const double thin = 0.5;
  static const double regular = 1.0;
  static const double medium = 1.5;
  static const double thick = 2.0;

  // Enhanced border widths for better visual hierarchy
  static const double micro = 0.5;
  static const double small = 1.0;
  static const double standard = 1.5;
  static const double large = 2.0;
  static const double extraLarge = 3.0;
}

/// Consistent elevation values - Enhanced for production with better hierarchy
class Elevation {
  static const double none = 0.0;
  static const double low = 2.0;
  static const double medium = 4.0;
  static const double high = 8.0;
  static const double highest = 16.0;

  // Enhanced elevation values for better visual hierarchy
  static const double micro = 1.0;
  static const double small = 2.0;
  static const double standard = 4.0;
  static const double large = 8.0;
  static const double extraLarge = 16.0;
  static const double massive = 24.0;
}

/// Helper class for consistent shadows - Enhanced for production with better hierarchy
class JyotiGPTShadows {
  static List<BoxShadow> low(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.08,
    blurRadius: 8,
    offset: const Offset(0, 2),
  );

  static List<BoxShadow> medium(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.12,
    blurRadius: 16,
    offset: const Offset(0, 4),
  );

  static List<BoxShadow> high(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.16,
    blurRadius: 24,
    offset: const Offset(0, 8),
  );

  static List<BoxShadow> glow(BuildContext context) =>
      glowWithTokens(context.colorTokens);

  static List<BoxShadow> glowWithTokens(AppColorTokens tokens) {
    final double alpha = tokens.brightness == Brightness.light ? 0.25 : 0.35;
    return [
      BoxShadow(
        color: tokens.brandTone60.withValues(alpha: alpha),
        blurRadius: 20,
        offset: const Offset(0, 0),
        spreadRadius: 0,
      ),
    ];
  }

  static List<BoxShadow> card(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.06,
    blurRadius: 12,
    offset: const Offset(0, 3),
  );

  static List<BoxShadow> button(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.1,
    blurRadius: 6,
    offset: const Offset(0, 2),
  );

  static List<BoxShadow> modal(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.2,
    blurRadius: 32,
    offset: const Offset(0, 12),
  );

  static List<BoxShadow> navigation(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.08,
    blurRadius: 16,
    offset: const Offset(0, -2),
  );

  static List<BoxShadow> messageBubble(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.04,
    blurRadius: 8,
    offset: const Offset(0, 1),
  );

  static List<BoxShadow> input(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.05,
    blurRadius: 4,
    offset: const Offset(0, 1),
  );

  static List<BoxShadow> pressed(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.15,
    blurRadius: 4,
    offset: const Offset(0, 1),
  );

  static List<BoxShadow> hover(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.12,
    blurRadius: 12,
    offset: const Offset(0, 4),
  );

  static List<BoxShadow> micro(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.04,
    blurRadius: 4,
    offset: const Offset(0, 1),
  );

  static List<BoxShadow> small(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.06,
    blurRadius: 8,
    offset: const Offset(0, 2),
  );

  static List<BoxShadow> standard(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.08,
    blurRadius: 12,
    offset: const Offset(0, 3),
  );

  static List<BoxShadow> large(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.12,
    blurRadius: 16,
    offset: const Offset(0, 4),
  );

  static List<BoxShadow> extraLarge(BuildContext context) => _shadow(
    context.colorTokens,
    opacity: 0.16,
    blurRadius: 24,
    offset: const Offset(0, 8),
  );

  static List<BoxShadow> _shadow(
    AppColorTokens tokens, {
    required double opacity,
    required double blurRadius,
    required Offset offset,
  }) {
    return [
      BoxShadow(
        color: _overlayColor(tokens, opacity),
        blurRadius: blurRadius,
        offset: offset,
        spreadRadius: 0,
      ),
    ];
  }

  static Color _overlayColor(AppColorTokens tokens, double alpha) {
    final Color base = tokens.overlayStrong.withValues(alpha: 1.0);
    return base.withValues(alpha: alpha.clamp(0.0, 1.0));
  }
}

/// Typography scale following JyotiGPT design tokens - Enhanced for production
class AppTypography {
  // Primary UI font now uses the platform default system font
  static const String fontFamily = '';
  static const String monospaceFontFamily = 'SF Mono';

  // Letter spacing values - Enhanced for better readability
  static const double letterSpacingTight = -0.5;
  static const double letterSpacingNormal = 0.0;
  static const double letterSpacingWide = 0.5;
  static const double letterSpacingExtraWide = 1.0;

  // Font sizes - Enhanced scale for better hierarchy
  static const double displayLarge = 48;
  static const double displayMedium = 36;
  static const double displaySmall = 32;
  static const double headlineLarge = 28;
  static const double headlineMedium = 24;
  static const double headlineSmall = 20;
  static const double bodyLarge = 18;
  static const double bodyMedium = 16;
  static const double bodySmall = 14;
  static const double labelLarge = 16;
  static const double labelMedium = 14;
  static const double labelSmall = 12;

  // Text styles following JyotiGPT design - Enhanced for production
  static final TextStyle displayLargeStyle = const TextStyle(
    fontWeight: FontWeight.w700,
    letterSpacing: -0.8,
    height: 1.1,
  ).copyWith(fontSize: displayLarge);

  static final TextStyle displayMediumStyle = const TextStyle(
    fontWeight: FontWeight.w700,
    letterSpacing: -0.6,
    height: 1.2,
  ).copyWith(fontSize: displayMedium);

  static final TextStyle bodyLargeStyle = const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    height: 1.6,
  ).copyWith(fontSize: bodyLarge);

  static final TextStyle bodyMediumStyle = const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    height: 1.6,
  ).copyWith(fontSize: bodyMedium);

  static final TextStyle codeStyle = const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    height: 1.5,
    fontFamily: monospaceFontFamily,
  ).copyWith(fontSize: bodySmall);

  // Additional styled text getters for convenience - Enhanced
  static TextStyle get headlineLargeStyle => const TextStyle(
    fontWeight: FontWeight.w700,
    letterSpacing: -0.4,
    height: 1.3,
  ).copyWith(fontSize: headlineLarge);

  static TextStyle get headlineMediumStyle => const TextStyle(
    fontWeight: FontWeight.w600,
    letterSpacing: -0.2,
    height: 1.3,
  ).copyWith(fontSize: headlineMedium);

  static TextStyle get headlineSmallStyle => const TextStyle(
    fontWeight: FontWeight.w600,
    letterSpacing: 0,
    height: 1.4,
  ).copyWith(fontSize: headlineSmall);

  static TextStyle get bodySmallStyle => const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    height: 1.5,
  ).copyWith(fontSize: bodySmall);

  // Enhanced text styles for chat messages
  static TextStyle get chatMessageStyle => const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0.0,
    height: 1.4,
  ).copyWith(fontSize: bodyMedium);

  static TextStyle get chatCodeStyle => const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    height: 1.5,
    fontFamily: monospaceFontFamily,
  ).copyWith(fontSize: bodySmall);

  // Enhanced label styles
  static TextStyle get labelStyle => const TextStyle(
    fontWeight: FontWeight.w500,
    letterSpacing: 0.2,
    height: 1.4,
  ).copyWith(fontSize: labelMedium);

  // Enhanced caption styles
  static TextStyle get captionStyle => const TextStyle(
    fontWeight: FontWeight.w500,
    letterSpacing: 0.5,
    height: 1.3,
  ).copyWith(fontSize: labelSmall);

  // Enhanced typography for better hierarchy
  static TextStyle get micro => const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0.1,
    height: 1.4,
  ).copyWith(fontSize: 10);

  static TextStyle get tiny => const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0.1,
    height: 1.4,
  ).copyWith(fontSize: 12);

  static TextStyle get small => const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    height: 1.5,
  ).copyWith(fontSize: 14);

  static TextStyle get standard => const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    height: 1.6,
  ).copyWith(fontSize: 16);

  static TextStyle get large => const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    height: 1.6,
  ).copyWith(fontSize: 18);

  static TextStyle get extraLarge => const TextStyle(
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    height: 1.5,
  ).copyWith(fontSize: 20);

  static TextStyle get huge => const TextStyle(
    fontWeight: FontWeight.w600,
    letterSpacing: -0.2,
    height: 1.3,
  ).copyWith(fontSize: 24);

  static TextStyle get massive => const TextStyle(
    fontWeight: FontWeight.w700,
    letterSpacing: -0.4,
    height: 1.2,
  ).copyWith(fontSize: 32);
}

/// Consistent icon sizes - Enhanced for production with better hierarchy
class IconSize {
  static const double xs = 12.0;
  static const double sm = 16.0;
  static const double md = 20.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;

  // Enhanced icon sizes for specific components with better hierarchy
  static const double button = 20.0;
  static const double card = 24.0;
  static const double input = 20.0;
  static const double modal = 24.0;
  static const double message = 18.0;
  static const double navigation = 24.0;
  static const double avatar = 40.0;
  static const double badge = 16.0;
  static const double chip = 18.0;
  static const double tooltip = 16.0;

  // Icon sizes for different contexts with improved hierarchy
  static const double micro = 12.0;
  static const double small = 16.0;
  static const double medium = 20.0;
  static const double large = 24.0;
  static const double extraLarge = 32.0;
  static const double huge = 48.0;

  // Specific component icon sizes with better consistency
  static const double chatBubble = 18.0;
  static const double actionButton = 20.0;
  static const double floatingButton = 24.0;
  static const double bottomSheet = 24.0;
  static const double dialog = 24.0;
  static const double snackbar = 20.0;
  static const double tabBar = 24.0;
  static const double appBar = 24.0;
  static const double listItem = 20.0;
  static const double formField = 20.0;
}

/// Alpha values for opacity/transparency - Enhanced for production with better hierarchy
class Alpha {
  static const double subtle = 0.1;
  static const double light = 0.3;
  static const double medium = 0.5;
  static const double strong = 0.7;
  static const double intense = 0.9;

  // Enhanced alpha values for specific use cases with better hierarchy
  static const double disabled = 0.38;
  static const double overlay = 0.5;
  static const double backdrop = 0.6;
  static const double highlight = 0.12;
  static const double pressed = 0.2;
  static const double hover = 0.08;
  static const double focus = 0.12;
  static const double selected = 0.16;
  static const double active = 0.24;
  static const double inactive = 0.6;

  // Alpha values for different states with improved hierarchy
  static const double primary = 1.0;
  static const double secondary = 0.7;
  static const double tertiary = 0.5;
  static const double quaternary = 0.3;
  static const double disabledText = 0.38;
  static const double disabledIcon = 0.38;
  static const double disabledBackground = 0.12;

  // Specific component alpha values with better consistency
  static const double buttonPressed = 0.2;
  static const double buttonHover = 0.08;
  static const double cardHover = 0.04;
  static const double inputFocus = 0.12;
  static const double modalBackdrop = 0.6;
  static const double snackbarBackground = 0.95;
  static const double tooltipBackground = 0.9;
  static const double badgeBackground = 0.1;
  static const double chipBackground = 0.08;
  static const double avatarBorder = 0.2;

  // Enhanced alpha values for better visual hierarchy
  static const double micro = 0.05;
  static const double tiny = 0.1;
  static const double small = 0.2;
  static const double standard = 0.3;
  static const double large = 0.5;
  static const double extraLarge = 0.7;
  static const double huge = 0.9;
}

/// Touch target sizes for accessibility compliance - Enhanced for production with better hierarchy
class TouchTarget {
  static const double minimum = 44.0;
  static const double comfortable = 48.0;
  static const double large = 56.0;

  // Enhanced touch targets for specific components with better hierarchy
  static const double button = 48.0;
  static const double card = 48.0;
  static const double input = 48.0;
  static const double modal = 48.0;
  static const double message = 44.0;
  static const double navigation = 48.0;
  static const double avatar = 48.0;
  static const double badge = 32.0;
  static const double chip = 32.0;
  static const double tooltip = 32.0;

  // Touch targets for different contexts with improved hierarchy
  static const double micro = 32.0;
  static const double small = 40.0;
  static const double medium = 48.0;
  static const double standard = 56.0;
  static const double extraLarge = 64.0;
  static const double huge = 80.0;

  // Specific component touch targets with better consistency
  static const double chatBubble = 44.0;
  static const double actionButton = 48.0;
  static const double floatingButton = 56.0;
  static const double bottomSheet = 48.0;
  static const double dialog = 48.0;
  static const double snackbar = 48.0;
  static const double tabBar = 48.0;
  static const double appBar = 48.0;
  static const double listItem = 48.0;
  static const double formField = 48.0;
  static const double iconButton = 48.0;
  static const double textButton = 44.0;
  static const double toggle = 48.0;
  static const double slider = 48.0;
  static const double checkbox = 48.0;
  static const double radio = 48.0;
}

/// Animation durations for consistent motion design - Enhanced for production with better hierarchy
class AnimationDuration {
  static const Duration instant = Duration(milliseconds: 100);
  static const Duration fast = Duration(milliseconds: 200);
  static const Duration medium = Duration(milliseconds: 300);
  static const Duration slow = Duration(milliseconds: 500);
  static const Duration slower = Duration(milliseconds: 800);
  static const Duration slowest = Duration(milliseconds: 1000);
  static const Duration extraSlow = Duration(milliseconds: 1200);
  static const Duration ultra = Duration(milliseconds: 1500);
  static const Duration extended = Duration(seconds: 2);
  static const Duration long = Duration(seconds: 4);

  // Enhanced durations for specific interactions with better hierarchy
  static const Duration microInteraction = Duration(milliseconds: 150);
  static const Duration buttonPress = Duration(milliseconds: 100);
  static const Duration cardHover = Duration(milliseconds: 200);
  static const Duration pageTransition = Duration(milliseconds: 400);
  static const Duration modalPresentation = Duration(milliseconds: 500);
  static const Duration typingIndicator = Duration(milliseconds: 800);
  static const Duration messageAppear = Duration(milliseconds: 350);
  static const Duration messageSlide = Duration(milliseconds: 400);

  // Enhanced durations for better visual hierarchy
  static const Duration micro = Duration(milliseconds: 50);
  static const Duration tiny = Duration(milliseconds: 100);
  static const Duration small = Duration(milliseconds: 200);
  static const Duration standard = Duration(milliseconds: 300);
  static const Duration large = Duration(milliseconds: 500);
  static const Duration extraLarge = Duration(milliseconds: 800);
  static const Duration huge = Duration(milliseconds: 1200);
}

/// Animation curves for consistent motion design - Enhanced for production with better hierarchy
class AnimationCurves {
  static const Curve easeIn = Curves.easeIn;
  static const Curve easeOut = Curves.easeOut;
  static const Curve easeInOut = Curves.easeInOut;
  static const Curve bounce = Curves.bounceOut;
  static const Curve elastic = Curves.elasticOut;
  static const Curve fastOutSlowIn = Curves.fastOutSlowIn;
  static const Curve linear = Curves.linear;

  // Enhanced curves for specific interactions with better hierarchy
  static const Curve buttonPress = Curves.easeOutCubic;
  static const Curve cardHover = Curves.easeInOutCubic;
  static const Curve messageSlide = Curves.easeOutCubic;
  static const Curve typingIndicator = Curves.easeInOut;
  static const Curve modalPresentation = Curves.easeOutBack;
  static const Curve pageTransition = Curves.easeInOutCubic;
  static const Curve microInteraction = Curves.easeOutQuart;
  static const Curve spring = Curves.elasticOut;

  // Enhanced curves for better visual hierarchy
  static const Curve micro = Curves.easeOutQuart;
  static const Curve tiny = Curves.easeOutCubic;
  static const Curve small = Curves.easeInOutCubic;
  static const Curve standard = Curves.easeInOut;
  static const Curve large = Curves.easeOutBack;
  static const Curve extraLarge = Curves.elasticOut;
  static const Curve huge = Curves.bounceOut;
}

/// Common animation values - Enhanced for production with better hierarchy
class AnimationValues {
  static const double fadeInOpacity = 0.0;
  static const double fadeOutOpacity = 1.0;
  static const Offset slideInFromTop = Offset(0, -0.05);
  static const Offset slideInFromBottom = Offset(0, 0.05);
  static const Offset slideInFromLeft = Offset(-0.05, 0);
  static const Offset slideInFromRight = Offset(0.05, 0);
  static const Offset slideCenter = Offset.zero;
  static const double scaleMin = 0.0;
  static const double scaleMax = 1.0;
  static const double shimmerBegin = -1.0;
  static const double shimmerEnd = 2.0;

  // Enhanced values for specific interactions with better hierarchy
  static const double buttonScalePressed = 0.95;
  static const double buttonScaleHover = 1.02;
  static const double cardScaleHover = 1.01;
  static const double messageSlideDistance = 0.1;
  static const double typingIndicatorScale = 0.8;
  static const double modalScale = 0.9;
  static const double pageSlideDistance = 0.15;
  static const double microInteractionScale = 0.98;

  // Enhanced values for better visual hierarchy
  static const double micro = 0.95;
  static const double tiny = 0.98;
  static const double small = 1.01;
  static const double standard = 1.02;
  static const double large = 1.05;
  static const double extraLarge = 1.1;
  static const double huge = 1.2;
}

/// Delay values for staggered animations - Enhanced for production with better hierarchy
class AnimationDelay {
  static const Duration none = Duration.zero;
  static const Duration short = Duration(milliseconds: 100);
  static const Duration medium = Duration(milliseconds: 200);
  static const Duration long = Duration(milliseconds: 400);
  static const Duration extraLong = Duration(milliseconds: 600);
  static const Duration ultra = Duration(milliseconds: 800);

  // Enhanced delays for specific interactions with better hierarchy
  static const Duration microDelay = Duration(milliseconds: 50);
  static const Duration buttonDelay = Duration(milliseconds: 75);
  static const Duration cardDelay = Duration(milliseconds: 150);
  static const Duration messageDelay = Duration(milliseconds: 100);
  static const Duration typingDelay = Duration(milliseconds: 200);
  static const Duration modalDelay = Duration(milliseconds: 300);
  static const Duration pageDelay = Duration(milliseconds: 250);
  static const Duration staggeredDelay = Duration(milliseconds: 50);

  // Enhanced delays for better visual hierarchy
  static const Duration micro = Duration(milliseconds: 25);
  static const Duration tiny = Duration(milliseconds: 50);
  static const Duration small = Duration(milliseconds: 100);
  static const Duration standard = Duration(milliseconds: 200);
  static const Duration large = Duration(milliseconds: 400);
  static const Duration extraLarge = Duration(milliseconds: 600);
  static const Duration huge = Duration(milliseconds: 800);
}
