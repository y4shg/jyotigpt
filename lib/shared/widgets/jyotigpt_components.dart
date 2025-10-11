import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../theme/theme_extensions.dart';
import '../services/brand_service.dart';
import '../../core/services/enhanced_accessibility_service.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';
import '../../core/services/platform_service.dart';
import '../../core/services/settings_service.dart';

/// Unified component library following JyotiGPT design patterns
/// This provides consistent, reusable UI components throughout the appf

class JyotiGPTButton extends ConsumerWidget {
  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool isDestructive;
  final bool isSecondary;
  final IconData? icon;
  final double? width;
  final bool isFullWidth;
  final bool isCompact;

  const JyotiGPTButton({
    super.key,
    required this.text,
    this.onPressed,
    this.isLoading = false,
    this.isDestructive = false,
    this.isSecondary = false,
    this.icon,
    this.width,
    this.isFullWidth = false,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hapticEnabled = ref.watch(hapticEnabledProvider);
    Color backgroundColor;
    Color textColor;

    if (isDestructive) {
      backgroundColor = context.jyotigptTheme.error;
      textColor = context.jyotigptTheme.buttonPrimaryText;
    } else if (isSecondary) {
      backgroundColor = context.jyotigptTheme.buttonSecondary;
      textColor = context.jyotigptTheme.buttonSecondaryText;
    } else {
      backgroundColor = context.jyotigptTheme.buttonPrimary;
      textColor = context.jyotigptTheme.buttonPrimaryText;
    }

    // Build semantic label
    String semanticLabel = text;
    if (isLoading) {
      final l10n = AppLocalizations.of(context);
      semanticLabel = '${l10n?.loadingContent ?? 'Loading'}: $text';
    } else if (isDestructive) {
      semanticLabel = 'Warning: $text';
    }

    return Semantics(
      label: semanticLabel,
      button: true,
      enabled: !isLoading && onPressed != null,
      child: SizedBox(
        width: isFullWidth ? double.infinity : width,
        height: isCompact ? TouchTarget.medium : TouchTarget.comfortable,
        child: ElevatedButton(
          onPressed: isLoading
              ? null
              : () {
                  if (onPressed != null) {
                    PlatformService.hapticFeedbackWithSettings(
                      type: isDestructive
                          ? HapticType.warning
                          : HapticType.light,
                      hapticEnabled: hapticEnabled,
                    );
                    onPressed!();
                  }
                },
          style: ElevatedButton.styleFrom(
            backgroundColor: backgroundColor,
            foregroundColor: textColor,
            disabledBackgroundColor: context.jyotigptTheme.buttonDisabled,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppBorderRadius.button),
            ),
            elevation: Elevation.none,
            shadowColor: backgroundColor.withValues(alpha: Alpha.standard),
            minimumSize: Size(
              TouchTarget.minimum,
              isCompact ? TouchTarget.medium : TouchTarget.comfortable,
            ),
            padding: EdgeInsets.symmetric(
              horizontal: isCompact ? Spacing.md : Spacing.buttonPadding,
              vertical: isCompact ? Spacing.sm : Spacing.sm,
            ),
          ),
          child: isLoading
              ? Semantics(
                  label:
                      AppLocalizations.of(context)?.loadingContent ?? 'Loading',
                  excludeSemantics: true,
                  child: SizedBox(
                    width: IconSize.small,
                    height: IconSize.small,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(textColor),
                    ),
                  ),
                )
              : Row(
                  mainAxisSize: MainAxisSize.min,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    if (icon != null) ...[
                      Icon(icon, size: IconSize.small),
                      SizedBox(width: Spacing.iconSpacing),
                    ],
                    Flexible(
                      child: EnhancedAccessibilityService.createAccessibleText(
                        text,
                        style: AppTypography.standard.copyWith(
                          fontWeight: FontWeight.w600,
                          color: textColor,
                        ),
                        maxLines: 1,
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}

class JyotiGPTInput extends StatelessWidget {
  final String? label;
  final String? hint;
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final VoidCallback? onTap;
  final bool obscureText;
  final bool enabled;
  final String? errorText;
  final int? maxLines;
  final Widget? suffixIcon;
  final Widget? prefixIcon;
  final TextInputType? keyboardType;
  final bool autofocus;
  final String? semanticLabel;
  final ValueChanged<String>? onSubmitted;
  final bool isRequired;

  const JyotiGPTInput({
    super.key,
    this.label,
    this.hint,
    this.controller,
    this.onChanged,
    this.onTap,
    this.obscureText = false,
    this.enabled = true,
    this.errorText,
    this.maxLines = 1,
    this.suffixIcon,
    this.prefixIcon,
    this.keyboardType,
    this.autofocus = false,
    this.semanticLabel,
    this.onSubmitted,
    this.isRequired = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ...[
          Row(
            children: [
              Text(
                label!,
                style: AppTypography.standard.copyWith(
                  fontWeight: FontWeight.w500,
                  color: context.jyotigptTheme.textPrimary,
                ),
              ),
              if (isRequired) ...[
                SizedBox(width: Spacing.textSpacing),
                Text(
                  '*',
                  style: AppTypography.standard.copyWith(
                    color: context.jyotigptTheme.error,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ],
          ),
          SizedBox(height: Spacing.sm),
        ],
        Semantics(
          label:
              semanticLabel ??
              label ??
              (AppLocalizations.of(context)?.inputField ?? 'Input field'),
          textField: true,
          child: TextField(
            controller: controller,
            onChanged: onChanged,
            onTap: onTap,
            onSubmitted: onSubmitted,
            obscureText: obscureText,
            enabled: enabled,
            maxLines: maxLines,
            keyboardType: keyboardType,
            autofocus: autofocus,
            style: AppTypography.standard.copyWith(
              color: context.jyotigptTheme.textPrimary,
            ),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: AppTypography.standard.copyWith(
                color: context.jyotigptTheme.inputPlaceholder,
              ),
              filled: true,
              fillColor: context.jyotigptTheme.inputBackground,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.inputBorder,
                  width: BorderWidth.standard,
                ),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.inputBorder,
                  width: BorderWidth.standard,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.buttonPrimary,
                  width: BorderWidth.thick,
                ),
              ),
              errorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.error,
                  width: BorderWidth.standard,
                ),
              ),
              focusedErrorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.error,
                  width: BorderWidth.thick,
                ),
              ),
              contentPadding: EdgeInsets.symmetric(
                horizontal: Spacing.inputPadding,
                vertical: Spacing.md,
              ),
              suffixIcon: suffixIcon,
              prefixIcon: prefixIcon,
              errorText: errorText,
              errorStyle: AppTypography.small.copyWith(
                color: context.jyotigptTheme.error,
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class JyotiGPTCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final bool isSelected;
  final bool isElevated;
  final bool isCompact;

  const JyotiGPTCard({
    super.key,
    required this.child,
    this.padding,
    this.onTap,
    this.isSelected = false,
    this.isElevated = false,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding:
            padding ??
            EdgeInsets.all(isCompact ? Spacing.md : Spacing.cardPadding),
        decoration: BoxDecoration(
          color: isSelected
              ? context.jyotigptTheme.buttonPrimary.withValues(
                  alpha: Alpha.highlight,
                )
              : context.jyotigptTheme.cardBackground,
          borderRadius: BorderRadius.circular(AppBorderRadius.card),
          border: Border.all(
            color: isSelected
                ? context.jyotigptTheme.buttonPrimary.withValues(
                    alpha: Alpha.standard,
                  )
                : context.jyotigptTheme.cardBorder,
            width: BorderWidth.standard,
          ),
          boxShadow: isElevated ? JyotiGPTShadows.card(context) : null,
        ),
        child: child,
      ),
    );
  }
}

class JyotiGPTIconButton extends ConsumerWidget {
  final IconData icon;
  final VoidCallback? onPressed;
  final String? tooltip;
  final bool isActive;
  final Color? backgroundColor;
  final Color? iconColor;
  final bool isCompact;
  final bool isCircular;

  const JyotiGPTIconButton({
    super.key,
    required this.icon,
    this.onPressed,
    this.tooltip,
    this.isActive = false,
    this.backgroundColor,
    this.iconColor,
    this.isCompact = false,
    this.isCircular = true,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hapticEnabled = ref.watch(hapticEnabledProvider);
    final effectiveBackgroundColor =
        backgroundColor ??
        (isActive
            ? context.jyotigptTheme.buttonPrimary.withValues(
                alpha: Alpha.highlight,
              )
            : Colors.transparent);
    final effectiveIconColor =
        iconColor ??
        (isActive
            ? context.jyotigptTheme.buttonPrimary
            : context.jyotigptTheme.iconSecondary);

    // Build semantic label with context
    String semanticLabel = tooltip ?? 'Button';
    if (isActive) {
      semanticLabel = '$semanticLabel, active';
    }

    return Semantics(
      label: semanticLabel,
      button: true,
      enabled: onPressed != null,
      child: Tooltip(
        message: tooltip ?? '',
        child: GestureDetector(
          onTap: () {
            if (onPressed != null) {
              PlatformService.hapticFeedbackWithSettings(
                type: HapticType.selection,
                hapticEnabled: hapticEnabled,
              );
              onPressed!();
            }
          },
          child: Container(
            width: isCompact ? TouchTarget.medium : TouchTarget.minimum,
            height: isCompact ? TouchTarget.medium : TouchTarget.minimum,
            decoration: BoxDecoration(
              color: effectiveBackgroundColor,
              borderRadius: BorderRadius.circular(
                isCircular
                    ? AppBorderRadius.circular
                    : AppBorderRadius.standard,
              ),
              border: isActive
                  ? Border.all(
                      color: context.jyotigptTheme.buttonPrimary.withValues(
                        alpha: Alpha.standard,
                      ),
                      width: BorderWidth.standard,
                    )
                  : null,
            ),
            child: Icon(
              icon,
              size: isCompact ? IconSize.small : IconSize.medium,
              color: effectiveIconColor,
              semanticLabel: tooltip,
            ),
          ),
        ),
      ),
    );
  }
}

class JyotiGPTLoadingIndicator extends StatelessWidget {
  final String? message;
  final double size;
  final bool isCompact;

  const JyotiGPTLoadingIndicator({
    super.key,
    this.message,
    this.size = 24,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: size,
          height: size,
          child: CircularProgressIndicator(
            strokeWidth: isCompact ? 2 : 3,
            valueColor: AlwaysStoppedAnimation<Color>(
              context.jyotigptTheme.buttonPrimary,
            ),
          ),
        ),
        if (message != null) ...[
          SizedBox(height: isCompact ? Spacing.sm : Spacing.md),
          Text(
            message!,
            style: AppTypography.standard.copyWith(
              color: context.jyotigptTheme.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ],
    );
  }
}

class JyotiGPTEmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final Widget? action;
  final bool isCompact;

  const JyotiGPTEmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.action,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(isCompact ? Spacing.md : Spacing.lg),
        child: SingleChildScrollView(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: isCompact ? IconSize.xxl : IconSize.xxl + Spacing.md,
                height: isCompact ? IconSize.xxl : IconSize.xxl + Spacing.md,
                decoration: BoxDecoration(
                  color: context.jyotigptTheme.surfaceBackground,
                  borderRadius: BorderRadius.circular(AppBorderRadius.circular),
                ),
                child: Icon(
                  icon,
                  size: isCompact ? IconSize.xl : TouchTarget.minimum,
                  color: context.jyotigptTheme.iconSecondary,
                ),
              ),
              SizedBox(height: isCompact ? Spacing.sm : Spacing.md),
              Text(
                title,
                style: AppTypography.headlineSmallStyle.copyWith(
                  color: context.jyotigptTheme.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: Spacing.sm),
              Text(
                message,
                style: AppTypography.standard.copyWith(
                  color: context.jyotigptTheme.textSecondary,
                ),
                textAlign: TextAlign.center,
                maxLines: isCompact ? 2 : null,
                overflow: isCompact ? TextOverflow.ellipsis : null,
              ),
              if (action != null) ...[
                SizedBox(height: isCompact ? Spacing.md : Spacing.lg),
                action!,
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class JyotiGPTAvatar extends StatelessWidget {
  final double size;
  final IconData? icon;
  final String? text;
  final bool isCompact;

  const JyotiGPTAvatar({
    super.key,
    this.size = 32,
    this.icon,
    this.text,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    return BrandService.createBrandAvatar(
      size: isCompact ? size * 0.8 : size,
      fallbackText: text,
      context: context,
    );
  }
}

class JyotiGPTBadge extends StatelessWidget {
  final String text;
  final Color? backgroundColor;
  final Color? textColor;
  final bool isCompact;
  // Optional text behavior controls for truncation/wrapping
  final int? maxLines;
  final TextOverflow? overflow;
  final bool? softWrap;

  const JyotiGPTBadge({
    super.key,
    required this.text,
    this.backgroundColor,
    this.textColor,
    this.isCompact = false,
    this.maxLines,
    this.overflow,
    this.softWrap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isCompact ? Spacing.sm : Spacing.md,
        vertical: isCompact ? Spacing.xs : Spacing.sm,
      ),
      decoration: BoxDecoration(
        color:
            backgroundColor ??
            context.jyotigptTheme.buttonPrimary.withValues(
              alpha: Alpha.badgeBackground,
            ),
        borderRadius: BorderRadius.circular(AppBorderRadius.badge),
      ),
      child: Text(
        text,
        style: AppTypography.small.copyWith(
          color: textColor ?? context.jyotigptTheme.buttonPrimary,
          fontWeight: FontWeight.w600,
        ),
        maxLines: maxLines,
        overflow: overflow,
        softWrap: softWrap,
      ),
    );
  }
}

class JyotiGPTChip extends StatelessWidget {
  final String label;
  final VoidCallback? onTap;
  final bool isSelected;
  final IconData? icon;
  final bool isCompact;

  const JyotiGPTChip({
    super.key,
    required this.label,
    this.onTap,
    this.isSelected = false,
    this.icon,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: isCompact ? Spacing.sm : Spacing.md,
          vertical: isCompact ? Spacing.xs : Spacing.sm,
        ),
        decoration: BoxDecoration(
          color: isSelected
              ? context.jyotigptTheme.buttonPrimary.withValues(
                  alpha: Alpha.highlight,
                )
              : context.jyotigptTheme.surfaceContainer,
          borderRadius: BorderRadius.circular(AppBorderRadius.chip),
          border: Border.all(
            color: isSelected
                ? context.jyotigptTheme.buttonPrimary.withValues(
                    alpha: Alpha.standard,
                  )
                : context.jyotigptTheme.dividerColor,
            width: BorderWidth.standard,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: isCompact ? IconSize.xs : IconSize.small,
                color: isSelected
                    ? context.jyotigptTheme.buttonPrimary
                    : context.jyotigptTheme.iconSecondary,
              ),
              SizedBox(width: Spacing.iconSpacing),
            ],
            Text(
              label,
              style: AppTypography.small.copyWith(
                color: isSelected
                    ? context.jyotigptTheme.buttonPrimary
                    : context.jyotigptTheme.textSecondary,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class JyotiGPTDivider extends StatelessWidget {
  final bool isCompact;
  final Color? color;

  const JyotiGPTDivider({super.key, this.isCompact = false, this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: BorderWidth.standard,
      color: color ?? context.jyotigptTheme.dividerColor,
      margin: EdgeInsets.symmetric(
        vertical: isCompact ? Spacing.sm : Spacing.md,
      ),
    );
  }
}

class JyotiGPTSpacer extends StatelessWidget {
  final double height;
  final bool isCompact;

  const JyotiGPTSpacer({super.key, this.height = 16, this.isCompact = false});

  @override
  Widget build(BuildContext context) {
    return SizedBox(height: isCompact ? height * 0.5 : height);
  }
}

/// Enhanced form field with better accessibility and validation
class AccessibleFormField extends StatelessWidget {
  final String? label;
  final String? hint;
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final VoidCallback? onTap;
  final bool obscureText;
  final bool enabled;
  final String? errorText;
  final int? maxLines;
  final Widget? suffixIcon;
  final Widget? prefixIcon;
  final TextInputType? keyboardType;
  final bool autofocus;
  final String? semanticLabel;
  final String? Function(String?)? validator;
  final bool isRequired;
  final bool isCompact;
  final Iterable<String>? autofillHints;

  const AccessibleFormField({
    super.key,
    this.label,
    this.hint,
    this.controller,
    this.onChanged,
    this.onSubmitted,
    this.onTap,
    this.obscureText = false,
    this.enabled = true,
    this.errorText,
    this.maxLines = 1,
    this.suffixIcon,
    this.prefixIcon,
    this.keyboardType,
    this.autofocus = false,
    this.semanticLabel,
    this.validator,
    this.isRequired = false,
    this.isCompact = false,
    this.autofillHints,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ...[
          Wrap(
            spacing: Spacing.textSpacing,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                label!,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.standard.copyWith(
                  fontWeight: FontWeight.w500,
                  color: context.jyotigptTheme.textPrimary,
                ),
              ),
              if (isRequired)
                Text(
                  '*',
                  style: AppTypography.standard.copyWith(
                    color: context.jyotigptTheme.error,
                    fontWeight: FontWeight.w600,
                  ),
                ),
            ],
          ),
          SizedBox(height: isCompact ? Spacing.xs : Spacing.sm),
        ],
        Semantics(
          label:
              semanticLabel ??
              label ??
              (AppLocalizations.of(context)?.inputField ?? 'Input field'),
          textField: true,
          child: TextFormField(
            controller: controller,
            onChanged: onChanged,
            onTap: onTap,
            onFieldSubmitted: onSubmitted,
            obscureText: obscureText,
            enabled: enabled,
            maxLines: maxLines,
            keyboardType: keyboardType,
            autofocus: autofocus,
            validator: validator,
            autofillHints: autofillHints,
            style: AppTypography.standard.copyWith(
              color: context.jyotigptTheme.textPrimary,
            ),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: AppTypography.standard.copyWith(
                color: context.jyotigptTheme.inputPlaceholder,
              ),
              filled: true,
              fillColor: context.jyotigptTheme.inputBackground,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.inputBorder,
                  width: BorderWidth.standard,
                ),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.inputBorder,
                  width: BorderWidth.standard,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.buttonPrimary,
                  width: BorderWidth.thick,
                ),
              ),
              errorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.error,
                  width: BorderWidth.standard,
                ),
              ),
              focusedErrorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppBorderRadius.input),
                borderSide: BorderSide(
                  color: context.jyotigptTheme.error,
                  width: BorderWidth.thick,
                ),
              ),
              contentPadding: EdgeInsets.symmetric(
                horizontal: isCompact ? Spacing.md : Spacing.inputPadding,
                vertical: isCompact ? Spacing.sm : Spacing.md,
              ),
              suffixIcon: suffixIcon,
              prefixIcon: prefixIcon,
              errorText: errorText,
              errorStyle: AppTypography.small.copyWith(
                color: context.jyotigptTheme.error,
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Enhanced section header with better typography
class JyotiGPTSectionHeader extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? action;
  final bool isCompact;

  const JyotiGPTSectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.action,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: isCompact ? Spacing.md : Spacing.pagePadding,
        vertical: isCompact ? Spacing.sm : Spacing.md,
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTypography.headlineSmallStyle.copyWith(
                    color: context.jyotigptTheme.textPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (subtitle != null) ...[
                  SizedBox(height: Spacing.textSpacing),
                  Text(
                    subtitle!,
                    style: AppTypography.standard.copyWith(
                      color: context.jyotigptTheme.textSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (action != null) ...[SizedBox(width: Spacing.md), action!],
        ],
      ),
    );
  }
}

/// Enhanced list item with better consistency
class JyotiGPTListItem extends StatelessWidget {
  final Widget leading;
  final Widget title;
  final Widget? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final bool isSelected;
  final bool isCompact;

  const JyotiGPTListItem({
    super.key,
    required this.leading,
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.isSelected = false,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.all(
          isCompact ? Spacing.sm : Spacing.listItemPadding,
        ),
        decoration: BoxDecoration(
          color: isSelected
              ? context.jyotigptTheme.buttonPrimary.withValues(
                  alpha: Alpha.highlight,
                )
              : Colors.transparent,
          borderRadius: BorderRadius.circular(AppBorderRadius.standard),
        ),
        child: Row(
          children: [
            leading,
            SizedBox(width: isCompact ? Spacing.sm : Spacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  title,
                  if (subtitle != null) ...[
                    SizedBox(height: Spacing.textSpacing),
                    subtitle!,
                  ],
                ],
              ),
            ),
            if (trailing != null) ...[
              SizedBox(width: isCompact ? Spacing.sm : Spacing.md),
              trailing!,
            ],
          ],
        ),
      ),
    );
  }
}
