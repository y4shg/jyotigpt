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
import '../../../shared/services/brand_service.dart';
import '../../../shared/theme/theme_extensions.dart';
import '../../../shared/widgets/jyotigpt_components.dart';

// CONFIGURATION: Preset server URL
const String PRESET_SERVER_URL = 'https://vovxb-yash.hf.space';

class ServerConnectionPage extends ConsumerStatefulWidget {
  const ServerConnectionPage({super.key});

  @override
  ConsumerState<ServerConnectionPage> createState() =>
      _ServerConnectionPageState();
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
      // Server already configured
      setState(() {
        _isConnected = true;
      });
    }
  }

  Future<void> _checkIfShouldAutoCheck() async {
    final activeServer = await ref.read(activeServerProvider.future);
    if (activeServer == null || activeServer.url != PRESET_SERVER_URL) {
      // No server configured yet, do the initial check
      _checkServerConnection();
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
      
      if (!isHealthy) {
        throw Exception('This does not appear to be an Open-WebUI server.');
      }

      setState(() {
        _isConnected = true;
      });
    } catch (e) {
      setState(() {
        _connectionError = _formatConnectionError(e.toString());
      });
    } finally {
      if (mounted) {
        setState(() {
          _isChecking = false;
        });
      }
    }
  }

  Future<void> _proceedToAuthentication() async {
    if (!_isConnected) {
      // Try to connect first
      await _checkServerConnection();
      if (!_isConnected) return;
    }

    try {
      String url = _validateAndFormatUrl(PRESET_SERVER_URL);

      // Check if server already exists
      final activeServer = await ref.read(activeServerProvider.future);
      ServerConfig configToUse;

      if (activeServer != null && activeServer.url == url) {
        // Server already exists, reuse it
        configToUse = activeServer;
      } else {
        // Create new server config
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

      // Navigate to authentication page
      if (mounted) {
        context.pushNamed(RouteNames.authentication, extra: configToUse);
      }
    } catch (e) {
      setState(() {
        _connectionError = _formatConnectionError(e.toString());
      });
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
    if (input.isEmpty) {
      throw Exception(AppLocalizations.of(context)!.serverUrlEmpty);
    }

    String url = input.trim();

    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'http://$url';
    }

    if (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }

    final uri = Uri.tryParse(url);
    if (uri == null) {
      throw Exception(AppLocalizations.of(context)!.invalidUrlFormat);
    }

    if (uri.scheme != 'http' && uri.scheme != 'https') {
      throw Exception(AppLocalizations.of(context)!.onlyHttpHttps);
    }

    if (uri.host.isEmpty) {
      throw Exception(AppLocalizations.of(context)!.serverAddressRequired);
    }

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
    if (error.contains('SocketException')) {
      return AppLocalizations.of(context)!.weCouldntReachServer;
    } else if (error.contains('timeout')) {
      return AppLocalizations.of(context)!.connectionTimedOut;
    } else if (error.contains('This does not appear to be an Open-WebUI server')) {
      return AppLocalizations.of(context)!.serverNotOpenWebUI;
    }

    return AppLocalizations.of(context)!.couldNotConnectGeneric;
  }

  @override
  Widget build(BuildContext context) {
    final reviewerMode = ref.watch(reviewerModeProvider);

    return ErrorBoundary(
      child: Scaffold(
        body: Stack(
          children: [
            // Background image
            Positioned.fill(
              child: Image.asset(
                'assets/images/background.png',
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) => Container(
                  color: Colors.black,
                ),
              ),
            ),
            
            // Content
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: Spacing.pagePadding,
                  vertical: Spacing.lg,
                ),
                child: Column(
                  children: [
                    // Header with progress indicator
                    _buildHeader(),

                    // Main content
                    Expanded(
                      child: Center(
                        child: SingleChildScrollView(
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 480),
                            child: Form(
                              key: _formKey,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  // Reviewer mode demo (if enabled)
                                  if (reviewerMode) ...[
                                    _buildReviewerModeSection(),
                                    const SizedBox(height: Spacing.xl),
                                  ],

                                  // Server connection status (only show if checking or error)
                                  if (_isChecking || _connectionError != null)
                                    _buildServerStatus(),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),

                    // Bottom section with title, description and button
                    _buildBottomSection(),
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
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Progress indicator (step 1 of 2)
        Row(
          children: [
            Container(
              width: 24,
              height: 4,
              decoration: BoxDecoration(
                color: context.jyotigptTheme.buttonPrimary,
                borderRadius: BorderRadius.circular(AppBorderRadius.round),
              ),
            ),
            const SizedBox(width: Spacing.xs),
            Container(
              width: 24,
              height: 4,
              decoration: BoxDecoration(
                color: context.jyotigptTheme.dividerColor.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(AppBorderRadius.round),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildReviewerModeSection() {
    return JyotiGPTCard(
      isElevated: false,
      padding: const EdgeInsets.all(Spacing.lg),
      child: Column(
        children: [
          Row(
            children: [
              Icon(
                Platform.isIOS ? CupertinoIcons.wand_stars : Icons.auto_awesome,
                color: context.jyotigptTheme.warning,
                size: IconSize.medium,
              ),
              const SizedBox(width: Spacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      AppLocalizations.of(context)!.demoModeActive,
                      style: context.jyotigptTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: context.jyotigptTheme.warning,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    Text(
                      AppLocalizations.of(context)!.skipServerSetupTryDemo,
                      style: context.jyotigptTheme.bodySmall?.copyWith(
                        color: context.jyotigptTheme.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: Spacing.lg),
          JyotiGPTButton(
            text: AppLocalizations.of(context)!.enterDemo,
            icon: Platform.isIOS ? CupertinoIcons.play_fill : Icons.play_arrow,
            onPressed: () {
              context.go(Routes.chat);
            },
            isSecondary: true,
            isFullWidth: true,
          ),
        ],
      ),
    );
  }

  Widget _buildServerStatus() {
    return JyotiGPTCard(
      isElevated: false,
      padding: const EdgeInsets.all(Spacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Connection status
          if (_isChecking)
            _buildCheckingStatus()
          else if (_connectionError != null)
            _buildErrorStatus(),
        ],
      ),
    );
  }

  Widget _buildCheckingStatus() {
    return Row(
      children: [
        SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: context.jyotigptTheme.buttonPrimary,
          ),
        ),
        const SizedBox(width: Spacing.md),
        Text(
          AppLocalizations.of(context)!.connecting,
          style: context.jyotigptTheme.bodyMedium?.copyWith(
            color: context.jyotigptTheme.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildErrorStatus() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Icon(
              Platform.isIOS
                  ? CupertinoIcons.exclamationmark_circle
                  : Icons.error_outline,
              color: context.jyotigptTheme.error,
              size: IconSize.medium,
            ),
            const SizedBox(width: Spacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    AppLocalizations.of(context)!.unableToConnectServer,
                    style: context.jyotigptTheme.bodyMedium?.copyWith(
                      color: context.jyotigptTheme.error,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (_connectionError != null) ...[
                    const SizedBox(height: Spacing.xs),
                    Text(
                      _connectionError!,
                      style: context.jyotigptTheme.bodySmall?.copyWith(
                        color: context.jyotigptTheme.textSecondary,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: Spacing.lg),
        JyotiGPTButton(
          text: AppLocalizations.of(context)!.retry,
          icon: Platform.isIOS ? CupertinoIcons.refresh : Icons.refresh,
          onPressed: _checkServerConnection,
          isSecondary: true,
          isFullWidth: true,
        ),
      ],
    );
  }

  Widget _buildBottomSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Title and description
        Text(
          AppLocalizations.of(context)!.connectToServer,
          textAlign: TextAlign.left,
          style: context.jyotigptTheme.headingLarge?.copyWith(
            fontWeight: FontWeight.w600,
            height: 1.3,
            color: Colors.white,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          AppLocalizations.of(context)!.enterServerAddress,
          textAlign: TextAlign.left,
          style: context.jyotigptTheme.bodyMedium?.copyWith(
            color: Colors.white.withValues(alpha: 0.9),
            height: 1.4,
          ),
        ),
        const SizedBox(height: Spacing.xl),
        
        // Next button
        JyotiGPTButton(
          text: AppLocalizations.of(context)!.next,
          icon: Platform.isIOS ? CupertinoIcons.arrow_right : Icons.arrow_forward,
          onPressed: _isConnected ? _proceedToAuthentication : null,
          isFullWidth: true,
        ),
      ],
    );
  }
}