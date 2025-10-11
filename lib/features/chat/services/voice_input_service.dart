import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:record/record.dart';
import 'package:stts/stts.dart';

part 'voice_input_service.g.dart';
// Removed path imports as server transcription fallback was removed

// Lightweight replacement for previous stt.LocaleName used across the UI
class LocaleName {
  final String localeId;
  final String name;
  const LocaleName(this.localeId, this.name);
}

class VoiceInputService {
  final AudioRecorder _recorder = AudioRecorder();
  final Stt _speech = Stt();
  bool _isInitialized = false;
  bool _isListening = false;
  bool _localSttAvailable = false;
  String? _selectedLocaleId;
  List<LocaleName> _locales = const [];
  StreamController<String>? _textStreamController;
  String _currentText = '';
  // Public stream for UI waveform visualization (emits partial text length as proxy)
  StreamController<int>? _intensityController;
  Stream<int> get intensityStream =>
      _intensityController?.stream ?? const Stream<int>.empty();
  int _lastIntensity = 0;
  Timer? _intensityDecayTimer;

  /// Public stream of partial/final transcript strings and special audio tokens.
  Stream<String> get textStream =>
      _textStreamController?.stream ?? const Stream<String>.empty();
  Timer? _autoStopTimer;
  StreamSubscription<Amplitude>? _ampSub;
  StreamSubscription<SttRecognition>? _sttResultSub;
  StreamSubscription<SttState>? _sttStateSub;

  bool get isSupportedPlatform => Platform.isAndroid || Platform.isIOS;

  Future<bool> initialize() async {
    if (_isInitialized) return true;
    if (!isSupportedPlatform) return false;
    // Prepare local speech recognizer
    try {
      // Check permission and supported status
      _localSttAvailable = await _speech.isSupported();
      if (_localSttAvailable) {
        try {
          final langs = await _speech.getLanguages();
          _locales = langs.map((l) => LocaleName(l, l)).toList();
          final deviceTag = WidgetsBinding.instance.platformDispatcher.locale
              .toLanguageTag();
          final match = _locales.firstWhere(
            (l) => l.localeId.toLowerCase() == deviceTag.toLowerCase(),
            orElse: () {
              final primary = deviceTag
                  .split(RegExp('[-_]'))
                  .first
                  .toLowerCase();
              return _locales.firstWhere(
                (l) => l.localeId.toLowerCase().startsWith('$primary-'),
                orElse: () => _locales.isNotEmpty
                    ? _locales.first
                    : LocaleName('en_US', 'en_US'),
              );
            },
          );
          _selectedLocaleId = match.localeId;
        } catch (e) {
          // ignore locale load errors
          _selectedLocaleId = null;
        }
      }
    } catch (_) {
      _localSttAvailable = false;
    }
    _isInitialized = true;
    return true;
  }

  Future<bool> checkPermissions() async {
    try {
      // Prefer stts permission check which will request microphone permission
      final mic = await _speech.hasPermission();
      if (mic) return true;
      return await _recorder.hasPermission();
    } catch (_) {
      return false;
    }
  }

  bool get isListening => _isListening;
  bool get isAvailable => _isInitialized; // service usable (local or fallback)
  bool get hasLocalStt => _localSttAvailable;

  // Add a method to check if on-device STT is properly supported
  Future<bool> checkOnDeviceSupport() async {
    if (!isSupportedPlatform || !_isInitialized) return false;
    try {
      final supported = await _speech.isSupported();
      return supported;
    } catch (e) {
      // ignore errors checking on-device support
      return false;
    }
  }

  // Test method to verify on-device STT functionality
  Future<String> testOnDeviceStt() async {
    try {
      // starting on-device STT test

      // First ensure we're initialized
      await initialize();

      if (!_localSttAvailable) {
        return 'Local STT not available. Available: $_localSttAvailable';
      }

      // Check microphone permission
      final hasMic = await checkPermissions();
      if (!hasMic) {
        return 'Microphone permission not granted';
      }

      // Test if speech recognition is available
      final supported = await _speech.isSupported();
      if (!supported) {
        return 'Speech recognition service is not available on this device';
      }

      // Set language if available, then start and stop quickly
      if (_selectedLocaleId != null) {
        try {
          await _speech.setLanguage(_selectedLocaleId!);
        } catch (_) {}
      }
      await _speech.start(SttRecognitionOptions(punctuation: true));
      await Future.delayed(const Duration(milliseconds: 100));
      await _speech.stop();

      return 'On-device STT test completed successfully. Local STT available: $_localSttAvailable, Selected locale: $_selectedLocaleId';
    } catch (e) {
      // on-device STT test failed
      return 'On-device STT test failed: $e';
    }
  }

  String? get selectedLocaleId => _selectedLocaleId;
  List<LocaleName> get locales => _locales;

  void setLocale(String? localeId) {
    _selectedLocaleId = localeId;
  }

