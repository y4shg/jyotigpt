import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:jyotigpt/core/error/api_error_handler.dart';
import 'package:jyotigpt/core/models/prompt.dart';
import 'package:jyotigpt/core/providers/app_providers.dart';
import 'package:jyotigpt/core/services/api_service.dart';

class PromptsService {
  const PromptsService(this._apiService);

  final ApiService _apiService;

  Future<List<Prompt>> getPrompts() async {
    try {
      final List<Map<String, dynamic>> response = await _apiService
          .getPrompts();
      return response
          .map((item) => Prompt.fromJson(item))
          .where((prompt) => prompt.command.isNotEmpty)
          .toList();
    } on DioException catch (error) {
      throw ApiErrorHandler().transformError(error);
    }
  }
}

final promptsServiceProvider = Provider<PromptsService?>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  if (apiService == null) return null;
  return PromptsService(apiService);
});
