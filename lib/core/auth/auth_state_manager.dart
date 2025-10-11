import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
// Types are used through app_providers.dart
import '../providers/app_providers.dart';
import '../models/user.dart';
import 'token_validator.dart';
import 'auth_cache_manager.dart';
import '../utils/debug_logger.dart';

part 'auth_state_manager.g.dart';

/// Comprehensive auth state representation
@immutable
class AuthState {
  const AuthState({
    required this.status,
    this.token,
    this.user,
    this.error,
    this.isLoading = false,
  });

  final AuthStatus status;
  final String? token;
  final User? user;
  final String? error;
  final bool isLoading;

  bool get isAuthenticated =>
      status == AuthStatus.authenticated && token != null;
  bool get hasValidToken => token != null && token!.isNotEmpty;
  bool get needsLogin =>
      status == AuthStatus.unauthenticated || status == AuthStatus.tokenExpired;

  AuthState copyWith({
    AuthStatus? status,
    String? token,
    User? user,
    String? error,
    bool? isLoading,
    bool clearToken = false,
    bool clearUser = false,
    bool clearError = false,
  }) {
    return AuthState(
      status: status ?? this.status,
      token: clearToken ? null : (token ?? this.token),
      user: clearUser ? null : (user ?? this.user),
      error: clearError ? null : (error ?? this.error),
      isLoading: isLoading ?? this.isLoading,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is AuthState &&
        other.status == status &&
        other.token == token &&
        other.user == user &&
        other.error == error &&
        other.isLoading == isLoading;
  }

  @override
  int get hashCode => Object.hash(status, token, user, error, isLoading);

  @override
  String toString() =>
      'AuthState(status: $status, hasToken: ${token != null}, hasUser: ${user != null}, error: $error, isLoading: $isLoading)';
}

enum AuthStatus {
  initial,
  loading,
  authenticated,
  unauthenticated,
  tokenExpired,
  error,
}

/// Unified auth state manager - single source of truth for all auth operations
@Riverpod(keepAlive: true)
class AuthStateManager extends _$AuthStateManager {
  final AuthCacheManager _cacheManager = AuthCacheManager();
  Future<bool>? _silentLoginFuture;

  AuthState get _current =>
      state.asData?.value ?? const AuthState(status: AuthStatus.initial);

  void _set(AuthState next, {bool cache = false}) {
    state = AsyncValue.data(next);
    if (cache) {
      _cacheManager.cacheAuthState(next);
    }
  }

  void _update(
    AuthState Function(AuthState current) transform, {
    bool cache = false,
  }) {
    final next = transform(_current);
    _set(next, cache: cache);
  }

  @override
  Future<AuthState> build() async {
    await _initialize();
    return _current;
  }

  /// Initialize auth state from storage
  Future<void> _initialize() async {
    _update(
      (current) =>
          current.copyWith(status: AuthStatus.loading, isLoading: true),
    );

    try {
      final storage = ref.read(optimizedStorageServiceProvider);
      final token = await storage.getAuthToken();

      if (token != null && token.isNotEmpty) {
        DebugLogger.auth('Found stored token during initialization');
        // Fast path: trust token format to avoid blocking startup on network
        final formatOk = _isValidTokenFormat(token);
        if (formatOk) {
          _update(
            (current) => current.copyWith(
              status: AuthStatus.authenticated,
              token: token,
              isLoading: false,
              clearError: true,
            ),
            cache: true,
          );

          // Update API service with token and kick off dependent background work
          _updateApiServiceToken(token);
          _preloadDefaultModel();
          _loadUserData();
          _prefetchConversations();

          // Background server validation; if it fails, invalidate token gracefully
          Future.microtask(() async {
            try {
              final ok = await _validateToken(token);
              DebugLogger.auth('Deferred token validation result: $ok');
              if (!ok) {
                await onTokenInvalidated();
              }
            } catch (_) {}
          });
        } else {
          // Token format invalid; clear and require login
          DebugLogger.auth('Token format invalid, deleting token');
          await storage.deleteAuthToken();
          _update(
            (current) => current.copyWith(
              status: AuthStatus.unauthenticated,
              isLoading: false,
              clearToken: true,
              clearError: true,
            ),
          );
        }
      } else {
        _update(
          (current) => current.copyWith(
            status: AuthStatus.unauthenticated,
            isLoading: false,
            clearToken: true,
            clearError: true,
          ),
        );
      }
    } catch (e) {
      DebugLogger.error('auth-init-failed', scope: 'auth/state', error: e);
      _update(
        (current) => current.copyWith(
          status: AuthStatus.error,
          error: 'Failed to initialize auth: $e',
          isLoading: false,
        ),
      );
    }
  }

