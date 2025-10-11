import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:dio/dio.dart';
import 'package:hive_ce/hive.dart';
import '../persistence/hive_boxes.dart';
import '../utils/debug_logger.dart';

/// Status of a queued attachment upload
enum QueuedAttachmentStatus { pending, uploading, completed, failed, cancelled }

/// Metadata for a queued attachment
class QueuedAttachment {
  final String id; // local queue id
  final String filePath;
  final String fileName;
  final int fileSize;
  final String? mimeType;
  final String? checksum;
  final DateTime enqueuedAt;

  // Upload state
  int retryCount;
  DateTime? nextRetryAt;
  QueuedAttachmentStatus status;
  String? lastError;
  String? fileId; // server-side file id once uploaded

  QueuedAttachment({
    required this.id,
    required this.filePath,
    required this.fileName,
    required this.fileSize,
    this.mimeType,
    this.checksum,
    DateTime? enqueuedAt,
    this.retryCount = 0,
    this.nextRetryAt,
    this.status = QueuedAttachmentStatus.pending,
    this.lastError,
    this.fileId,
  }) : enqueuedAt = enqueuedAt ?? DateTime.now();

  Map<String, dynamic> toJson() => {
    'id': id,
    'filePath': filePath,
    'fileName': fileName,
    'fileSize': fileSize,
    'mimeType': mimeType,
    'checksum': checksum,
    'enqueuedAt': enqueuedAt.toIso8601String(),
    'retryCount': retryCount,
    'nextRetryAt': nextRetryAt?.toIso8601String(),
    'status': status.name,
    'lastError': lastError,
    'fileId': fileId,
  };

  factory QueuedAttachment.fromJson(Map<String, dynamic> json) =>
      QueuedAttachment(
        id: json['id'] as String,
        filePath: json['filePath'] as String,
        fileName: json['fileName'] as String,
        fileSize: (json['fileSize'] as num).toInt(),
        mimeType: json['mimeType'] as String?,
        checksum: json['checksum'] as String?,
        enqueuedAt:
            DateTime.tryParse(json['enqueuedAt'] ?? '') ?? DateTime.now(),
        retryCount: (json['retryCount'] as num?)?.toInt() ?? 0,
        nextRetryAt: json['nextRetryAt'] != null
            ? DateTime.tryParse(json['nextRetryAt'])
            : null,
        status: QueuedAttachmentStatus.values.firstWhere(
          (e) => e.name == json['status'],
          orElse: () => QueuedAttachmentStatus.pending,
        ),
        lastError: json['lastError'] as String?,
        fileId: json['fileId'] as String?,
      );

  QueuedAttachment copyWith({
    int? retryCount,
    DateTime? nextRetryAt,
    QueuedAttachmentStatus? status,
    String? lastError,
    String? fileId,
  }) => QueuedAttachment(
    id: id,
    filePath: filePath,
    fileName: fileName,
    fileSize: fileSize,
    mimeType: mimeType,
    checksum: checksum,
    enqueuedAt: enqueuedAt,
    retryCount: retryCount ?? this.retryCount,
    nextRetryAt: nextRetryAt ?? this.nextRetryAt,
    status: status ?? this.status,
    lastError: lastError ?? this.lastError,
    fileId: fileId ?? this.fileId,
  );
}

typedef UploadCallback =
    Future<String> Function(String filePath, String fileName);
typedef AttachmentsEventCallback = void Function(List<QueuedAttachment> queue);

/// A lightweight background queue to upload attachments when back online.
class AttachmentUploadQueue {
  static final AttachmentUploadQueue _instance =
      AttachmentUploadQueue._internal();
  factory AttachmentUploadQueue() => _instance;
  AttachmentUploadQueue._internal();

  static const int _maxRetries = 4;
  static const Duration _baseRetryDelay = Duration(seconds: 5);
  static const Duration _maxRetryDelay = Duration(minutes: 5);

  late final Box<dynamic> _queueBox;
  bool _initialized = false;
  final List<QueuedAttachment> _queue = [];
  Timer? _retryTimer;
  bool _isProcessing = false;

  // Dependencies
  UploadCallback? _onUpload;
  AttachmentsEventCallback? _onQueueChanged;

  // Streams
  final _queueController = StreamController<List<QueuedAttachment>>.broadcast();
  Stream<List<QueuedAttachment>> get queueStream => _queueController.stream;

  List<QueuedAttachment> get queue => List.unmodifiable(_queue);

  Future<void> initialize({
    required UploadCallback onUpload,
    AttachmentsEventCallback? onQueueChanged,
  }) async {
    _onUpload = onUpload;
    _onQueueChanged = onQueueChanged;
    if (!_initialized) {
      _queueBox = Hive.box<dynamic>(HiveBoxNames.attachmentQueue);
      _initialized = true;
    }
    await _load();
    _startPeriodicProcessing();
    DebugLogger.log(
      'AttachmentUploadQueue initialized with \${_queue.length} items',
      scope: 'attachments/queue',
    );
  }

  Future<String> enqueue({
    required String filePath,
    required String fileName,
    required int fileSize,
    String? mimeType,
    String? checksum,
  }) async {
    final id = DateTime.now().microsecondsSinceEpoch.toString();
    final item = QueuedAttachment(
      id: id,
      filePath: filePath,
      fileName: fileName,
      fileSize: fileSize,
      mimeType: mimeType,
      checksum: checksum,
      status: QueuedAttachmentStatus.pending,
    );
    _queue.add(item);
    await _save();
    _notify();
    _processSafe();
    return id;
  }

