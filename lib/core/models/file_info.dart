import 'package:freezed_annotation/freezed_annotation.dart';

part 'file_info.freezed.dart';
part 'file_info.g.dart';

@freezed
sealed class FileInfo with _$FileInfo {
  const factory FileInfo({
    required String id,
    required String filename,
    required String originalFilename,
    required int size,
    required String mimeType,
    required DateTime createdAt,
    required DateTime updatedAt,
    String? userId,
    String? hash,
    Map<String, dynamic>? metadata,
  }) = _FileInfo;

  factory FileInfo.fromJson(Map<String, dynamic> json) =>
      _$FileInfoFromJson(json);
}
