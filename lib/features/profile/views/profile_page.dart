import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../shared/theme/theme_extensions.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher_string.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';
import '../../../core/widgets/error_boundary.dart';
import '../../../shared/widgets/improved_loading_states.dart';

import '../../../shared/utils/ui_utils.dart';
import '../../../shared/widgets/themed_dialogs.dart';
import '../../../shared/widgets/sheet_handle.dart';
import '../../../shared/widgets/jyotigpt_components.dart';
import '../../../core/providers/app_providers.dart';
import '../../../core/services/navigation_service.dart';
import '../../auth/providers/unified_auth_providers.dart';
import '../../../core/services/settings_service.dart';
import '../../../core/models/model.dart';
import '../../../core/services/api_service.dart';
import '../../../core/models/user.dart' as models;
import 'dart:async';
import 'dart:io';
import '../../chat/views/chat_page_helpers.dart';
import '../../../shared/widgets/modal_safe_area.dart';
import '../../../core/utils/user_display_name.dart';
import '../../../core/utils/user_avatar_utils.dart';
import '../../../core/utils/model_icon_utils.dart';
import '../../../shared/widgets/user_avatar.dart';
import '../../../shared/widgets/model_avatar.dart';

/// Profile page (You tab) showing user info and main actions
/// Enhanced with production-grade design tokens for better cohesion
class ProfilePage extends ConsumerWidget {
  static const _githubSponsorsUrl = 'https://github.com/sponsors/y4shg';
  static const _buyMeACoffeeUrl = 'https://www.buymeacoffee.com/y4shg';

  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final api = ref.watch(apiServiceProvider);

