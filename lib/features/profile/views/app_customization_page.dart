import 'dart:io' show Platform;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/services/settings_service.dart';
import '../../../shared/theme/theme_extensions.dart';
import '../../../shared/theme/color_palettes.dart';
import '../../tools/providers/tools_providers.dart';
import '../../../core/models/tool.dart';
import '../../../shared/widgets/jyotigpt_components.dart';
import '../../../shared/utils/ui_utils.dart';
import '../../../core/providers/app_providers.dart';
import '../../../l10n/app_localizations.dart';

class AppCustomizationPage extends ConsumerWidget {
  const AppCustomizationPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(appSettingsProvider);
    final themeMode = ref.watch(appThemeModeProvider);
    final platformBrightness = MediaQuery.platformBrightnessOf(context);
    final themeDescription = () {
      if (themeMode == ThemeMode.system) {
        final systemThemeLabel = platformBrightness == Brightness.dark
            ? AppLocalizations.of(context)!.themeDark
            : AppLocalizations.of(context)!.themeLight;
        return AppLocalizations.of(context)!.followingSystem(systemThemeLabel);
      }
      if (themeMode == ThemeMode.dark) {
        return AppLocalizations.of(context)!.currentlyUsingDarkTheme;
      }
      return AppLocalizations.of(context)!.currentlyUsingLightTheme;
    }();
    final locale = ref.watch(appLocaleProvider);
    final currentLanguageCode = locale?.languageCode ?? 'system';
    final languageLabel = _resolveLanguageLabel(context, currentLanguageCode);
    final activePalette = ref.watch(appThemePaletteProvider);

