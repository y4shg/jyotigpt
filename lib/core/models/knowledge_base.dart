import 'package:freezed_annotation/freezed_annotation.dart';

part 'knowledge_base.freezed.dart';
part 'knowledge_base.g.dart';

@freezed
sealed class KnowledgeBase with _$KnowledgeBase {
  const factory KnowledgeBase({
    required String id,
    required String name,
    String? description,
    required DateTime createdAt,
    required DateTime updatedAt,
    @Default(0) int itemCount,
    @Default({}) Map<String, dynamic> metadata,
  }) = _KnowledgeBase;

  factory KnowledgeBase.fromJson(Map<String, dynamic> json) =>
      _$KnowledgeBaseFromJson(json);
}

@freezed
sealed class KnowledgeBaseItem with _$KnowledgeBaseItem {
  const factory KnowledgeBaseItem({
    required String id,
    required String content,
    String? title,
    required DateTime createdAt,
    required DateTime updatedAt,
    @Default({}) Map<String, dynamic> metadata,
  }) = _KnowledgeBaseItem;

  factory KnowledgeBaseItem.fromJson(Map<String, dynamic> json) =>
      _$KnowledgeBaseItemFromJson(json);
}
