import 'dart:async';
import 'dart:developer' as developer;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/widgets/error_boundary.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'core/providers/app_providers.dart';
import 'core/persistence/hive_bootstrap.dart';
import 'core/persistence/persistence_migrator.dart';
import 'core/persistence/persistence_providers.dart';
import 'core/router/app_router.dart';
import 'features/auth/providers/unified_auth_providers.dart';
import 'core/auth/auth_state_manager.dart';
import 'core/utils/debug_logger.dart';
import 'core/utils/system_ui_style.dart';

import 'package:jyotigpt/l10n/app_localizations.dart';
import 'core/services/share_receiver_service.dart';
import 'core/providers/app_startup_providers.dart';

developer.TimelineTask? _startupTimeline;

void main() {
  runZonedGuarded(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      // Global error handlers
      FlutterError.onError = (FlutterErrorDetails details) {
        DebugLogger.error(
          'flutter-error',
          scope: 'app/framework',
          error: details.exception,
        );
        final stack = details.stack;
        if (stack != null) {
          debugPrintStack(stackTrace: stack);
        }
      };
      WidgetsBinding.instance.platformDispatcher.onError = (error, stack) {
        DebugLogger.error(
          'platform-error',
          scope: 'app/platform',
          error: error,
          stackTrace: stack,
        );
        debugPrintStack(stackTrace: stack);
        return true;
      };

      // Start startup timeline instrumentation
      _startupTimeline = developer.TimelineTask();
      _startupTimeline!.start('app_startup');
      _startupTimeline!.instant('bindings_initialized');

      // Defer edge-to-edge mode to post-frame to avoid impacting first paint
      WidgetsBinding.instance.addPostFrameCallback((_) {
        // ignore: discarded_futures
        SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
        _startupTimeline?.instant('edge_to_edge_enabled');
      });

      const secureStorage = FlutterSecureStorage(
        aOptions: AndroidOptions(
          encryptedSharedPreferences: true,
          sharedPreferencesName: 'jyotigpt_secure_prefs',
          preferencesKeyPrefix: 'jyotigpt_',
          resetOnError: false,
        ),
        iOptions: IOSOptions(
          accountName: 'jyotigpt_secure_storage',
          synchronizable: false,
        ),
      );
      _startupTimeline!.instant('secure_storage_ready');

      // Initialize Hive (now optimized with migration state caching)
      final hiveBoxes = await HiveBootstrap.instance.ensureInitialized();
      _startupTimeline!.instant('hive_ready');

      // Run migration check (now fast-pathed after first run)
      final migrator = PersistenceMigrator(hiveBoxes: hiveBoxes);
      await migrator.migrateIfNeeded();
      _startupTimeline!.instant('migration_complete');

      // Finish timeline after first frame paints
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _startupTimeline?.instant('first_frame_rendered');
        _startupTimeline?.finish();
        _startupTimeline = null;
      });

      runApp(
        ProviderScope(
          overrides: [
            secureStorageProvider.overrideWithValue(secureStorage),
            hiveBoxesProvider.overrideWithValue(hiveBoxes),
          ],
          child: const JyotiGPTApp(),
        ),
      );
      developer.Timeline.instantSync('runApp_called');
    },
    (error, stack) {
      DebugLogger.error(
        'zone-error',
        scope: 'app',
        error: error,
        stackTrace: stack,
      );
      debugPrintStack(stackTrace: stack);
    },
  );
}

class JyotiGPTApp extends ConsumerStatefulWidget {
  const JyotiGPTApp({super.key});

  @override
  ConsumerState<JyotiGPTApp> createState() => _JyotiGPTAppState();
}

class _JyotiGPTAppState extends ConsumerState<JyotiGPTApp> {
  Brightness? _lastAppliedOverlayBrightness;
  @override
  void initState() {
    super.initState();
    // Delay heavy provider initialization until after the first frame so the
    // initial paint stays responsive.
    WidgetsBinding.instance.addPostFrameCallback((_) => _initializeAppState());
  }

  void _initializeAppState() {
    DebugLogger.auth('init', scope: 'app');

    void queueInit(void Function() action, {Duration delay = Duration.zero}) {
      Future<void>.delayed(delay, () {
        if (!mounted) return;
        action();
      });
    }

    queueInit(() => ref.read(authStateManagerProvider));
    queueInit(
      () => ref.read(authApiIntegrationProvider),
      delay: const Duration(milliseconds: 16),
    );
    queueInit(
      () => ref.read(defaultModelAutoSelectionProvider),
      delay: const Duration(milliseconds: 24),
    );
    queueInit(
      () => ref.read(shareReceiverInitializerProvider),
      delay: const Duration(milliseconds: 32),
    );

    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(appStartupFlowProvider.notifier).start();
    });
  }

  @override
  void dispose() {
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final themeMode = ref.watch(appThemeModeProvider.select((mode) => mode));
    final router = ref.watch(goRouterProvider);
    final locale = ref.watch(appLocaleProvider);
    final lightTheme = ref.watch(appLightThemeProvider);
    final darkTheme = ref.watch(appDarkThemeProvider);

    return ErrorBoundary(
      child: MaterialApp.router(
        routerConfig: router,
        onGenerateTitle: (context) => AppLocalizations.of(context)!.appTitle,
        theme: lightTheme,
        darkTheme: darkTheme,
        themeMode: themeMode,
        debugShowCheckedModeBanner: false,
        locale: locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        localeListResolutionCallback: (deviceLocales, supported) {
          if (locale != null) return locale;
          if (deviceLocales == null || deviceLocales.isEmpty) {
            return supported.first;
          }
          for (final device in deviceLocales) {
            for (final loc in supported) {
              if (loc.languageCode == device.languageCode) return loc;
            }
          }
          return supported.first;
        },
        builder: (context, child) {
          final brightness = Theme.of(context).brightness;
          if (_lastAppliedOverlayBrightness != brightness) {
            _lastAppliedOverlayBrightness = brightness;
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (!mounted) return;
              applySystemUiOverlayStyleOnce(brightness: brightness);
            });
          }
          final mediaQuery = MediaQuery.of(context);
          return MediaQuery(
            data: mediaQuery.copyWith(
              textScaler: mediaQuery.textScaler.clamp(
                minScaleFactor: 1.0,
                maxScaleFactor: 3.0,
              ),
            ),
            child: child ?? const SizedBox.shrink(),
          );
        },
      ),
    );
  }
}
