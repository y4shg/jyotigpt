import 'dart:async';

import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import '../../../core/providers/app_providers.dart';
import '../../../core/services/background_streaming_handler.dart';
import '../../../core/services/socket_service.dart';
import '../../../core/utils/markdown_to_text.dart';
import '../providers/chat_providers.dart';
import 'text_to_speech_service.dart';
import 'voice_input_service.dart';
import 'voice_call_notification_service.dart';

part 'voice_call_service.g.dart';

enum VoiceCallState {
  idle,
  connecting,
  listening,
  processing,
  speaking,
  error,
  disconnected,
}

class VoiceCallService {
  static const String _voiceCallStreamId = 'voice-call';

  final VoiceInputService _voiceInput;
  final TextToSpeechService _tts;
  final SocketService _socketService;
  final Ref _ref;
  final VoiceCallNotificationService _notificationService =
      VoiceCallNotificationService();

  VoiceCallState _state = VoiceCallState.idle;
  String? _sessionId;
  StreamSubscription<String>? _transcriptSubscription;
  StreamSubscription<int>? _intensitySubscription;
  String _accumulatedTranscript = '';
  bool _isDisposed = false;
  bool _isMuted = false;
  SocketEventSubscription? _socketSubscription;
  Timer? _keepAliveTimer;

  final StreamController<VoiceCallState> _stateController =
      StreamController<VoiceCallState>.broadcast();
  final StreamController<String> _transcriptController =
      StreamController<String>.broadcast();
  final StreamController<String> _responseController =
      StreamController<String>.broadcast();
  final StreamController<int> _intensityController =
      StreamController<int>.broadcast();

  VoiceCallService({
    required VoiceInputService voiceInput,
    required TextToSpeechService tts,
    required SocketService socketService,
    required Ref ref,
  }) : _voiceInput = voiceInput,
       _tts = tts,
       _socketService = socketService,
       _ref = ref {
    _tts.bindHandlers(
      onStart: _handleTtsStart,
      onComplete: _handleTtsComplete,
      onError: _handleTtsError,
    );

    // Set up notification action handler
    _notificationService.onActionPressed = _handleNotificationAction;
  }

  VoiceCallState get state => _state;
  Stream<VoiceCallState> get stateStream => _stateController.stream;
  Stream<String> get transcriptStream => _transcriptController.stream;
  Stream<String> get responseStream => _responseController.stream;
  Stream<int> get intensityStream => _intensityController.stream;

  Future<void> initialize() async {
    if (_isDisposed) return;

    // Initialize notification service
    await _notificationService.initialize();

    // Request notification permissions if needed
    final notificationsEnabled = await _notificationService
        .areNotificationsEnabled();
    if (!notificationsEnabled) {
      await _notificationService.requestPermissions();
    }

    // Initialize voice input
    final voiceInitialized = await _voiceInput.initialize();
    if (!voiceInitialized) {
      _updateState(VoiceCallState.error);
      throw Exception('Voice input initialization failed');
    }

    // Check if local STT is available
    final hasLocalStt = _voiceInput.hasLocalStt;
    if (!hasLocalStt) {
      _updateState(VoiceCallState.error);
      throw Exception('Speech recognition not available on this device');
    }

    // Check microphone permissions
    final hasMicPermission = await _voiceInput.checkPermissions();
    if (!hasMicPermission) {
      _updateState(VoiceCallState.error);
      throw Exception('Microphone permission not granted');
    }

    // Initialize TTS
    await _tts.initialize();
  }

  Future<void> startCall(String? conversationId) async {
    if (_isDisposed) return;

    try {
      // Update state (this will trigger notification)
      _updateState(VoiceCallState.connecting);

      // Enable wake lock to keep screen on and prevent audio interruption
      await WakelockPlus.enable();

      // Ensure socket connection
      await _socketService.ensureConnected();
      _sessionId = _socketService.sessionId;

      if (_sessionId == null) {
        throw Exception('Failed to establish socket connection');
      }

      await BackgroundStreamingHandler.instance.startBackgroundExecution(const [
        _voiceCallStreamId,
      ], requiresMicrophone: true);

      // Set up periodic keep-alive to refresh wake lock (every 5 minutes)
      _keepAliveTimer?.cancel();
      _keepAliveTimer = Timer.periodic(
        const Duration(minutes: 5),
        (_) => BackgroundStreamingHandler.instance.keepAlive(),
      );

      // Set up socket event listener for assistant responses
      _socketSubscription = _socketService.addChatEventHandler(
        conversationId: conversationId,
        sessionId: _sessionId,
        requireFocus: false,
        handler: _handleSocketEvent,
      );

      // Start listening for user voice input
      await _startListening();
    } catch (e) {
      _updateState(VoiceCallState.error);
      _keepAliveTimer?.cancel();
      _keepAliveTimer = null;
      await WakelockPlus.disable();
      await _notificationService.cancelNotification();
      await BackgroundStreamingHandler.instance.stopBackgroundExecution(const [
        _voiceCallStreamId,
      ]);
      rethrow;
    }
  }