  /// Perform login with API key
  Future<bool> loginWithApiKey(
    String apiKey, {
    bool rememberCredentials = false,
  }) async {
    _update(
      (current) => current.copyWith(
        status: AuthStatus.loading,
        isLoading: true,
        clearError: true,
      ),
    );

    try {
      // Validate API key format
      if (apiKey.trim().isEmpty) {
        throw Exception('API key cannot be empty');
      }

      // Ensure API service is available
      await _ensureApiServiceAvailable();
      final api = ref.read(apiServiceProvider);
      if (api == null) {
        throw Exception('No server connection available');
      }

      // Use API key directly as Bearer token
      final tokenStr = apiKey.trim();

      // Validate token format (consistent with credentials method)
      if (!_isValidTokenFormat(tokenStr)) {
        throw Exception('Invalid API key format');
      }

      // Update API service with the API key
      _updateApiServiceToken(tokenStr);

      // Validate by attempting to fetch user info
      try {
        await api.getCurrentUser(); // Just validate, don't store user data yet

        // Save token to storage
        final storage = ref.read(optimizedStorageServiceProvider);
        await storage.saveAuthToken(tokenStr);

        // Save API key if requested (for convenience, though less secure than credentials)
        if (rememberCredentials) {
          final activeServer = await ref.read(activeServerProvider.future);
          if (activeServer != null) {
            // Store API key as a special credential type
            await storage.saveCredentials(
              serverId: activeServer.id,
              username:
                  'api_key_user', // Special username to indicate API key auth
              password: tokenStr, // Store API key in password field
            );
            await storage.setRememberCredentials(true);
          }
        }

        // Update state (without user data initially)
        _update(
          (current) => current.copyWith(
            status: AuthStatus.authenticated,
            token: tokenStr,
            isLoading: false,
            clearError: true,
          ),
          cache: true,
        );

        // Update API service with token and kick off dependent background work
        _updateApiServiceToken(tokenStr);
        _preloadDefaultModel();

        // Load user data in background (consistent with credentials method)
        _loadUserData();
        _prefetchConversations();

        DebugLogger.auth('API key login successful');
        return true;
      } catch (e) {
        // If user fetch fails, the API key might be invalid
        throw Exception('Invalid API key or insufficient permissions');
      }
    } catch (e) {
      DebugLogger.error('api-key-login-failed', scope: 'auth/state', error: e);
      _update(
        (current) => current.copyWith(
          status: AuthStatus.error,
          error: e.toString(),
          isLoading: false,
          clearToken: true,
        ),
      );
      return false;
    }
  }

  /// Perform login with credentials
  Future<bool> login(
    String username,
    String password, {
    bool rememberCredentials = false,
  }) async {
    _update(
      (current) => current.copyWith(
        status: AuthStatus.loading,
        isLoading: true,
        clearError: true,
      ),
    );

    try {
      // Ensure API service is available (active server/provider rebuild race)
      await _ensureApiServiceAvailable();
      final api = ref.read(apiServiceProvider);
      if (api == null) {
        throw Exception('No server connection available');
      }

      // Perform login API call
      final response = await api.login(username, password);

      // Extract and validate token
      final token = response['token'] ?? response['access_token'];
      if (token == null || token.toString().trim().isEmpty) {
        throw Exception('No authentication token received');
      }

      final tokenStr = token.toString();
      if (!_isValidTokenFormat(tokenStr)) {
        throw Exception('Invalid authentication token format');
      }

      // Save token to storage
      final storage = ref.read(optimizedStorageServiceProvider);
      await storage.saveAuthToken(tokenStr);

      // Save credentials if requested
      if (rememberCredentials) {
        final activeServer = await ref.read(activeServerProvider.future);
        if (activeServer != null) {
          await storage.saveCredentials(
            serverId: activeServer.id,
            username: username,
            password: password,
          );
          await storage.setRememberCredentials(true);
        }
      }

      // Update state and API service
      _update(
        (current) => current.copyWith(
          status: AuthStatus.authenticated,
          token: tokenStr,
          isLoading: false,
          clearError: true,
        ),
        cache: true,
      );

      _updateApiServiceToken(tokenStr);
      _preloadDefaultModel();

      // Load user data in background
      _loadUserData();
      _prefetchConversations();

      DebugLogger.auth('Login successful');
      return true;
    } catch (e) {
      DebugLogger.error('login-failed', scope: 'auth/state', error: e);
      _update(
        (current) => current.copyWith(
          status: AuthStatus.error,
          error: e.toString(),
          isLoading: false,
          clearToken: true,
        ),
      );
      return false;
    }
  }

