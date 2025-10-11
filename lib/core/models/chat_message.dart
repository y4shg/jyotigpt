import 'package:freezed_annotation/freezed_annotation.dart';

// Freezed applies JsonKey to constructor parameters which triggers
// invalid_annotation_target; suppress it for this data model file.
// ignore_for_file: invalid_annotation_target

part 'chat_message.freezed.dart';
part 'chat_message.g.dart';

@freezed
sealed class ChatMessage with _$ChatMessage {
  const factory ChatMessage({
    required String id,
    required String role, // 'user', 'assistant', 'system'
    required String content,
    required DateTime timestamp,
    String? model,
    @Default(false) bool isStreaming,
    List<String>? attachmentIds,
    List<Map<String, dynamic>>? files, // For generated images
    Map<String, dynamic>? metadata,
    @Default(<ChatStatusUpdate>[]) List<ChatStatusUpdate> statusHistory,
    @Default(<String>[]) List<String> followUps,
    @Default(<ChatCodeExecution>[]) List<ChatCodeExecution> codeExecutions,
    @JsonKey(
      name: 'sources',
      fromJson: _sourceRefsFromJson,
      toJson: _sourceRefsToJson,
    )
    @Default(<ChatSourceReference>[])
    List<ChatSourceReference> sources,
    Map<String, dynamic>? usage,
  }) = _ChatMessage;

  factory ChatMessage.fromJson(Map<String, dynamic> json) =>
      _$ChatMessageFromJson(json);
}

@freezed
abstract class ChatStatusUpdate with _$ChatStatusUpdate {
  const factory ChatStatusUpdate({
    String? action,
    String? description,
    bool? done,
    bool? hidden,
    int? count,
    String? query,
    @JsonKey(fromJson: _safeStringList, toJson: _stringListToJson)
    @Default(<String>[])
    List<String> queries,
    @JsonKey(fromJson: _safeStringList, toJson: _stringListToJson)
    @Default(<String>[])
    List<String> urls,
    @JsonKey(fromJson: _statusItemsFromJson, toJson: _statusItemsToJson)
    @Default(<ChatStatusItem>[])
    List<ChatStatusItem> items,
    @JsonKey(
      name: 'timestamp',
      fromJson: _timestampFromJson,
      toJson: _timestampToJson,
    )
    DateTime? occurredAt,
  }) = _ChatStatusUpdate;

  factory ChatStatusUpdate.fromJson(Map<String, dynamic> json) =>
      _$ChatStatusUpdateFromJson(json);
}

@freezed
abstract class ChatStatusItem with _$ChatStatusItem {
  const factory ChatStatusItem({
    String? title,
    String? link,
    String? snippet,
    Map<String, dynamic>? metadata,
  }) = _ChatStatusItem;

  factory ChatStatusItem.fromJson(Map<String, dynamic> json) =>
      _$ChatStatusItemFromJson(json);
}

@freezed
abstract class ChatCodeExecution with _$ChatCodeExecution {
  const factory ChatCodeExecution({
    @JsonKey(fromJson: _requiredString) required String id,
    @JsonKey(fromJson: _nullableString) String? name,
    @JsonKey(fromJson: _nullableString) String? language,
    @JsonKey(fromJson: _nullableString) String? code,
    ChatCodeExecutionResult? result,
    Map<String, dynamic>? metadata,
  }) = _ChatCodeExecution;

  factory ChatCodeExecution.fromJson(Map<String, dynamic> json) =>
      _$ChatCodeExecutionFromJson(json);
}

@freezed
abstract class ChatCodeExecutionResult with _$ChatCodeExecutionResult {
  const factory ChatCodeExecutionResult({
    String? output,
    String? error,
    @JsonKey(fromJson: _executionFilesFromJson, toJson: _executionFilesToJson)
    @Default(<ChatExecutionFile>[])
    List<ChatExecutionFile> files,
    Map<String, dynamic>? metadata,
  }) = _ChatCodeExecutionResult;

  factory ChatCodeExecutionResult.fromJson(Map<String, dynamic> json) =>
      _$ChatCodeExecutionResultFromJson(json);
}

@freezed
abstract class ChatExecutionFile with _$ChatExecutionFile {
  const factory ChatExecutionFile({
    @JsonKey(fromJson: _nullableString) String? name,
    @JsonKey(fromJson: _nullableString) String? url,
    Map<String, dynamic>? metadata,
  }) = _ChatExecutionFile;

