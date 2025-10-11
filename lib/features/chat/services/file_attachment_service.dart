import 'dart:io';
import 'dart:convert';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path/path.dart' as path;
import '../../../core/services/api_service.dart';
import '../../../core/providers/app_providers.dart';
import '../../../core/utils/debug_logger.dart';

class FileAttachmentService {
  final ApiService _apiService;
  final ImagePicker _imagePicker = ImagePicker();

  FileAttachmentService(this._apiService);

  // Pick files from device
  Future<List<File>> pickFiles({
    bool allowMultiple = true,
    List<String>? allowedExtensions,
  }) async {
    try {
      final result = await FilePicker.platform.pickFiles(
        allowMultiple: allowMultiple,
        type: allowedExtensions != null ? FileType.custom : FileType.any,
        allowedExtensions: allowedExtensions,
      );

      if (result == null || result.files.isEmpty) {
        return [];
      }

      return result.files
          .where((file) => file.path != null)
          .map((file) => File(file.path!))
          .toList();
    } catch (e) {
      throw Exception('Failed to pick files: $e');
    }
  }

  // Pick image from gallery
  Future<File?> pickImage() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 85,
      );

      if (image == null) return null;
      return File(image.path);
    } catch (e) {
      throw Exception('Failed to pick image: $e');
    }
  }

  // Take photo from camera
  Future<File?> takePhoto() async {
    try {
      final XFile? photo = await _imagePicker.pickImage(
        source: ImageSource.camera,
        imageQuality: 85,
      );

      if (photo == null) return null;
      return File(photo.path);
    } catch (e) {
      throw Exception('Failed to take photo: $e');
    }
  }

  // Compress image similar to OpenWebUI's implementation
  Future<String> compressImage(
    String imageDataUrl,
    int? maxWidth,
    int? maxHeight,
  ) async {
    try {
      // Decode base64 data
      final data = imageDataUrl.split(',')[1];
      final bytes = base64Decode(data);

      // Decode image
      final codec = await ui.instantiateImageCodec(bytes);
      final frame = await codec.getNextFrame();
      final image = frame.image;

      int width = image.width;
      int height = image.height;

      // Calculate new dimensions maintaining aspect ratio
      if (maxWidth != null && maxHeight != null) {
        if (width <= maxWidth && height <= maxHeight) {
          return imageDataUrl; // No compression needed
        }

        if (width / height > maxWidth / maxHeight) {
          height = ((maxWidth * height) / width).round();
          width = maxWidth;
        } else {
          width = ((maxHeight * width) / height).round();
          height = maxHeight;
        }
      } else if (maxWidth != null) {
        if (width <= maxWidth) {
          return imageDataUrl; // No compression needed
        }
        height = ((maxWidth * height) / width).round();
        width = maxWidth;
      } else if (maxHeight != null) {
        if (height <= maxHeight) {
          return imageDataUrl; // No compression needed
        }
        width = ((maxHeight * width) / height).round();
        height = maxHeight;
      }

      // Create compressed image
      final recorder = ui.PictureRecorder();
      final canvas = Canvas(recorder);

      canvas.drawImageRect(
        image,
        Rect.fromLTWH(0, 0, image.width.toDouble(), image.height.toDouble()),
        Rect.fromLTWH(0, 0, width.toDouble(), height.toDouble()),
        Paint(),
      );

      final picture = recorder.endRecording();
      final compressedImage = await picture.toImage(width, height);
      final byteData = await compressedImage.toByteData(
        format: ui.ImageByteFormat.png,
      );
      final compressedBytes = byteData!.buffer.asUint8List();

      // Convert back to data URL
      final compressedBase64 = base64Encode(compressedBytes);
      return 'data:image/png;base64,$compressedBase64';
    } catch (e) {
      DebugLogger.error(
        'compress-failed',
        scope: 'attachments/image',
        error: e,
      );
      return imageDataUrl; // Return original if compression fails
    }
  }

  // Convert image file to base64 data URL with compression
  Future<String?> convertImageToDataUrl(
    File imageFile, {
    bool enableCompression = false,
    int? maxWidth,
    int? maxHeight,
  }) async {
    try {
      DebugLogger.log(
        'convert-start',
        scope: 'attachments/image',
        data: {'path': imageFile.path},
      );

      // Read the file as bytes
      final bytes = await imageFile.readAsBytes();

      // Determine MIME type based on file extension
      final ext = path.extension(imageFile.path).toLowerCase();
      String mimeType = 'image/png'; // default

      if (ext == '.jpg' || ext == '.jpeg') {
        mimeType = 'image/jpeg';
      } else if (ext == '.gif') {
        mimeType = 'image/gif';
      } else if (ext == '.webp') {
        mimeType = 'image/webp';
      }

      // Convert to base64
      final base64String = base64Encode(bytes);
      String dataUrl = 'data:$mimeType;base64,$base64String';

      // Apply compression if enabled
      if (enableCompression && (maxWidth != null || maxHeight != null)) {
        dataUrl = await compressImage(dataUrl, maxWidth, maxHeight);
      }

      DebugLogger.log(
        'convert-done',
        scope: 'attachments/image',
        data: {'mime': mimeType},
      );
      return dataUrl;
    } catch (e) {
      DebugLogger.error('convert-failed', scope: 'attachments/image', error: e);
      return null;
    }
  }

  // Upload file with progress tracking
  Stream<FileUploadState> uploadFile(File file) async* {
    DebugLogger.log(
      'upload-start',
      scope: 'attachments/file',
      data: {'path': file.path},
    );
    try {
      final fileName = path.basename(file.path);
      final fileSize = await file.length();

      DebugLogger.log(
        'file-details',
        scope: 'attachments/file',
        data: {'name': fileName, 'bytes': fileSize},
      );

      yield FileUploadState(
        file: file,
        fileName: fileName,
        fileSize: fileSize,
        progress: 0.0,
        status: FileUploadStatus.uploading,
      );

      // Check if this is an image file
      final ext = path.extension(fileName).toLowerCase();
      final isImage = [
        'jpg',
        'jpeg',
        'png',
        'gif',
        'webp',
      ].contains(ext.substring(1));

      // Upload ALL files (including images) to server for consistency with web client
      DebugLogger.log('upload-progress', scope: 'attachments/file');
      final fileId = await _apiService.uploadFile(file.path, fileName);
      DebugLogger.log(
        'upload-complete',
        scope: 'attachments/file',
        data: {'fileId': fileId},
      );

      yield FileUploadState(
        file: file,
        fileName: fileName,
        fileSize: fileSize,
        progress: 1.0,
        status: FileUploadStatus.completed,
        fileId: fileId,
        isImage: isImage,
      );
    } catch (e) {
      DebugLogger.error('upload-failed', scope: 'attachments/file', error: e);
      final fileName = path.basename(file.path);
      final fileSize = await file.length();

      yield FileUploadState(
        file: file,
        fileName: fileName,
        fileSize: fileSize,
        progress: 0.0,
        status: FileUploadStatus.failed,
        error: e.toString(),
      );
    }
  }

  // Upload multiple files
  Stream<List<FileUploadState>> uploadMultipleFiles(List<File> files) async* {
    final states = <String, FileUploadState>{};

    for (final file in files) {
      final uploadStream = uploadFile(file);
      await for (final state in uploadStream) {
        states[file.path] = state;
        yield states.values.toList();
      }
    }
  }

  // Format file size for display
  String formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  // Get file icon based on extension
  String getFileIcon(String fileName) {
    final ext = path.extension(fileName).toLowerCase();

    // Documents
    if (['.pdf', '.doc', '.docx'].contains(ext)) return '📄';
    if (['.xls', '.xlsx'].contains(ext)) return '📊';
    if (['.ppt', '.pptx'].contains(ext)) return '📊';

    // Images
    if (['.jpg', '.jpeg', '.png', '.gif', '.webp'].contains(ext)) return '🖼️';

    // Code
    if (['.js', '.ts', '.py', '.dart', '.java', '.cpp'].contains(ext)) {
      return '💻';
    }
    if (['.html', '.css', '.json', '.xml'].contains(ext)) return '🌐';

    // Archives
    if (['.zip', '.rar', '.7z', '.tar', '.gz'].contains(ext)) return '📦';

    // Media
    if (['.mp3', '.wav', '.flac', '.m4a'].contains(ext)) return '🎵';
    if (['.mp4', '.avi', '.mov', '.mkv'].contains(ext)) return '🎬';

    return '📎';
  }
}

