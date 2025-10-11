import 'package:flutter/material.dart';
import '../theme/theme_extensions.dart';
import 'package:flutter/cupertino.dart';
import 'dart:io' show Platform;
import '../theme/color_tokens.dart';
import '../theme/color_palettes.dart';

/// Centralized service for consistent brand identity throughout the app
/// Uses the hub icon as the primary brand element
class BrandService {
  BrandService._();

  /// Primary brand icon - the hub icon (consistent across platforms)
  static IconData get primaryIcon => Icons.hub;

  /// Alternative brand icons for different contexts
  static IconData get primaryIconOutlined => Icons.hub_outlined;
  static IconData get connectivityIcon =>
      Platform.isIOS ? CupertinoIcons.wifi : Icons.wifi;
  static IconData get networkIcon =>
      Platform.isIOS ? CupertinoIcons.globe : Icons.public;

  /// Brand colors - these should be accessed through context.jyotigptTheme in UI components
  static Color primaryBrandColor({
    BuildContext? context,
    Brightness? brightness,
  }) {
    final palette = _resolvePalette(context);
    final resolvedBrightness = brightness ?? _resolveBrightness(context);
    return palette.primaryFor(resolvedBrightness);
  }

  static Color secondaryBrandColor({
    BuildContext? context,
    Brightness? brightness,
  }) {
    final palette = _resolvePalette(context);
    final resolvedBrightness = brightness ?? _resolveBrightness(context);
    return palette.secondaryFor(resolvedBrightness);
  }

  static Color accentBrandColor({
    BuildContext? context,
    Brightness? brightness,
  }) {
    final palette = _resolvePalette(context);
    final resolvedBrightness = brightness ?? _resolveBrightness(context);
    return palette.accentFor(resolvedBrightness);
  }

