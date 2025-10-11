import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:hive_ce/hive.dart';
import '../persistence/hive_boxes.dart';
import '../persistence/persistence_keys.dart';
import 'animation_service.dart';

part 'settings_service.g.dart';

/// Service for managing app-wide settings including accessibility preferences
class SettingsService {
  static const String _reduceMotionKey = PreferenceKeys.reduceMotion;
  static const String _animationSpeedKey = PreferenceKeys.animationSpeed;
  static const String _hapticFeedbackKey = PreferenceKeys.hapticFeedback;
  static const String _highContrastKey = PreferenceKeys.highContrast;
  static const String _largeTextKey = PreferenceKeys.largeText;
  static const String _darkModeKey = PreferenceKeys.darkMode;
  static const String _defaultModelKey = PreferenceKeys.defaultModel;
  // Voice input settings
  static const String _voiceLocaleKey = PreferenceKeys.voiceLocaleId;
  static const String _voiceHoldToTalkKey = PreferenceKeys.voiceHoldToTalk;
  static const String _voiceAutoSendKey = PreferenceKeys.voiceAutoSendFinal;
  // Realtime transport preference
  static const String _socketTransportModeKey =
      PreferenceKeys.socketTransportMode; // 'auto' or 'ws'
  // Quick pill visibility selections (max 2)
  static const String _quickPillsKey = PreferenceKeys
      .quickPills; // StringList of identifiers e.g. ['web','image','tools']
  // Chat input behavior
  static const String _sendOnEnterKey = PreferenceKeys.sendOnEnterKey;
  static Box<dynamic> _preferencesBox() =>
      Hive.box<dynamic>(HiveBoxNames.preferences);

  /// Get reduced motion preference
  static Future<bool> getReduceMotion() {
    final value = _preferencesBox().get(_reduceMotionKey) as bool?;
    return Future.value(value ?? false);
  }

  /// Set reduced motion preference
  static Future<void> setReduceMotion(bool value) {
    return _preferencesBox().put(_reduceMotionKey, value);
  }

  /// Get animation speed multiplier (0.5 - 2.0)
  static Future<double> getAnimationSpeed() {
    final value = _preferencesBox().get(_animationSpeedKey) as num?;
    return Future.value((value?.toDouble() ?? 1.0).clamp(0.5, 2.0));
  }

  /// Set animation speed multiplier
  static Future<void> setAnimationSpeed(double value) {
    final sanitized = value.clamp(0.5, 2.0).toDouble();
    return _preferencesBox().put(_animationSpeedKey, sanitized);
  }

  /// Get haptic feedback preference
  static Future<bool> getHapticFeedback() {
    final value = _preferencesBox().get(_hapticFeedbackKey) as bool?;
    return Future.value(value ?? true);
  }

  /// Set haptic feedback preference
  static Future<void> setHapticFeedback(bool value) {
    return _preferencesBox().put(_hapticFeedbackKey, value);
  }

  /// Get high contrast preference
  static Future<bool> getHighContrast() {
    final value = _preferencesBox().get(_highContrastKey) as bool?;
    return Future.value(value ?? false);
  }

  /// Set high contrast preference
  static Future<void> setHighContrast(bool value) {
    return _preferencesBox().put(_highContrastKey, value);
  }

  /// Get large text preference
  static Future<bool> getLargeText() {
    final value = _preferencesBox().get(_largeTextKey) as bool?;
    return Future.value(value ?? false);
  }

  /// Set large text preference
  static Future<void> setLargeText(bool value) {
    return _preferencesBox().put(_largeTextKey, value);
  }

  /// Get dark mode preference
  static Future<bool> getDarkMode() {
    final value = _preferencesBox().get(_darkModeKey) as bool?;
    return Future.value(value ?? true);
  }

  /// Set dark mode preference
  static Future<void> setDarkMode(bool value) {
    return _preferencesBox().put(_darkModeKey, value);
  }

  /// Get default model preference
  static Future<String?> getDefaultModel() {
    final value = _preferencesBox().get(_defaultModelKey) as String?;
    return Future.value(value);
  }

  /// Set default model preference
  static Future<void> setDefaultModel(String? modelId) {
    final box = _preferencesBox();
    if (modelId != null) {
      return box.put(_defaultModelKey, modelId);
    }
    return box.delete(_defaultModelKey);
  }