    return ErrorBoundary(
      child: user.when(
        data: (userData) => _buildScaffold(
          context,
          body: _buildProfileBody(context, ref, userData, api),
        ),
        loading: () => _buildScaffold(
          context,
          body: _buildCenteredState(
            context,
            ImprovedLoadingState(
              message: AppLocalizations.of(context)!.loadingProfile,
            ),
          ),
        ),
        error: (error, stack) => _buildScaffold(
          context,
          body: _buildCenteredState(
            context,
            ImprovedEmptyState(
              title: AppLocalizations.of(context)!.unableToLoadProfile,
              subtitle: AppLocalizations.of(context)!.pleaseCheckConnection,
              icon: UiUtils.platformIcon(
                ios: CupertinoIcons.exclamationmark_triangle,
                android: Icons.error_outline,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Scaffold _buildScaffold(BuildContext context, {required Widget body}) {
    return Scaffold(
      backgroundColor: context.jyotigptTheme.surfaceBackground,
      appBar: _buildAppBar(context),
      body: body,
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context) {
    final canPop = ModalRoute.of(context)?.canPop ?? false;
    return AppBar(
      backgroundColor: context.jyotigptTheme.surfaceBackground,
      surfaceTintColor: Colors.transparent,
      elevation: Elevation.none,
      toolbarHeight: kToolbarHeight,
      automaticallyImplyLeading: false,
      leading: canPop
          ? IconButton(
              icon: Icon(
                UiUtils.platformIcon(
                  ios: CupertinoIcons.back,
                  android: Icons.arrow_back,
                ),
                color: context.jyotigptTheme.iconPrimary,
              ),
              onPressed: () => Navigator.of(context).maybePop(),
              tooltip: AppLocalizations.of(context)!.back,
            )
          : null,
      titleSpacing: 0,
      title: Text(
        AppLocalizations.of(context)!.you,
        style: AppTypography.headlineSmallStyle.copyWith(
          color: context.jyotigptTheme.textPrimary,
          fontWeight: FontWeight.w600,
        ),
      ),
      centerTitle: true,
    );
  }

  Widget _buildCenteredState(BuildContext context, Widget child) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.pagePadding),
        child: Center(child: child),
      ),
    );
  }

  Widget _buildProfileBody(
    BuildContext context,
    WidgetRef ref,
    dynamic userData,
    ApiService? api,
  ) {
    return SafeArea(
      child: ListView(
        physics: const BouncingScrollPhysics(
          parent: AlwaysScrollableScrollPhysics(),
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.pagePadding,
          vertical: Spacing.pagePadding,
        ),
        children: [
          _buildProfileHeader(context, userData, api),
          const SizedBox(height: Spacing.xl),
          _buildAccountSection(context, ref),
          const SizedBox(height: Spacing.xl),
          _buildSupportSection(context),
        ],
      ),
    );
  }

  Widget _buildSupportSection(BuildContext context) {
    final theme = context.jyotigptTheme;
    final textTheme =
        theme.bodySmall?.copyWith(color: theme.textSecondary) ??
        TextStyle(color: theme.textSecondary);

    final supportTiles = [
      _buildSupportOption(
        context,
        icon: UiUtils.platformIcon(
          ios: CupertinoIcons.heart,
          android: Icons.favorite_border,
        ),
        title: AppLocalizations.of(context)!.githubSponsorsTitle,
        subtitle: AppLocalizations.of(context)!.githubSponsorsSubtitle,
        url: _githubSponsorsUrl,
        color: theme.success,
      ),
      _buildSupportOption(
        context,
        icon: UiUtils.platformIcon(
          ios: CupertinoIcons.gift,
          android: Icons.coffee,
        ),
        title: AppLocalizations.of(context)!.buyMeACoffeeTitle,
        subtitle: AppLocalizations.of(context)!.buyMeACoffeeSubtitle,
        url: _buyMeACoffeeUrl,
        color: theme.warning,
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          AppLocalizations.of(context)!.supportJyotiGPT,
          style: theme.headingSmall?.copyWith(color: theme.textPrimary),
        ),
        const SizedBox(height: Spacing.xs),
        Text(
          AppLocalizations.of(context)!.supportJyotiGPTSubtitle,
          style: textTheme,
        ),
        const SizedBox(height: Spacing.sm),
        for (var i = 0; i < supportTiles.length; i++) ...[
          supportTiles[i],
          if (i != supportTiles.length - 1) const SizedBox(height: Spacing.md),
        ],
      ],
    );
  }

  Widget _buildSupportOption(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required String url,
    required Color color,
  }) {
    final theme = context.jyotigptTheme;
    return _ProfileSettingTile(
      onTap: () => _openExternalLink(context, url),
      isDestructive: false,
      leading: _buildIconBadge(context, icon, color: color),
      title: title,
      subtitle: subtitle,
      trailing: Icon(
        UiUtils.platformIcon(
          ios: CupertinoIcons.arrow_up_right,
          android: Icons.open_in_new,
        ),
        color: theme.iconSecondary,
        size: IconSize.small,
      ),
    );
  }

  Future<void> _openExternalLink(BuildContext context, String url) async {
    try {
      final launched = await launchUrlString(
        url,
        mode: LaunchMode.externalApplication,
      );

      if (!launched && context.mounted) {
        UiUtils.showMessage(
          context,
          AppLocalizations.of(context)!.errorMessage,
        );
      }
    } on PlatformException catch (_) {
      if (!context.mounted) return;
      UiUtils.showMessage(context, AppLocalizations.of(context)!.errorMessage);
    } catch (_) {
      if (!context.mounted) return;
      UiUtils.showMessage(context, AppLocalizations.of(context)!.errorMessage);
    }
  }

  Widget _buildProfileHeader(
    BuildContext context,
    dynamic user,
    ApiService? api,
  ) {
    final displayName = deriveUserDisplayName(user);
    final characters = displayName.characters;
    final initial = characters.isNotEmpty
        ? characters.first.toUpperCase()
        : 'U';
    final avatarUrl = resolveUserAvatarUrlForUser(api, user);

    String? extractEmail(dynamic source) {
      if (source is models.User) {
        return source.email;
      }
      if (source is Map) {
        final value = source['email'];
        if (value is String && value.trim().isNotEmpty) {
          return value.trim();
        }
        final nested = source['user'];
        if (nested is Map) {
          final nestedValue = nested['email'];
          if (nestedValue is String && nestedValue.trim().isNotEmpty) {
            return nestedValue.trim();
          }
        }
      }
      return null;
    }

    final email = extractEmail(user) ?? 'No email';
    final theme = context.jyotigptTheme;
    final accent = theme.buttonPrimary;

    return Container(
      padding: const EdgeInsets.all(Spacing.md),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppBorderRadius.large),
        border: Border.all(
          color: accent.withValues(alpha: 0.15),
          width: BorderWidth.thin,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              UserAvatar(size: 56, imageUrl: avatarUrl, fallbackText: initial),
              const SizedBox(width: Spacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      displayName,
                      style: theme.headingMedium?.copyWith(
                        color: theme.textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    Row(
                      children: [
                        Icon(
                          UiUtils.platformIcon(
                            ios: CupertinoIcons.envelope,
                            android: Icons.mail_outline,
                          ),
                          size: IconSize.small,
                          color: theme.textSecondary,
                        ),
                        const SizedBox(width: Spacing.xs),
                        Flexible(
                          child: Text(
                            email,
                            style: theme.bodySmall?.copyWith(
                              color: theme.textSecondary,
                            ),
                            overflow: TextOverflow.ellipsis,
                            maxLines: 1,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAccountSection(BuildContext context, WidgetRef ref) {
    final items = [
      _buildDefaultModelTile(context, ref),
      _buildAccountOption(
        context,
        icon: UiUtils.platformIcon(
          ios: CupertinoIcons.slider_horizontal_3,
          android: Icons.tune,
        ),
        title: AppLocalizations.of(context)!.appCustomization,
        subtitle: AppLocalizations.of(context)!.appCustomizationSubtitle,
        onTap: () {
          context.pushNamed(RouteNames.appCustomization);
        },
      ),
      _buildAboutTile(context),
      _buildAccountOption(
        context,
        icon: UiUtils.platformIcon(
          ios: CupertinoIcons.square_arrow_left,
          android: Icons.logout,
        ),
        title: AppLocalizations.of(context)!.signOut,
        subtitle: AppLocalizations.of(context)!.endYourSession,
        onTap: () => _signOut(context, ref),
        isDestructive: true,
        showChevron: false,
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < items.length; i++) ...[
          items[i],
          if (i != items.length - 1) const SizedBox(height: Spacing.md),
        ],
      ],
    );
  }

  Widget _buildAccountOption(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    bool isDestructive = false,
    bool showChevron = true,
  }) {
    final theme = context.jyotigptTheme;
    final color = isDestructive ? theme.error : theme.buttonPrimary;
    return _ProfileSettingTile(
      onTap: onTap,
      isDestructive: isDestructive,
      leading: _buildIconBadge(context, icon, color: color),
      title: title,
      subtitle: subtitle,
      trailing: showChevron
          ? Icon(
              UiUtils.platformIcon(
                ios: CupertinoIcons.chevron_right,
                android: Icons.chevron_right,
              ),
              color: theme.iconSecondary,
              size: IconSize.small,
            )
          : null,
    );
  }

  Widget _buildDefaultModelTile(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(appSettingsProvider);
    final modelsAsync = ref.watch(modelsProvider);
    final api = ref.watch(apiServiceProvider);

    return modelsAsync.when(
      data: (models) {
        final currentModel = models.firstWhere(
          (m) => m.id == settings.defaultModel,
          orElse: () => models.isNotEmpty
              ? models.first
              : Model(
                  id: 'none',
                  name: AppLocalizations.of(context)!.noModelsAvailable,
                ),
        );

        final selectedModelExplicit = settings.defaultModel != null;
        final modelIconUrl = selectedModelExplicit
            ? resolveModelIconUrlForModel(api, currentModel)
            : null;
        final modelLabel = selectedModelExplicit
            ? currentModel.name
            : AppLocalizations.of(context)!.autoSelect;

        final theme = context.jyotigptTheme;

        Widget leading;
        if (selectedModelExplicit) {
          leading = Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: theme.surfaceBackground.withValues(alpha: 0.85),
              borderRadius: BorderRadius.circular(AppBorderRadius.small),
              border: Border.all(
                color: theme.cardBorder,
                width: BorderWidth.thin,
              ),
            ),
            alignment: Alignment.center,
            child: ModelAvatar(
              size: 28,
              imageUrl: modelIconUrl,
              label: currentModel.name,
            ),
          );
        } else {
          leading = _buildIconBadge(
            context,
            UiUtils.platformIcon(
              ios: CupertinoIcons.wand_stars,
              android: Icons.auto_awesome,
            ),
            color: theme.buttonPrimary,
          );
        }

        return _ProfileSettingTile(
          leading: leading,
          title: AppLocalizations.of(context)!.defaultModel,
          subtitle: modelLabel,
          onTap: () => _showModelSelector(context, ref, models),
        );
      },
      loading: () => _ProfileSettingTile(
        leading: _buildIconBadge(
          context,
          UiUtils.platformIcon(
            ios: CupertinoIcons.cube_box,
            android: Icons.psychology,
          ),
          color: context.jyotigptTheme.buttonPrimary,
        ),
        title: AppLocalizations.of(context)!.defaultModel,
        subtitle: AppLocalizations.of(context)!.loadingModels,
        showChevron: false,
        trailing: SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(
              context.jyotigptTheme.buttonPrimary,
            ),
          ),
        ),
      ),
      error: (error, stack) => _ProfileSettingTile(
        leading: _buildIconBadge(
          context,
          UiUtils.platformIcon(
            ios: CupertinoIcons.exclamationmark_triangle,
            android: Icons.error_outline,
          ),
          color: context.jyotigptTheme.error,
        ),
        title: AppLocalizations.of(context)!.defaultModel,
        subtitle: AppLocalizations.of(context)!.failedToLoadModels,
        isDestructive: true,
        showChevron: false,
        onTap: () => ref.invalidate(modelsProvider),
        trailing: IconButton(
          onPressed: () => ref.invalidate(modelsProvider),
          tooltip: AppLocalizations.of(context)!.retry,
          icon: Icon(
            UiUtils.platformIcon(
              ios: CupertinoIcons.refresh,
              android: Icons.refresh,
            ),
            color: context.jyotigptTheme.error,
            size: IconSize.small,
          ),
        ),
      ),
    );
  }

  Widget _buildIconBadge(
    BuildContext context,
    IconData icon, {
    required Color color,
  }) {
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppBorderRadius.small),
        border: Border.all(
          color: color.withValues(alpha: 0.2),
          width: BorderWidth.thin,
        ),
      ),
      alignment: Alignment.center,
      child: Icon(icon, color: color, size: IconSize.medium),
    );
  }

