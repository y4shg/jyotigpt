import 'package:riverpod_annotation/riverpod_annotation.dart';

import 'package:jyotigpt/core/models/tool.dart';
import 'package:jyotigpt/core/services/tools_service.dart';

part 'tools_providers.g.dart';

@Riverpod(keepAlive: true)
Future<List<Tool>> toolsList(Ref ref) async {
  final toolsService = ref.watch(toolsServiceProvider);
  if (toolsService == null) return [];
  return await toolsService.getTools();
}

@Riverpod(keepAlive: true)
class SelectedToolIds extends _$SelectedToolIds {
  @override
  List<String> build() => [];

  void set(List<String> ids) => state = List<String>.from(ids);
}
