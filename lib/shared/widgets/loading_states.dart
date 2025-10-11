import 'package:flutter/material.dart';
import '../theme/theme_extensions.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:io' show Platform;
import '../services/brand_service.dart';
import '../theme/color_tokens.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';

/// Standard loading indicators following JyotiGPT design patterns
class JyotiGPTLoading {
  // Private constructor to prevent instantiation
  JyotiGPTLoading._();

  /// Primary loading indicator
  static Widget primary({
    double size = IconSize.lg,
    Color? color,
    String? message,
  }) {
    return _LoadingIndicator(
      size: size,
      color: color,
      message: message,
      type: _LoadingType.primary,
    );
  }

  /// Inline loading for content areas
  static Widget inline({
    double size = IconSize.md,
    Color? color,
    String? message,
    BuildContext? context,
  }) {
    return _LoadingIndicator(
      size: size,
      color:
          color ??
          (context?.jyotigptTheme.loadingIndicator ??
              context?.jyotigptTheme.buttonPrimary ??
              BrandService.primaryBrandColor(context: context)),
      message: message,
      type: _LoadingType.inline,
    );
  }

  /// Button loading state
  static Widget button({
    double size = IconSize.sm,
    Color? color,
    BuildContext? context,
  }) {
    final tokens = context?.colorTokens ?? AppColorTokens.fallback();
    return _LoadingIndicator(
      size: size,
      color:
          color ??
          (context?.jyotigptTheme.buttonPrimaryText ??
              context?.jyotigptTheme.textPrimary ??
              tokens.neutralTone00),
      type: _LoadingType.button,
    );
  }

  /// Overlay loading for full screen
  static Widget overlay({String? message, bool darkBackground = true}) {
    return _LoadingOverlay(message: message, darkBackground: darkBackground);
  }

  /// Skeleton loading for content placeholders
  static Widget skeleton({
    double width = double.infinity,
    double height = 20,
    BorderRadius? borderRadius,
  }) {
    return _SkeletonLoader(
      width: width,
      height: height,
      borderRadius: borderRadius ?? BorderRadius.circular(AppBorderRadius.xs),
    );
  }

  /// List item skeleton
  static Widget listItemSkeleton({bool showAvatar = true, int lines = 2}) {
    return _ListItemSkeleton(showAvatar: showAvatar, lines: lines);
  }
}

enum _LoadingType { primary, inline, button }

class _LoadingIndicator extends StatelessWidget {
  final double size;
  final Color? color;
  final String? message;
  final _LoadingType type;

  const _LoadingIndicator({
    required this.size,
    this.color,
    this.message,
    required this.type,
  });

  @override
  Widget build(BuildContext context) {
    final resolvedColor = color ?? context.jyotigptTheme.loadingIndicator;

    Widget indicator;

    if (Platform.isIOS) {
      indicator = CupertinoActivityIndicator(
        color: resolvedColor,
        radius: size / 2,
      );
    } else {
      indicator = SizedBox(
        width: size,
        height: size,
        child: CircularProgressIndicator(
          strokeWidth: size / 8,
          valueColor: AlwaysStoppedAnimation<Color>(resolvedColor),
        ),
      );
    }

    if (message == null) {
      return indicator;
    }

    final spacing = type == _LoadingType.button ? Spacing.sm : Spacing.xs;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        indicator,
        SizedBox(height: spacing),
        Text(
          message!,
          style: TextStyle(
            color: color,
            fontSize: type == _LoadingType.button
                ? AppTypography.bodySmall
                : AppTypography.bodyLarge,
            fontWeight: FontWeight.w500,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _LoadingOverlay extends StatelessWidget {
  final String? message;
  final bool darkBackground;

  const _LoadingOverlay({this.message, required this.darkBackground});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: darkBackground
          ? context.jyotigptTheme.surfaceBackground.withValues(
              alpha: Alpha.strong,
            )
          : context.jyotigptTheme.surfaceBackground.withValues(
              alpha: Alpha.intense,
            ),
      child: Center(
        child: Container(
          padding: const EdgeInsets.all(Spacing.lg),
          decoration: BoxDecoration(
            color: darkBackground
                ? context.jyotigptTheme.surfaceBackground
                : context.jyotigptTheme.surfaceBackground,
            borderRadius: BorderRadius.circular(AppBorderRadius.lg),
            boxShadow: JyotiGPTShadows.high(context),
          ),
          child: JyotiGPTLoading.primary(
            size: IconSize.xl,
            color: context.jyotigptTheme.buttonPrimary,
            message: message,
          ),
        ),
      ),
    ).animate().fadeIn(duration: AnimationDuration.fast);
  }
}

class _SkeletonLoader extends StatefulWidget {
  final double width;
  final double height;
  final BorderRadius borderRadius;

  const _SkeletonLoader({
    required this.width,
    required this.height,
    required this.borderRadius,
  });

  @override
  State<_SkeletonLoader> createState() => _SkeletonLoaderState();
}

class _SkeletonLoaderState extends State<_SkeletonLoader>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: AnimationDuration.ultra,
      vsync: this,
    );
    _animation =
        Tween<double>(
          begin: AnimationValues.shimmerBegin,
          end: AnimationValues.shimmerEnd,
        ).animate(
          CurvedAnimation(
            parent: _controller,
            curve: AnimationCurves.easeInOut,
          ),
        );
    _controller.repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  void deactivate() {
    // Pause shimmer during deactivation to avoid rebuilds in wrong build scope
    _controller.stop();
    super.deactivate();
  }

