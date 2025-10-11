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
import '../../../core/services/input_validation_service.dart';
import '../../../core/services/navigation_service.dart';
import '../../../core/widgets/error_boundary.dart';
import '../../../shared/services/brand_service.dart';
import '../../../shared/theme/theme_extensions.dart';
import '../../../shared/widgets/jyotigpt_components.dart';

class ServerConnectionPage extends ConsumerStatefulWidget {
  const ServerConnectionPage({super.key});

  @override
  ConsumerState<ServerConnectionPage> createState() =>
      _ServerConnectionPageState();
}

class _ServerConnectionPageState extends ConsumerState<ServerConnectionPage> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _urlController = TextEditingController();
  final Map<String, String> _customHeaders = {};
  final TextEditingController _headerKeyController = TextEditingController();
  final TextEditingController _headerValueController = TextEditingController();

  String? _connectionError;
  bool _isConnecting = false;
  bool _showAdvancedSettings = false;
  bool _allowSelfSignedCertificates = false;

  @override
  void initState() {
    super.initState();
    _prefillFromState();
  }

  Future<void> _prefillFromState() async {
    final activeServer = await ref.read(activeServerProvider.future);
    if (!mounted || activeServer == null) return;
    setState(() {
      _urlController.text = activeServer.url;
      _allowSelfSignedCertificates = activeServer.allowSelfSignedCertificates;
    });
  }

  @override
  void dispose() {
    _urlController.dispose();
    _headerKeyController.dispose();
    _headerValueController.dispose();
    super.dispose();
  }

  Future<void> _connectToServer() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isConnecting = true;
      _connectionError = null;
    });

    try {
      String url = _validateAndFormatUrl(_urlController.text.trim());

      final tempConfig = ServerConfig(
        id: const Uuid().v4(),
        name: _deriveServerNameFromUrl(url),
        url: url,
        customHeaders: Map<String, String>.from(_customHeaders),
        isActive: true,
        allowSelfSignedCertificates: _allowSelfSignedCertificates,
      );

      final api = ApiService(serverConfig: tempConfig);
      final isHealthy = await api.checkHealth();
      if (!isHealthy) {
        throw Exception('This does not appear to be an Open-WebUI server.');
      }

      await _saveServerConfig(tempConfig);

      // Navigate to authentication page
      if (mounted) {
        context.pushNamed(RouteNames.authentication, extra: tempConfig);
      }
    } catch (e) {
      setState(() {
        _connectionError = _formatConnectionError(e.toString());
      });
    } finally {
      if (mounted) {
        setState(() {
          _isConnecting = false;
        });
      }
    }
  }

  Future<void> _saveServerConfig(ServerConfig config) async {
    final storage = ref.read(optimizedStorageServiceProvider);
    await storage.saveServerConfigs([config]);
    await storage.setActiveServerId(config.id);
    ref.invalidate(serverConfigsProvider);
    ref.invalidate(activeServerProvider);
  }

  String _validateAndFormatUrl(String input) {
    if (input.isEmpty) {
      throw Exception(AppLocalizations.of(context)!.serverUrlEmpty);
    }

    // Clean up the input
    String url = input.trim();

    // Add protocol if missing
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'http://$url';
    }

    // Remove trailing slash
    if (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }

    // Parse and validate the URI
    final uri = Uri.tryParse(url);
    if (uri == null) {
      throw Exception(AppLocalizations.of(context)!.invalidUrlFormat);
    }

    // Validate scheme
    if (uri.scheme != 'http' && uri.scheme != 'https') {
      throw Exception(AppLocalizations.of(context)!.onlyHttpHttps);
    }

    // Validate host
    if (uri.host.isEmpty) {
      throw Exception(AppLocalizations.of(context)!.serverAddressRequired);
    }

    // Validate port if specified
    if (uri.hasPort) {
      if (uri.port < 1 || uri.port > 65535) {
        throw Exception(AppLocalizations.of(context)!.portRange);
      }
    }

    // Validate IP address format if it looks like an IP
    if (_isIPAddress(uri.host) && !_isValidIPAddress(uri.host)) {
      throw Exception(AppLocalizations.of(context)!.invalidIpFormat);
    }

    return url;
  }

  bool _isIPAddress(String host) {
    return RegExp(r'^\d+\.\d+\.\d+\.\d+$').hasMatch(host);
  }

  bool _isValidIPAddress(String ip) {
    final parts = ip.split('.');
    if (parts.length != 4) return false;

    for (final part in parts) {
      final num = int.tryParse(part);
      if (num == null || num < 0 || num > 255) return false;
    }
    return true;
  }

  String _deriveServerNameFromUrl(String url) {
    try {
      final uri = Uri.parse(url);
      if (uri.host.isNotEmpty) return uri.host;
    } catch (_) {}
    return 'Server';
  }

  String _formatConnectionError(String error) {
    // Clean up the error message
    String cleanError = error.replaceFirst('Exception: ', '');

    // Handle specific error types
    if (error.contains('SocketException')) {
      return AppLocalizations.of(context)!.weCouldntReachServer;
    } else if (error.contains('timeout')) {
      return AppLocalizations.of(context)!.connectionTimedOut;
    } else if (error.contains('Server URL cannot be empty')) {
      return AppLocalizations.of(context)!.serverUrlEmpty;
    } else if (error.contains('Invalid URL format')) {
      return AppLocalizations.of(context)!.invalidUrlFormat;
    } else if (error.contains('Only HTTP and HTTPS')) {
      return AppLocalizations.of(context)!.useHttpOrHttpsOnly;
    } else if (error.contains('Server address is required')) {
      return cleanError;
    } else if (error.contains('Port must be between')) {
      return cleanError;
    } else if (error.contains('Invalid IP address format')) {
      return cleanError;
    } else if (error.contains(
      'This does not appear to be an Open-WebUI server',
    )) {
      return AppLocalizations.of(context)!.serverNotOpenWebUI;
    }

    return AppLocalizations.of(context)!.couldNotConnectGeneric;
  }

  @override
  Widget build(BuildContext context) {
    final reviewerMode = ref.watch(reviewerModeProvider);

    return ErrorBoundary(
      child: Scaffold(
        backgroundColor: context.jyotigptTheme.surfaceBackground,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.pagePadding,
              vertical: Spacing.lg,
            ),
            child: Column(
              children: [
                // Header with progress indicator
                _buildHeader(),

                const SizedBox(height: Spacing.xl),

                // Main content
                Expanded(
                  child: SingleChildScrollView(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 480),
                      child: Form(
                        key: _formKey,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            // Brand header
                            _buildBrandHeader(reviewerMode),

                            const SizedBox(height: Spacing.xl),

                            // Welcome section
                            _buildWelcomeSection(),

                            const SizedBox(height: Spacing.xl),

                            // Reviewer mode demo (if enabled)
                            if (reviewerMode) ...[
                              _buildReviewerModeSection(),
                              const SizedBox(height: Spacing.xl),
                            ],

                            // Server connection form
                            _buildServerForm(),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                // Bottom action button
                _buildConnectButton(),
              ],
            ),
          ),
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

  Widget _buildBrandHeader(bool reviewerMode) {
    return GestureDetector(
      onLongPress: () async {
        HapticFeedback.mediumImpact();
        await ref.read(reviewerModeProvider.notifier).toggle();
        if (!mounted) return;
        final enabled = ref.read(reviewerModeProvider);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              enabled
                  ? 'Reviewer Mode enabled: Demo without server'
                  : 'Reviewer Mode disabled',
            ),
          ),
        );
      },
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Brand logo
          BrandService.createBrandIcon(
            size: 56,
            useGradient: false,
            addShadow: false,
            context: context,
          ),
          // Reviewer mode badge
          if (reviewerMode)
            Positioned(
              bottom: -4,
              child: JyotiGPTBadge(
                text: AppLocalizations.of(context)!.demoBadge,
                backgroundColor: context.jyotigptTheme.warning.withValues(
                  alpha: 0.15,
                ),
                textColor: context.jyotigptTheme.warning,
                isCompact: true,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildWelcomeSection() {
    return Column(
      children: [
        Text(
          AppLocalizations.of(context)!.connectToServer,
          textAlign: TextAlign.center,
          style: context.jyotigptTheme.headingLarge?.copyWith(
            fontWeight: FontWeight.w600,
            height: 1.3,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          AppLocalizations.of(context)!.enterServerAddress,
          textAlign: TextAlign.center,
          style: context.jyotigptTheme.bodyMedium?.copyWith(
            color: context.jyotigptTheme.textSecondary,
            height: 1.4,
          ),
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

  Widget _buildServerForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AccessibleFormField(
          label: AppLocalizations.of(context)!.serverUrl,
          hint: AppLocalizations.of(context)!.serverUrlHint,
          controller: _urlController,
          validator: InputValidationService.combine([
            InputValidationService.validateRequired,
            (value) =>
                InputValidationService.validateUrl(value, required: true),
          ]),
          keyboardType: TextInputType.url,
          semanticLabel: AppLocalizations.of(context)!.enterServerUrlSemantic,
          onSubmitted: (_) => _connectToServer(),
          prefixIcon: Icon(
            Platform.isIOS ? CupertinoIcons.globe : Icons.public,
            color: context.jyotigptTheme.iconSecondary,
          ),
          autofillHints: const [AutofillHints.url],
          isRequired: true,
        ),

        if (_connectionError != null) ...[
          const SizedBox(height: Spacing.md),
          _buildErrorMessage(_connectionError!),
        ],

        const SizedBox(height: Spacing.lg),

        // Advanced settings
        _buildAdvancedSettings(),
      ],
    );
  }

  Widget _buildAdvancedSettings() {
    return Column(
      children: [
        InkWell(
          onTap: () =>
              setState(() => _showAdvancedSettings = !_showAdvancedSettings),
          borderRadius: BorderRadius.circular(AppBorderRadius.button),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.sm,
            ),
            child: Row(
              children: [
                Icon(
                  Platform.isIOS ? CupertinoIcons.gear_alt : Icons.settings,
                  color: context.jyotigptTheme.iconSecondary,
                  size: IconSize.small,
                ),
                const SizedBox(width: Spacing.sm),
                Expanded(
                  child: Text(
                    AppLocalizations.of(context)!.advancedSettings,
                    style: context.jyotigptTheme.bodySmall?.copyWith(
                      color: context.jyotigptTheme.textSecondary,
                    ),
                  ),
                ),
                if (_customHeaders.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(right: Spacing.sm),
                    child: JyotiGPTBadge(
                      text: '${_customHeaders.length}',
                      backgroundColor: context.jyotigptTheme.buttonPrimary
                          .withValues(alpha: 0.1),
                      textColor: context.jyotigptTheme.buttonPrimary,
                      isCompact: true,
                    ),
                  ),
                AnimatedRotation(
                  duration: AnimationDuration.microInteraction,
                  turns: _showAdvancedSettings ? 0.5 : 0,
                  child: Icon(
                    Platform.isIOS
                        ? CupertinoIcons.chevron_down
                        : Icons.expand_more,
                    color: context.jyotigptTheme.iconSecondary,
                    size: IconSize.small,
                  ),
                ),
              ],
            ),
          ),
        ),
        AnimatedSize(
          duration: AnimationDuration.microInteraction,
          curve: Curves.easeInOutCubic,
          child: _showAdvancedSettings
              ? _buildAdvancedSettingsContent()
              : const SizedBox.shrink(),
        ),
      ],
    );
  }

  Widget _buildAdvancedSettingsContent() {
    return Padding(
      padding: const EdgeInsets.all(Spacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(Spacing.md),
            margin: const EdgeInsets.only(bottom: Spacing.md),
            decoration: BoxDecoration(
              color: context.jyotigptTheme.surfaceContainer.withValues(
                alpha: 0.3,
              ),
              borderRadius: BorderRadius.circular(AppBorderRadius.small),
              border: Border.all(
                color: context.jyotigptTheme.dividerColor.withValues(alpha: 0.4),
                width: BorderWidth.thin,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Platform.isIOS
                      ? CupertinoIcons.lock_shield
                      : Icons.verified_user,
                  color: context.jyotigptTheme.iconSecondary,
                  size: IconSize.small,
                ),
                const SizedBox(width: Spacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        AppLocalizations.of(
                          context,
                        )!.allowSelfSignedCertificates,
                        style: context.jyotigptTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: context.jyotigptTheme.textPrimary,
                        ),
                      ),
                      const SizedBox(height: Spacing.xs),
                      Text(
                        AppLocalizations.of(
                          context,
                        )!.allowSelfSignedCertificatesDescription,
                        style: context.jyotigptTheme.bodySmall?.copyWith(
                          color: context.jyotigptTheme.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: Spacing.sm),
                Switch.adaptive(
                  value: _allowSelfSignedCertificates,
                  onChanged: (value) {
                    setState(() {
                      _allowSelfSignedCertificates = value;
                    });
                  },
                  activeTrackColor: context.jyotigptTheme.buttonPrimary,
                ),
              ],
            ),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                AppLocalizations.of(context)!.customHeaders,
                style: context.jyotigptTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w500,
                ),
              ),
              if (_customHeaders.isNotEmpty)
                Text(
                  '${_customHeaders.length}/10',
                  style: context.jyotigptTheme.bodySmall?.copyWith(
                    color: _customHeaders.length >= 10
                        ? context.jyotigptTheme.error
                        : context.jyotigptTheme.textSecondary,
                  ),
                ),
            ],
          ),
          const SizedBox(height: Spacing.xs),
          Text(
            AppLocalizations.of(context)!.customHeadersDescription,
            style: context.jyotigptTheme.bodySmall?.copyWith(
              color: context.jyotigptTheme.textSecondary,
            ),
          ),
          const SizedBox(height: Spacing.md),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                flex: 2,
                child: AccessibleFormField(
                  label: AppLocalizations.of(context)!.headerName,
                  hint: 'X-Custom-Header',
                  controller: _headerKeyController,
                  validator: (value) => _validateHeaderKey(value ?? ''),
                  semanticLabel: 'Enter header name',
                  isCompact: true,
                  keyboardType: TextInputType.text,
                ),
              ),
              const SizedBox(width: Spacing.sm),
              Expanded(
                flex: 3,
                child: AccessibleFormField(
                  label: AppLocalizations.of(context)!.headerValue,
                  hint: AppLocalizations.of(context)!.headerValueHint,
                  controller: _headerValueController,
                  validator: (value) => _validateHeaderValue(value ?? ''),
                  semanticLabel: 'Enter header value',
                  isCompact: true,
                  keyboardType: TextInputType.text,
                ),
              ),
              const SizedBox(width: Spacing.sm),
              JyotiGPTIconButton(
                icon: Platform.isIOS ? CupertinoIcons.plus : Icons.add,
                onPressed: _customHeaders.length >= 10
                    ? null
                    : _addCustomHeader,
                tooltip: _customHeaders.length >= 10
                    ? AppLocalizations.of(context)!.maximumHeadersReached
                    : AppLocalizations.of(context)!.addHeader,
                backgroundColor: _customHeaders.length >= 10
                    ? context.jyotigptTheme.surfaceContainer
                    : context.jyotigptTheme.buttonPrimary,
                iconColor: _customHeaders.length >= 10
                    ? context.jyotigptTheme.textDisabled
                    : context.jyotigptTheme.buttonPrimaryText,
              ),
            ],
          ),
          if (_customHeaders.isNotEmpty) ...[
            const SizedBox(height: Spacing.md),
            _buildCustomHeadersList(),
          ],
        ],
      ),
    );
  }

  Widget _buildCustomHeadersList() {
    return Column(
      children: _customHeaders.entries.map((entry) {
        return Container(
          margin: const EdgeInsets.only(bottom: Spacing.xs),
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.md,
            vertical: Spacing.sm,
          ),
          decoration: BoxDecoration(
            color: context.jyotigptTheme.surfaceContainer.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(AppBorderRadius.small),
            border: Border.all(
              color: context.jyotigptTheme.dividerColor.withValues(alpha: 0.5),
              width: BorderWidth.standard,
            ),
          ),
          child: Row(
            children: [
              Flexible(
                fit: FlexFit.loose,
                child: Text(
                  entry.key,
                  style: context.jyotigptTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: Spacing.sm),
              Expanded(
                child: Text(
                  entry.value,
                  style: context.jyotigptTheme.bodySmall?.copyWith(
                    color: context.jyotigptTheme.textSecondary,
                    fontFamily: 'monospace',
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: Spacing.sm),
              JyotiGPTIconButton(
                icon: Platform.isIOS ? CupertinoIcons.xmark : Icons.close,
                onPressed: () => _removeCustomHeader(entry.key),
                tooltip: AppLocalizations.of(context)!.removeHeader,
                backgroundColor: Colors.transparent,
                iconColor: context.jyotigptTheme.textSecondary,
                isCompact: true,
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildConnectButton() {
    return Padding(
      padding: const EdgeInsets.only(top: Spacing.lg),
      child: JyotiGPTButton(
        text: _isConnecting
            ? AppLocalizations.of(context)!.connecting
            : AppLocalizations.of(context)!.connectToServerButton,
        icon: _isConnecting
            ? null
            : (Platform.isIOS
                  ? CupertinoIcons.arrow_right
                  : Icons.arrow_forward),
        onPressed: _isConnecting ? null : _connectToServer,
        isLoading: _isConnecting,
        isFullWidth: true,
      ),
    );
  }

  Widget _buildErrorMessage(String message) {
    return Semantics(
      liveRegion: true,
      label: message,
      child: Container(
        padding: const EdgeInsets.all(Spacing.md),
        decoration: BoxDecoration(
          color: context.jyotigptTheme.error.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(AppBorderRadius.small),
          border: Border.all(
            color: context.jyotigptTheme.error.withValues(alpha: 0.2),
            width: BorderWidth.standard,
          ),
        ),
        child: Row(
          children: [
            Icon(
              Platform.isIOS
                  ? CupertinoIcons.exclamationmark_circle
                  : Icons.error_outline,
              color: context.jyotigptTheme.error,
              size: IconSize.small,
            ),
            const SizedBox(width: Spacing.sm),
            Expanded(
              child: Text(
                message,
                style: context.jyotigptTheme.bodySmall?.copyWith(
                  color: context.jyotigptTheme.error,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _addCustomHeader() {
    final key = _headerKeyController.text.trim();
    final value = _headerValueController.text.trim();

    if (key.isEmpty || value.isEmpty) return;

    // Validate header name
    final keyValidation = _validateHeaderKey(key);
    if (keyValidation != null) {
      _showHeaderError(keyValidation);
      return;
    }

    // Validate header value
    final valueValidation = _validateHeaderValue(value);
    if (valueValidation != null) {
      _showHeaderError(valueValidation);
      return;
    }

    // Check for duplicates
    if (_customHeaders.containsKey(key)) {
      _showHeaderError(AppLocalizations.of(context)!.headerAlreadyExists(key));
      return;
    }

    // Check header count limit
    if (_customHeaders.length >= 10) {
      _showHeaderError(AppLocalizations.of(context)!.maxHeadersReachedDetail);
      return;
    }

    setState(() {
      _customHeaders[key] = value;
      _headerKeyController.clear();
      _headerValueController.clear();
    });
    HapticFeedback.lightImpact();
  }

  String? _validateHeaderKey(String key) {
    // RFC 7230 compliant header name validation
    if (key.isEmpty) return AppLocalizations.of(context)!.headerNameEmpty;
    if (key.length > 64) return AppLocalizations.of(context)!.headerNameTooLong;

    // Check for valid characters (RFC 7230: token characters)
    if (!RegExp(r'^[a-zA-Z0-9!#$&\-^_`|~]+$').hasMatch(key)) {
      return AppLocalizations.of(context)!.headerNameInvalidChars;
    }

    // Check for reserved headers that should not be overridden
    final lowerKey = key.toLowerCase();
    final reservedHeaders = {
      'authorization',
      'content-type',
      'content-length',
      'host',
      'user-agent',
      'accept',
      'accept-encoding',
      'connection',
      'transfer-encoding',
      'upgrade',
      'via',
      'warning',
    };

    if (reservedHeaders.contains(lowerKey)) {
      return AppLocalizations.of(context)!.headerNameReserved(key);
    }

    return null;
  }

  String? _validateHeaderValue(String value) {
    if (value.isEmpty) return AppLocalizations.of(context)!.headerValueEmpty;
    if (value.length > 1024) {
      return AppLocalizations.of(context)!.headerValueTooLong;
    }

    // Check for valid characters (no control characters except tab)
    for (int i = 0; i < value.length; i++) {
      final char = value.codeUnitAt(i);
      // Allow printable ASCII (32-126) and tab (9)
      if (char != 9 && (char < 32 || char > 126)) {
        return AppLocalizations.of(context)!.headerValueInvalidChars;
      }
    }

    // Check for security-sensitive patterns
    if (value.toLowerCase().contains('script') ||
        value.contains('<') ||
        value.contains('>')) {
      return AppLocalizations.of(context)!.headerValueUnsafe;
    }

    return null;
  }

  void _showHeaderError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: context.jyotigptTheme.error,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _removeCustomHeader(String key) {
    setState(() {
      _customHeaders.remove(key);
    });
    HapticFeedback.lightImpact();
  }
}