  Future<void> processQueue() async {
    if (_isProcessing) return;
    if (_onUpload == null) return;

    _isProcessing = true;
    try {
      // Quick network probe using Dio HEAD to common health path if possible
      final dio = Dio();
      try {
        await dio.head('/api/health').timeout(const Duration(seconds: 3));
      } catch (_) {
        // Best effort; continue and let upload fail if actually offline
      }

      final now = DateTime.now();
      final pending = _queue.where(
        (e) =>
            (e.status == QueuedAttachmentStatus.pending ||
                e.status == QueuedAttachmentStatus.failed) &&
            (e.nextRetryAt == null || now.isAfter(e.nextRetryAt!)),
      );

      for (final item in List<QueuedAttachment>.from(pending)) {
        await _processSingle(item);
      }
    } finally {
      _isProcessing = false;
    }
  }

  Future<void> _processSingle(QueuedAttachment item) async {
    if (_onUpload == null) return;
    try {
      _update(item.id, item.copyWith(status: QueuedAttachmentStatus.uploading));

      final fileId = await _onUpload!.call(item.filePath, item.fileName);

      _update(
        item.id,
        item.copyWith(
          status: QueuedAttachmentStatus.completed,
          fileId: fileId,
          retryCount: 0,
          nextRetryAt: null,
          lastError: null,
        ),
      );

      await _save();
      _notify();
      DebugLogger.log(
        'Attachment ${item.id} uploaded successfully (fileId=$fileId)',
        scope: 'attachments/queue',
      );
    } catch (e) {
      final retries = item.retryCount + 1;
      if (retries >= _maxRetries) {
        _update(
          item.id,
          item.copyWith(
            status: QueuedAttachmentStatus.failed,
            retryCount: retries,
            lastError: e.toString(),
          ),
        );
        await _save();
        _notify();
        DebugLogger.log(
          'WARNING: Attachment ${item.id} failed after $_maxRetries attempts',
          scope: 'attachments/queue',
        );
        return;
      }

      final delay = _retryDelayWithJitter(retries);
      _update(
        item.id,
        item.copyWith(
          status: QueuedAttachmentStatus.pending,
          retryCount: retries,
          nextRetryAt: DateTime.now().add(delay),
          lastError: e.toString(),
        ),
      );
      await _save();
      _notify();
      DebugLogger.log(
        'Scheduled retry for attachment ${item.id} in ${delay.inSeconds}s',
        scope: 'attachments/queue',
      );
    }
  }

  Duration _retryDelayWithJitter(int retryCount) {
    final base = _baseRetryDelay.inMilliseconds;
    final exp = min(
      base * pow(2, retryCount - 1),
      _maxRetryDelay.inMilliseconds.toDouble(),
    ).toInt();
    final jitter = Random().nextInt(1000); // up to 1s jitter
    return Duration(milliseconds: exp + jitter);
  }

  void _startPeriodicProcessing() {
    _retryTimer?.cancel();
    _retryTimer = Timer.periodic(
      const Duration(seconds: 10),
      (_) => _processSafe(),
    );
    // Also kick once after a short delay
    Timer(const Duration(milliseconds: 500), _processSafe);
  }

  void _processSafe() {
    // Fire and forget
    unawaited(processQueue());
  }

  void _update(String id, QueuedAttachment updated) {
    final idx = _queue.indexWhere((e) => e.id == id);
    if (idx != -1) {
      _queue[idx] = updated;
    }
  }

  Future<void> remove(String id) async {
    _queue.removeWhere((e) => e.id == id);
    await _save();
    _notify();
  }

  Future<void> retry(String id) async {
    final idx = _queue.indexWhere((e) => e.id == id);
    if (idx == -1) return;
    _queue[idx] = _queue[idx].copyWith(
      status: QueuedAttachmentStatus.pending,
      retryCount: 0,
      nextRetryAt: null,
      lastError: null,
    );
    await _save();
    _notify();
    _processSafe();
  }

  Future<void> clearFailed() async {
    _queue.removeWhere((e) => e.status == QueuedAttachmentStatus.failed);
    await _save();
    _notify();
  }

  Future<void> clearAll() async {
    _queue.clear();
    await _save();
    _notify();
  }

  // Utilities
  Future<void> _load() async {
    final stored = _queueBox.get(HiveStoreKeys.attachmentQueueEntries);
    if (stored == null) {
      return;
    }

    List<dynamic> rawList;
    if (stored is String && stored.isNotEmpty) {
      rawList = (jsonDecode(stored) as List<dynamic>);
    } else if (stored is List) {
      rawList = stored;
    } else {
      return;
    }

    _queue
      ..clear()
      ..addAll(
        rawList.map(
          (item) =>
              QueuedAttachment.fromJson(Map<String, dynamic>.from(item as Map)),
        ),
      );
  }

  Future<void> _save() async {
    final list = _queue.map((e) => e.toJson()).toList(growable: false);
    await _queueBox.put(HiveStoreKeys.attachmentQueueEntries, list);
  }

  void _notify() {
    _onQueueChanged?.call(queue);
    _queueController.add(queue);
  }
}