  /// Load all settings
  static Future<AppSettings> loadSettings() {
    final box = _preferencesBox();
    return Future.value(
      AppSettings(
        reduceMotion: (box.get(_reduceMotionKey) as bool?) ?? false,
        animationSpeed:
            (box.get(_animationSpeedKey) as num?)?.toDouble() ?? 1.0,
        hapticFeedback: (box.get(_hapticFeedbackKey) as bool?) ?? true,
        highContrast: (box.get(_highContrastKey) as bool?) ?? false,
        largeText: (box.get(_largeTextKey) as bool?) ?? false,
        darkMode: (box.get(_darkModeKey) as bool?) ?? true,
        defaultModel: box.get(_defaultModelKey) as String?,
        voiceLocaleId: box.get(_voiceLocaleKey) as String?,
        voiceHoldToTalk: (box.get(_voiceHoldToTalkKey) as bool?) ?? false,
        voiceAutoSendFinal: (box.get(_voiceAutoSendKey) as bool?) ?? false,
        socketTransportMode:
            box.get(_socketTransportModeKey, defaultValue: 'ws') as String,
        quickPills: List<String>.from(
          (box.get(_quickPillsKey) as List<dynamic>?) ?? const <String>[],
        ),
        sendOnEnter: (box.get(_sendOnEnterKey) as bool?) ?? false,
      ),
    );
  }

  /// Save all settings
  static Future<void> saveSettings(AppSettings settings) async {
    final box = _preferencesBox();
    final updates = <String, Object?>{
      _reduceMotionKey: settings.reduceMotion,
      _animationSpeedKey: settings.animationSpeed,
      _hapticFeedbackKey: settings.hapticFeedback,
      _highContrastKey: settings.highContrast,
      _largeTextKey: settings.largeText,
      _darkModeKey: settings.darkMode,
      _voiceHoldToTalkKey: settings.voiceHoldToTalk,
      _voiceAutoSendKey: settings.voiceAutoSendFinal,
      _socketTransportModeKey: settings.socketTransportMode,
      _quickPillsKey: settings.quickPills.take(2).toList(),
      _sendOnEnterKey: settings.sendOnEnter,
    };

    await box.putAll(updates);

    if (settings.defaultModel != null) {
      await box.put(_defaultModelKey, settings.defaultModel);
    } else {
      await box.delete(_defaultModelKey);
    }

    if (settings.voiceLocaleId != null && settings.voiceLocaleId!.isNotEmpty) {
      await box.put(_voiceLocaleKey, settings.voiceLocaleId);
    } else {
      await box.delete(_voiceLocaleKey);
    }
  }

  // Voice input specific settings
  static Future<String?> getVoiceLocaleId() {
    final value = _preferencesBox().get(_voiceLocaleKey) as String?;
    return Future.value(value);
  }

  static Future<void> setVoiceLocaleId(String? localeId) {
    final box = _preferencesBox();
    if (localeId == null || localeId.isEmpty) {
      return box.delete(_voiceLocaleKey);
    }
    return box.put(_voiceLocaleKey, localeId);
  }

  static Future<bool> getVoiceHoldToTalk() {
    final value = _preferencesBox().get(_voiceHoldToTalkKey) as bool?;
    return Future.value(value ?? false);
  }

  static Future<void> setVoiceHoldToTalk(bool value) {
    return _preferencesBox().put(_voiceHoldToTalkKey, value);
  }

  static Future<bool> getVoiceAutoSendFinal() {
    final value = _preferencesBox().get(_voiceAutoSendKey) as bool?;
    return Future.value(value ?? false);
  }

  static Future<void> setVoiceAutoSendFinal(bool value) {
    return _preferencesBox().put(_voiceAutoSendKey, value);
  }

  /// Transport mode: 'auto' (polling+websocket) or 'ws' (websocket only)
  static Future<String> getSocketTransportMode() {
    final value = _preferencesBox().get(_socketTransportModeKey) as String?;
    return Future.value(value ?? 'ws');
  }

  static Future<void> setSocketTransportMode(String mode) {
    if (mode != 'auto' && mode != 'ws') {
      mode = 'auto';
    }
    return _preferencesBox().put(_socketTransportModeKey, mode);
  }

  // Quick Pills (visibility)
  static Future<List<String>> getQuickPills() {
    final stored = _preferencesBox().get(_quickPillsKey) as List<dynamic>?;
    if (stored == null) {
      return Future.value(const []);
    }
    return Future.value(List<String>.from(stored.take(2)));
  }