  /// Wait briefly until the API service becomes available
  Future<void> _ensureApiServiceAvailable({
    Duration timeout = const Duration(seconds: 2),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      final api = ref.read(apiServiceProvider);
      if (api != null) return;
      await Future.delayed(const Duration(milliseconds: 50));
    }
  }

  /// Perform silent auto-login with saved credentials
  Future<bool> silentLogin() async {
    // Coalesce concurrent calls (e.g., UI + interceptor retry)
    if (_silentLoginFuture != null) {
      return await _silentLoginFuture!;
    }
    final thisAttempt = _performSilentLogin();
    _silentLoginFuture = thisAttempt;
    try {
      return await thisAttempt;
    } finally {
      if (identical(_silentLoginFuture, thisAttempt)) {
        _silentLoginFuture = null;
      }
    }
  }

  Future<bool> _performSilentLogin() async {
    _update(
      (current) => current.copyWith(
        status: AuthStatus.loading,
        isLoading: true,
        clearError: true,
      ),
    );

    try {
      final storage = ref.read(optimizedStorageServiceProvider);
      final savedCredentials = await storage.getSavedCredentials();

      if (savedCredentials == null) {
        _update(
          (current) => current.copyWith(
            status: AuthStatus.unauthenticated,
            isLoading: false,
            clearError: true,
          ),
        );
        return false;
      }

      final serverId = savedCredentials['serverId']!;
      final username = savedCredentials['username']!;
      final password = savedCredentials['password']!;

      // Ensure the saved server still exists before switching
      final serverConfigs = await ref.read(serverConfigsProvider.future);
      final hasServer = serverConfigs.any((config) => config.id == serverId);

      if (!hasServer) {
        await storage.deleteSavedCredentials();
        await storage.setActiveServerId(null);
        ref.invalidate(serverConfigsProvider);
        ref.invalidate(activeServerProvider);

        _update(
          (current) => current.copyWith(
            status: AuthStatus.error,
            error:
                'Saved server configuration is no longer available. Please reconnect.',
            isLoading: false,
          ),
        );
        return false;
      }

      // Set active server once we know it exists
      await storage.setActiveServerId(serverId);
      ref.invalidate(activeServerProvider);

      // Wait for server connection
      final activeServer = await ref.read(activeServerProvider.future);
      if (activeServer == null) {
        await storage.setActiveServerId(null);
        _update(
          (current) => current.copyWith(
            status: AuthStatus.error,
            error: 'Server configuration not found',
            isLoading: false,
          ),
        );
        return false;
      }

      // Attempt login (detect API key vs normal credentials)
      if (username == 'api_key_user') {
        // This is a saved API key
        return await loginWithApiKey(password, rememberCredentials: false);
      } else {
        // Normal username/password credentials
        return await login(username, password, rememberCredentials: false);
      }
    } catch (e) {
      DebugLogger.error('silent-login-failed', scope: 'auth/state', error: e);

      // Clear invalid credentials on auth errors
      if (e.toString().contains('401') ||
          e.toString().contains('403') ||
          e.toString().contains('authentication') ||
          e.toString().contains('unauthorized')) {
        final storage = ref.read(optimizedStorageServiceProvider);
        await storage.deleteSavedCredentials();
      }

      _update(
        (current) => current.copyWith(
          status: AuthStatus.unauthenticated,
          error: e.toString(),
          isLoading: false,
          clearToken: true,
        ),
      );
      return false;
    }
  }

  /// Handle token invalidation (called by API service)
  Future<void> onTokenInvalidated() async {
    // Avoid spamming logs if multiple requests invalidate at once
    final reloginInProgress = _silentLoginFuture != null;
    if (!reloginInProgress) {
      DebugLogger.auth('Auth token invalidated');
    }

    // Clear token from storage
    final storage = ref.read(optimizedStorageServiceProvider);
    await storage.deleteAuthToken();
    _updateApiServiceToken(null);

    // Update state
    _update(
      (current) => current.copyWith(
        status: AuthStatus.tokenExpired,
        clearToken: true,
        clearUser: true,
        clearError: true,
      ),
    );

    // Attempt silent re-login if credentials are available
    final hasCredentials = await storage.getSavedCredentials() != null;
    if (hasCredentials) {
      if (!reloginInProgress) {
        DebugLogger.auth('Attempting silent re-login after token invalidation');
      }
      await silentLogin();
    }
  }

