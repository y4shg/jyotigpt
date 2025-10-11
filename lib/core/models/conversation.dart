import 'package:freezed_annotation/freezed_annotation.dart';
import 'chat_message.dart';

part 'conversation.freezed.dart';
part 'conversation.g.dart';

@freezed
sealed class Conversation with _$Conversation {
  const factory Conversation({
    required String id,
    required String title,
    required DateTime createdAt,
    required DateTime updatedAt,
    String? model,
    String? systemPrompt,
    @Default([]) List<ChatMessage> messages,
    @Default({}) Map<String, dynamic> metadata,
    @Default(false) bool pinned,
    @Default(false) bool archived,
    String? shareId,
    String? folderId,
    @Default([]) List<String> tags,
  }) = _Conversation;

  factory Conversation.fromJson(Map<String, dynamic> json) =>
      _$ConversationFromJson(json);
}
