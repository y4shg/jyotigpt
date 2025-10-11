import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'api_error.dart';
import 'error_parser.dart';
import '../utils/debug_logger.dart';

/// Comprehensive API error handler with structured error parsing
/// Handles all types of API errors and converts them to standardized format
class ApiErrorHandler {
  static final ApiErrorHandler _instance = ApiErrorHandler._internal();
  factory ApiErrorHandler() => _instance;
  ApiErrorHandler._internal();

  final ErrorParser _errorParser = ErrorParser();

  /// Transform any exception into standardized ApiError
  ApiError transformError(
    dynamic error, {
    String? endpoint,
    String? method,
    Map<String, dynamic>? requestData,
  }) {
    try {
      if (error is DioException) {
        return _handleDioException(error, endpoint: endpoint, method: method);
      } else if (error is ApiError) {
        return error;
      } else {
        return ApiError.unknown(
          message: 'An unexpected error occurred',
          originalError: error,
          technical: error.toString(),
        );
      }
    } catch (e) {
      // Fallback error if transformation itself fails
      DebugLogger.log(
        'ApiErrorHandler: Error transforming exception: $e',
        scope: 'api/error-handler',
      );
      return ApiError.unknown(
        message: 'A system error occurred',
        originalError: error,
        technical: 'Error transformation failed: $e',
      );
    }
  }

  /// Handle DioException with detailed error parsing
  ApiError _handleDioException(
    DioException dioError, {
    String? endpoint,
    String? method,
  }) {
    final statusCode = dioError.response?.statusCode;
    final responseData = dioError.response?.data;
    final requestPath = endpoint ?? dioError.requestOptions.path;
    final httpMethod = method ?? dioError.requestOptions.method;

    // Log error details for debugging
    _logErrorDetails(dioError, requestPath, httpMethod);

    switch (dioError.type) {
      case DioExceptionType.connectionTimeout:
        return ApiError.timeout(
          message: 'Connection timeout - please check your internet connection',
          endpoint: requestPath,
          method: httpMethod,
          timeoutDuration: dioError.requestOptions.connectTimeout,
        );

      case DioExceptionType.sendTimeout:
        return ApiError.timeout(
          message: 'Request send timeout - the upload took too long',
          endpoint: requestPath,
          method: httpMethod,
          timeoutDuration: dioError.requestOptions.sendTimeout,
        );

      case DioExceptionType.receiveTimeout:
        return ApiError.timeout(
          message: 'Response timeout - the server took too long to respond',
          endpoint: requestPath,
          method: httpMethod,
          timeoutDuration: dioError.requestOptions.receiveTimeout,
        );

      case DioExceptionType.badCertificate:
        return ApiError.security(
          message:
              'Security certificate error - unable to verify server identity',
          endpoint: requestPath,
          method: httpMethod,
        );

      case DioExceptionType.connectionError:
        return ApiError.network(
          message:
              'Network connection error - please check your internet connection',
          endpoint: requestPath,
          method: httpMethod,
          originalError: dioError,
        );

      case DioExceptionType.cancel:
        return ApiError.cancelled(
          message: 'Request was cancelled',
          endpoint: requestPath,
          method: httpMethod,
        );

      case DioExceptionType.badResponse:
        return _handleBadResponse(
          dioError,
          requestPath,
          httpMethod,
          statusCode,
          responseData,
        );

      case DioExceptionType.unknown:
        return ApiError.unknown(
          message: 'An unexpected network error occurred',
          endpoint: requestPath,
          method: httpMethod,
          originalError: dioError,
          technical: dioError.message,
        );
    }
  }