  Future<void> _startListening() async {
    if (_isDisposed) return;

    try {
      _accumulatedTranscript = '';

      // Check if voice input is available
      if (!_voiceInput.hasLocalStt) {
        _updateState(VoiceCallState.error);
        throw Exception('Voice input not available on this device');
      }

      _updateState(VoiceCallState.listening);

      final stream = await _voiceInput.beginListening();

      _transcriptSubscription = stream.listen(
        (text) {
          if (_isDisposed) return;
          _accumulatedTranscript = text;
          _transcriptController.add(text);
        },
        onError: (error) {
          if (_isDisposed) return;
          _updateState(VoiceCallState.error);
        },
        onDone: () async {
          if (_isDisposed) return;
          // User stopped speaking, send message to assistant
          if (_accumulatedTranscript.trim().isNotEmpty) {
            await _sendMessageToAssistant(_accumulatedTranscript);
          } else {
            // No input, restart listening
            await _startListening();
          }
        },
      );

      // Forward intensity stream for waveform visualization
      _intensitySubscription = _voiceInput.intensityStream.listen((intensity) {
        if (_isDisposed) return;
        _intensityController.add(intensity);
      });
    } catch (e) {
      _updateState(VoiceCallState.error);
      rethrow;
    }
  }

  Future<void> _sendMessageToAssistant(String text) async {
    if (_isDisposed) return;

    try {
      _updateState(VoiceCallState.processing);
      _accumulatedResponse = ''; // Reset response accumulator

      // Send message using the existing chat infrastructure
      sendMessageFromService(_ref, text, null);
    } catch (e) {
      _updateState(VoiceCallState.error);
      rethrow;
    }
  }

  String _accumulatedResponse = '';
  bool _isSpeaking = false;

  void _handleSocketEvent(
    Map<String, dynamic> event,
    void Function(dynamic response)? ack,
  ) {
    if (_isDisposed) return;

    final outerData = event['data'];

    if (outerData is Map<String, dynamic>) {
      final eventType = outerData['type']?.toString();
      final innerData = outerData['data'];

      if (eventType == 'chat:completion' && innerData is Map<String, dynamic>) {
        // Handle full content replacement (used by some models/backends)
        if (innerData.containsKey('content')) {
          final content = innerData['content']?.toString() ?? '';
          if (content.isNotEmpty) {
            _accumulatedResponse = content;
            _responseController.add(content);
          }
        }

        // Handle streaming delta chunks (incremental updates)
        if (innerData.containsKey('choices')) {
          final choices = innerData['choices'] as List?;
          if (choices != null && choices.isNotEmpty) {
            final firstChoice = choices[0] as Map<String, dynamic>?;
            final delta = firstChoice?['delta'];
            final finishReason = firstChoice?['finish_reason'];

            // Extract incremental content from delta
            if (delta is Map<String, dynamic>) {
              final deltaContent = delta['content']?.toString() ?? '';
              if (deltaContent.isNotEmpty) {
                _accumulatedResponse += deltaContent;
                _responseController.add(_accumulatedResponse);
              }
            }

            // Check for completion
            if (finishReason == 'stop') {
              if (_accumulatedResponse.isNotEmpty && !_isSpeaking) {
                _speakResponse(_accumulatedResponse);
                _accumulatedResponse = '';
              } else if (_accumulatedResponse.isEmpty) {
                // No response, restart listening
                _startListening();
              }
            }
          }
        }
      }
    }
  }

  Future<void> _speakResponse(String response) async {
    if (_isDisposed || _isSpeaking) return;

    try {
      _isSpeaking = true;

      // Stop listening before speaking
      await _voiceInput.stopListening();
      await _transcriptSubscription?.cancel();
      await _intensitySubscription?.cancel();

      _updateState(VoiceCallState.speaking);

      // Convert markdown to clean text for TTS
      final cleanText = MarkdownToText.convert(response);
      if (cleanText.isEmpty) {
        // No speakable content, restart listening
        _isSpeaking = false;
        await _startListening();
        return;
      }

      await _tts.speak(cleanText);
      // After speaking completes, _handleTtsComplete will restart listening
    } catch (e) {
      _isSpeaking = false;
      _updateState(VoiceCallState.error);
      // Restart listening even if TTS fails
      await _startListening();
    }
  }

