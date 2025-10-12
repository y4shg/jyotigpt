import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:jyotigpt/l10n/app_localizations.dart';

import '../../../core/providers/app_providers.dart';
import '../../../core/utils/user_display_name.dart';
import '../../../shared/theme/theme_extensions.dart';
import '../../../shared/widgets/sheet_handle.dart';
import '../../auth/providers/unified_auth_providers.dart';

class OnboardingSheet extends ConsumerStatefulWidget {
  const OnboardingSheet({super.key});

  @override
  ConsumerState<OnboardingSheet> createState() => _OnboardingSheetState();
}

class _OnboardingSheetState extends ConsumerState<OnboardingSheet> {
  final PageController _controller = PageController();
  int _index = 0;

  void _next(int pageCount) {
    if (_index < pageCount - 1) {
      _controller.nextPage(
        duration: AnimationDuration.fast,
        curve: AnimationCurves.easeInOut,
      );
    } else {
      Navigator.pop(context);
    }
  }

  List<_OnboardingPage> _buildPages(
    AppLocalizations l10n,
    String greetingName,
  ) {
    return [
      _OnboardingPage(
        title: l10n.onboardStartTitle(greetingName),
        subtitle: l10n.onboardStartSubtitle,
        icon: CupertinoIcons.chat_bubble_2,
        bullets: [l10n.onboardStartBullet1, l10n.onboardStartBullet2],
      ),
      _OnboardingPage(
        title: l10n.onboardAttachTitle,
        subtitle: l10n.onboardAttachSubtitle,
        icon: CupertinoIcons.doc_on_doc,
        bullets: [l10n.onboardAttachBullet1, l10n.onboardAttachBullet2],
      ),
      _OnboardingPage(
        title: l10n.onboardSpeakTitle,
        subtitle: l10n.onboardSpeakSubtitle,
        icon: CupertinoIcons.mic_fill,
        bullets: [l10n.onboardSpeakBullet1, l10n.onboardSpeakBullet2],
      ),
      _OnboardingPage(
        title: l10n.onboardQuickTitle,
        subtitle: l10n.onboardQuickSubtitle,
        icon: CupertinoIcons.line_horizontal_3,
        bullets: [l10n.onboardQuickBullet1, l10n.onboardQuickBullet2],
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final height = MediaQuery.of(context).size.height;
    final l10n = AppLocalizations.of(context)!;
    final currentUserAsync = ref.watch(currentUserProvider);
    final userFromProfile = currentUserAsync.maybeWhen(
      data: (user) => user,
      orElse: () => null,
    );
    final authUser = ref.watch(currentUserProvider2);
    final user = userFromProfile ?? authUser;
    final greetingName = deriveUserDisplayName(user);
    final pages = _buildPages(l10n, greetingName);
    final pageCount = pages.length;
    return Container(
      height: height * 0.7,
      decoration: BoxDecoration(
        color: context.jyotigptTheme.surfaceBackground,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(AppBorderRadius.modal),
        ),
        boxShadow: JyotiGPTShadows.modal(context),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(Spacing.lg),
          child: Column(
            children: [
              // Handle bar (standardized)
              const SheetHandle(),

              Expanded(
                child: PageView.builder(
                  controller: _controller,
                  itemCount: pageCount,
                  onPageChanged: (i) => setState(() => _index = i),
                  itemBuilder: (context, i) {
                    final page = pages[i];
                    final content = _IllustratedPage(page: page);
                    // Ensure content can scroll vertically when space is tight,
                    // while keeping it centered when there is enough space.
                    return LayoutBuilder(
                      builder: (context, constraints) {
                        final centered = ConstrainedBox(
                          constraints: BoxConstraints(
                            minHeight: constraints.maxHeight,
                          ),
                          child: Center(child: content),
                        );
                        return SingleChildScrollView(
                          physics: const ClampingScrollPhysics(),
                          child: centered,
                        );
                      },
                    );
                  },
                ),
              ),

              const SizedBox(height: Spacing.md),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(pageCount, (i) {
                  final active = i == _index;
                  return AnimatedContainer(
                    duration: AnimationDuration.fast,
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    height: 6,
                    width: active ? 20 : 6,
                    decoration: BoxDecoration(
                      color: active
                          ? context.jyotigptTheme.buttonPrimary
                          : context.jyotigptTheme.dividerColor,
                      borderRadius: BorderRadius.circular(
                        AppBorderRadius.badge,
                      ),
                    ),
                  );
                }),
              ),

              const SizedBox(height: Spacing.lg),
              Row(
                children: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: Text(
                      l10n.skip,
                      style: TextStyle(
                        color: context.jyotigptTheme.textSecondary,
                      ),
                    ),
                  ),
                  const Spacer(),
                  FilledButton(
                    onPressed: () => _next(pageCount),
                    style: FilledButton.styleFrom(
                      backgroundColor: context.jyotigptTheme.buttonPrimary,
                      foregroundColor: context.jyotigptTheme.buttonPrimaryText,
                      padding: const EdgeInsets.symmetric(
                        horizontal: Spacing.lg,
                        vertical: Spacing.sm,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(
                          AppBorderRadius.button,
                        ),
                      ),
                    ),
                    child: Text(
                      _index == pageCount - 1 ? l10n.done : l10n.next,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _OnboardingPage {
  final String title;
  final String subtitle;
  final IconData icon;
  final List<String>? bullets;
  const _OnboardingPage({
    required this.title,
    required this.subtitle,
    required this.icon,
    this.bullets,
  });
}

class _IllustratedPage extends StatelessWidget {
  final _OnboardingPage page;
  const _IllustratedPage({required this.page});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        // Inner Fire blob illustration
        SizedBox(
          height: 160,
          child: Stack(
            alignment: Alignment.center,
            children: [
              Positioned(top: 10, left: 24, child: _blob(context, 90, 0.18)),
              Positioned(
                bottom: 0,
                right: 16,
                child: _blob(context, 130, 0.12),
              ),
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: context.jyotigptTheme.buttonPrimary,
                  borderRadius: BorderRadius.circular(AppBorderRadius.avatar),
                  boxShadow: JyotiGPTShadows.glow(context),
                ),
                child: Icon(page.icon, color: context.jyotigptTheme.textInverse),
              ).animate().scale(duration: AnimationDuration.fast),
            ],
          ),
        ),
        const SizedBox(height: Spacing.lg),
        Text(
          page.title,
          style: TextStyle(
            fontSize: AppTypography.headlineMedium,
            fontWeight: FontWeight.w700,
            color: context.jyotigptTheme.textPrimary,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          page.subtitle,
          style: TextStyle(
            fontSize: AppTypography.bodyLarge,
            color: context.jyotigptTheme.textSecondary,
          ),
          textAlign: TextAlign.center,
        ),
        if (page.bullets != null && page.bullets!.isNotEmpty) ...[
          const SizedBox(height: Spacing.md),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: page.bullets!
                .map(
                  (b) => Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: Spacing.lg,
                      vertical: 4,
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          margin: const EdgeInsets.only(top: 8, right: 8),
                          decoration: BoxDecoration(
                            color: context.jyotigptTheme.buttonPrimary,
                            shape: BoxShape.circle,
                          ),
                        ),
                        Expanded(
                          child: Text(
                            b,
                            style: TextStyle(
                              color: context.jyotigptTheme.textSecondary,
                              fontSize: AppTypography.bodyMedium,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ],
    );
  }

  Widget _blob(BuildContext context, double size, double alpha) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: context.jyotigptTheme.buttonPrimary.withValues(alpha: alpha),
        boxShadow: JyotiGPTShadows.glow(context),
      ),
    );
  }
}
