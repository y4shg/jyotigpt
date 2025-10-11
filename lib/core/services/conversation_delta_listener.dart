import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/socket_event.dart';
import '../providers/app_providers.dart';

/// Signature for callbacks that receive conversation delta updates.
typedef ConversationDeltaDataCallback = void Function(ConversationDelta delta);

/// Signature for callbacks that handle errors emitted by the delta stream.
typedef ConversationDeltaErrorCallback =
    void Function(Object error, StackTrace stackTrace);

/// Registers a listener for [ConversationDelta] updates behind Riverpod's
/// listening API and exposes explicit lifecycle control.
class ConversationDeltaListener {
  ConversationDeltaListener({
    required dynamic ref,
    required ConversationDeltaRequest request,
    required ConversationDeltaDataCallback onDelta,
    required ConversationDeltaErrorCallback onError,
  }) : _ref = ref,
       _request = request,
       _onDelta = onDelta,
       _onError = onError;

  final dynamic _ref;
  final ConversationDeltaRequest _request;
  final ConversationDeltaDataCallback _onDelta;
  final ConversationDeltaErrorCallback _onError;

  ProviderSubscription<AsyncValue<ConversationDelta>>? _subscription;
  bool _disposed = false;

  /// Returns `true` when a Riverpod subscription is currently active.
  bool get isActive => _subscription != null;

  /// Starts listening for [ConversationDelta] updates. Subsequent calls are
  /// no-ops while the listener is already active.
  void start() {
    if (_disposed || isActive) {
      return;
    }

    void handleNext(
      AsyncValue<ConversationDelta>? previous,
      AsyncValue<ConversationDelta> next,
    ) {
      if (!_isMounted) {
        stop();
        return;
      }

      switch (next) {
        case AsyncData(value: final delta):
          _onDelta(delta);
        case AsyncError(:final error, :final stackTrace):
          _onError(error, stackTrace);
        default:
      }
    }

    final ref = _ref;
    if (ref is Ref) {
      _subscription = ref.listen(
        conversationDeltaStreamProvider(_request),
        handleNext,
        fireImmediately: false,
      );
      return;
    }
    if (ref is ProviderContainer) {
      _subscription = ref.listen(
        conversationDeltaStreamProvider(_request),
        handleNext,
        fireImmediately: false,
      );
      return;
    }

    throw ArgumentError('Unsupported ref type: ${ref.runtimeType}');
  }

  /// Stops listening for deltas and releases resources. Safe to call multiple
  /// times.
  void stop() {
    _subscription?.close();
    _subscription = null;
  }

  /// Disposes the listener permanently and ensures the subscription is closed.
  void dispose() {
    if (_disposed) {
      return;
    }
    _disposed = true;
    stop();
  }

  bool get _isMounted {
    final ref = _ref;
    if (ref is Ref) {
      return ref.mounted;
    }
    return !_disposed;
  }
}

/// Type signature for registering delta listeners within helper utilities.
typedef RegisterConversationDeltaListener =
    VoidCallback Function({
      required ConversationDeltaRequest request,
      required ConversationDeltaDataCallback onDelta,
      required ConversationDeltaErrorCallback onError,
    });

/// Convenience factory that wires up [ConversationDeltaListener] and returns
/// the disposer callback expected by streaming helpers.
RegisterConversationDeltaListener createConversationDeltaRegistrar(
  dynamic ref,
) {
  return ({
    required ConversationDeltaRequest request,
    required ConversationDeltaDataCallback onDelta,
    required ConversationDeltaErrorCallback onError,
  }) {
    final listener = ConversationDeltaListener(
      ref: ref,
      request: request,
      onDelta: onDelta,
      onError: onError,
    )..start();

    return listener.dispose;
  };
}