  /// Handle bad response errors with detailed status code analysis
  ApiError _handleBadResponse(
    DioException dioError,
    String requestPath,
    String httpMethod,
    int? statusCode,
    dynamic responseData,
  ) {
    if (statusCode == null) {
      return ApiError.server(
        message: 'Invalid server response',
        endpoint: requestPath,
        method: httpMethod,
        statusCode: null,
      );
    }

    switch (statusCode) {
      case 400:
        return _handleBadRequest(
          dioError,
          requestPath,
          httpMethod,
          responseData,
        );

      case 401:
        return ApiError.authentication(
          message: 'Authentication failed - please sign in again',
          endpoint: requestPath,
          method: httpMethod,
          statusCode: statusCode,
        );

      case 403:
        return ApiError.authorization(
          message: 'Access denied - you don\'t have permission for this action',
          endpoint: requestPath,
          method: httpMethod,
          statusCode: statusCode,
        );

      case 404:
        return ApiError.notFound(
          message: 'The requested resource was not found',
          endpoint: requestPath,
          method: httpMethod,
          statusCode: statusCode,
        );

      case 422:
        return _handleValidationError(
          dioError,
          requestPath,
          httpMethod,
          responseData,
        );

      case 429:
        return ApiError.rateLimit(
          message: 'Too many requests - please wait before trying again',
          endpoint: requestPath,
          method: httpMethod,
          statusCode: statusCode,
          retryAfter: _extractRetryAfter(dioError.response?.headers),
        );

      default:
        if (statusCode >= 500) {
          return _handleServerError(
            dioError,
            requestPath,
            httpMethod,
            statusCode,
            responseData,
          );
        } else {
          return ApiError.client(
            message: 'Client error occurred',
            endpoint: requestPath,
            method: httpMethod,
            statusCode: statusCode,
            details: _errorParser.parseErrorResponse(responseData),
          );
        }
    }
  }

  /// Handle 400 Bad Request with detailed parsing
  ApiError _handleBadRequest(
    DioException dioError,
    String requestPath,
    String httpMethod,
    dynamic responseData,
  ) {
    final parsedError = _errorParser.parseErrorResponse(responseData);

    return ApiError.badRequest(
      message:
          parsedError.message ?? 'Invalid request - please check your input',
      endpoint: requestPath,
      method: httpMethod,
      details: parsedError,
    );
  }

  /// Handle 422 Validation Error with field-specific parsing
  ApiError _handleValidationError(
    DioException dioError,
    String requestPath,
    String httpMethod,
    dynamic responseData,
  ) {
    final parsedError = _errorParser.parseValidationError(responseData);

    return ApiError.validation(
      message: 'Validation failed - please check your input',
      endpoint: requestPath,
      method: httpMethod,
      fieldErrors: parsedError.fieldErrors,
      details: parsedError,
    );
  }

  /// Handle server errors (5xx)
  ApiError _handleServerError(
    DioException dioError,
    String requestPath,
    String httpMethod,
    int statusCode,
    dynamic responseData,
  ) {
    final parsedError = _errorParser.parseErrorResponse(responseData);

    String message;
    switch (statusCode) {
      case 500:
        message = 'Internal server error - please try again later';
        break;
      case 502:
        message = 'Bad gateway - the server is temporarily unavailable';
        break;
      case 503:
        message = 'Service unavailable - the server is temporarily down';
        break;
      case 504:
        message = 'Gateway timeout - the server took too long to respond';
        break;
      default:
        message = 'Server error occurred - please try again later';
    }

    return ApiError.server(
      message: message,
      endpoint: requestPath,
      method: httpMethod,
      statusCode: statusCode,
      details: parsedError,
    );
  }

  /// Extract retry-after header for rate limiting
  Duration? _extractRetryAfter(Headers? headers) {
    if (headers == null) return null;

    final retryAfterHeader =
        headers.value('retry-after') ??
        headers.value('Retry-After') ??
        headers.value('X-RateLimit-Reset-After');

    if (retryAfterHeader != null) {
      final seconds = int.tryParse(retryAfterHeader);
      if (seconds != null) {
        return Duration(seconds: seconds);
      }
    }

    return null;
  }