  // Theme and language controls moved to AppCustomizationPage.

  Widget _buildAboutTile(BuildContext context) {
    return _buildAccountOption(
      context,
      icon: UiUtils.platformIcon(
        ios: CupertinoIcons.info,
        android: Icons.info_outline,
      ),
      title: AppLocalizations.of(context)!.aboutApp,
      subtitle: AppLocalizations.of(context)!.aboutAppSubtitle,
      onTap: () => _showAboutDialog(context),
    );
  }

  Future<void> _showAboutDialog(BuildContext context) async {
    try {
      final info = await PackageInfo.fromPlatform();
      // Update dialog with dynamic version each time
      // GitHub repo URL source of truth
      const githubUrl = 'https://github.com/y4shg/jyotigpt';

      if (!context.mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) {
          return AlertDialog(
            backgroundColor: ctx.jyotigptTheme.surfaceBackground,
            title: Text(
              AppLocalizations.of(ctx)!.aboutJyotiGPT,
              style: ctx.jyotigptTheme.headingSmall?.copyWith(
                color: ctx.jyotigptTheme.textPrimary,
              ),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  AppLocalizations.of(
                    ctx,
                  )!.versionLabel(info.version, info.buildNumber),
                  style: ctx.jyotigptTheme.bodyMedium?.copyWith(
                    color: ctx.jyotigptTheme.textSecondary,
                  ),
                ),
                const SizedBox(height: Spacing.md),
                InkWell(
                  onTap: () => launchUrlString(
                    githubUrl,
                    mode: LaunchMode.externalApplication,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        UiUtils.platformIcon(
                          ios: CupertinoIcons.link,
                          android: Icons.link,
                        ),
                        size: IconSize.small,
                        color: ctx.jyotigptTheme.buttonPrimary,
                      ),
                      const SizedBox(width: Spacing.xs),
                      Text(
                        AppLocalizations.of(ctx)!.githubRepository,
                        style: ctx.jyotigptTheme.bodyMedium?.copyWith(
                          color: ctx.jyotigptTheme.buttonPrimary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: Text(AppLocalizations.of(ctx)!.closeButtonSemantic),
              ),
            ],
          );
        },
      );
    } catch (e) {
      if (!context.mounted) return;
      UiUtils.showMessage(
        context,
        AppLocalizations.of(context)!.unableToLoadAppInfo,
      );
    }
  }

