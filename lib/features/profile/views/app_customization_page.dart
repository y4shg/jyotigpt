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
    
    // Only allow tool IDs, no 'web' or 'image'
    final allowed = <String>{...tools.map((t) => t.id)};

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
                children: buildToolChips(),
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
    final l10n = AppLocalizations.of(context)!;
    switch (code) {
      // Indian Languages (13)
      case 'hi': return l10n.hindi;
      case 'bn': return l10n.bengali;
      case 'ta': return l10n.tamil;
      case 'te': return l10n.telugu;
      case 'mr': return l10n.marathi;
      case 'gu': return l10n.gujarati;
      case 'kn': return l10n.kannada;
      case 'ml': return l10n.malayalam;
      case 'pa': return l10n.punjabi;
      case 'ur': return l10n.urdu;
      case 'ne': return l10n.nepali;
      case 'as': return l10n.assamese;
      case 'or': return l10n.odia;
      // European Languages (24)
      case 'en': return l10n.english;
      case 'es': return l10n.spanish;
      case 'fr': return l10n.francais;
      case 'de': return l10n.deutsch;
      case 'it': return l10n.italiano;
      case 'pt': return l10n.portuguese;
      case 'nl': return l10n.dutch;
      case 'pl': return l10n.polish;
      case 'ru': return l10n.russian;
      case 'uk': return l10n.ukrainian;
      case 'sv': return l10n.swedish;
      case 'da': return l10n.danish;
      case 'no': return l10n.norwegian;
      case 'fi': return l10n.finnish;
      case 'cs': return l10n.czech;
      case 'hu': return l10n.hungarian;
      case 'ro': return l10n.romanian;
      case 'el': return l10n.greek;
      case 'sk': return l10n.slovak;
      case 'sr': return l10n.serbian;
      case 'hr': return l10n.croatian;
      case 'bg': return l10n.bulgarian;
      // Asia-Pacific / Middle East / Africa (11)
      case 'zh-cn': return l10n.chineseSimplified;
      case 'zh-tw': return l10n.chineseTraditional;
      case 'ja': return l10n.japanese;
      case 'ko': return l10n.korean;
      case 'id': return l10n.indonesian;
      case 'vi': return l10n.vietnamese;
      case 'th': return l10n.thai;
      case 'ar': return l10n.arabic;
      case 'fa': return l10n.persian;
      case 'he': return l10n.hebrew;
      case 'sw': return l10n.swahili;
      // Americas (2)
      case 'es-MX': return l10n.spanishMexico;
      case 'pt-BR': return l10n.portugueseBrazil;
      default: return l10n.system;
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
    final l10n = AppLocalizations.of(context)!;
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
          child: ListView(
            shrinkWrap: true,
            children: [
              const SizedBox(height: Spacing.sm),
              _buildLanguageTile(context, current, 'system', l10n.system),
              // Indian Languages
              _buildLanguageTile(context, current, 'hi', l10n.hindi),
              _buildLanguageTile(context, current, 'bn', l10n.bengali),
              _buildLanguageTile(context, current, 'ta', l10n.tamil),
              _buildLanguageTile(context, current, 'te', l10n.telugu),
              _buildLanguageTile(context, current, 'mr', l10n.marathi),
              _buildLanguageTile(context, current, 'gu', l10n.gujarati),
              _buildLanguageTile(context, current, 'kn', l10n.kannada),
              _buildLanguageTile(context, current, 'ml', l10n.malayalam),
              _buildLanguageTile(context, current, 'pa', l10n.punjabi),
              _buildLanguageTile(context, current, 'ur', l10n.urdu),
              _buildLanguageTile(context, current, 'ne', l10n.nepali),
              _buildLanguageTile(context, current, 'as', l10n.assamese),
              _buildLanguageTile(context, current, 'or', l10n.odia),
              // European Languages
              _buildLanguageTile(context, current, 'en', l10n.english),
              _buildLanguageTile(context, current, 'es', l10n.spanish),
              _buildLanguageTile(context, current, 'fr', l10n.francais),
              _buildLanguageTile(context, current, 'de', l10n.deutsch),
              _buildLanguageTile(context, current, 'it', l10n.italiano),
              _buildLanguageTile(context, current, 'pt', l10n.portuguese),
              _buildLanguageTile(context, current, 'nl', l10n.dutch),
              _buildLanguageTile(context, current, 'pl', l10n.polish),
              _buildLanguageTile(context, current, 'ru', l10n.russian),
              _buildLanguageTile(context, current, 'uk', l10n.ukrainian),
              _buildLanguageTile(context, current, 'sv', l10n.swedish),
              _buildLanguageTile(context, current, 'da', l10n.danish),
              _buildLanguageTile(context, current, 'no', l10n.norwegian),
              _buildLanguageTile(context, current, 'fi', l10n.finnish),
              _buildLanguageTile(context, current, 'cs', l10n.czech),
              _buildLanguageTile(context, current, 'hu', l10n.hungarian),
              _buildLanguageTile(context, current, 'ro', l10n.romanian),
              _buildLanguageTile(context, current, 'el', l10n.greek),
              _buildLanguageTile(context, current, 'sk', l10n.slovak),
              _buildLanguageTile(context, current, 'sr', l10n.serbian),
              _buildLanguageTile(context, current, 'hr', l10n.croatian),
              _buildLanguageTile(context, current, 'bg', l10n.bulgarian),
              // Asia-Pacific / Middle East / Africa
              _buildLanguageTile(context, current, 'zh-cn', l10n.chineseSimplified),
              _buildLanguageTile(context, current, 'zh-tw', l10n.chineseTraditional),
              _buildLanguageTile(context, current, 'ja', l10n.japanese),
              _buildLanguageTile(context, current, 'ko', l10n.korean),
              _buildLanguageTile(context, current, 'id', l10n.indonesian),
              _buildLanguageTile(context, current, 'vi', l10n.vietnamese),
              _buildLanguageTile(context, current, 'th', l10n.thai),
              _buildLanguageTile(context, current, 'ar', l10n.arabic),
              _buildLanguageTile(context, current, 'fa', l10n.persian),
              _buildLanguageTile(context, current, 'he', l10n.hebrew),
              _buildLanguageTile(context, current, 'sw', l10n.swahili),
              // Americas
              _buildLanguageTile(context, current, 'es-MX', l10n.spanishMexico),
              _buildLanguageTile(context, current, 'pt-BR', l10n.portugueseBrazil),
              const SizedBox(height: Spacing.sm),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLanguageTile(BuildContext context, String current, String code, String label) {
    return ListTile(
      title: Text(label),
      trailing: current == code ? const Icon(Icons.check) : null,
      onTap: () => Navigator.pop(context, code),
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