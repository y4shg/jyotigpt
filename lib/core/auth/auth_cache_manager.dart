import 'auth_state_manager.dart';
import '../utils/debug_logger.dart';

/// Comprehensive caching manager for auth-related operations
/// Reduces redundant operations and improves app performance
class AuthCacheManager {
  static final AuthCacheManager _instance = AuthCacheManager._internal();
  factory AuthCacheManager() => _instance;
  AuthCacheManager._internal();

  // Cache for various auth-related operations
  final Map<String, dynamic> _cache = {};
  final Map<String, DateTime> _cacheTimestamps = {};

  // Cache timeouts for different types of data
  static const Duration _shortCache = Duration(
    minutes: 2,
  ); // For frequently changing data
  static const Duration _mediumCache = Duration(
    minutes: 5,
  ); // For moderately stable data
  static const Duration _longCache = Duration(minutes: 15); // For stable data

  // Cache keys
  static const String _userDataKey = 'user_data';
  static const String _serverConnectionKey = 'server_connection';
  static const String _credentialsExistKey = 'credentials_exist';
  static const String _serverConfigsKey = 'server_configs';

  /// Cache user data with medium timeout
  void cacheUserData(dynamic userData) {
    _cache[_userDataKey] = userData;
    _cacheTimestamps[_userDataKey] = DateTime.now();
    DebugLogger.storage('User data cached');
  }

  /// Get cached user data
  dynamic getCachedUserData() {
    if (_isCacheValid(_userDataKey, _mediumCache)) {
      DebugLogger.storage('Using cached user data');
      return _cache[_userDataKey];
    }
    return null;
  }

  /// Cache server connection status with short timeout
  void cacheServerConnection(bool isConnected) {
    _cache[_serverConnectionKey] = isConnected;
    _cacheTimestamps[_serverConnectionKey] = DateTime.now();
  }

  /// Get cached server connection status
  bool? getCachedServerConnection() {
    if (_isCacheValid(_serverConnectionKey, _shortCache)) {
      return _cache[_serverConnectionKey] as bool?;
    }
    return null;
  }

  /// Cache credentials existence with medium timeout
  void cacheCredentialsExist(bool exist) {
    _cache[_credentialsExistKey] = exist;
    _cacheTimestamps[_credentialsExistKey] = DateTime.now();
  }

  /// Get cached credentials existence
  bool? getCachedCredentialsExist() {
    if (_isCacheValid(_credentialsExistKey, _mediumCache)) {
      return _cache[_credentialsExistKey] as bool?;
    }
    return null;
  }

  /// Cache server configurations with long timeout
  void cacheServerConfigs(List<dynamic> configs) {
    _cache[_serverConfigsKey] = configs;
    _cacheTimestamps[_serverConfigsKey] = DateTime.now();
  }

  /// Get cached server configurations
  List<dynamic>? getCachedServerConfigs() {
    if (_isCacheValid(_serverConfigsKey, _longCache)) {
      return _cache[_serverConfigsKey] as List<dynamic>?;
    }
    return null;
  }

  /// Check if cache entry is valid
  bool _isCacheValid(String key, Duration timeout) {
    final timestamp = _cacheTimestamps[key];
    if (timestamp == null) return false;

    return DateTime.now().difference(timestamp) < timeout;
  }

  /// Clear specific cache entry
  void clearCacheEntry(String key) {
    _cache.remove(key);
    _cacheTimestamps.remove(key);
    DebugLogger.storage('Cache entry cleared: $key');
  }

  /// Clear all auth-related cache
  void clearAuthCache() {
    _cache.clear();
    _cacheTimestamps.clear();
    DebugLogger.storage('All auth cache cleared');
  }

  /// Clear expired cache entries
  void cleanExpiredCache() {
    final now = DateTime.now();
    final expiredKeys = <String>[];

    for (final entry in _cacheTimestamps.entries) {
      // Use the longest timeout for cleanup to be conservative
      if (now.difference(entry.value) > _longCache) {
        expiredKeys.add(entry.key);
      }
    }

    for (final key in expiredKeys) {
      _cache.remove(key);
      _cacheTimestamps.remove(key);
    }

    if (expiredKeys.isNotEmpty) {
      DebugLogger.storage(
        'Cleaned ${expiredKeys.length} expired cache entries',
      );
    }
  }

  /// Get cache statistics for monitoring
  Map<String, dynamic> getCacheStats() {
    final now = DateTime.now();
    final stats = <String, dynamic>{};

    stats['totalEntries'] = _cache.length;
    stats['entries'] = <String, Map<String, dynamic>>{};

    for (final key in _cache.keys) {
      final timestamp = _cacheTimestamps[key];
      if (timestamp != null) {
        stats['entries'][key] = {
          'age': now.difference(timestamp).inSeconds,
          'hasData': _cache[key] != null,
        };
      }
    }

    return stats;
  }

  /// Optimize cache by removing least recently used entries if cache gets too large
  void optimizeCache() {
    const maxCacheSize = 20; // Reasonable limit for auth cache

    if (_cache.length <= maxCacheSize) return;

    // Sort by timestamp (oldest first)
    final sortedEntries = _cacheTimestamps.entries.toList()
      ..sort((a, b) => a.value.compareTo(b.value));

    // Remove oldest entries
    final entriesToRemove = sortedEntries.length - maxCacheSize;
    for (int i = 0; i < entriesToRemove; i++) {
      final key = sortedEntries[i].key;
      _cache.remove(key);
      _cacheTimestamps.remove(key);
    }

    DebugLogger.storage(
      'Cache optimized, removed $entriesToRemove old entries',
    );
  }

  /// Cache state from AuthState for quick access
  void cacheAuthState(AuthState authState) {
    if (authState.user != null) {
      cacheUserData(authState.user);
    }

    // Don't cache loading or error states
    if (authState.status == AuthStatus.authenticated) {
      _cache['auth_status'] = authState.status;
      _cacheTimestamps['auth_status'] = DateTime.now();
    }
  }

  /// Get cached auth status
  AuthStatus? getCachedAuthStatus() {
    if (_isCacheValid('auth_status', _shortCache)) {
      return _cache['auth_status'] as AuthStatus?;
    }
    return null;
  }
}
