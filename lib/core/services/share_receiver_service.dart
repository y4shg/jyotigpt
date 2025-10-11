import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_handler/share_handler.dart' as sh;

import '../../features/auth/providers/unified_auth_providers.dart';
import '../../features/chat/providers/chat_providers.dart';
import '../../features/chat/services/file_attachment_service.dart';
import '../../core/providers/app_providers.dart';
import '../../shared/services/tasks/task_queue.dart';
import 'package:path/path.dart' as path;
import 'navigation_service.dart';
import '../utils/debug_logger.dart';
// Server chat creation/title generation occur on first send via chat providers

/// Lightweight payload for a share event
class SharedPayload {
  final String? text;
  final List<String> filePaths;
  const SharedPayload({this.text, this.filePaths = const []});

  bool get hasAnything =>
      (text != null && text!.trim().isNotEmpty) || filePaths.isNotEmpty;
}

/// Holds a pending shared payload until the app is ready (e.g., authed + model loaded)
final pendingSharedPayloadProvider =
    NotifierProvider<PendingSharedPayloadNotifier, SharedPayload?>(
      PendingSharedPayloadNotifier.new,
    );

class PendingSharedPayloadNotifier extends Notifier<SharedPayload?> {
  @override
  SharedPayload? build() => null;

  void set(SharedPayload? payload) => state = payload;
}

/// Initializes listening to OS share intents and handles them
final shareReceiverInitializerProvider = Provider<void>((ref) {
  // Only mobile platforms handle OS share intents
  if (kIsWeb) return;
  if (!(Platform.isAndroid || Platform.isIOS)) return;

  // Listen for app readiness: authenticated and model available
  void maybeProcessPending() {
    final navState = ref.read(authNavigationStateProvider);
    final model = ref.read(selectedModelProvider);
    final pending = ref.read(pendingSharedPayloadProvider);
    final isOnChatRoute = NavigationService.currentRoute == Routes.chat;
    if (pending != null &&
        pending.hasAnything &&
        navState == AuthNavigationState.authenticated &&
        model != null &&
        isOnChatRoute) {
      _processPayload(ref, pending);
      ref.read(pendingSharedPayloadProvider.notifier).set(null);
    }
  }

  // React when auth/model changes to process a queued share
  ref.listen<AuthNavigationState>(
    authNavigationStateProvider,
    (prev, next) => maybeProcessPending(),
  );
  ref.listen(selectedModelProvider, (prev, next) => maybeProcessPending());
  // Also poll once shortly after navigation settles to ensure ChatPage is ready
  Future.delayed(
    const Duration(milliseconds: 150),
    () => maybeProcessPending(),
  );

  // Hook into share_handler after a short defer to avoid startup contention
  WidgetsBinding.instance.addPostFrameCallback((_) async {
    await Future.delayed(const Duration(milliseconds: 300));

    final handler = sh.ShareHandler.instance;

    // Handle initial share when app is cold-started via Share
    Future.microtask(() async {
      try {
        final dynamic media = await handler.getInitialSharedMedia();
        final payload = _toPayload(media);
        if (payload.hasAnything) {
          ref.read(pendingSharedPayloadProvider.notifier).set(payload);
          maybeProcessPending();
        }
      } catch (e) {
        DebugLogger.log(
          'ShareReceiver: failed to get initial shared media: $e',
          scope: 'share',
        );
      }
    });

    // Handle subsequent shares while app is alive
    final streamSub = handler.sharedMediaStream.listen((dynamic media) {
      try {
        final payload = _toPayload(media);
        if (payload.hasAnything) {
          ref.read(pendingSharedPayloadProvider.notifier).set(payload);
          maybeProcessPending();
        }
      } catch (e) {
        DebugLogger.log(
          'ShareReceiver: failed to parse shared media: $e',
          scope: 'share',
        );
      }
    });

    // Ensure cleanup
    ref.onDispose(() async {
      await streamSub.cancel();
    });
  });
});

SharedPayload _toPayload(dynamic media) {
  if (media == null) return const SharedPayload();

  String? text;
  final filePaths = <String>[];

  try {
    // Common field in share_handler: `content` (String?)
    text = (media as dynamic).content as String?;
  } catch (_) {
    try {
      // Some plugins use `text`
      text = (media as dynamic).text as String?;
    } catch (_) {}
  }

  try {
    final list = (media as dynamic).attachments as List<dynamic>?;
    if (list != null) {
      for (final att in list) {
        try {
          final p = (att as dynamic).path as String?;
          if (p != null && p.isNotEmpty) filePaths.add(p);
        } catch (_) {
          // Ignore a malformed entry
        }
      }
    }
  } catch (_) {
    // Older plugins may call it files
    try {
      final list = (media as dynamic).files as List<dynamic>?;
      if (list != null) {
        for (final att in list) {
          try {
            final p = (att as dynamic).path as String?;
            if (p != null && p.isNotEmpty) filePaths.add(p);
          } catch (_) {}
        }
      }
    } catch (_) {}
  }

  return SharedPayload(text: text, filePaths: filePaths);
}

Future<void> _processPayload(Ref ref, SharedPayload payload) async {
  try {
    // Start a fresh chat context but do NOT auto-send
    startNewChat(ref);

    // Prefer attaching files to the composer so user can add text before sending
    if (payload.filePaths.isNotEmpty) {
      final svc = ref.read(fileAttachmentServiceProvider);
      if (svc != null) {
        // Add files to attachment list and kick off uploads, mirroring UI flow
        final files = payload.filePaths.map((p) => File(p)).toList();
        if (files.isNotEmpty) {
          ref.read(attachedFilesProvider.notifier).addFiles(files);

          // Enqueue uploads via task queue to unify progress + retry
          final activeConv = ref.read(activeConversationProvider);
          for (final file in files) {
            try {
              await ref
                  .read(taskQueueProvider.notifier)
                  .enqueueUploadMedia(
                    conversationId: activeConv?.id,
                    filePath: file.path,
                    fileName: path.basename(file.path),
                    fileSize: await file.length(),
                  );
            } catch (_) {}
          }
        }
      }
    }

    // Prefill text in the composer (do not auto-send) and request focus
    final text = payload.text?.trim();
    if (text != null && text.isNotEmpty) {
      ref.read(prefilledInputTextProvider.notifier).set(text);
      // Bump focus trigger to ensure input focuses after navigation/build
      final current = ref.read(inputFocusTriggerProvider);
      ref.read(inputFocusTriggerProvider.notifier).set(current + 1);
    }
    // Do NOT create a server chat here. The chat is created on first send
    // (with server syncing + title generation) in chat_providers.dart.
  } catch (e) {
    DebugLogger.log(
      'ShareReceiver: failed to process payload: $e',
      scope: 'share',
    );
  }
}
