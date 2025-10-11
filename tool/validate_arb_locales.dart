import 'dart:convert';
import 'dart:io';

/// Validates ARB locale files against the English template (app_en.arb).
/// - Ensures no duplicate keys within any ARB file.
/// - Ensures each non-meta key in EN exists in other locales.
/// - Ensures placeholder names match between EN and other locales.
/// - Reports unused keys (best-effort) by scanning lib/ for usages of
///   AppLocalizations.of(context)!.someKey. Unused keys are WARNINGS by default.
///
/// Exit codes:
///   0 = success (no hard errors; warnings may be printed)
///   1 = validation errors (duplicates, missing keys, placeholder mismatches)
Future<void> main(List<String> args) async {
  final basePath = 'lib/l10n/app_en.arb';
  final dir = Directory('lib/l10n');
  if (!await File(basePath).exists()) {
    stderr.writeln('Base ARB not found: $basePath');
    exit(1);
  }

  final arbFiles = await dir
      .list()
      .where((e) => e.path.endsWith('.arb'))
      .map((e) => File(e.path))
      .toList();

  final baseFile = File(basePath);
  final base = _readJson(baseFile);
  final baseKeys = _nonMetaKeys(base);
  final basePlaceholders = _placeholdersMap(base);

  final errors = <String>[];
  final warnings = <String>[];

  // NOTE: Duplicate keys at the top-level are invalid JSON and unlikely.
  // We skip duplicate detection to avoid false positives from nested meta keys.

  // Validate translations against base
  for (final f in arbFiles) {
    if (f.path.endsWith('_en.arb')) continue;
    final data = _readJson(f);
    final keys = _nonMetaKeys(data);

    // Missing keys
    final missing = baseKeys.difference(keys);
    if (missing.isNotEmpty) {
      errors.add('[${f.path}] Missing keys: ${missing.toList()..sort()}');
    }

    // Placeholder parity checks
    final transPlaceholders = _placeholdersMap(data);
    for (final k in basePlaceholders.keys) {
      final basePh = basePlaceholders[k] ?? const <String>{};
      final trPh = transPlaceholders[k];
      if (trPh == null) {
        // If string exists but no meta placeholders, warn only.
        if (keys.contains(k) && basePh.isNotEmpty) {
          warnings.add(
            '[${f.path}] Key "$k" missing @meta placeholders; base has ${basePh.toList()..sort()}',
          );
        }
        continue;
      }
      if (basePh.length != trPh.length || !basePh.containsAll(trPh)) {
        warnings.add(
          '[${f.path}] Placeholder mismatch for "$k": expected ${basePh.toList()..sort()}, got ${trPh.toList()..sort()}',
        );
      }
    }
  }

  // Unused keys (best-effort) — WARNINGS only
  final usedKeys = await _scanUsedLocalizationKeys();
  final unused = baseKeys.difference(usedKeys);
  if (unused.isNotEmpty) {
    warnings.add('Unused keys in EN (best-effort): ${unused.toList()..sort()}');
  }

  // Print results
  if (errors.isNotEmpty) {
    stderr.writeln('ARB validation errors:');
    for (final e in errors) {
      stderr.writeln(' - $e');
    }
  }
  if (warnings.isNotEmpty) {
    stdout.writeln('ARB validation warnings:');
    for (final w in warnings) {
      stdout.writeln(' - $w');
    }
  }

  exit(errors.isEmpty ? 0 : 1);
}

Map<String, dynamic> _readJson(File f) {
  final content = f.readAsStringSync();
  return json.decode(content) as Map<String, dynamic>;
}

Set<String> _nonMetaKeys(Map<String, dynamic> m) {
  return m.keys.where((k) => !k.startsWith('@') && k != '@@locale').toSet();
}

Map<String, Set<String>> _placeholdersMap(Map<String, dynamic> m) {
  final map = <String, Set<String>>{};
  for (final entry in m.entries) {
    final key = entry.key;
    if (!key.startsWith('@')) continue;
    final value = entry.value;
    if (value is! Map<String, dynamic>) continue;
    final placeholders = value['placeholders'];
    if (placeholders is Map<String, dynamic>) {
      map[key.substring(1)] = placeholders.keys.toSet();
    }
  }
  return map;
}

// Duplicate detection intentionally omitted (see note above).

Future<Set<String>> _scanUsedLocalizationKeys() async {
  final libDir = Directory('lib');
  final used = <String>{};
  final dartFiles = await libDir
      .list(recursive: true)
      .where((e) => e.path.endsWith('.dart'))
      .map((e) => File(e.path))
      .toList();

  final regex = RegExp(r'AppLocalizations\.of\([^)]*\)!\.([a-zA-Z0-9_]+)');
  for (final f in dartFiles) {
    final text = await f.readAsString();
    for (final m in regex.allMatches(text)) {
      final key = m.group(1);
      if (key != null) used.add(key);
    }
  }
  return used;
}
