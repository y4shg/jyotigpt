import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/app_providers.dart';
import '../../../core/services/attachment_upload_queue.dart';
import '../../../core/utils/debug_logger.dart';
import '../../../features/chat/providers/chat_providers.dart' as chat;
import '../../../features/chat/services/file_attachment_service.dart';
import 'outbound_task.dart';

class TaskWorker {
  final Ref _ref;
  TaskWorker(this._ref);

  Future<void> perform(OutboundTask task) async {
    await task.map<Future<void>>(
      sendTextMessage: _performSendText,
      uploadMedia: _performUploadMedia,
      executeToolCall: _performExecuteToolCall,
      generateImage: _performGenerateImage,
      imageToDataUrl: _performImageToDataUrl,
    );
  }

  Future<void> _performSendText(SendTextMessageTask task) async {
    // Ensure uploads referenced in attachments are completed if they are local queued ids
    // For now, assume attachments are already uploaded (fileIds or data URLs) as UI uploads eagerly.
    // If needed, we could resolve queued uploads here by integrating with AttachmentUploadQueue.
    final isReviewer = _ref.read(reviewerModeProvider);
    if (!isReviewer) {
      final api = _ref.read(apiServiceProvider);
      if (api == null) {
        throw Exception('API not available');
      }
    }

    // Set active conversation if provided; otherwise keep current
    try {
      // If a specific conversation id is provided and differs from current, load it
      final active = _ref.read(activeConversationProvider);
      if (task.conversationId != null &&
          task.conversationId!.isNotEmpty &&
          (active == null || active.id != task.conversationId)) {
        try {
          final api = _ref.read(apiServiceProvider);
          if (api != null) {
            final conv = await api.getConversation(task.conversationId!);
            _ref.read(activeConversationProvider.notifier).set(conv);
          }
        } catch (_) {
          // If loading fails, proceed; send flow can create a new conversation
        }
      }
    } catch (_) {}

    // Delegate to existing unified send implementation
    await chat.sendMessageFromService(
      _ref,
      task.text,
      task.attachments.isEmpty ? null : task.attachments,
      task.toolIds.isEmpty ? null : task.toolIds,
    );
  }

  Future<void> _performUploadMedia(UploadMediaTask task) async {
    final uploader = AttachmentUploadQueue();
    // Ensure queue initialized with API upload callback
    try {
      final api = _ref.read(apiServiceProvider);
      if (api != null) {
        await uploader.initialize(onUpload: (p, n) => api.uploadFile(p, n));
      }
    } catch (_) {}

    // Enqueue and then wait until the item reaches a terminal state for basic parity
    final id = await uploader.enqueue(
      filePath: task.filePath,
      fileName: task.fileName,
      fileSize: task.fileSize ?? 0,
      mimeType: task.mimeType,
      checksum: task.checksum,
    );

    final completer = Completer<void>();
    late final StreamSubscription<List<QueuedAttachment>> sub;
    sub = uploader.queueStream.listen((items) {
      QueuedAttachment? entry;
      try {
        entry = items.firstWhere((e) => e.id == id);
      } catch (_) {
        entry = null;
      }
      if (entry == null) return;

      // Reflect progress into UI attachment state if that file is present
      try {
        final current = _ref.read(attachedFilesProvider);
        final idx = current.indexWhere((f) => f.file.path == task.filePath);
        if (idx != -1) {
          final existing = current[idx];
          final status = switch (entry.status) {
            QueuedAttachmentStatus.pending => FileUploadStatus.uploading,
            QueuedAttachmentStatus.uploading => FileUploadStatus.uploading,
            QueuedAttachmentStatus.completed => FileUploadStatus.completed,
            QueuedAttachmentStatus.failed => FileUploadStatus.failed,
            QueuedAttachmentStatus.cancelled => FileUploadStatus.failed,
          };
          final newState = FileUploadState(
            file: File(task.filePath),
            fileName: task.fileName,
            fileSize: task.fileSize ?? existing.fileSize,
            progress: status == FileUploadStatus.completed
                ? 1.0
                : existing.progress,
            status: status,
            fileId: entry.fileId ?? existing.fileId,
            error: entry.lastError,
          );
          _ref
              .read(attachedFilesProvider.notifier)
              .updateFileState(task.filePath, newState);
        }
      } catch (_) {}
      switch (entry.status) {
        case QueuedAttachmentStatus.completed:
        case QueuedAttachmentStatus.failed:
        case QueuedAttachmentStatus.cancelled:
          sub.cancel();
          completer.complete();
          break;
        default:
          break;
      }
    });

    // Fire a process tick
    unawaited(uploader.processQueue());
    await completer.future.timeout(
      const Duration(minutes: 2),
      onTimeout: () {
        try {
          sub.cancel();
        } catch (_) {}
        DebugLogger.warning('UploadMediaTask timed out: ${task.fileName}');
        return;
      },
    );
  }