  static Future<void> setQuickPills(List<String> pills) {
    return _preferencesBox().put(_quickPillsKey, pills.take(2).toList());
  }

  // Chat input behavior
  static Future<bool> getSendOnEnter() {
    final value = _preferencesBox().get(_sendOnEnterKey) as bool?;
    return Future.value(value ?? false);
  }

  static Future<void> setSendOnEnter(bool value) {
    return _preferencesBox().put(_sendOnEnterKey, value);
  }

  /// Get effective animation duration considering all settings
  static Duration getEffectiveAnimationDuration(
    BuildContext context,
    Duration defaultDuration,
    AppSettings settings,
  ) {
    // Check system reduced motion first
    if (MediaQuery.of(context).disableAnimations || settings.reduceMotion) {
      return Duration.zero;
    }

    // Apply user animation speed preference
    final adjustedMs =
        (defaultDuration.inMilliseconds / settings.animationSpeed).round();
    return Duration(milliseconds: adjustedMs.clamp(50, 1000));
  }

  /// Get text scale factor considering user preferences
  static double getEffectiveTextScaleFactor(
    BuildContext context,
    AppSettings settings,
  ) {
    final textScaler = MediaQuery.of(context).textScaler;
    double baseScale = textScaler.scale(1.0);

    // Apply large text preference
    if (settings.largeText) {
      baseScale *= 1.3;
    }

    // Ensure reasonable bounds
    return baseScale.clamp(0.8, 3.0);
  }
}

/// Sentinel class to detect when defaultModel parameter is not provided
class _DefaultValue {
  const _DefaultValue();
}

/// Data class for app settings
class AppSettings {
  final bool reduceMotion;
  final double animationSpeed;
  final bool hapticFeedback;
  final bool highContrast;
  final bool largeText;
  final bool darkMode;
  final String? defaultModel;
  final String? voiceLocaleId;
  final bool voiceHoldToTalk;
  final bool voiceAutoSendFinal;
  final String socketTransportMode; // 'auto' or 'ws'
  final List<String> quickPills; // e.g., ['web','image']
  final bool sendOnEnter;
  const AppSettings({
    this.reduceMotion = false,
    this.animationSpeed = 1.0,
    this.hapticFeedback = true,
    this.highContrast = false,
    this.largeText = false,
    this.darkMode = true,
    this.defaultModel,
    this.voiceLocaleId,
    this.voiceHoldToTalk = false,
    this.voiceAutoSendFinal = false,
    this.socketTransportMode = 'ws',
    this.quickPills = const [],
    this.sendOnEnter = false,
  });

