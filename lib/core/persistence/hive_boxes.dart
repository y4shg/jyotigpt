import 'package:hive_ce/hive.dart';

/// Logical names for Hive boxes used by the app.
final class HiveBoxNames {
  static const String preferences = 'preferences_v1';
  static const String caches = 'caches_v1';
  static const String attachmentQueue = 'attachment_queue_v1';
  static const String metadata = 'metadata_v1';
}

/// Well-known keys stored inside Hive boxes.
final class HiveStoreKeys {
  // Metadata
  static const String migrationVersion = 'migration_version';

  // Cache entries
  static const String localConversations = 'local_conversations';
  static const String attachmentQueueEntries = 'attachment_queue_entries';
  static const String taskQueue = 'outbound_task_queue_v1';
}

/// Grouped Hive boxes that remain open for the app lifecycle.
class HiveBoxes {
  HiveBoxes({
    required this.preferences,
    required this.caches,
    required this.attachmentQueue,
    required this.metadata,
  });

  final Box<dynamic> preferences;
  final Box<dynamic> caches;
  final Box<dynamic> attachmentQueue;
  final Box<dynamic> metadata;
}