  Future<void> _performExecuteToolCall(ExecuteToolCallTask task) async {
    // Resolve API + selected model
    final api = _ref.read(apiServiceProvider);
    final selectedModel = _ref.read(selectedModelProvider);
    if (api == null || selectedModel == null) {
      throw Exception('API or model not available');
    }

    // Optionally bring the target conversation to foreground
    try {
      final active = _ref.read(activeConversationProvider);
      if (task.conversationId != null &&
          task.conversationId!.isNotEmpty &&
          (active == null || active.id != task.conversationId)) {
        try {
          final conv = await api.getConversation(task.conversationId!);
          _ref.read(activeConversationProvider.notifier).set(conv);
        } catch (_) {}
      }
    } catch (_) {}

    // Lookup tool by name (or id fallback)
    String? resolvedToolId;
    try {
      final tools = await api.getAvailableTools();
      for (final t in tools) {
        final id = (t['id'] ?? '').toString();
        final name = (t['name'] ?? '').toString();
        if (name.toLowerCase() == task.toolName.toLowerCase() ||
            id.toLowerCase() == task.toolName.toLowerCase()) {
          resolvedToolId = id;
          break;
        }
      }
    } catch (_) {}

    // Build an explicit user instruction to run the tool with arguments.
    // Passing the specific tool id hints the server/provider to execute it via native function calling.
    final args = task.arguments;
    String argsSnippet;
    try {
      argsSnippet = const JsonEncoder.withIndent('  ').convert(args);
    } catch (_) {
      argsSnippet = args.toString();
    }
    final instruction =
        'Run the tool "${task.toolName}" with the following JSON arguments and return the result succinctly.\n'
        'If the tool is not available, respond with a brief error.\n\n'
        'Arguments:\n'
        '```json\n$argsSnippet\n```';

    // Send as a normal message but constrain tools to the resolved tool (if found)
    final toolIds = (resolvedToolId != null && resolvedToolId.isNotEmpty)
        ? <String>[resolvedToolId]
        : null;

    await chat.sendMessageFromService(_ref, instruction, null, toolIds);
  }

  Future<void> _performGenerateImage(GenerateImageTask task) async {
    final api = _ref.read(apiServiceProvider);
    final selectedModel = _ref.read(selectedModelProvider);
    if (api == null || selectedModel == null) {
      throw Exception('API or model not available');
    }

    // Ensure the target conversation is active if provided
    try {
      final active = _ref.read(activeConversationProvider);
      if (task.conversationId != null &&
          task.conversationId!.isNotEmpty &&
          (active == null || active.id != task.conversationId)) {
        try {
          final conv = await api.getConversation(task.conversationId!);
          _ref.read(activeConversationProvider.notifier).set(conv);
        } catch (_) {}
      }
    } catch (_) {}

    // Temporarily enable image-generation background flow for this send
    final prev = _ref.read(chat.imageGenerationEnabledProvider);
    try {
      _ref.read(chat.imageGenerationEnabledProvider.notifier).set(true);
      await chat.sendMessageFromService(_ref, task.prompt, null, null);
    } finally {
      _ref.read(chat.imageGenerationEnabledProvider.notifier).set(prev);
    }
  }

  Future<void> _performImageToDataUrl(ImageToDataUrlTask task) async {
    // Upload images to server instead of converting to data URLs
    final uploader = AttachmentUploadQueue();
    try {
      final api = _ref.read(apiServiceProvider);
      if (api != null) {
        await uploader.initialize(onUpload: (p, n) => api.uploadFile(p, n));
      }
    } catch (_) {}

    try {
      final current = _ref.read(attachedFilesProvider);
      final idx = current.indexWhere((f) => f.file.path == task.filePath);
      if (idx != -1) {
        final existing = current[idx];
        final uploading = FileUploadState(
          file: existing.file,
          fileName: task.fileName,
          fileSize: existing.fileSize,
          progress: 0.0,
          status: FileUploadStatus.uploading,
          fileId: existing.fileId,
        );
        _ref
            .read(attachedFilesProvider.notifier)
            .updateFileState(task.filePath, uploading);
      }
    } catch (_) {}

    final id = await uploader.enqueue(
      filePath: task.filePath,
      fileName: task.fileName,
      fileSize: File(task.filePath).lengthSync(),
    );

    final completer = Completer<void>();
    late final StreamSubscription<List<QueuedAttachment>> sub;
    sub = uploader.queueStream.listen((items) {
      QueuedAttachment? entry;
      try {
        entry = items.firstWhere((e) => e.id == id);
      } catch (_) {
        entry = null;
      }
      if (entry == null) return;
      try {
        final current = _ref.read(attachedFilesProvider);
        final idx = current.indexWhere((f) => f.file.path == task.filePath);
        if (idx != -1) {
          final existing = current[idx];
          final status = switch (entry.status) {
            QueuedAttachmentStatus.pending => FileUploadStatus.uploading,
            QueuedAttachmentStatus.uploading => FileUploadStatus.uploading,
            QueuedAttachmentStatus.completed => FileUploadStatus.completed,
            QueuedAttachmentStatus.failed => FileUploadStatus.failed,
            QueuedAttachmentStatus.cancelled => FileUploadStatus.failed,
          };
          final newState = FileUploadState(
            file: File(task.filePath),
            fileName: task.fileName,
            fileSize: existing.fileSize,
            progress: status == FileUploadStatus.completed
                ? 1.0
                : existing.progress,
            status: status,
            fileId: entry.fileId ?? existing.fileId,
            isImage: true,
            error: entry.lastError,
          );
          _ref
              .read(attachedFilesProvider.notifier)
              .updateFileState(task.filePath, newState);
        }
      } catch (_) {}
      switch (entry.status) {
        case QueuedAttachmentStatus.completed:
        case QueuedAttachmentStatus.failed:
        case QueuedAttachmentStatus.cancelled:
          sub.cancel();
          completer.complete();
          break;
        default:
          break;
      }
    });

    unawaited(uploader.processQueue());
    await completer.future.timeout(
      const Duration(minutes: 2),
      onTimeout: () {
        try {
          sub.cancel();
        } catch (_) {}
        DebugLogger.warning('Image upload timed out: ${task.fileName}');
        return;
      },
    );
  }
}