  /// Creates a branded icon with consistent styling
  static Widget createBrandIcon({
    double size = 24,
    Color? color,
    IconData? icon,
    bool useGradient = false,
    bool addShadow = false,
    BuildContext? context,
  }) {
    final iconData = icon ?? primaryIcon;
    final resolvedColor = color ?? primaryBrandColor(context: context);

    Widget iconWidget = Icon(
      iconData,
      size: size,
      color: useGradient ? null : resolvedColor,
    );

    if (useGradient) {
      iconWidget = ShaderMask(
        blendMode: BlendMode.srcIn,
        shaderCallback: (bounds) => LinearGradient(
          colors: [
            primaryBrandColor(context: context),
            secondaryBrandColor(context: context),
          ],
        ).createShader(bounds),
        child: Icon(iconData, size: size),
      );
    }

    if (addShadow) {
      iconWidget = Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: primaryBrandColor(context: context).withValues(alpha: 0.3),
              blurRadius: size * 0.3,
              offset: Offset(0, size * 0.1),
            ),
          ],
        ),
        child: iconWidget,
      );
    }

    return iconWidget;
  }

  /// Creates a branded avatar with the hub icon
  static Widget createBrandAvatar({
    double size = 40,
    Color? backgroundColor,
    Color? iconColor,
    bool useGradient = true,
    String? fallbackText,
    BuildContext? context,
  }) {
    final bgColor = backgroundColor ?? primaryBrandColor(context: context);
    final tokens = _resolveTokens(context);
    final iColor =
        iconColor ??
        (context?.jyotigptTheme.textInverse ?? tokens.neutralTone00);

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: useGradient
            ? LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  primaryBrandColor(context: context),
                  secondaryBrandColor(context: context),
                ],
              )
            : null,
        color: useGradient ? null : bgColor,
        borderRadius: BorderRadius.circular(size / 2),
        boxShadow: [
          BoxShadow(
            color: primaryBrandColor(context: context).withValues(alpha: 0.3),
            blurRadius: size * 0.2,
            offset: Offset(0, size * 0.1),
          ),
        ],
      ),
      child: fallbackText != null && fallbackText.isNotEmpty
          ? Center(
              child: Text(
                fallbackText.toUpperCase(),
                style: TextStyle(
                  color: iColor,
                  fontSize: size * 0.4,
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          : Icon(primaryIcon, size: size * 0.5, color: iColor),
    );
  }

  /// Creates a branded loading indicator
  static Widget createBrandLoadingIndicator({
    double size = 24,
    double strokeWidth = 2,
    Color? color,
    BuildContext? context,
  }) {
    return SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        strokeWidth: strokeWidth,
        valueColor: AlwaysStoppedAnimation<Color>(
          color ?? primaryBrandColor(context: context),
        ),
      ),
    );
  }

  /// Creates a branded empty state icon
  static Widget createBrandEmptyStateIcon({
    double size = 80,
    Color? color,
    bool showBackground = true,
    BuildContext? context,
  }) {
    final tokens = _resolveTokens(context);
    final iconColor =
        color ?? (context?.jyotigptTheme.iconSecondary ?? tokens.neutralTone80);

    if (!showBackground) {
      return createBrandIcon(
        size: size,
        color: iconColor,
        icon: primaryIconOutlined,
        context: context,
      );
    }

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: context?.jyotigptTheme.surfaceBackground ?? tokens.neutralTone10,
        borderRadius: BorderRadius.circular(size / 2),
        border: Border.all(
          color: context?.jyotigptTheme.dividerColor ?? tokens.neutralTone40,
          width: 2,
        ),
      ),
      child: createBrandIcon(
        size: size * 0.5,
        color: iconColor,
        icon: primaryIconOutlined,
        context: context,
      ),
    );
  }

  /// Creates a branded button with hub icon
  static Widget createBrandButton({
    required String text,
    required VoidCallback? onPressed,
    bool isLoading = false,
    IconData? icon,
    double? width,
    bool isSecondary = false,
    BuildContext? context,
  }) {
    final theme = context?.jyotigptTheme;
    final tokens = _resolveTokens(context);
    return SizedBox(
      width: width,
      height: 48,
      child: ElevatedButton.icon(
        onPressed: isLoading ? null : onPressed,
        icon: isLoading
            ? createBrandLoadingIndicator(size: IconSize.sm, context: context)
            : createBrandIcon(
                size: IconSize.md,
                icon: icon ?? primaryIcon,
                color: theme?.textInverse ?? tokens.neutralTone00,
                context: context,
              ),
        label: Text(text),
        style: ElevatedButton.styleFrom(
          backgroundColor: isSecondary
              ? (theme?.buttonSecondary ?? tokens.neutralTone20)
              : (theme?.buttonPrimary ?? primaryBrandColor(context: context)),
          foregroundColor: theme?.buttonPrimaryText ?? tokens.brandOn60,
          disabledBackgroundColor:
              theme?.buttonDisabled ?? tokens.neutralTone40,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppBorderRadius.md),
          ),
          elevation: Elevation.none,
        ),
      ),
    );
  }

  /// Brand-specific semantic labels for accessibility
  static String get brandName => 'JyotiGPT';
  static String get brandDescription => 'Your AI Conversation Hub';
  static String get connectionLabel => 'Hub Connection';
  static String get networkLabel => 'Network Hub';

  /// Creates branded AppBar with consistent styling
  static PreferredSizeWidget createBrandAppBar({
    required String title,
    List<Widget>? actions,
    Widget? leading,
    bool centerTitle = true,
    double elevation = 0,
    BuildContext? context,
  }) {
    return AppBar(
      title: Text(
        title,
        style: context != null
            ? context.jyotigptTheme.headingSmall?.copyWith(
                color: context.jyotigptTheme.textPrimary,
                fontWeight: FontWeight.w600,
              )
            : TextStyle(
                fontSize: AppTypography.headlineSmall,
                fontWeight: FontWeight.w600,
              ),
      ),
      centerTitle: centerTitle,
      elevation: elevation,
      backgroundColor: context?.jyotigptTheme.surfaceBackground,
      surfaceTintColor: Colors.transparent,
      shadowColor: Colors.transparent,
      leading: leading,
      actions: actions,
    );
  }

  /// Creates a branded splash screen logo
  static Widget createSplashLogo({
    double size = 140,
    bool animate = true,
    BuildContext? context,
  }) {
    final theme = context?.jyotigptTheme;
    final tokens = _resolveTokens(context);
    final baseColor =
        theme?.buttonPrimary ??
        primaryBrandColor(context: context, brightness: Brightness.dark);
    final accentColor =
        theme?.buttonPrimary.withValues(alpha: 0.8) ??
        secondaryBrandColor(context: context, brightness: Brightness.dark);

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [baseColor, accentColor],
        ),
        borderRadius: BorderRadius.circular(size / 2),
        boxShadow: context != null
            ? JyotiGPTShadows.glow(context)
            : JyotiGPTShadows.glowWithTokens(tokens),
      ),
      child: Icon(
        primaryIcon,
        size: size * 0.5,
        color: theme?.textInverse ?? tokens.neutralTone00,
      ),
    );
  }

  static AppColorPalette _resolvePalette(BuildContext? context) {
    if (context == null) {
      return AppColorPalettes.auroraViolet;
    }
    final extension = Theme.of(context).extension<AppPaletteThemeExtension>();
    return extension?.palette ?? AppColorPalettes.auroraViolet;
  }

  static Brightness _resolveBrightness(BuildContext? context) {
    return context != null ? Theme.of(context).brightness : Brightness.light;
  }

  static AppColorTokens _resolveTokens(BuildContext? context) {
    final palette = _resolvePalette(context);
    final brightness = _resolveBrightness(context);
    return brightness == Brightness.dark
        ? AppColorTokens.dark(palette: palette)
        : AppColorTokens.light(palette: palette);
  }
}
