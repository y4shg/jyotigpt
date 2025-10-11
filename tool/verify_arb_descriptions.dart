import 'dart:convert';
import 'dart:io';

/// Verifies that every non-meta key in app_en.arb has a corresponding
/// @key entry with a non-empty `description`.
///
/// Usage: dart run tool/verify_arb_descriptions.dart
Future<void> main() async {
  final arbPath = 'lib/l10n/app_en.arb';
  final file = File(arbPath);
  if (!await file.exists()) {
    stderr.writeln('ARB file not found: $arbPath');
    exit(2);
  }

  final content = await file.readAsString();
  late final Map<String, dynamic> data;
  try {
    data = json.decode(content) as Map<String, dynamic>;
  } catch (e) {
    stderr.writeln('Failed to parse $arbPath as JSON: $e');
    exit(2);
  }

  final missingMeta = <String>[];
  final missingDescription = <String>[];

  for (final entry in data.entries) {
    final key = entry.key;
    if (key.startsWith('@') || key == '@@locale') continue; // meta

    final metaKey = '@$key';
    final meta = data[metaKey];
    if (meta == null || meta is! Map) {
      missingMeta.add(key);
      continue;
    }
    final desc = meta['description'];
    if (desc is! String || desc.trim().isEmpty) {
      missingDescription.add(key);
    }
  }

  if (missingMeta.isEmpty && missingDescription.isEmpty) {
    stdout.writeln(
      'ARB descriptions check passed: all keys have @meta.description.',
    );
    return;
  }

  if (missingMeta.isNotEmpty) {
    stderr.writeln('Missing @meta for keys (${missingMeta.length}):');
    for (final k in missingMeta) {
      stderr.writeln(' - $k');
    }
  }
  if (missingDescription.isNotEmpty) {
    stderr.writeln(
      'Missing description in @meta for keys (${missingDescription.length}):',
    );
    for (final k in missingDescription) {
      stderr.writeln(' - $k');
    }
  }
  exit(1);
}
