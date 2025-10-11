import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/markdown_to_text.dart';
import '../services/text_to_speech_service.dart';

enum TtsPlaybackStatus { idle, initializing, loading, speaking, paused, error }

class TextToSpeechState {
  final bool initialized;
  final bool available;
  final TtsPlaybackStatus status;
  final String? activeMessageId;
  final String? errorMessage;

  const TextToSpeechState({
    this.initialized = false,
    this.available = false,
    this.status = TtsPlaybackStatus.idle,
    this.activeMessageId,
    this.errorMessage,
  });

  bool get isSpeaking => status == TtsPlaybackStatus.speaking;
  bool get isBusy =>
      status == TtsPlaybackStatus.loading ||
      status == TtsPlaybackStatus.initializing;

  TextToSpeechState copyWith({
    bool? initialized,
    bool? available,
    TtsPlaybackStatus? status,
    String? activeMessageId,
    bool clearActiveMessageId = false,
    String? errorMessage,
    bool clearErrorMessage = false,
  }) {
    return TextToSpeechState(
      initialized: initialized ?? this.initialized,
      available: available ?? this.available,
      status: status ?? this.status,
      activeMessageId: clearActiveMessageId
          ? null
          : activeMessageId ?? this.activeMessageId,
      errorMessage: clearErrorMessage
          ? null
          : errorMessage ?? this.errorMessage,
    );
  }
}

class TextToSpeechController extends Notifier<TextToSpeechState> {
  late final TextToSpeechService _service;
  bool _handlersBound = false;
  Future<bool>? _initializationFuture;

  @override
  TextToSpeechState build() {
    _service = ref.watch(textToSpeechServiceProvider);
    if (!_handlersBound) {
      _handlersBound = true;
      _service.bindHandlers(
        onStart: _handleStart,
        onComplete: _handleCompletion,
        onCancel: _handleCancellation,
        onPause: _handlePause,
        onContinue: _handleContinue,
        onError: _handleError,
      );

      ref.onDispose(() {
        unawaited(_service.stop());
      });
    }
    return const TextToSpeechState();
  }

  Future<bool> _ensureInitialized() {
    final existing = _initializationFuture;
    if (existing != null) {
      return existing;
    }

    state = state.copyWith(
      status: TtsPlaybackStatus.initializing,
      clearErrorMessage: true,
    );

    final future = _service
        .initialize()
        .then((available) {
          if (!ref.mounted) {
            return available;
          }

          state = state.copyWith(
            initialized: true,
            available: available,
            status: TtsPlaybackStatus.idle,
          );
          return available;
        })
        .catchError((error, _) {
          if (!ref.mounted) {
            return false;
          }

          state = state.copyWith(
            initialized: true,
            available: false,
            status: TtsPlaybackStatus.error,
            errorMessage: error.toString(),
            clearActiveMessageId: true,
          );
          return false;
        });

    _initializationFuture = future;
    future.whenComplete(() {
      _initializationFuture = null;
    });

    return future;
  }

  Future<void> toggleForMessage({
    required String messageId,
    required String text,
  }) async {
    if (text.trim().isEmpty) {
      return;
    }

    final isCurrentlyActive =
        state.activeMessageId == messageId &&
        state.status != TtsPlaybackStatus.idle &&
        state.status != TtsPlaybackStatus.error;

    if (isCurrentlyActive) {
      await stop();
      return;
    }

    final available = await _ensureInitialized();
    if (!available) {
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(
        status: TtsPlaybackStatus.error,
        errorMessage: 'Text-to-speech unavailable',
        clearActiveMessageId: true,
      );
      return;
    }

    state = state.copyWith(
      status: TtsPlaybackStatus.loading,
      activeMessageId: messageId,
      clearErrorMessage: true,
    );

    try {
      // Convert markdown to clean text for TTS
      final cleanText = MarkdownToText.convert(text);
      if (cleanText.isEmpty) {
        // No speakable content
        if (!ref.mounted) {
          return;
        }
        state = state.copyWith(
          status: TtsPlaybackStatus.idle,
          clearActiveMessageId: true,
        );
        return;
      }

      await _service.speak(cleanText);
      if (!ref.mounted) {
        return;
      }
      if (state.status == TtsPlaybackStatus.loading) {
        state = state.copyWith(status: TtsPlaybackStatus.speaking);
      }
    } catch (e) {
      if (!ref.mounted) {
        return;
      }
      state = state.copyWith(
        status: TtsPlaybackStatus.error,
        errorMessage: e.toString(),
        clearActiveMessageId: true,
      );
    }
  }

  Future<void> pause() async {
    if (!state.initialized || !state.available) {
      return;
    }
    await _service.pause();
  }

  Future<void> stop() async {
    await _service.stop();
    if (!ref.mounted) {
      return;
    }
    state = state.copyWith(
      status: TtsPlaybackStatus.idle,
      clearActiveMessageId: true,
      clearErrorMessage: true,
    );
  }

  void _handleStart() {
    if (!ref.mounted) {
      return;
    }
    state = state.copyWith(status: TtsPlaybackStatus.speaking);
  }

  void _handleCompletion() {
    if (!ref.mounted) {
      return;
    }
    state = state.copyWith(
      status: TtsPlaybackStatus.idle,
      clearActiveMessageId: true,
    );
  }

  void _handleCancellation() {
    if (!ref.mounted) {
      return;
    }
    state = state.copyWith(
      status: TtsPlaybackStatus.idle,
      clearActiveMessageId: true,
    );
  }

  void _handlePause() {
    if (!ref.mounted) {
      return;
    }
    state = state.copyWith(status: TtsPlaybackStatus.paused);
  }

  void _handleContinue() {
    if (!ref.mounted) {
      return;
    }
    state = state.copyWith(status: TtsPlaybackStatus.speaking);
  }

  void _handleError(String message) {
    if (!ref.mounted) {
      return;
    }
    state = state.copyWith(
      status: TtsPlaybackStatus.error,
      errorMessage: message,
      clearActiveMessageId: true,
    );
  }
}

final textToSpeechServiceProvider = Provider<TextToSpeechService>((ref) {
  final service = TextToSpeechService();
  ref.onDispose(() {
    unawaited(service.dispose());
  });
  return service;
});

final textToSpeechControllerProvider =
    NotifierProvider<TextToSpeechController, TextToSpeechState>(
      TextToSpeechController.new,
    );
