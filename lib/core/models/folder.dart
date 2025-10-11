import 'package:freezed_annotation/freezed_annotation.dart';

part 'folder.freezed.dart';

@freezed
sealed class Folder with _$Folder {
  const factory Folder({
    required String id,
    required String name,
    String? parentId,
    String? userId,
    DateTime? createdAt,
    DateTime? updatedAt,
    @Default(false) bool isExpanded,
    @Default([]) List<String> conversationIds,
    Map<String, dynamic>? meta,
    Map<String, dynamic>? data,
    Map<String, dynamic>? items,
  }) = _Folder;

  factory Folder.fromJson(Map<String, dynamic> json) {
    // Extract conversation IDs from items.chats if available
    final items = json['items'] as Map<String, dynamic>?;
    final chats = items?['chats'] as List?;

    // Handle both string IDs and conversation objects
    final conversationIds =
        chats
            ?.map((chat) {
              if (chat is String) {
                return chat;
              } else if (chat is Map<String, dynamic>) {
                return chat['id'] as String? ?? '';
              }
              return '';
            })
            .where((id) => id.isNotEmpty)
            .toList()
            .cast<String>() ??
        <String>[];

    // Handle Unix timestamp conversion
    DateTime? parseTimestamp(dynamic timestamp) {
      if (timestamp == null) return null;
      if (timestamp is int) {
        return DateTime.fromMillisecondsSinceEpoch(timestamp * 1000);
      }
      if (timestamp is String) {
        return DateTime.parse(timestamp);
      }
      return null;
    }

    // Create the modified JSON with proper field mapping
    return Folder(
      id: json['id'] as String,
      name: json['name'] as String,
      parentId: json['parent_id'] as String?,
      userId: json['user_id'] as String?,
      createdAt: parseTimestamp(json['created_at']),
      updatedAt: parseTimestamp(json['updated_at']),
      isExpanded: json['is_expanded'] as bool? ?? false,
      conversationIds: conversationIds,
      meta: json['meta'] as Map<String, dynamic>?,
      data: json['data'] as Map<String, dynamic>?,
      items: json['items'] as Map<String, dynamic>?,
    );
  }
}