  /// Logout user
  Future<void> logout() async {
    _update(
      (current) =>
          current.copyWith(status: AuthStatus.loading, isLoading: true),
    );

    try {
      // Call server logout if possible
      final api = ref.read(apiServiceProvider);
      if (api != null) {
        try {
          await api.logout();
        } catch (e) {
          DebugLogger.warning(
            'server-logout-failed',
            scope: 'auth/state',
            data: {'error': e.toString()},
          );
        }
      }

      // Clear all local auth data
      final storage = ref.read(optimizedStorageServiceProvider);
      await storage.clearAuthData();
      _updateApiServiceToken(null);

      // Clear active server to force return to server connection page
      await storage.setActiveServerId(null);
      ref.invalidate(activeServerProvider);

      // Update state
      _update(
        (current) => current.copyWith(
          status: AuthStatus.unauthenticated,
          isLoading: false,
          clearToken: true,
          clearUser: true,
          clearError: true,
        ),
      );

      DebugLogger.auth('Logout complete');
    } catch (e) {
      DebugLogger.error('logout-failed', scope: 'auth/state', error: e);
      // Even if logout fails, clear local state
      final storage = ref.read(optimizedStorageServiceProvider);
      await storage.setActiveServerId(null);
      ref.invalidate(activeServerProvider);

      _update(
        (current) => current.copyWith(
          status: AuthStatus.unauthenticated,
          isLoading: false,
          clearToken: true,
          clearUser: true,
          error: 'Logout error: $e',
        ),
      );
      _updateApiServiceToken(null);
    }
  }

  /// Preload the default model as soon as authentication succeeds.
  void _preloadDefaultModel() {
    Future.microtask(() async {
      if (!ref.mounted) return;
      try {
        await ref.read(defaultModelProvider.future);
        DebugLogger.auth('Default model preload requested');
      } catch (e) {
        if (!ref.mounted) return;
        DebugLogger.warning(
          'default-model-preload-failed',
          scope: 'auth/state',
          data: {'error': e.toString()},
        );
      }
    });
  }

  /// Prime the conversations list so navigation drawers show real data after login.
  void _prefetchConversations() {
    Future.microtask(() {
      if (!ref.mounted) return;
      try {
        refreshConversationsCache(ref, includeFolders: true);
        DebugLogger.auth('Conversations prefetch scheduled');
      } catch (e) {
        if (!ref.mounted) return;
        DebugLogger.warning(
          'conversation-prefetch-failed',
          scope: 'auth/state',
          data: {'error': e.toString()},
        );
      }
    });
  }

  /// Load user data in background with JWT extraction fallback
  Future<void> _loadUserData() async {
    try {
      // First try to extract user info from JWT token if available
      final current = _current;
      if (current.token != null) {
        final jwtUserInfo = TokenValidator.extractUserInfo(current.token!);
        if (jwtUserInfo != null) {
          final userFromJwt = _userFromJwtClaims(jwtUserInfo);
          if (userFromJwt != null) {
            DebugLogger.auth('Extracted user info from JWT token');
            _update((current) => current.copyWith(user: userFromJwt));
          }

          // Still try to load from server in background for complete data
          Future.microtask(() => _loadServerUserData());
          return;
        }
      }

      // Fall back to server data loading
      await _loadServerUserData();
    } catch (e) {
      DebugLogger.warning(
        'user-data-load-failed',
        scope: 'auth/state',
        data: {'error': e.toString()},
      );
      // Don't update state on user data load failure
    }
  }

  /// Load complete user data from server
  Future<void> _loadServerUserData() async {
    try {
      final api = ref.read(apiServiceProvider);
      final current = _current;
      if (api != null && current.isAuthenticated) {
        // Check if we already have user data from token validation
        if (current.user != null) {
          DebugLogger.auth('user-data-present-from-token', scope: 'auth/state');
          return;
        }

        final user = await api.getCurrentUser();
        _update((current) => current.copyWith(user: user));
        DebugLogger.auth('Loaded complete user data from server');
      }
    } catch (e) {
      DebugLogger.warning(
        'server-user-data-load-failed',
        scope: 'auth/state',
        data: {'error': e.toString()},
      );
      // Don't update state on server data load failure - keep JWT data if available
    }
  }

  /// Update API service with current token
  void _updateApiServiceToken(String? token) {
    final api = ref.read(apiServiceProvider);
    api?.updateAuthToken(token);
  }

  /// Validate token format using advanced validation
  bool _isValidTokenFormat(String token) {
    final result = TokenValidator.validateTokenFormat(token);
    return result.isValid;
  }

