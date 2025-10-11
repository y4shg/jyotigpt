import 'dart:async';

/// A simple activity-based watchdog.
///
/// Call [ping] whenever activity occurs. If no activity happens
/// within [window], [onTimeout] fires. Optionally, an [absoluteCap]
/// enforces a maximum total duration regardless of activity.
class InactivityWatchdog {
  InactivityWatchdog({
    required Duration window,
    required this.onTimeout,
    Duration? absoluteCap,
  }) : _window = window,
       _absoluteCap = absoluteCap;

  final void Function() onTimeout;

  Duration _window;
  Duration? _absoluteCap;
  Timer? _timer;
  Timer? _absoluteTimer;
  bool _started = false;

  Duration get window => _window;

  void setWindow(Duration newWindow) {
    _window = newWindow;
    if (_started) {
      // Restart timer with new window
      _restart();
    }
  }

  void setAbsoluteCap(Duration? cap) {
    _absoluteCap = cap;
    if (_started) {
      _absoluteTimer?.cancel();
      if (_absoluteCap != null) {
        _absoluteTimer = Timer(_absoluteCap!, _fire);
      }
    }
  }

  void start() {
    if (_started) return;
    _started = true;
    _restart();
    if (_absoluteCap != null) {
      _absoluteTimer = Timer(_absoluteCap!, _fire);
    }
  }

  void ping() {
    if (!_started) {
      start();
      return;
    }
    _restart();
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
    _absoluteTimer?.cancel();
    _absoluteTimer = null;
    _started = false;
  }

  void dispose() => stop();

  void _restart() {
    _timer?.cancel();
    _timer = Timer(_window, _fire);
  }

  void _fire() {
    stop();
    try {
      onTimeout();
    } catch (_) {}
  }
}