  /// Log error details for debugging and monitoring
  void _logErrorDetails(
    DioException dioError,
    String requestPath,
    String httpMethod,
  ) {
    if (kDebugMode) {
      DebugLogger.log('🔴 API Error Details:', scope: 'api/error-handler');
      DebugLogger.log(
        '  Method: ${httpMethod.toUpperCase()}',
        scope: 'api/error-handler',
      );
      DebugLogger.log('  Endpoint: $requestPath', scope: 'api/error-handler');
      DebugLogger.log('  Type: ${dioError.type}', scope: 'api/error-handler');
      DebugLogger.log(
        '  Status: ${dioError.response?.statusCode}',
        scope: 'api/error-handler',
      );

      if (dioError.response?.data != null) {
        DebugLogger.error('Response data available (truncated for security)');
      }

      if (dioError.requestOptions.data != null) {
        DebugLogger.log(
          '  Request Data: ${dioError.requestOptions.data}',
          scope: 'api/error-handler',
        );
      }

      DebugLogger.log(
        '  Error: ${dioError.message}',
        scope: 'api/error-handler',
      );
    }

    // In production, you would send this to your error tracking service
    // FirebaseCrashlytics.instance.recordError(dioError, stackTrace);
    // Sentry.captureException(dioError);
  }

  /// Check if error is retryable
  bool isRetryable(ApiError error) {
    switch (error.type) {
      case ApiErrorType.timeout:
      case ApiErrorType.network:
      case ApiErrorType.server:
        return true;
      case ApiErrorType.rateLimit:
        return true; // Can retry after waiting
      case ApiErrorType.authentication:
        return false; // Need new token
      case ApiErrorType.authorization:
      case ApiErrorType.notFound:
      case ApiErrorType.validation:
      case ApiErrorType.badRequest:
        return false; // Client errors aren't retryable
      case ApiErrorType.cancelled:
      case ApiErrorType.security:
      case ApiErrorType.unknown:
        return false;
    }
  }

  /// Get suggested retry delay for retryable errors
  Duration? getRetryDelay(ApiError error) {
    if (!isRetryable(error)) return null;

    switch (error.type) {
      case ApiErrorType.rateLimit:
        return error.retryAfter ?? const Duration(minutes: 1);
      case ApiErrorType.timeout:
        return const Duration(seconds: 5);
      case ApiErrorType.network:
        return const Duration(seconds: 3);
      case ApiErrorType.server:
        return const Duration(seconds: 10);
      default:
        return const Duration(seconds: 5);
    }
  }

  /// Get user-friendly error message with actionable advice
  String getUserMessage(ApiError error) {
    final baseMessage = error.message;

    // Add actionable advice based on error type
    switch (error.type) {
      case ApiErrorType.network:
        return '$baseMessage\n\nPlease check your internet connection and try again.';
      case ApiErrorType.timeout:
        return '$baseMessage\n\nThis might be due to a slow connection. Try again in a moment.';
      case ApiErrorType.authentication:
        return '$baseMessage\n\nPlease sign in again to continue.';
      case ApiErrorType.authorization:
        return '$baseMessage\n\nContact support if you believe this is an error.';
      case ApiErrorType.validation:
        return '$baseMessage\n\nPlease correct the highlighted fields and try again.';
      case ApiErrorType.rateLimit:
        final delay = error.retryAfter;
        if (delay != null) {
          final minutes = delay.inMinutes;
          final seconds = delay.inSeconds % 60;
          return '$baseMessage\n\nPlease wait ${minutes > 0 ? '${minutes}m ' : ''}${seconds}s before trying again.';
        }
        return '$baseMessage\n\nPlease wait a moment before trying again.';
      case ApiErrorType.server:
        return '$baseMessage\n\nOur servers are experiencing issues. Please try again in a few minutes.';
      default:
        return baseMessage;
    }
  }
}