  Stream<String> startListening() {
    if (!_isInitialized) {
      throw Exception('Voice input not initialized');
    }

    if (_isListening) {
      stopListening();
    }

    _textStreamController = StreamController<String>.broadcast();
    _currentText = '';
    _isListening = true;
    _intensityController = StreamController<int>.broadcast();
    _lastIntensity = 0;

    // Begin a gentle decay timer so the UI level bars fall when silent
    _intensityDecayTimer?.cancel();
    _intensityDecayTimer = Timer.periodic(const Duration(milliseconds: 120), (
      t,
    ) {
      if (!_isListening) return;
      if (_lastIntensity <= 0) return;
      _lastIntensity = (_lastIntensity - 1).clamp(0, 10);
      try {
        _intensityController?.add(_lastIntensity);
      } catch (_) {}
    });

    // Check if speech recognition is available before trying to use it
    if (_localSttAvailable) {
      // Schedule a check for speech recognition availability
      Future.microtask(() async {
        try {
          final isStillAvailable = await _speech.isSupported();
          if (!isStillAvailable && _isListening) {
            // Speech recognition no longer available; stop listening
            _localSttAvailable = false;
            _stopListening();
            return;
          }
        } catch (e) {
          // ignore availability check errors
        }
      });

      // Local on-device STT path
      _autoStopTimer?.cancel();
      _autoStopTimer = Timer(const Duration(seconds: 60), () {
        if (_isListening) {
          _stopListening();
        }
      });

      // Listen for results and state changes; keep subscriptions so we can cancel later
      _sttResultSub = _speech.onResultChanged.listen((SttRecognition result) {
        if (!_isListening) return;
        final prevLen = _currentText.length;
        _currentText = result.text;
        _textStreamController?.add(_currentText);
        // Map number of new characters to a rough 0..10 intensity
        final delta = (_currentText.length - prevLen).clamp(0, 50);
        final mapped = (delta / 5.0).ceil(); // 0 chars -> 0, 1-5 -> 1, ...
        _lastIntensity = mapped.clamp(0, 10);
        try {
          _intensityController?.add(_lastIntensity);
        } catch (_) {}
        if (result.isFinal) {
          _stopListening();
        }
      }, onError: (_) {});

      _sttStateSub = _speech.onStateChanged.listen((_) {}, onError: (_) {});

      try {
        if (_selectedLocaleId != null) {
          _speech.setLanguage(_selectedLocaleId!).catchError((_) {});
        }
        // Start recognition (no await blocking the sync flow)
        _speech.start(SttRecognitionOptions(punctuation: true)).catchError((_) {
          // On-device STT failed; stop listening entirely as server transcription is removed
          _localSttAvailable = false;
          _stopListening();
        });
      } catch (e) {
        _localSttAvailable = false;
        _stopListening();
      }
    } else {
      // No local STT available; stop immediately since server transcription is removed
      _stopListening();
    }

    return _textStreamController!.stream;
  }

  /// Centralized entry point to begin voice recognition.
  /// Ensures initialization and microphone permission before starting.
  Future<Stream<String>> beginListening() async {
    // Ensure service is ready
    await initialize();
    // Ensure microphone permission (triggers OS prompt if needed)
    final hasMic = await checkPermissions();
    if (!hasMic) {
      throw Exception('Microphone permission not granted');
    }
    // Start listening and return the transcript stream
    return startListening();
  }

  Future<void> stopListening() async {
    await _stopListening();
  }

  Future<void> _stopListening() async {
    if (!_isListening) return;

    _isListening = false;
    if (_localSttAvailable) {
      try {
        await _speech.stop();
      } catch (_) {}
      // Cancel STT subscriptions
      try {
        _sttResultSub?.cancel();
      } catch (_) {}
      _sttResultSub = null;
      try {
        _sttStateSub?.cancel();
      } catch (_) {}
      _sttStateSub = null;
    }

    _autoStopTimer?.cancel();
    _autoStopTimer = null;
    _ampSub?.cancel();
    _ampSub = null;
    _intensityDecayTimer?.cancel();
    _intensityDecayTimer = null;
    _lastIntensity = 0;

    if (_currentText.isNotEmpty) {
      _textStreamController?.add(_currentText);
    }

    _textStreamController?.close();
    _textStreamController = null;
    _intensityController?.close();
    _intensityController = null;
  }

  void dispose() {
    stopListening();
    try {
      _speech.dispose().catchError((_) {});
    } catch (_) {}
  }

  // Recording fallback removed; only on-device STT is supported now

  // Native locales not used in server transcription mode
}

final voiceInputServiceProvider = Provider<VoiceInputService>((ref) {
  return VoiceInputService();
});

@Riverpod(keepAlive: true)
Future<bool> voiceInputAvailable(Ref ref) async {
  final service = ref.watch(voiceInputServiceProvider);
  if (!service.isSupportedPlatform) return false;
  final initialized = await service.initialize();
  if (!initialized) return false;
  // If local STT exists, we consider it available; otherwise ensure mic permission for fallback
  if (service.hasLocalStt) return true;
  final hasPermission = await service.checkPermissions();
  if (!hasPermission) return false;
  return service.isAvailable;
}

final voiceInputStreamProvider = StreamProvider<String>((ref) {
  final service = ref.watch(voiceInputServiceProvider);
  return service.textStream;
});

/// Stream of crude voice intensity for waveform visuals
final voiceIntensityStreamProvider = StreamProvider<int>((ref) {
  final service = ref.watch(voiceInputServiceProvider);
  return service.intensityStream;
});
