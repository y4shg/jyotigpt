/// Keys previously stored in SharedPreferences. Centralized so Hive-based
/// storage and migration logic stay aligned.
final class PreferenceKeys {
  static const String reduceMotion = 'reduce_motion';
  static const String animationSpeed = 'animation_speed';
  static const String hapticFeedback = 'haptic_feedback';
  static const String highContrast = 'high_contrast';
  static const String largeText = 'large_text';
  static const String darkMode = 'dark_mode';
  static const String defaultModel = 'default_model';
  static const String voiceLocaleId = 'voice_locale_id';
  static const String voiceHoldToTalk = 'voice_hold_to_talk';
  static const String voiceAutoSendFinal = 'voice_auto_send_final';
  static const String socketTransportMode = 'socket_transport_mode';
  static const String quickPills = 'quick_pills';
  static const String sendOnEnterKey = 'send_on_enter';
  static const String rememberCredentials = 'remember_credentials';
  static const String activeServerId = 'active_server_id';
  static const String themeMode = 'theme_mode';
  static const String themePalette = 'theme_palette_v1';
  static const String localeCode = 'locale_code_v1';
  static const String onboardingSeen = 'onboarding_seen_v1';
  static const String reviewerMode = 'reviewer_mode_v1';
}

final class LegacyPreferenceKeys {
  static const String attachmentUploadQueue = 'attachment_upload_queue';
  static const String taskQueue = 'outbound_task_queue_v1';
}