  Future<void> _showModelSelector(
    BuildContext context,
    WidgetRef ref,
    List<Model> models,
  ) async {
    final result = await showModalBottomSheet<String?>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _DefaultModelBottomSheet(
        models: models,
        currentDefaultModelId: ref.read(appSettingsProvider).defaultModel,
      ),
    );

    // result is non-null only when Save button is pressed
    // null means the sheet was dismissed without saving
    if (result != null) {
      // Handle special case: 'auto-select' should be stored as null
      final modelIdToSave = result == 'auto-select' ? null : result;
      await ref
          .read(appSettingsProvider.notifier)
          .setDefaultModel(modelIdToSave);
    }
  }

  void _signOut(BuildContext context, WidgetRef ref) async {
    final confirm = await ThemedDialogs.confirm(
      context,
      title: AppLocalizations.of(context)!.signOut,
      message: AppLocalizations.of(context)!.endYourSession,
      confirmText: AppLocalizations.of(context)!.signOut,
      isDestructive: true,
    );

    if (confirm) {
      await ref.read(authActionsProvider).logout();
    }
  }
}

class _ProfileSettingTile extends StatelessWidget {
  const _ProfileSettingTile({
    required this.leading,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.trailing,
    this.isDestructive = false,
    this.showChevron = true,
  });

