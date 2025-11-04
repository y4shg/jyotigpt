import 'dart:io' show Platform;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter/services.dart';
import 'package:uuid/uuid.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';

import '../../../core/models/server_config.dart';
import '../../../core/providers/app_providers.dart';
import '../../../core/services/api_service.dart';
import '../../../core/services/navigation_service.dart';
import '../../../core/widgets/error_boundary.dart';
import '../../../shared/theme/theme_extensions.dart';
import '../../../shared/widgets/jyotigpt_components.dart';

const String PRESET_SERVER_URL = 'https://vovxb-yash.hf.space';

class ServerConnectionPage extends ConsumerStatefulWidget {
  const ServerConnectionPage({super.key});

  @override
  ConsumerState<ServerConnectionPage> createState() => _ServerConnectionPageState();
}

class _ServerConnectionPageState extends ConsumerState<ServerConnectionPage> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _urlController = TextEditingController(text: PRESET_SERVER_URL);

  String? _connectionError;
  bool _isChecking = false;
  bool _isConnected = false;

  @override
  void initState() {
    super.initState();
    _loadExistingConfig();
    _checkIfShouldAutoCheck();
  }

  Future<void> _loadExistingConfig() async {
    final activeServer = await ref.read(activeServerProvider.future);
    if (activeServer != null && activeServer.url == PRESET_SERVER_URL) {
      setState(() => _isConnected = true);
    }
  }

  Future<void> _checkIfShouldAutoCheck() async {
    final activeServer = await ref.read(activeServerProvider.future);
    if (activeServer == null || activeServer.url != PRESET_SERVER_URL) {
      await _checkServerConnection();
    }
  }

  Future<void> _checkServerConnection() async {
    setState(() {
      _isChecking = true;
      _connectionError = null;
      _isConnected = false;
    });

    try {
      String url = _validateAndFormatUrl(PRESET_SERVER_URL);

      final tempConfig = ServerConfig(
        id: const Uuid().v4(),
        name: _deriveServerNameFromUrl(url),
        url: url,
        customHeaders: {},
        isActive: true,
        allowSelfSignedCertificates: false,
      );

      final api = ApiService(serverConfig: tempConfig);
      final isHealthy = await api.checkHealth();
      if (!isHealthy) throw Exception('This does not appear to be an Open-WebUI server.');

      setState(() => _isConnected = true);
    } catch (e) {
      setState(() => _connectionError = _formatConnectionError(e.toString()));
    } finally {
      if (mounted) setState(() => _isChecking = false);
    }
  }

  Future<void> _proceedToAuthentication() async {
    if (!_isConnected) {
      await _checkServerConnection();
      if (!_isConnected) return;
    }

    try {
      String url = _validateAndFormatUrl(PRESET_SERVER_URL);
      final activeServer = await ref.read(activeServerProvider.future);
      ServerConfig configToUse;

      if (activeServer != null && activeServer.url == url) {
        configToUse = activeServer;
      } else {
        configToUse = ServerConfig(
          id: const Uuid().v4(),
          name: _deriveServerNameFromUrl(url),
          url: url,
          customHeaders: {},
          isActive: true,
          allowSelfSignedCertificates: false,
        );
        await _saveServerConfig(configToUse);
      }

      if (mounted) context.pushNamed(RouteNames.authentication, extra: configToUse);
    } catch (e) {
      setState(() => _connectionError = _formatConnectionError(e.toString()));
    }
  }

  Future<void> _saveServerConfig(ServerConfig config) async {
    final storage = ref.read(optimizedStorageServiceProvider);
    await storage.saveServerConfigs([config]);
    await storage.setActiveServerId(config.id);
    ref.invalidate(serverConfigsProvider);
    ref.invalidate(activeServerProvider);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  String _validateAndFormatUrl(String input) {
    if (input.isEmpty) throw Exception(AppLocalizations.of(context)!.serverUrlEmpty);
    String url = input.trim();
    if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'http://$url';
    if (url.endsWith('/')) url = url.substring(0, url.length - 1);
    final uri = Uri.tryParse(url);
    if (uri == null) throw Exception(AppLocalizations.of(context)!.invalidUrlFormat);
    if (uri.scheme != 'http' && uri.scheme != 'https') throw Exception(AppLocalizations.of(context)!.onlyHttpHttps);
    if (uri.host.isEmpty) throw Exception(AppLocalizations.of(context)!.serverAddressRequired);
    return url;
  }

  String _deriveServerNameFromUrl(String url) {
    try {
      final uri = Uri.parse(url);
      if (uri.host.isNotEmpty) return uri.host;
    } catch (_) {}
    return 'Server';
  }

  String _formatConnectionError(String error) {
    if (error.contains('SocketException')) return AppLocalizations.of(context)!.weCouldntReachServer;
    if (error.contains('timeout')) return AppLocalizations.of(context)!.connectionTimedOut;
    if (error.contains('This does not appear to be an Open-WebUI server')) return AppLocalizations.of(context)!.serverNotOpenWebUI;
    return AppLocalizations.of(context)!.couldNotConnectGeneric;
  }

  @override
  Widget build(BuildContext context) {
    return ErrorBoundary(
      child: Scaffold(
        body: Stack(
          children: [
            Positioned.fill(
              child: Image.asset('assets/images/background.png', fit: BoxFit.cover),
            ),
            Positioned.fill(
              child: Container(color: Colors.black.withOpacity(0.3)),
            ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: Spacing.pagePadding, vertical: Spacing.lg),
                child: Column(
                  children: [
                    _buildHeader(),
                    const Spacer(),
                    Align(
                      alignment: Alignment.bottomCenter,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            AppLocalizations.of(context)!.connectToServer,
                            textAlign: TextAlign.center,
                            style: context.jyotigptTheme.headingLarge?.copyWith(
                              fontWeight: FontWeight.w600,
                              color: Colors.white,
                              height: 1.3,
                            ),
                          ),
                          const SizedBox(height: Spacing.sm),
                          Text(
                            AppLocalizations.of(context)!.enterServerAddress,
                            textAlign: TextAlign.center,
                            style: context.jyotigptTheme.bodyMedium?.copyWith(
                              color: Colors.white.withOpacity(0.85),
                              height: 1.4,
                            ),
                          ),
                          const SizedBox(height: Spacing.lg),
                          _buildNextButton(),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return const SizedBox(height: 4, child: LinearProgressIndicator());
  }

  Widget _buildNextButton() {
    return JyotiGPTButton(
      text: AppLocalizations.of(context)!.next,
      icon: Platform.isIOS ? CupertinoIcons.arrow_right : Icons.arrow_forward,
      onPressed: _isConnected ? _proceedToAuthentication : null,
      isFullWidth: true,
    );
  }
}