  AppSettings copyWith({
    bool? reduceMotion,
    double? animationSpeed,
    bool? hapticFeedback,
    bool? highContrast,
    bool? largeText,
    bool? darkMode,
    Object? defaultModel = const _DefaultValue(),
    Object? voiceLocaleId = const _DefaultValue(),
    bool? voiceHoldToTalk,
    bool? voiceAutoSendFinal,
    String? socketTransportMode,
    List<String>? quickPills,
    bool? sendOnEnter,
  }) {
    return AppSettings(
      reduceMotion: reduceMotion ?? this.reduceMotion,
      animationSpeed: animationSpeed ?? this.animationSpeed,
      hapticFeedback: hapticFeedback ?? this.hapticFeedback,
      highContrast: highContrast ?? this.highContrast,
      largeText: largeText ?? this.largeText,
      darkMode: darkMode ?? this.darkMode,
      defaultModel: defaultModel is _DefaultValue
          ? this.defaultModel
          : defaultModel as String?,
      voiceLocaleId: voiceLocaleId is _DefaultValue
          ? this.voiceLocaleId
          : voiceLocaleId as String?,
      voiceHoldToTalk: voiceHoldToTalk ?? this.voiceHoldToTalk,
      voiceAutoSendFinal: voiceAutoSendFinal ?? this.voiceAutoSendFinal,
      socketTransportMode: socketTransportMode ?? this.socketTransportMode,
      quickPills: quickPills ?? this.quickPills,
      sendOnEnter: sendOnEnter ?? this.sendOnEnter,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is AppSettings &&
        other.reduceMotion == reduceMotion &&
        other.animationSpeed == animationSpeed &&
        other.hapticFeedback == hapticFeedback &&
        other.highContrast == highContrast &&
        other.largeText == largeText &&
        other.darkMode == darkMode &&
        other.defaultModel == defaultModel &&
        other.voiceLocaleId == voiceLocaleId &&
        other.voiceHoldToTalk == voiceHoldToTalk &&
        other.voiceAutoSendFinal == voiceAutoSendFinal &&
        other.sendOnEnter == sendOnEnter &&
        _listEquals(other.quickPills, quickPills);
    // socketTransportMode intentionally not included in == to avoid frequent rebuilds
  }

  @override
  int get hashCode {
    return Object.hash(
      reduceMotion,
      animationSpeed,
      hapticFeedback,
      highContrast,
      largeText,
      darkMode,
      defaultModel,
      voiceLocaleId,
      voiceHoldToTalk,
      voiceAutoSendFinal,
      socketTransportMode,
      sendOnEnter,
      Object.hashAllUnordered(quickPills),
    );
  }
}

bool _listEquals(List<String> a, List<String> b) {
  if (identical(a, b)) return true;
  if (a.length != b.length) return false;
  for (int i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}

/// Provider for app settings
@Riverpod(keepAlive: true)
class AppSettingsNotifier extends _$AppSettingsNotifier {
  bool _initialized = false;

  @override
  AppSettings build() {
    if (!_initialized) {
      _initialized = true;
      Future.microtask(_loadSettings);
    }
    return const AppSettings();
  }

  Future<void> _loadSettings() async {
    final settings = await SettingsService.loadSettings();
    if (!ref.mounted) {
      return;
    }
    state = settings;
  }

  Future<void> setReduceMotion(bool value) async {
    state = state.copyWith(reduceMotion: value);
    await SettingsService.setReduceMotion(value);
  }

  Future<void> setAnimationSpeed(double value) async {
    state = state.copyWith(animationSpeed: value);
    await SettingsService.setAnimationSpeed(value);
  }

  Future<void> setHapticFeedback(bool value) async {
    state = state.copyWith(hapticFeedback: value);
    await SettingsService.setHapticFeedback(value);
  }

  Future<void> setHighContrast(bool value) async {
    state = state.copyWith(highContrast: value);
    await SettingsService.setHighContrast(value);
  }

  Future<void> setLargeText(bool value) async {
    state = state.copyWith(largeText: value);
    await SettingsService.setLargeText(value);
  }

  Future<void> setDarkMode(bool value) async {
    state = state.copyWith(darkMode: value);
    await SettingsService.setDarkMode(value);
  }

  Future<void> setDefaultModel(String? modelId) async {
    state = state.copyWith(defaultModel: modelId);
    await SettingsService.setDefaultModel(modelId);
  }

  Future<void> setVoiceLocaleId(String? localeId) async {
    state = state.copyWith(voiceLocaleId: localeId);
    await SettingsService.setVoiceLocaleId(localeId);
  }

  Future<void> setVoiceHoldToTalk(bool value) async {
    state = state.copyWith(voiceHoldToTalk: value);
    await SettingsService.setVoiceHoldToTalk(value);
  }

  Future<void> setVoiceAutoSendFinal(bool value) async {
    state = state.copyWith(voiceAutoSendFinal: value);
    await SettingsService.setVoiceAutoSendFinal(value);
  }

  Future<void> setSocketTransportMode(String mode) async {
    state = state.copyWith(socketTransportMode: mode);
    await SettingsService.setSocketTransportMode(mode);
  }

  Future<void> setQuickPills(List<String> pills) async {
    // Enforce max 2; accept arbitrary server tool IDs plus built-ins
    final filtered = pills.take(2).toList();
    state = state.copyWith(quickPills: filtered);
    await SettingsService.setQuickPills(filtered);
  }

  Future<void> setSendOnEnter(bool value) async {
    state = state.copyWith(sendOnEnter: value);
    await SettingsService.setSendOnEnter(value);
  }

  Future<void> resetToDefaults() async {
    const defaultSettings = AppSettings();
    await SettingsService.saveSettings(defaultSettings);
    state = defaultSettings;
  }
}

/// Provider for checking if haptic feedback should be enabled
final hapticEnabledProvider = Provider<bool>((ref) {
  final settings = ref.watch(appSettingsProvider);
  return settings.hapticFeedback;
});

/// Provider for effective animation settings
final effectiveAnimationSettingsProvider = Provider<AnimationSettings>((ref) {
  final appSettings = ref.watch(appSettingsProvider);

  return AnimationSettings(
    reduceMotion: appSettings.reduceMotion,
    performance: AnimationPerformance.adaptive,
    animationSpeed: appSettings.animationSpeed,
  );
});