  final Widget leading;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final Widget? trailing;
  final bool isDestructive;
  final bool showChevron;

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;
    final textColor = isDestructive ? theme.error : theme.textPrimary;
    final subtitleColor = isDestructive
        ? theme.error.withValues(alpha: 0.85)
        : theme.textSecondary;

    return JyotiGPTCard(
      padding: const EdgeInsets.all(Spacing.md),
      onTap: onTap,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          leading,
          const SizedBox(width: Spacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.bodyMedium?.copyWith(
                    color: textColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: Spacing.xs),
                Text(
                  subtitle,
                  style: theme.bodySmall?.copyWith(color: subtitleColor),
                ),
              ],
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: Spacing.sm),
            trailing!,
          ] else if (showChevron && onTap != null) ...[
            const SizedBox(width: Spacing.sm),
            Icon(
              UiUtils.platformIcon(
                ios: CupertinoIcons.chevron_right,
                android: Icons.chevron_right,
              ),
              color: theme.iconSecondary,
              size: IconSize.small,
            ),
          ],
        ],
      ),
    );
  }
}

class _DefaultModelBottomSheet extends ConsumerStatefulWidget {
  final List<Model> models;
  final String? currentDefaultModelId;

  const _DefaultModelBottomSheet({
    required this.models,
    required this.currentDefaultModelId,
  });

  @override
  ConsumerState<_DefaultModelBottomSheet> createState() =>
      _DefaultModelBottomSheetState();
}