  void _handleTtsStart() {
    if (_isDisposed) return;
    _updateState(VoiceCallState.speaking);
  }

  void _handleTtsComplete() {
    if (_isDisposed) return;
    _isSpeaking = false;
    // After assistant finishes speaking, start listening for user again
    _startListening();
  }

  void _handleTtsError(String error) {
    if (_isDisposed) return;
    _updateState(VoiceCallState.error);
    // Try to recover by restarting listening
    _startListening();
  }

  Future<void> stopCall() async {
    if (_isDisposed) return;

    // Cancel keep-alive timer
    _keepAliveTimer?.cancel();
    _keepAliveTimer = null;

    await _transcriptSubscription?.cancel();
    await _intensitySubscription?.cancel();
    _socketSubscription?.dispose();

    await _voiceInput.stopListening();
    await _tts.stop();

    await BackgroundStreamingHandler.instance.stopBackgroundExecution(const [
      _voiceCallStreamId,
    ]);

    // Cancel notification
    await _notificationService.cancelNotification();

    // Disable wake lock when call ends
    await WakelockPlus.disable();

    _sessionId = null;
    _accumulatedTranscript = '';
    _isMuted = false;
    _updateState(VoiceCallState.disconnected);
  }

  Future<void> pauseListening() async {
    if (_isDisposed) return;
    await _voiceInput.stopListening();
    await _transcriptSubscription?.cancel();
    await _intensitySubscription?.cancel();
  }

  Future<void> resumeListening() async {
    if (_isDisposed) return;
    await _startListening();
  }

  Future<void> cancelSpeaking() async {
    if (_isDisposed) return;
    await _tts.stop();
    // Immediately restart listening
    await _startListening();
  }

  void _updateState(VoiceCallState newState) {
    if (_isDisposed) return;
    _state = newState;
    _stateController.add(newState);

    // Update notification when state changes (fire and forget)
    _updateNotification().catchError((e) {
      // Ignore notification errors
    });
  }

  Future<void> _updateNotification() async {
    // Skip notification for idle, error, and disconnected states
    if (_state == VoiceCallState.idle ||
        _state == VoiceCallState.error ||
        _state == VoiceCallState.disconnected) {
      return;
    }

    try {
      final selectedModel = _ref.read(selectedModelProvider);
      final modelName = selectedModel?.name ?? 'Assistant';

      await _notificationService.updateCallStatus(
        modelName: modelName,
        isMuted: _isMuted,
        isSpeaking: _state == VoiceCallState.speaking,
      );
    } catch (e) {
      // Silently ignore notification errors
    }
  }

  void _handleNotificationAction(String action) {
    switch (action) {
      case 'mute_call':
        _toggleMute();
        break;
      case 'unmute_call':
        _toggleMute();
        break;
      case 'end_call':
        stopCall();
        break;
    }
  }

  void _toggleMute() {
    _isMuted = !_isMuted;
    if (_isMuted) {
      pauseListening();
    } else {
      resumeListening();
    }
    _updateNotification();
  }

  Future<void> dispose() async {
    _isDisposed = true;

    // Cancel keep-alive timer
    _keepAliveTimer?.cancel();
    _keepAliveTimer = null;

    await _transcriptSubscription?.cancel();
    await _intensitySubscription?.cancel();
    _socketSubscription?.dispose();

    _voiceInput.dispose();
    await _tts.dispose();

    // Cancel notification
    await _notificationService.cancelNotification();

    // Ensure wake lock is disabled on dispose
    await WakelockPlus.disable();

    await BackgroundStreamingHandler.instance.stopBackgroundExecution(const [
      _voiceCallStreamId,
    ]);

    await _stateController.close();
    await _transcriptController.close();
    await _responseController.close();
    await _intensityController.close();
  }
}

@Riverpod(keepAlive: true)
VoiceCallService voiceCallService(Ref ref) {
  final voiceInput = ref.watch(voiceInputServiceProvider);
  final tts = TextToSpeechService();
  final socketService = ref.watch(socketServiceProvider);

  if (socketService == null) {
    throw Exception('Socket service not available');
  }

  final service = VoiceCallService(
    voiceInput: voiceInput,
    tts: tts,
    socketService: socketService,
    ref: ref,
  );

  ref.onDispose(() {
    service.dispose();
  });

  return service;
}