    return Scaffold(
      backgroundColor: context.jyotigptTheme.surfaceBackground,
      appBar: _buildAppBar(context),
      body: SafeArea(
        child: ListView(
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.pagePadding,
            vertical: Spacing.pagePadding,
          ),
          children: [
            _buildDisplaySection(
              context,
              ref,
              themeMode,
              themeDescription,
              currentLanguageCode,
              languageLabel,
              settings,
              activePalette,
            ),
            const SizedBox(height: Spacing.xl),
            _buildQuickPillsSection(context, ref, settings),
            const SizedBox(height: Spacing.xl),
            _buildChatSection(context, ref, settings),
          ],
        ),
      ),
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
        AppLocalizations.of(context)!.appCustomization,
        style: AppTypography.headlineSmallStyle.copyWith(
          color: context.jyotigptTheme.textPrimary,
          fontWeight: FontWeight.w600,
        ),
      ),
      centerTitle: true,
    );
  }

  Widget _buildDisplaySection(
    BuildContext context,
    WidgetRef ref,
    ThemeMode themeMode,
    String themeDescription,
    String currentLanguageCode,
    String languageLabel,
    AppSettings settings,
    AppColorPalette palette,
  ) {
    final theme = context.jyotigptTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          AppLocalizations.of(context)!.display,
          style:
              theme.headingSmall?.copyWith(color: theme.textPrimary) ??
              TextStyle(color: theme.textPrimary, fontSize: 18),
        ),
        const SizedBox(height: Spacing.sm),
        _buildThemeSelector(context, ref, themeMode, themeDescription),
        const SizedBox(height: Spacing.md),
        _buildPaletteSelector(context, ref, palette),
        const SizedBox(height: Spacing.md),
        _CustomizationTile(
          leading: _buildIconBadge(
            context,
            UiUtils.platformIcon(
              ios: CupertinoIcons.globe,
              android: Icons.language,
            ),
            color: theme.buttonPrimary,
          ),
          title: AppLocalizations.of(context)!.appLanguage,
          subtitle: languageLabel,
          onTap: () async {
            final selected = await _showLanguageSelector(
              context,
              currentLanguageCode,
            );
            if (selected == null) return;
            if (selected == 'system') {
              await ref.read(appLocaleProvider.notifier).setLocale(null);
            } else {
              await ref
                  .read(appLocaleProvider.notifier)
                  .setLocale(Locale(selected));
            }
          },
        ),
      ],
    );
  }

  Widget _buildThemeSelector(
    BuildContext context,
    WidgetRef ref,
    ThemeMode themeMode,
    String themeDescription,
  ) {
    final theme = context.jyotigptTheme;

    return JyotiGPTCard(
      padding: const EdgeInsets.all(Spacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildIconBadge(
                context,
                UiUtils.platformIcon(
                  ios: CupertinoIcons.moon_stars,
                  android: Icons.dark_mode,
                ),
                color: theme.buttonPrimary,
              ),
              const SizedBox(width: Spacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      AppLocalizations.of(context)!.darkMode,
                      style: theme.bodyMedium?.copyWith(
                        color: theme.textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    Text(
                      themeDescription,
                      style: theme.bodySmall?.copyWith(
                        color: theme.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: Spacing.md),
          Wrap(
            spacing: Spacing.sm,
            runSpacing: Spacing.sm,
            children: [
              _buildThemeChip(
                context,
                ref,
                mode: ThemeMode.system,
                isSelected: themeMode == ThemeMode.system,
                label: AppLocalizations.of(context)!.system,
                icon: UiUtils.platformIcon(
                  ios: CupertinoIcons.sparkles,
                  android: Icons.auto_mode,
                ),
              ),
              _buildThemeChip(
                context,
                ref,
                mode: ThemeMode.light,
                isSelected: themeMode == ThemeMode.light,
                label: AppLocalizations.of(context)!.themeLight,
                icon: UiUtils.platformIcon(
                  ios: CupertinoIcons.sun_max,
                  android: Icons.light_mode,
                ),
              ),
              _buildThemeChip(
                context,
                ref,
                mode: ThemeMode.dark,
                isSelected: themeMode == ThemeMode.dark,
                label: AppLocalizations.of(context)!.themeDark,
                icon: UiUtils.platformIcon(
                  ios: CupertinoIcons.moon_fill,
                  android: Icons.dark_mode,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPaletteSelector(
    BuildContext context,
    WidgetRef ref,
    AppColorPalette activePalette,
  ) {
    final theme = context.jyotigptTheme;
    final palettes = AppColorPalettes.all;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          AppLocalizations.of(context)!.themePalette,
          style:
              theme.bodyLarge?.copyWith(
                color: theme.textPrimary,
                fontWeight: FontWeight.w600,
              ) ??
              TextStyle(color: theme.textPrimary, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: Spacing.xs),
        Text(
          AppLocalizations.of(context)!.themePaletteDescription,
          style:
              theme.bodySmall?.copyWith(color: theme.textSecondary) ??
              TextStyle(color: theme.textSecondary),
        ),
        const SizedBox(height: Spacing.sm),
        JyotiGPTCard(
          padding: const EdgeInsets.all(Spacing.md),
          child: Column(
            children: [
              for (final palette in palettes)
                _PaletteOption(
                  palette: palette,
                  activeId: activePalette.id,
                  onSelect: () => ref
                      .read(appThemePaletteProvider.notifier)
                      .setPalette(palette.id),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildThemeChip(
    BuildContext context,
    WidgetRef ref, {
    required ThemeMode mode,
    required bool isSelected,
    required String label,
    required IconData icon,
  }) {
    return JyotiGPTChip(
      label: label,
      icon: icon,
      isSelected: isSelected,
      onTap: () => ref.read(appThemeModeProvider.notifier).setTheme(mode),
    );
  }

  Widget _buildQuickPillsSection(
    BuildContext context,
    WidgetRef ref,
    AppSettings settings,
  ) {
    final theme = context.jyotigptTheme;
    final selectedRaw = ref.watch(
      appSettingsProvider.select((s) => s.quickPills),
    );
    final toolsAsync = ref.watch(toolsListProvider);
    final tools = toolsAsync.maybeWhen(
      data: (value) => value,
      orElse: () => const <Tool>[],
    );
    final allowed = <String>{'web', 'image', ...tools.map((t) => t.id)};

    final selected = selectedRaw
        .where((id) => allowed.contains(id))
        .take(2)
        .toList();
    if (selected.length != selectedRaw.length) {
      Future.microtask(
        () => ref.read(appSettingsProvider.notifier).setQuickPills(selected),
      );
    }

    final selectedCount = selected.length;

    Future<void> toggle(String id) async {
      final next = List<String>.from(selected);
      if (next.contains(id)) {
        next.remove(id);
      } else {
        if (next.length >= 2) return;
        next.add(id);
      }
      await ref.read(appSettingsProvider.notifier).setQuickPills(next);
    }

    List<Widget> buildToolChips() {
      return tools.map((tool) {
        final isSelected = selected.contains(tool.id);
        final canSelect = selectedCount < 2 || isSelected;
        return JyotiGPTChip(
          label: tool.name,
          icon: Icons.extension,
          isSelected: isSelected,
          onTap: canSelect ? () => toggle(tool.id) : null,
        );
      }).toList();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          AppLocalizations.of(context)!.onboardQuickTitle,
          style:
              theme.headingSmall?.copyWith(color: theme.textPrimary) ??
              TextStyle(color: theme.textPrimary, fontSize: 18),
        ),
        const SizedBox(height: Spacing.sm),
        JyotiGPTCard(
          padding: const EdgeInsets.all(Spacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildIconBadge(
                    context,
                    UiUtils.platformIcon(
                      ios: CupertinoIcons.bolt,
                      android: Icons.flash_on,
                    ),
                    color: theme.buttonPrimary,
                  ),
                  const SizedBox(width: Spacing.md),
                  Expanded(
                    child: Text(
                      AppLocalizations.of(context)!.quickActionsDescription,
                      style: theme.bodySmall?.copyWith(
                        color: theme.textSecondary,
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: selected.isEmpty
                        ? null
                        : () => ref
                              .read(appSettingsProvider.notifier)
                              .setQuickPills(const []),
                    child: Text(AppLocalizations.of(context)!.clear),
                  ),
                ],
              ),
              const SizedBox(height: Spacing.md),
              Wrap(
                spacing: Spacing.sm,
                runSpacing: Spacing.sm,
                children: [
                  JyotiGPTChip(
                    label: AppLocalizations.of(context)!.web,
                    icon: Platform.isIOS ? CupertinoIcons.search : Icons.search,
                    isSelected: selected.contains('web'),
                    onTap: (selectedCount < 2 || selected.contains('web'))
                        ? () => toggle('web')
                        : null,
                  ),
                  JyotiGPTChip(
                    label: AppLocalizations.of(context)!.imageGen,
                    icon: Platform.isIOS ? CupertinoIcons.photo : Icons.image,
                    isSelected: selected.contains('image'),
                    onTap: (selectedCount < 2 || selected.contains('image'))
                        ? () => toggle('image')
                        : null,
                  ),
                  ...buildToolChips(),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildChatSection(
    BuildContext context,
    WidgetRef ref,
    AppSettings settings,
  ) {
    final theme = context.jyotigptTheme;
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.chatSettings,
          style:
              theme.headingSmall?.copyWith(color: theme.textPrimary) ??
              TextStyle(color: theme.textPrimary, fontSize: 18),
        ),
        const SizedBox(height: Spacing.sm),
        _CustomizationTile(
          leading: _buildIconBadge(
            context,
            Platform.isIOS ? CupertinoIcons.paperplane : Icons.keyboard_return,
            color: theme.buttonPrimary,
          ),
          title: l10n.sendOnEnter,
          subtitle: l10n.sendOnEnterDescription,
          trailing: Switch.adaptive(
            value: settings.sendOnEnter,
            onChanged: (value) =>
                ref.read(appSettingsProvider.notifier).setSendOnEnter(value),
          ),
          showChevron: false,
          onTap: () => ref
              .read(appSettingsProvider.notifier)
              .setSendOnEnter(!settings.sendOnEnter),
        ),
      ],
    );
  }

  String _resolveLanguageLabel(BuildContext context, String code) {
    switch (code) {
      case 'en':
        return AppLocalizations.of(context)!.english;
      case 'de':
        return AppLocalizations.of(context)!.deutsch;
      case 'fr':
        return AppLocalizations.of(context)!.francais;
      case 'it':
        return AppLocalizations.of(context)!.italiano;
      default:
        return AppLocalizations.of(context)!.system;
    }
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

  Future<String?> _showLanguageSelector(BuildContext context, String current) {
    return showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => Container(
        decoration: BoxDecoration(
          color: context.jyotigptTheme.surfaceBackground,
          borderRadius: const BorderRadius.vertical(
            top: Radius.circular(AppBorderRadius.modal),
          ),
          boxShadow: JyotiGPTShadows.modal(context),
        ),
        child: SafeArea(
          top: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: Spacing.sm),
              ListTile(
                title: Text(AppLocalizations.of(context)!.system),
                trailing: current == 'system' ? const Icon(Icons.check) : null,
                onTap: () => Navigator.pop(context, 'system'),
              ),
              ListTile(
                title: Text(AppLocalizations.of(context)!.english),
                trailing: current == 'en' ? const Icon(Icons.check) : null,
                onTap: () => Navigator.pop(context, 'en'),
              ),
              ListTile(
                title: Text(AppLocalizations.of(context)!.deutsch),
                trailing: current == 'de' ? const Icon(Icons.check) : null,
                onTap: () => Navigator.pop(context, 'de'),
              ),
              ListTile(
                title: Text(AppLocalizations.of(context)!.francais),
                trailing: current == 'fr' ? const Icon(Icons.check) : null,
                onTap: () => Navigator.pop(context, 'fr'),
              ),
              ListTile(
                title: Text(AppLocalizations.of(context)!.italiano),
                trailing: current == 'it' ? const Icon(Icons.check) : null,
                onTap: () => Navigator.pop(context, 'it'),
              ),
              const SizedBox(height: Spacing.sm),
            ],
          ),
        ),
      ),
    );
  }
}

class _PaletteOption extends StatelessWidget {
  const _PaletteOption({
    required this.palette,
    required this.activeId,
    required this.onSelect,
  });

  final AppColorPalette palette;
  final String activeId;
  final VoidCallback onSelect;

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;
    final isSelected = palette.id == activeId;
    final previewColors =
        palette.preview ??
        <Color>[
          palette.light.primary,
          palette.light.secondary,
          palette.dark.primary,
        ];

    return InkWell(
      onTap: onSelect,
      borderRadius: BorderRadius.circular(AppBorderRadius.small),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: Spacing.sm),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              isSelected ? Icons.radio_button_checked : Icons.radio_button_off,
              color: isSelected ? theme.buttonPrimary : theme.iconSecondary,
              size: IconSize.small,
            ),
            const SizedBox(width: Spacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: Text(
                          palette.label,
                          style: theme.bodyMedium?.copyWith(
                            color: theme.textPrimary,
                            fontWeight: isSelected
                                ? FontWeight.w600
                                : FontWeight.w500,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (isSelected)
                        Padding(
                          padding: const EdgeInsets.only(left: Spacing.xs),
                          child: Icon(
                            Icons.check_circle,
                            color: theme.buttonPrimary,
                            size: IconSize.small,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: Spacing.xxs),
                  Text(
                    palette.description,
                    style:
                        theme.bodySmall?.copyWith(color: theme.textSecondary) ??
                        TextStyle(color: theme.textSecondary),
                  ),
                  const SizedBox(height: Spacing.xs),
                  Row(
                    children: [
                      for (final color in previewColors)
                        _PaletteColorDot(color: color),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PaletteColorDot extends StatelessWidget {
  const _PaletteColorDot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;
    return Container(
      margin: const EdgeInsets.only(right: Spacing.xs),
      width: 18,
      height: 18,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(
          color: theme.dividerColor.withValues(alpha: 0.3),
          width: BorderWidth.thin,
        ),
      ),
    );
  }
}

class _CustomizationTile extends StatelessWidget {
  const _CustomizationTile({
    required this.leading,
    required this.title,
    required this.subtitle,
    this.trailing,
    this.onTap,
    this.showChevron = true,
  });

  final Widget leading;
  final String title;
  final String subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final bool showChevron;

  @override
  Widget build(BuildContext context) {
    final theme = context.jyotigptTheme;
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
                    color: theme.textPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: Spacing.xs),
                Text(
                  subtitle,
                  style: theme.bodySmall?.copyWith(color: theme.textSecondary),
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