class _DefaultModelBottomSheetState
    extends ConsumerState<_DefaultModelBottomSheet> {
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  List<Model> _filteredModels = [];
  Timer? _searchDebounce;
  String? _selectedModelId;

  Widget _capabilityChip({required IconData icon, required String label}) {
    return Container(
      margin: const EdgeInsets.only(right: Spacing.xs),
      padding: const EdgeInsets.symmetric(horizontal: Spacing.xs, vertical: 2),
      decoration: BoxDecoration(
        color: context.jyotigptTheme.buttonPrimary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppBorderRadius.chip),
        border: Border.all(
          color: context.jyotigptTheme.buttonPrimary.withValues(alpha: 0.3),
          width: BorderWidth.thin,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: context.jyotigptTheme.buttonPrimary),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: AppTypography.labelSmall,
              color: context.jyotigptTheme.textSecondary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    // If no default model is set (null), default to auto-select
    _selectedModelId = widget.currentDefaultModelId ?? 'auto-select';
    // Add auto-select as first item
    _filteredModels = _allModels();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _searchDebounce?.cancel();
    super.dispose();
  }

  List<Model> _allModels() {
    return [
      const Model(id: 'auto-select', name: 'Auto-select'),
      ...widget.models,
    ];
  }

  void _filterModels(String query) {
    setState(() => _searchQuery = query);

    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 160), () {
      if (!mounted) return;

      final normalized = query.trim().toLowerCase();
      final allModels = _allModels();
      final filtered = normalized.isEmpty
          ? allModels
          : allModels.where((model) {
              final name = model.name.toLowerCase();
              final id = model.id.toLowerCase();
              return name.contains(normalized) || id.contains(normalized);
            }).toList();

      setState(() {
        _filteredModels = filtered;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => Navigator.of(context).maybePop(),
            child: const SizedBox.shrink(),
          ),
        ),
        DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.75,
          maxChildSize: 0.92,
          minChildSize: 0.45,
          builder: (context, scrollController) {
            return Container(
              decoration: BoxDecoration(
                color: context.jyotigptTheme.surfaceBackground,
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(AppBorderRadius.bottomSheet),
                ),
                border: Border.all(
                  color: context.jyotigptTheme.dividerColor,
                  width: BorderWidth.regular,
                ),
                boxShadow: JyotiGPTShadows.modal(context),
              ),
              child: ModalSheetSafeArea(
                padding: const EdgeInsets.symmetric(
                  horizontal: Spacing.modalPadding,
                  vertical: Spacing.modalPadding,
                ),
                child: Column(
                  children: [
                    // Handle bar (standardized)
                    const SheetHandle(),

                    // Header removed (no icon/title or save button)
                    const SizedBox(height: Spacing.md),

                    // Search field
                    Padding(
                      padding: const EdgeInsets.only(bottom: Spacing.md),
                      child: TextField(
                        controller: _searchController,
                        style: AppTypography.standard.copyWith(
                          color: context.jyotigptTheme.textPrimary,
                        ),
                        onChanged: _filterModels,
                        decoration: InputDecoration(
                          isDense: true,
                          hintText: AppLocalizations.of(context)!.searchModels,
                          hintStyle: AppTypography.standard.copyWith(
                            color: context.jyotigptTheme.inputPlaceholder,
                          ),
                          prefixIcon: Icon(
                            Platform.isIOS
                                ? CupertinoIcons.search
                                : Icons.search,
                            color: context.jyotigptTheme.iconSecondary,
                            size: IconSize.input,
                          ),
                          prefixIconConstraints: const BoxConstraints(
                            minWidth: TouchTarget.minimum,
                            minHeight: TouchTarget.minimum,
                          ),
                          suffixIcon: _searchQuery.isNotEmpty
                              ? IconButton(
                                  onPressed: () {
                                    _searchController.clear();
                                    _filterModels('');
                                  },
                                  icon: Icon(
                                    Platform.isIOS
                                        ? CupertinoIcons.clear_circled_solid
                                        : Icons.clear,
                                    color: context.jyotigptTheme.iconSecondary,
                                    size: IconSize.input,
                                  ),
                                )
                              : null,
                          suffixIconConstraints: const BoxConstraints(
                            minWidth: TouchTarget.minimum,
                            minHeight: TouchTarget.minimum,
                          ),
                          filled: true,
                          fillColor: context.jyotigptTheme.inputBackground,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(
                              AppBorderRadius.md,
                            ),
                            borderSide: BorderSide.none,
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(
                              AppBorderRadius.md,
                            ),
                            borderSide: BorderSide(
                              color: context.jyotigptTheme.inputBorder,
                              width: 1,
                            ),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(
                              AppBorderRadius.md,
                            ),
                            borderSide: BorderSide(
                              color: context.jyotigptTheme.buttonPrimary,
                              width: 1,
                            ),
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: Spacing.md,
                            vertical: Spacing.xs,
                          ),
                        ),
                      ),
                    ),

                    // Section header (cohesive with Chats Drawer)
                    Padding(
                      padding: const EdgeInsets.only(bottom: Spacing.sm),
                      child: Row(
                        children: [
                          Text(
                            AppLocalizations.of(context)!.availableModels,
                            style: AppTypography.bodySmallStyle.copyWith(
                              fontWeight: FontWeight.w600,
                              color: context.jyotigptTheme.textSecondary,
                              letterSpacing: 0.2,
                            ),
                          ),
                          const SizedBox(width: Spacing.xs),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: context.jyotigptTheme.surfaceBackground
                                  .withValues(alpha: 0.6),
                              borderRadius: BorderRadius.circular(
                                AppBorderRadius.xs,
                              ),
                              border: Border.all(
                                color: context.jyotigptTheme.dividerColor,
                                width: BorderWidth.thin,
                              ),
                            ),
                            child: Text(
                              '${_filteredModels.length}',
                              style: AppTypography.bodySmallStyle.copyWith(
                                color: context.jyotigptTheme.textSecondary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: Spacing.sm),

                    // Models list
                    Expanded(
                      child: Scrollbar(
                        controller: scrollController,
                        child: _filteredModels.isEmpty
                            ? Center(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      Platform.isIOS
                                          ? CupertinoIcons.search_circle
                                          : Icons.search_off,
                                      size: 48,
                                      color: context.jyotigptTheme.iconSecondary,
                                    ),
                                    const SizedBox(height: Spacing.md),
                                    Text(
                                      AppLocalizations.of(context)!.noResults,
                                      style: TextStyle(
                                        color:
                                            context.jyotigptTheme.textSecondary,
                                        fontSize: AppTypography.bodyLarge,
                                      ),
                                    ),
                                  ],
                                ),
                              )
                            : ListView.builder(
                                controller: scrollController,
                                padding: EdgeInsets.zero,
                                itemCount: _filteredModels.length,
                                itemBuilder: (context, index) {
                                  final model = _filteredModels[index];
                                  final isAutoSelect =
                                      model.id == 'auto-select';
                                  final isSelected = isAutoSelect
                                      ? _selectedModelId == null ||
                                            _selectedModelId == 'auto-select'
                                      : _selectedModelId == model.id;

                                  return _buildModelListTile(
                                    model: model,
                                    isSelected: isSelected,
                                    isAutoSelect: isAutoSelect,
                                    onTap: () {
                                      HapticFeedback.lightImpact();
                                      final selectedId = isAutoSelect
                                          ? 'auto-select'
                                          : model.id;
                                      Navigator.pop(context, selectedId);
                                    },
                                  );
                                },
                              ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ],
    );
  }

  bool _modelSupportsReasoning(Model model) {
    final params = model.supportedParameters ?? const [];
    return params.any((p) => p.toLowerCase().contains('reasoning'));
  }

  Widget _buildModelListTile({
    required Model model,
    required bool isSelected,
    required bool isAutoSelect,
    required VoidCallback onTap,
  }) {
    final api = ref.watch(apiServiceProvider);

    final Widget leading;
    if (isAutoSelect) {
      leading = Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: context.jyotigptTheme.buttonPrimary.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(AppBorderRadius.md),
        ),
        child: Icon(
          Platform.isIOS ? CupertinoIcons.wand_stars : Icons.auto_awesome,
          color: context.jyotigptTheme.buttonPrimary,
          size: 16,
        ),
      );
    } else {
      final iconUrl = resolveModelIconUrlForModel(api, model);
      leading = ModelAvatar(size: 32, imageUrl: iconUrl, label: model.name);
    }

    return PressableScale(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppBorderRadius.small),
      child: Container(
        margin: const EdgeInsets.only(bottom: Spacing.sm),
        decoration: BoxDecoration(
          color: isSelected
              ? context.jyotigptTheme.buttonPrimary.withValues(alpha: 0.1)
              : context.jyotigptTheme.surfaceBackground.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(AppBorderRadius.small),
          border: Border.all(
            color: isSelected
                ? context.jyotigptTheme.buttonPrimary.withValues(alpha: 0.3)
                : context.jyotigptTheme.dividerColor.withValues(alpha: 0.5),
            width: BorderWidth.standard,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(Spacing.sm),
          child: Row(
            children: [
              leading,
              const SizedBox(width: Spacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isAutoSelect
                          ? AppLocalizations.of(context)!.autoSelect
                          : model.name,
                      style: TextStyle(
                        color: context.jyotigptTheme.textPrimary,
                        fontWeight: FontWeight.w600,
                        fontSize: AppTypography.bodyMedium,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (isAutoSelect) ...[
                      const SizedBox(height: Spacing.xs),
                      Text(
                        'Let the app choose the best model',
                        style: TextStyle(
                          fontSize: AppTypography.bodySmall,
                          color: context.jyotigptTheme.textSecondary,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                    ] else if (model.isMultimodal ||
                        _modelSupportsReasoning(model)) ...[
                      const SizedBox(height: Spacing.xs),
                      Row(
                        children: [
                          if (model.isMultimodal)
                            _capabilityChip(
                              icon: Platform.isIOS
                                  ? CupertinoIcons.photo
                                  : Icons.image,
                              label: 'Multimodal',
                            ),
                          if (_modelSupportsReasoning(model))
                            _capabilityChip(
                              icon: Platform.isIOS
                                  ? CupertinoIcons.lightbulb
                                  : Icons.psychology_alt,
                              label: 'Reasoning',
                            ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: Spacing.sm),
              if (isSelected)
                Icon(
                  Platform.isIOS ? CupertinoIcons.check_mark : Icons.check,
                  color: context.jyotigptTheme.buttonPrimary,
                  size: IconSize.small,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
