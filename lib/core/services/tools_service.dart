import 'package:dio/dio.dart';
import 'package:jyotigpt/core/models/tool.dart';
import 'package:jyotigpt/core/services/api_service.dart';
import 'package:jyotigpt/core/error/api_error_handler.dart';
import 'package:jyotigpt/core/providers/app_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ToolsService {
  final ApiService _apiService;

  ToolsService(this._apiService);

  Future<List<Tool>> getTools() async {
    try {
      final response = await _apiService.dio.get('/api/v1/tools/');
      return (response.data as List)
          .map((json) => Tool.fromJson(json))
          .toList();
    } on DioException catch (e) {
      throw ApiErrorHandler().transformError(e);
    }
  }
}

final toolsServiceProvider = Provider<ToolsService?>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  if (apiService == null) return null;
  return ToolsService(apiService);
});