  @override
  void activate() {
    super.activate();
    if (!_controller.isAnimating) {
      _controller.repeat();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: widget.width,
      height: widget.height,
      decoration: BoxDecoration(
        borderRadius: widget.borderRadius,
        color: context.jyotigptTheme.shimmerBase,
      ),
      child: AnimatedBuilder(
        animation: _animation,
        builder: (context, child) {
          return Container(
            decoration: BoxDecoration(
              borderRadius: widget.borderRadius,
              gradient: LinearGradient(
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
                colors: [
                  Colors.transparent,
                  context.jyotigptTheme.shimmerHighlight,
                  Colors.transparent,
                ],
                stops: [
                  (_animation.value - 0.3).clamp(0.0, 1.0),
                  _animation.value.clamp(0.0, 1.0),
                  (_animation.value + 0.3).clamp(0.0, 1.0),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ListItemSkeleton extends StatelessWidget {
  final bool showAvatar;
  final int lines;

  const _ListItemSkeleton({required this.showAvatar, required this.lines});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.xs,
      ),
      child: Row(
        children: [
          if (showAvatar) ...[
            JyotiGPTLoading.skeleton(
              width: TouchTarget.minimum,
              height: TouchTarget.minimum,
              borderRadius: BorderRadius.circular(AppBorderRadius.xl),
            ),
            const SizedBox(width: Spacing.xs),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: List.generate(lines, (index) {
                return Padding(
                  padding: EdgeInsets.only(
                    bottom: index < lines - 1 ? Spacing.sm : 0,
                  ),
                  child: JyotiGPTLoading.skeleton(
                    width: index == lines - 1 ? 150 : double.infinity,
                    height: index == 0 ? 16 : 14,
                  ),
                );
              }),
            ),
          ),
        ],
      ),
    );
  }
}

/// Loading state wrapper for async operations
class LoadingStateWrapper<T> extends StatelessWidget {
  final AsyncValue<T> asyncValue;
  final Widget Function(T data) builder;
  final Widget? loadingWidget;
  final Widget Function(Object error, StackTrace stackTrace)? errorBuilder;
  final bool showLoadingOverlay;

  const LoadingStateWrapper({
    super.key,
    required this.asyncValue,
    required this.builder,
    this.loadingWidget,
    this.errorBuilder,
    this.showLoadingOverlay = false,
  });

  @override
  Widget build(BuildContext context) {
    return asyncValue.when(
      data: builder,
      loading: () => showLoadingOverlay
          ? JyotiGPTLoading.overlay(
              message: AppLocalizations.of(context)!.loadingContent,
            )
          : loadingWidget ??
                JyotiGPTLoading.primary(
                  message: AppLocalizations.of(context)!.loadingContent,
                ),
      error: (error, stackTrace) {
        if (errorBuilder != null) {
          return errorBuilder!(error, stackTrace);
        }

        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Platform.isIOS
                    ? CupertinoIcons.exclamationmark_triangle
                    : Icons.error_outline,
                size: IconSize.xxl,
                color: context.jyotigptTheme.error,
              ),
              const SizedBox(height: Spacing.md),
              Text(
                AppLocalizations.of(context)!.errorMessage,
                style: TextStyle(
                  color: context.jyotigptTheme.textSecondary,
                  fontSize: AppTypography.headlineSmall,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: Spacing.sm),
              Text(
                error.toString(),
                style: TextStyle(
                  color: context.jyotigptTheme.textSecondary,
                  fontSize: AppTypography.bodySmall,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        );
      },
    );
  }
}

/// Button with loading state
class LoadingButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final Widget child;
  final bool isLoading;
  final bool isPrimary;

  const LoadingButton({
    super.key,
    required this.onPressed,
    required this.child,
    this.isLoading = false,
    this.isPrimary = true,
  });

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: isLoading ? null : onPressed,
      style: isPrimary
          ? FilledButton.styleFrom(
              backgroundColor: context.jyotigptTheme.buttonPrimary,
              foregroundColor: context.jyotigptTheme.buttonPrimaryText,
            )
          : null,
      child: isLoading ? JyotiGPTLoading.button(context: context) : child,
    );
  }
}

/// Refresh indicator with JyotiGPT styling
class JyotiGPTRefreshIndicator extends StatelessWidget {
  final Widget child;
  final Future<void> Function() onRefresh;

  const JyotiGPTRefreshIndicator({
    super.key,
    required this.child,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      color: context.jyotigptTheme.buttonPrimary,
      backgroundColor: context.jyotigptTheme.surfaceBackground,
      child: child,
    );
  }
}
