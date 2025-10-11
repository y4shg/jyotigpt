import 'package:freezed_annotation/freezed_annotation.dart';

part 'tool.freezed.dart';

@freezed
sealed class Tool with _$Tool {
  const Tool._();

  const factory Tool({
    required String id,
    required String name,
    String? description,
    String? userId,
    Map<String, dynamic>? meta,
  }) = _Tool;

  factory Tool.fromJson(Map<String, dynamic> json) {
    return Tool(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      userId: json['user_id'] as String?,
      meta: json['meta'] as Map<String, dynamic>?,
    );
  }
}