  /// Validate token with comprehensive validation (format + server)
  Future<bool> _validateToken(String token) async {
    // Check cache first
    final cachedResult = TokenValidationCache.getCachedResult(token);
    if (cachedResult != null) {
      DebugLogger.auth(
        'Using cached token validation result: ${cachedResult.isValid}',
      );
      return cachedResult.isValid;
    }

    // Fast format validation first
    final formatResult = TokenValidator.validateTokenFormat(token);
    if (!formatResult.isValid) {
      DebugLogger.warning(
        'token-format-invalid',
        scope: 'auth/state',
        data: {'message': formatResult.message},
      );
      TokenValidationCache.cacheResult(token, formatResult);
      return false;
    }

    // If format is valid but token is expiring soon, try server validation
    if (formatResult.isExpiringSoon) {
      DebugLogger.auth('token-expiring-soon', scope: 'auth/state');
    }

    // Server validation (async with timeout)
    try {
      final api = ref.read(apiServiceProvider);
      if (api == null) {
        DebugLogger.warning('token-validation-no-api', scope: 'auth/state');
        return formatResult.isValid; // Fall back to format validation
      }

      User? validationUser;
      final serverResult = await TokenValidator.validateTokenWithServer(
        token,
        () async {
          // Update API with token for validation
          api.updateAuthToken(token);
          // Try to fetch user data as validation
          validationUser = await api.getCurrentUser();
          return validationUser!;
        },
      );

      // Store the user data if validation was successful
      if (serverResult.isValid &&
          validationUser != null &&
          _current.isAuthenticated) {
        _update((current) => current.copyWith(user: validationUser));
        DebugLogger.auth('Cached user data from token validation');
      }

      TokenValidationCache.cacheResult(token, serverResult);

      DebugLogger.auth(
        'Server token validation: ${serverResult.isValid} - ${serverResult.message}',
      );
      return serverResult.isValid;
    } catch (e) {
      DebugLogger.warning(
        'token-validation-failed',
        scope: 'auth/state',
        data: {'error': e.toString()},
      );
      // On network error, fall back to format validation if it was valid
      return formatResult.isValid;
    }
  }

  /// Check if user has saved credentials (with caching)
  Future<bool> hasSavedCredentials() async {
    // Check cache first
    final cachedResult = _cacheManager.getCachedCredentialsExist();
    if (cachedResult != null) {
      return cachedResult;
    }

    try {
      final storage = ref.read(optimizedStorageServiceProvider);
      final hasCredentials = await storage.hasCredentials();

      // Cache the result
      _cacheManager.cacheCredentialsExist(hasCredentials);

      return hasCredentials;
    } catch (e) {
      return false;
    }
  }

  /// Refresh current auth state
  Future<void> refresh() async {
    // Clear cache before refresh to ensure fresh data
    _cacheManager.clearAuthCache();
    TokenValidationCache.clearCache();

    await _initialize();
  }

  /// Clean up expired caches (called periodically)
  void cleanupCaches() {
    _cacheManager.cleanExpiredCache();
    _cacheManager.optimizeCache();
  }

  /// Get performance statistics
  Map<String, dynamic> getPerformanceStats() {
    return {
      'authCache': _cacheManager.getCacheStats(),
      'tokenValidationCache': 'Managed by TokenValidationCache',
      'storageCache': 'Managed by OptimizedStorageService',
    };
  }

  User? _userFromJwtClaims(Map<String, dynamic> claims) {
    final id =
        (claims['sub'] ?? claims['username'] ?? claims['email'])
            ?.toString()
            .trim() ??
        '';
    final username =
        (claims['username'] ?? claims['name'])?.toString().trim() ?? '';
    final emailValue = claims['email'];
    final email = emailValue == null ? '' : emailValue.toString().trim();

    if (id.isEmpty && username.isEmpty && email.isEmpty) {
      return null;
    }

    String resolvedRole = 'user';
    final roles = claims['roles'];
    if (roles is List && roles.isNotEmpty) {
      resolvedRole = roles.first.toString();
    } else if (roles is String && roles.isNotEmpty) {
      resolvedRole = roles;
    }

    return User(
      id: id.isNotEmpty
          ? id
          : (username.isNotEmpty ? username : email.ifEmptyReturn('user')),
      username: username.ifEmptyReturn(
        email.ifEmptyReturn(id.ifEmptyReturn('user')),
      ),
      email: email,
      role: resolvedRole,
      isActive: true,
    );
  }
}

extension _StringFallbackExtension on String {
  String ifEmptyReturn(String fallback) => isEmpty ? fallback : this;
}
