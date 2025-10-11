import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../shared/theme/theme_extensions.dart';
import '../error/enhanced_error_service.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';

/// Error boundary widget that catches and handles errors in child widgets
class ErrorBoundary extends ConsumerStatefulWidget {
  final Widget child;
  final Widget Function(Object error, StackTrace? stack)? errorBuilder;
  final void Function(Object error, StackTrace? stack)? onError;
  final bool showErrorDialog;
  final bool allowRetry;

  const ErrorBoundary({
    super.key,
    required this.child,
    this.errorBuilder,
    this.onError,
    this.showErrorDialog = false,
    this.allowRetry = true,
  });

  @override
  ConsumerState<ErrorBoundary> createState() => _ErrorBoundaryState();
}

class _ErrorBoundaryState extends ConsumerState<ErrorBoundary> {
  Object? _error;
  StackTrace? _stackTrace;
  bool _hasError = false;
  void Function(FlutterErrorDetails details)? _previousOnError;

  void _scheduleHandleError(Object error, StackTrace? stack) {
    // Defer to next frame to avoid setState during build exceptions
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _handleError(error, stack);
      }
    });
  }

  @override
  void initState() {
    super.initState();

    // Set up Flutter error handling for this widget
    _previousOnError = FlutterError.onError;
    FlutterError.onError = (FlutterErrorDetails details) {
      // Forward to any previously registered handler to avoid interfering
      _previousOnError?.call(details);
      // Defer handling to avoid setState during build
      _scheduleHandleError(details.exception, details.stack);
    };
  }

  @override
  void dispose() {
    // Restore previous error handler to avoid leaking global state
    if (FlutterError.onError != _previousOnError) {
      FlutterError.onError = _previousOnError;
    }
    super.dispose();
  }

  void _handleError(Object error, StackTrace? stack) {
    // Log error
    enhancedErrorService.logError(
      error,
      context: 'ErrorBoundary',
      stackTrace: stack,
    );

    // Call custom error handler if provided
    widget.onError?.call(error, stack);

    // Update state
    if (mounted) {
      setState(() {
        _error = error;
        _stackTrace = stack;
        _hasError = true;
      });

      // Show error dialog if requested
      if (widget.showErrorDialog && context.mounted) {
        enhancedErrorService.showErrorDialog(context, error);
      }
    }
  }

  void _retry() {
    setState(() {
      _error = null;
      _stackTrace = null;
      _hasError = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_hasError && _error != null) {
      // Use custom error builder if provided
      if (widget.errorBuilder != null) {
        return widget.errorBuilder!(_error!, _stackTrace);
      }

      // Default error UI
      // Respect ambient text direction when available; fall back to LTR.
      TextDirection direction;
      try {
        direction = Directionality.of(context);
      } catch (_) {
        direction = TextDirection.ltr;
      }

      return Directionality(
        textDirection: direction,
        child: Scaffold(
          backgroundColor: context.jyotigptTheme.surfaceBackground,
          body: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.error_outline,
                    size: 64,
                    color: context.jyotigptTheme.error,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    AppLocalizations.of(context)?.errorMessage ??
                        'An unexpected error occurred',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: context.jyotigptTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    enhancedErrorService.getUserMessage(_error!),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: context.jyotigptTheme.textSecondary,
                    ),
                  ),
                  if (widget.allowRetry) ...[
                    const SizedBox(height: 24),
                    FilledButton.icon(
                      onPressed: _retry,
                      icon: const Icon(Icons.refresh),
                      label: Text(
                        AppLocalizations.of(context)?.retry ?? 'Retry',
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      );
    }

    // Wrap child in error handler
    return Builder(
      builder: (context) {
        ErrorWidget.builder = (FlutterErrorDetails details) {
          // Defer handling to avoid setState during build of error widgets
          _scheduleHandleError(details.exception, details.stack);
          return const SizedBox.shrink();
        };

        try {
          return widget.child;
        } catch (error, stack) {
          // Defer handling to avoid setState during build
          _scheduleHandleError(error, stack);
          return const SizedBox.shrink();
        }
      },
    );
  }
}

/// Widget that handles async operations with proper error handling
class AsyncErrorBoundary extends ConsumerWidget {
  final Future<Widget> Function() builder;
  final Widget? loadingWidget;
  final Widget Function(Object error)? errorWidget;
  final bool showRetry;

  const AsyncErrorBoundary({
    super.key,
    required this.builder,
    this.loadingWidget,
    this.errorWidget,
    this.showRetry = true,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FutureBuilder<Widget>(
      future: builder(),
      builder: (context, snapshot) {
        // Loading state
        if (snapshot.connectionState == ConnectionState.waiting) {
          return loadingWidget ??
              const Center(child: CircularProgressIndicator());
        }

        // Error state
        if (snapshot.hasError) {
          final error = snapshot.error!;

          // Log error
          enhancedErrorService.logError(
            error,
            context: 'AsyncErrorBoundary',
            stackTrace: snapshot.stackTrace,
          );

          // Use custom error widget if provided
          if (errorWidget != null) {
            return errorWidget!(error);
          }

          // Default error widget
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.error_outline,
                    size: 48,
                    color: context.jyotigptTheme.error,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    enhancedErrorService.getUserMessage(error),
                    textAlign: TextAlign.center,
                  ),
                  if (showRetry) ...[
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: () {
                        // Force rebuild to retry
                        (context as Element).markNeedsBuild();
                      },
                      icon: const Icon(Icons.refresh),
                      label: Text(
                        AppLocalizations.of(context)?.retry ?? 'Retry',
                      ),
                    ),
                  ],
                ],
              ),
            ),
          );
        }

        // Success state
        return snapshot.data ?? const SizedBox.shrink();
      },
    );
  }
}

/// Stream error boundary for handling stream errors
class StreamErrorBoundary<T> extends ConsumerWidget {
  final Stream<T> stream;
  final Widget Function(T data) builder;
  final Widget? loadingWidget;
  final Widget Function(Object error)? errorWidget;
  final T? initialData;

  const StreamErrorBoundary({
    super.key,
    required this.stream,
    required this.builder,
    this.loadingWidget,
    this.errorWidget,
    this.initialData,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return StreamBuilder<T>(
      stream: stream,
      initialData: initialData,
      builder: (context, snapshot) {
        // Error state
        if (snapshot.hasError) {
          final error = snapshot.error!;

          // Log error
          enhancedErrorService.logError(
            error,
            context: 'StreamErrorBoundary',
            stackTrace: snapshot.stackTrace,
          );

          // Use custom error widget if provided
          if (errorWidget != null) {
            return errorWidget!(error);
          }

          // Default error widget
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.error_outline,
                    size: 48,
                    color: context.jyotigptTheme.error,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    enhancedErrorService.getUserMessage(error),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          );
        }

        // Loading state
        if (!snapshot.hasData) {
          return loadingWidget ??
              const Center(child: CircularProgressIndicator());
        }

        // Success state
        return builder(snapshot.data as T);
      },
    );
  }
}
