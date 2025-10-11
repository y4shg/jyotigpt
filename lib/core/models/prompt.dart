import 'package:flutter/foundation.dart';

@immutable
class Prompt {
  const Prompt({
    required this.command,
    required this.title,
    required this.content,
    this.accessControl,
    this.userId,
    this.timestamp,
  });

  final String command;
  final String title;
  final String content;
  final Map<String, dynamic>? accessControl;
  final String? userId;
  final int? timestamp;

  factory Prompt.fromJson(Map<String, dynamic> json) {
    final rawCommand = (json['command'] as String? ?? '').trim();
    final normalizedCommand = rawCommand.startsWith('/')
        ? rawCommand
        : (rawCommand.isEmpty ? rawCommand : '/$rawCommand');

    return Prompt(
      command: normalizedCommand,
      title: json['title'] as String? ?? '',
      content: json['content'] as String? ?? '',
      accessControl: json['access_control'] is Map<String, dynamic>
          ? Map<String, dynamic>.from(json['access_control'] as Map)
          : null,
      userId: json['user_id'] as String?,
      timestamp: json['timestamp'] is int
          ? json['timestamp'] as int
          : int.tryParse('${json['timestamp']}'),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'command': command,
      'title': title,
      'content': content,
      if (accessControl != null) 'access_control': accessControl,
      if (userId != null) 'user_id': userId,
      if (timestamp != null) 'timestamp': timestamp,
    };
  }

  Prompt copyWith({
    String? command,
    String? title,
    String? content,
    Map<String, dynamic>? accessControl,
    String? userId,
    int? timestamp,
  }) {
    return Prompt(
      command: command ?? this.command,
      title: title ?? this.title,
      content: content ?? this.content,
      accessControl: accessControl ?? this.accessControl,
      userId: userId ?? this.userId,
      timestamp: timestamp ?? this.timestamp,
    );
  }
}
