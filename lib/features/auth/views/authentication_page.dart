import 'dart:io' show Platform;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/models/server_config.dart';
import '../../../core/providers/app_providers.dart';
import '../../../core/services/input_validation_service.dart';
import '../../../core/services/navigation_service.dart';
import '../../../core/widgets/error_boundary.dart';
import '../../../shared/services/brand_service.dart';
import '../../../shared/theme/theme_extensions.dart';
import '../../../shared/widgets/jyotigpt_components.dart';
import '../../../core/auth/auth_state_manager.dart';
import '../../../core/utils/debug_logger.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';
import '../providers/unified_auth_providers.dart';

class AuthenticationPage extends ConsumerStatefulWidget {
  final ServerConfig? serverConfig;

  const AuthenticationPage({super.key, this.serverConfig});

  @override
  ConsumerState<AuthenticationPage> createState() => _AuthenticationPageState();
}

class _AuthenticationPageState extends ConsumerState<AuthenticationPage> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _apiKeyController = TextEditingController();

  bool _obscurePassword = true;
  bool _useApiKey = false;
  String? _loginError;
  bool _isSigningIn = false;

  @override
  void initState() {
    super.initState();
    _loadSavedCredentials();
  }

  Future<void> _loadSavedCredentials() async {
    final storage = ref.read(optimizedStorageServiceProvider);
    final savedCredentials = await storage.getSavedCredentials();
    if (savedCredentials != null) {
      setState(() {
        _usernameController.text = savedCredentials['username'] ?? '';
      });
    }
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _apiKeyController.dispose();
    super.dispose();
  }

  Future<void> _signIn() async {
    final l10n = AppLocalizations.of(context)!;
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isSigningIn = true;
      _loginError = null;
    });

    try {
      final actions = ref.read(authActionsProvider);
      bool success;

      if (_useApiKey) {
        success = await actions.loginWithApiKey(
          _apiKeyController.text.trim(),
          rememberCredentials: true, // Consistent with credentials method
        );
      } else {
        success = await actions.login(
          _usernameController.text.trim(),
          _passwordController.text,
          rememberCredentials: true,
        );
      }

      if (!success) {
        final authState = ref.read(authStateManagerProvider);
        throw Exception(authState.error ?? l10n.loginFailed);
      }

      // Success - navigation will be handled by auth state change
    } catch (e) {
      setState(() {
        _loginError = _formatLoginError(e.toString());
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSigningIn = false;
        });
      }
    }
  }

  String _formatLoginError(String error) {
    if (error.contains('401') || error.contains('Unauthorized')) {
      return AppLocalizations.of(context)!.invalidCredentials;
    } else if (error.contains('redirect')) {
      return AppLocalizations.of(context)!.serverRedirectingHttps;
    } else if (error.contains('SocketException')) {
      return AppLocalizations.of(context)!.unableToConnectServer;
    } else if (error.contains('timeout')) {
      return AppLocalizations.of(context)!.requestTimedOut;
    }
    return AppLocalizations.of(context)!.genericSignInFailed;
  }

  @override
  Widget build(BuildContext context) {
    // Listen for auth state changes to navigate on successful login
    ref.listen<AsyncValue<AuthState>>(authStateManagerProvider, (
      previous,
      next,
    ) {
      final nextState = next.asData?.value;
      final prevState = previous?.asData?.value;
      if (mounted &&
          nextState?.isAuthenticated == true &&
          prevState?.isAuthenticated != true) {
        DebugLogger.auth(
          'Authentication successful, initializing background resources',
        );

        // Model selection and onboarding will be handled by the chat page
        // to avoid widget disposal issues

        DebugLogger.auth('Navigating to chat page');
        // Navigate directly to chat page on successful authentication
        context.go(Routes.chat);
      }
    });

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
                            // Server connection status
                            _buildServerStatus(),

                            const SizedBox(height: Spacing.xl),

                            // Welcome section
                            _buildWelcomeSection(),

                            const SizedBox(height: Spacing.xl),

                            // Authentication form
                            _buildAuthForm(),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                // Bottom action button
                _buildSignInButton(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        JyotiGPTIconButton(
          icon: Platform.isIOS ? CupertinoIcons.back : Icons.arrow_back,
          onPressed: () => context.go(Routes.serverConnection),
          tooltip: AppLocalizations.of(context)!.backToServerSetup,
        ),
        const Spacer(),
        // Progress indicator (step 2 of 2)
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
                color: context.jyotigptTheme.buttonPrimary,
                borderRadius: BorderRadius.circular(AppBorderRadius.round),
              ),
            ),
          ],
        ),
        const Spacer(),
        const SizedBox(width: TouchTarget.minimum), // Balance the back button
      ],
    );
  }

  Widget _buildServerStatus() {
    // Prefer route-provided config; otherwise fall back to active server
    final activeServerAsync = ref.watch(activeServerProvider);
    final cfg =
        widget.serverConfig ??
        activeServerAsync.maybeWhen(data: (s) => s, orElse: () => null);
    final hostText = () {
      try {
        final url = cfg?.url;
        if (url != null && url.isNotEmpty) return Uri.parse(url).host;
      } catch (_) {}
      return 'Server';
    }();
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.sm,
      ),
      decoration: BoxDecoration(
        color: context.jyotigptTheme.success.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppBorderRadius.small),
        border: Border.all(
          color: context.jyotigptTheme.success.withValues(alpha: 0.2),
          width: BorderWidth.standard,
        ),
      ),
      child: Row(
        children: [
          Icon(
            Platform.isIOS
                ? CupertinoIcons.checkmark_circle
                : Icons.check_circle_outline,
            color: context.jyotigptTheme.success,
            size: IconSize.small,
          ),
          const SizedBox(width: Spacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  AppLocalizations.of(context)!.connectedToServer,
                  style: context.jyotigptTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.w500,
                    color: context.jyotigptTheme.success,
                  ),
                ),
                Text(
                  hostText,
                  style: context.jyotigptTheme.bodySmall?.copyWith(
                    color: context.jyotigptTheme.textSecondary,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWelcomeSection() {
    return Column(
      children: [
        BrandService.createBrandIcon(
          size: 48,
          useGradient: false,
          addShadow: false,
          context: context,
        ),
        const SizedBox(height: Spacing.lg),
        Text(
          AppLocalizations.of(context)!.signIn,
          textAlign: TextAlign.center,
          style: context.jyotigptTheme.headingLarge?.copyWith(
            fontWeight: FontWeight.w600,
            height: 1.3,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          AppLocalizations.of(context)!.enterCredentials,
          textAlign: TextAlign.center,
          style: context.jyotigptTheme.bodyMedium?.copyWith(
            color: context.jyotigptTheme.textSecondary,
            height: 1.4,
          ),
        ),
      ],
    );
  }

  Widget _buildAuthForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Authentication mode toggle
        _buildAuthModeToggle(),

        const SizedBox(height: Spacing.lg),

        // Authentication form fields
        _buildAuthFields(),

        if (_loginError != null) ...[
          const SizedBox(height: Spacing.md),
          _buildErrorMessage(_loginError!),
        ],
      ],
    );
  }

  Widget _buildAuthModeToggle() {
    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: context.jyotigptTheme.surfaceContainer.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(AppBorderRadius.small),
        border: Border.all(
          color: context.jyotigptTheme.dividerColor.withValues(alpha: 0.5),
          width: BorderWidth.standard,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildAuthToggleOption(
              icon: Platform.isIOS
                  ? CupertinoIcons.person_circle
                  : Icons.account_circle_outlined,
              label: AppLocalizations.of(context)!.credentials,
              isSelected: !_useApiKey,
              onTap: () => setState(() => _useApiKey = false),
            ),
          ),
          Expanded(
            child: _buildAuthToggleOption(
              icon: Platform.isIOS
                  ? CupertinoIcons.lock_shield
                  : Icons.vpn_key_outlined,
              label: AppLocalizations.of(context)!.apiKey,
              isSelected: _useApiKey,
              onTap: () => setState(() => _useApiKey = true),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAuthToggleOption({
    required IconData icon,
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return AnimatedContainer(
      duration: AnimationDuration.microInteraction,
      curve: Curves.easeInOutCubic,
      child: Material(
        color: isSelected
            ? context.jyotigptTheme.buttonPrimary
            : Colors.transparent,
        borderRadius: BorderRadius.circular(AppBorderRadius.small - 1),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppBorderRadius.small - 1),
          child: Container(
            padding: const EdgeInsets.symmetric(
              vertical: Spacing.sm,
              horizontal: Spacing.sm,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  icon,
                  size: IconSize.small,
                  color: isSelected
                      ? context.jyotigptTheme.buttonPrimaryText
                      : context.jyotigptTheme.iconSecondary,
                ),
                const SizedBox(width: Spacing.xs),
                Text(
                  label,
                  style: context.jyotigptTheme.bodySmall?.copyWith(
                    color: isSelected
                        ? context.jyotigptTheme.buttonPrimaryText
                        : context.jyotigptTheme.textSecondary,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAuthFields() {
    return AnimatedSwitcher(
      duration: AnimationDuration.pageTransition,
      switchInCurve: Curves.easeInOutCubic,
      switchOutCurve: Curves.easeInOutCubic,
      transitionBuilder: (Widget child, Animation<double> animation) {
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.1),
              end: Offset.zero,
            ).animate(animation),
            child: child,
          ),
        );
      },
      child: _useApiKey ? _buildApiKeyForm() : _buildCredentialsForm(),
    );
  }

  Widget _buildApiKeyForm() {
    return Column(
      key: const ValueKey('api_key_form'),
      children: [
        AccessibleFormField(
          label: AppLocalizations.of(context)!.apiKey,
          hint: 'sk-...',
          controller: _apiKeyController,
          validator: InputValidationService.combine([
            InputValidationService.validateRequired,
            (value) => InputValidationService.validateMinLength(
              value,
              10,
              fieldName: AppLocalizations.of(context)!.apiKey,
            ),
          ]),
          obscureText: _obscurePassword,
          semanticLabel: AppLocalizations.of(context)!.enterApiKey,
          prefixIcon: Icon(
            Platform.isIOS
                ? CupertinoIcons.lock_shield
                : Icons.vpn_key_outlined,
            color: context.jyotigptTheme.iconSecondary,
          ),
          suffixIcon: IconButton(
            icon: Icon(
              _obscurePassword
                  ? (Platform.isIOS
                        ? CupertinoIcons.eye_slash
                        : Icons.visibility_off)
                  : (Platform.isIOS ? CupertinoIcons.eye : Icons.visibility),
              color: context.jyotigptTheme.iconSecondary,
            ),
            onPressed: () =>
                setState(() => _obscurePassword = !_obscurePassword),
          ),
          onSubmitted: (_) => _signIn(),
          isRequired: true,
          autofillHints: const [AutofillHints.password],
        ),
      ],
    );
  }

  Widget _buildCredentialsForm() {
    return Column(
      key: const ValueKey('credentials_form'),
      children: [
        AccessibleFormField(
          label: AppLocalizations.of(context)!.usernameOrEmail,
          hint: AppLocalizations.of(context)!.usernameOrEmailHint,
          controller: _usernameController,
          validator: InputValidationService.combine([
            InputValidationService.validateRequired,
            (value) => InputValidationService.validateEmailOrUsername(value),
          ]),
          keyboardType: TextInputType.emailAddress,
          semanticLabel: AppLocalizations.of(context)!.usernameOrEmailHint,
          prefixIcon: Icon(
            Platform.isIOS ? CupertinoIcons.person : Icons.person_outline,
            color: context.jyotigptTheme.iconSecondary,
          ),
          autofillHints: const [AutofillHints.username, AutofillHints.email],
          isRequired: true,
        ),
        const SizedBox(height: Spacing.lg),
        AccessibleFormField(
          label: AppLocalizations.of(context)!.password,
          hint: AppLocalizations.of(context)!.passwordHint,
          controller: _passwordController,
          validator: InputValidationService.combine([
            InputValidationService.validateRequired,
            (value) => InputValidationService.validateMinLength(
              value,
              1,
              fieldName: AppLocalizations.of(context)!.password,
            ),
          ]),
          obscureText: _obscurePassword,
          semanticLabel: AppLocalizations.of(context)!.passwordHint,
          prefixIcon: Icon(
            Platform.isIOS ? CupertinoIcons.lock : Icons.lock_outline,
            color: context.jyotigptTheme.iconSecondary,
          ),
          suffixIcon: IconButton(
            icon: Icon(
              _obscurePassword
                  ? (Platform.isIOS
                        ? CupertinoIcons.eye_slash
                        : Icons.visibility_off)
                  : (Platform.isIOS ? CupertinoIcons.eye : Icons.visibility),
              color: context.jyotigptTheme.iconSecondary,
            ),
            onPressed: () =>
                setState(() => _obscurePassword = !_obscurePassword),
          ),
          onSubmitted: (_) => _signIn(),
          autofillHints: const [AutofillHints.password],
          isRequired: true,
        ),
      ],
    );
  }

  Widget _buildSignInButton() {
    return Padding(
      padding: const EdgeInsets.only(top: Spacing.lg),
      child: JyotiGPTButton(
        text: _isSigningIn
            ? AppLocalizations.of(context)!.signingIn
            : _useApiKey
            ? AppLocalizations.of(context)!.signInWithApiKey
            : AppLocalizations.of(context)!.signIn,
        icon: _isSigningIn
            ? null
            : (Platform.isIOS
                  ? CupertinoIcons.arrow_right
                  : Icons.arrow_forward),
        onPressed: _isSigningIn ? null : _signIn,
        isLoading: _isSigningIn,
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
}