// File upload state
class FileUploadState {
  final File file;
  final String fileName;
  final int fileSize;
  final double progress;
  final FileUploadStatus status;
  final String? fileId;
  final String? error;
  final bool? isImage; // Added for image files

  FileUploadState({
    required this.file,
    required this.fileName,
    required this.fileSize,
    required this.progress,
    required this.status,
    this.fileId,
    this.error,
    this.isImage, // Added for image files
  });

  String get formattedSize {
    if (fileSize < 1024) return '$fileSize B';
    if (fileSize < 1024 * 1024) {
      return '${(fileSize / 1024).toStringAsFixed(1)} KB';
    }
    if (fileSize < 1024 * 1024 * 1024) {
      return '${(fileSize / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(fileSize / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  String get fileIcon {
    final ext = path.extension(fileName).toLowerCase();

    // Documents
    if (['.pdf', '.doc', '.docx'].contains(ext)) return '📄';
    if (['.xls', '.xlsx'].contains(ext)) return '📊';
    if (['.ppt', '.pptx'].contains(ext)) return '📊';

    // Images
    if (['.jpg', '.jpeg', '.png', '.gif', '.webp'].contains(ext)) return '🖼️';

    // Code
    if (['.js', '.ts', '.py', '.dart', '.java', '.cpp'].contains(ext)) {
      return '💻';
    }
    if (['.html', '.css', '.json', '.xml'].contains(ext)) return '🌐';

    // Archives
    if (['.zip', '.rar', '.7z', '.tar', '.gz'].contains(ext)) return '📦';

    // Media
    if (['.mp3', '.wav', '.flac', '.m4a'].contains(ext)) return '🎵';
    if (['.mp4', '.avi', '.mov', '.mkv'].contains(ext)) return '🎬';

    return '📎';
  }
}

enum FileUploadStatus { pending, uploading, completed, failed }

// Mock file attachment service for reviewer mode
class MockFileAttachmentService {
  final ImagePicker _imagePicker = ImagePicker();