  factory ChatExecutionFile.fromJson(Map<String, dynamic> json) =>
      _$ChatExecutionFileFromJson(json);
}

@freezed
abstract class ChatSourceReference with _$ChatSourceReference {
  const factory ChatSourceReference({
    @JsonKey(fromJson: _nullableString) String? id,
    @JsonKey(fromJson: _nullableString) String? title,
    @JsonKey(fromJson: _nullableString) String? url,
    @JsonKey(fromJson: _nullableString) String? snippet,
    @JsonKey(fromJson: _nullableString) String? type,
    Map<String, dynamic>? metadata,
  }) = _ChatSourceReference;

  factory ChatSourceReference.fromJson(Map<String, dynamic> json) =>
      _$ChatSourceReferenceFromJson(json);
}

List<String> _safeStringList(dynamic value) {
  if (value is List) {
    return value
        .whereType<dynamic>()
        .map((e) => e?.toString().trim() ?? '')
        .where((s) => s.isNotEmpty)
        .toList(growable: false);
  }
  if (value is String && value.isNotEmpty) {
    return [value];
  }
  return const [];
}

List<String> _stringListToJson(List<String> value) =>
    List<String>.from(value, growable: false);

List<ChatStatusItem> _statusItemsFromJson(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) {
          try {
            // Convert Map to Map<String, dynamic> safely
            final Map<String, dynamic> itemMap = {};
            item.forEach((key, v) {
              itemMap[key.toString()] = v;
            });
            return ChatStatusItem.fromJson(itemMap);
          } catch (e) {
            // Skip invalid entries
            return null;
          }
        })
        .where((item) => item != null)
        .cast<ChatStatusItem>()
        .toList(growable: false);
  }
  return const [];
}

List<Map<String, dynamic>> _statusItemsToJson(List<ChatStatusItem> value) {
  return value.map((item) => item.toJson()).toList(growable: false);
}

List<ChatExecutionFile> _executionFilesFromJson(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) {
          try {
            // Convert Map to Map<String, dynamic> safely
            final Map<String, dynamic> fileMap = {};
            item.forEach((key, v) {
              fileMap[key.toString()] = v;
            });
            return ChatExecutionFile.fromJson(fileMap);
          } catch (e) {
            // Skip invalid entries
            return null;
          }
        })
        .where((item) => item != null)
        .cast<ChatExecutionFile>()
        .toList(growable: false);
  }
  return const [];
}

List<Map<String, dynamic>> _executionFilesToJson(
  List<ChatExecutionFile> files,
) {
  return files.map((file) => file.toJson()).toList(growable: false);
}

List<ChatSourceReference> _sourceRefsFromJson(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) {
          try {
            // Convert Map to Map<String, dynamic> safely
            final Map<String, dynamic> refMap = {};
            item.forEach((key, v) {
              refMap[key.toString()] = v;
            });
            return ChatSourceReference.fromJson(refMap);
          } catch (e) {
            // Skip invalid entries
            return null;
          }
        })
        .where((item) => item != null)
        .cast<ChatSourceReference>()
        .toList(growable: false);
  }
  return const [];
}

List<Map<String, dynamic>> _sourceRefsToJson(
  List<ChatSourceReference> references,
) {
  return references.map((ref) => ref.toJson()).toList(growable: false);
}

DateTime? _timestampFromJson(dynamic value) {
  if (value == null) return null;
  if (value is DateTime) return value;
  if (value is int) {
    // Heuristics: treat seconds vs milliseconds
    final isSeconds = value < 1000000000000;
    final millis = isSeconds ? value * 1000 : value;
    return DateTime.fromMillisecondsSinceEpoch(millis, isUtc: true).toLocal();
  }
  if (value is double) {
    final millis = value < 1000000000 ? (value * 1000).toInt() : value.toInt();
    return DateTime.fromMillisecondsSinceEpoch(millis, isUtc: true).toLocal();
  }
  if (value is String && value.isNotEmpty) {
    return DateTime.tryParse(value)?.toLocal();
  }
  return null;
}

String? _timestampToJson(DateTime? value) => value?.toIso8601String();

String _requiredString(dynamic value, {String fallback = ''}) {
  if (value == null) return fallback;
  final str = value.toString();
  return str.isEmpty ? fallback : str;
}

String? _nullableString(dynamic value) {
  if (value == null) return null;
  final str = value.toString();
  return str.isEmpty ? null : str;
}
