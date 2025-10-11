import 'dart:io' show Platform;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/models/server_config.dart';
import '../../../core/providers/app_providers.dart';
import '../../../core/services/connectivity_service.dart';
import '../../../core/services/navigation_service.dart';
import '../../../core/widgets/error_boundary.dart';
import '../../../l10n/app_localizations.dart';
import '../../../shared/theme/theme_extensions.dart';
import '../../../shared/widgets/jyotigpt_components.dart';
import '../providers/unified_auth_providers.dart';

class ConnectionIssuePage extends ConsumerStatefulWidget {
  const ConnectionIssuePage({super.key});

  @override
  ConsumerState<ConnectionIssuePage> createState() =>
      _ConnectionIssuePageState();
}

class _ConnectionIssuePageState extends ConsumerState<ConnectionIssuePage> {
  bool _isLoggingOut = false;
  String? _statusMessage;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final connectivity = ref.watch(connectivityStatusProvider);
    final activeServerAsync = ref.watch(activeServerProvider);
    final activeServer = activeServerAsync.asData?.value;

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
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 480),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _buildHeader(context, l10n, connectivity),
                          if (activeServer != null) ...[
                            const SizedBox(height: Spacing.sm),
                            _buildServerDetails(context, activeServer),
                          ],
                          const SizedBox(height: Spacing.lg),
                          Text(
                            l10n.connectionIssueSubtitle,
                            textAlign: TextAlign.center,
                            style: context.jyotigptTheme.bodyMedium?.copyWith(
                              color: context.jyotigptTheme.textSecondary,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                _buildActions(context, l10n),
                if (_statusMessage != null) ...[
                  const SizedBox(height: Spacing.sm),
                  _buildStatusMessage(context, _statusMessage!),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    AppLocalizations l10n,
    ConnectivityStatus? connectivity,
  ) {
    final iconColor = context.jyotigptTheme.error;
    final statusText = _statusLabel(connectivity, l10n);

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: context.jyotigptTheme.error.withValues(alpha: 0.1),
            shape: BoxShape.circle,
            border: Border.all(
              color: context.jyotigptTheme.error.withValues(alpha: 0.2),
              width: BorderWidth.thin,
            ),
          ),
          child: Icon(
            Platform.isIOS
                ? CupertinoIcons.wifi_exclamationmark
                : Icons.wifi_off_rounded,
            color: iconColor,
            size: 28,
          ),
        ),
        const SizedBox(height: Spacing.lg),
        Text(
          l10n.connectionIssueTitle,
          textAlign: TextAlign.center,
          style: context.jyotigptTheme.headingMedium?.copyWith(
            fontWeight: FontWeight.w600,
            color: context.jyotigptTheme.textPrimary,
          ),
        ),
        if (statusText != null) ...[
          const SizedBox(height: Spacing.xs),
          Text(
            statusText,
            textAlign: TextAlign.center,
            style: context.jyotigptTheme.bodySmall?.copyWith(
              color: context.jyotigptTheme.textSecondary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildServerDetails(BuildContext context, ServerConfig server) {
    final host = _resolveHost(server);

    return Column(
      children: [
        Text(
          host,
          textAlign: TextAlign.center,
          style: context.jyotigptTheme.bodyMedium?.copyWith(
            color: context.jyotigptTheme.textPrimary,
            fontFamily: 'monospace',
          ),
        ),
        const SizedBox(height: Spacing.xs),
        Text(
          server.url,
          textAlign: TextAlign.center,
          style: context.jyotigptTheme.bodySmall?.copyWith(
            color: context.jyotigptTheme.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildActions(BuildContext context, AppLocalizations l10n) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          JyotiGPTButton(
            text: l10n.retry,
            onPressed: _isLoggingOut
                ? null
                : () => context.go(Routes.serverConnection),
            icon: Platform.isIOS
                ? CupertinoIcons.refresh
                : Icons.refresh_rounded,
            isFullWidth: true,
          ),
          const SizedBox(height: Spacing.sm),
          JyotiGPTButton(
            text: l10n.signOut,
            onPressed: _isLoggingOut ? null : () => _logout(l10n),
            isLoading: _isLoggingOut,
            isSecondary: true,
            icon: Platform.isIOS
                ? CupertinoIcons.arrow_turn_up_left
                : Icons.logout,
            isFullWidth: true,
            isCompact: true,
          ),
        ],
      ),
    );
  }

  Widget _buildStatusMessage(BuildContext context, String message) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
      child: Text(
        message,
        textAlign: TextAlign.center,
        style: context.jyotigptTheme.bodySmall?.copyWith(
          color: context.jyotigptTheme.textSecondary,
        ),
      ),
    );
  }

  Future<void> _logout(AppLocalizations l10n) async {
    setState(() {
      _isLoggingOut = true;
      _statusMessage = null;
    });

    try {
      await ref.read(authActionsProvider).logout();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _statusMessage = l10n.couldNotConnectGeneric;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoggingOut = false;
        });
      }
    }
  }

  String _resolveHost(ServerConfig? config) {
    final url = config?.url;
    if (url == null || url.isEmpty) {
      return 'Open WebUI';
    }

    try {
      final uri = Uri.parse(url);
      if (uri.host.isNotEmpty) {
        return uri.host;
      }
      return url;
    } catch (_) {
      return url;
    }
  }

  String? _statusLabel(ConnectivityStatus? status, AppLocalizations l10n) {
    if (status == null) return null;
    switch (status) {
      case ConnectivityStatus.online:
        return l10n.connectedToServer;
      case ConnectivityStatus.offline:
        return l10n.pleaseCheckConnection;
    }
  }
}