  // Reuse the same methods from parent class
  Future<List<File>> pickFiles({
    bool allowMultiple = true,
    List<String>? allowedExtensions,
  }) async {
    try {
      final result = await FilePicker.platform.pickFiles(
        allowMultiple: allowMultiple,
        type: allowedExtensions != null ? FileType.custom : FileType.any,
        allowedExtensions: allowedExtensions,
      );

      if (result == null || result.files.isEmpty) {
        return [];
      }

      return result.files
          .where((file) => file.path != null)
          .map((file) => File(file.path!))
          .toList();
    } catch (e) {
      throw Exception('Failed to pick files: $e');
    }
  }

  Future<File?> pickImage() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 85,
      );
      return image != null ? File(image.path) : null;
    } catch (e) {
      throw Exception('Failed to pick image: $e');
    }
  }

  Future<File?> takePhoto() async {
    try {
      final XFile? photo = await _imagePicker.pickImage(
        source: ImageSource.camera,
        imageQuality: 85,
      );
      return photo != null ? File(photo.path) : null;
    } catch (e) {
      throw Exception('Failed to take photo: $e');
    }
  }

  // Mock upload file with progress tracking
  Stream<FileUploadState> uploadFile(File file) async* {
    DebugLogger.log(
      'mock-upload',
      scope: 'attachments/mock',
      data: {'path': file.path},
    );

    final fileName = path.basename(file.path);
    final fileSize = await file.length();

    // Yield initial state
    yield FileUploadState(
      file: file,
      fileName: fileName,
      fileSize: fileSize,
      progress: 0.0,
      status: FileUploadStatus.uploading,
    );

    // Simulate upload progress
    for (int i = 1; i <= 10; i++) {
      await Future.delayed(const Duration(milliseconds: 100));
      yield FileUploadState(
        file: file,
        fileName: fileName,
        fileSize: fileSize,
        progress: i / 10,
        status: FileUploadStatus.uploading,
      );
    }

    // Yield completed state with mock file ID
    yield FileUploadState(
      file: file,
      fileName: fileName,
      fileSize: fileSize,
      progress: 1.0,
      status: FileUploadStatus.completed,
      fileId: 'mock_file_${DateTime.now().millisecondsSinceEpoch}',
    );

    DebugLogger.log('mock-complete', scope: 'attachments/mock');
  }

  Future<List<String>> uploadFiles(
    List<File> files, {
    Function(int, int)? onProgress,
    required String conversationId,
  }) async {
    // Simulate upload progress for reviewer mode
    final uploadIds = <String>[];

    for (int i = 0; i < files.length; i++) {
      if (onProgress != null) {
        // Simulate progress
        for (int j = 0; j <= 100; j += 10) {
          await Future.delayed(const Duration(milliseconds: 50));
          onProgress(i, j);
        }
      }
      // Generate mock upload ID
      uploadIds.add('mock_upload_${DateTime.now().millisecondsSinceEpoch}_$i');
    }

    return uploadIds;
  }
}

// Providers
final fileAttachmentServiceProvider = Provider<dynamic>((ref) {
  final isReviewerMode = ref.watch(reviewerModeProvider);

  if (isReviewerMode) {
    return MockFileAttachmentService();
  }

  final apiService = ref.watch(apiServiceProvider);
  if (apiService == null) return null;
  return FileAttachmentService(apiService);
});

// State notifier for managing attached files
class AttachedFilesNotifier extends Notifier<List<FileUploadState>> {
  @override
  List<FileUploadState> build() => [];

  void addFiles(List<File> files) {
    final newStates = files
        .map(
          (file) => FileUploadState(
            file: file,
            fileName: path.basename(file.path),
            fileSize: file.lengthSync(),
            progress: 0.0,
            status: FileUploadStatus.pending,
          ),
        )
        .toList();

    state = [...state, ...newStates];
  }

  void updateFileState(String filePath, FileUploadState newState) {
    state = [
      for (final fileState in state)
        if (fileState.file.path == filePath) newState else fileState,
    ];
  }

  void removeFile(String filePath) {
    state = state
        .where((fileState) => fileState.file.path != filePath)
        .toList();
  }

  void clearAll() {
    state = [];
  }
}

final attachedFilesProvider =
    NotifierProvider<AttachedFilesNotifier, List<FileUploadState>>(
      AttachedFilesNotifier.new,
    );
