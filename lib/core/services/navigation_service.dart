import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../shared/widgets/themed_dialogs.dart';

/// Service for handling navigation throughout the app.
///
/// With GoRouter in place, this class mostly provides convenient wrappers
/// around the global router so existing callers can trigger navigation
/// without directly depending on BuildContext.
class NavigationService {
  static final GlobalKey<NavigatorState> navigatorKey =
      GlobalKey<NavigatorState>(debugLabel: 'rootNavigator');

  static GoRouter? _router;

  static GoRouter get router {
    final router = _router;
    if (router == null) {
      throw StateError('GoRouter has not been attached to NavigationService.');
    }
    return router;
  }

  static void attachRouter(GoRouter router) {
    _router = router;
  }

  static NavigatorState? get navigator => navigatorKey.currentState;
  static BuildContext? get context => navigatorKey.currentContext;

  /// The current location reported by GoRouter.
  static String? get currentRoute {
    final router = _router;
    if (router == null) return null;
    return router.routeInformationProvider.value.uri.toString();
  }

  /// Navigate to a specific route path.
  static Future<void> navigateTo(String routeName) async {
    final router = _router;
    if (router == null) return;
    router.go(routeName);
  }

  /// Navigate back with an optional result payload.
  static void goBack<T>([T? result]) {
    final router = _router;
    if (router?.canPop() == true) {
      router!.pop(result);
    }
  }

  /// Check whether the router can pop the current route.
  static bool canGoBack() => _router?.canPop() ?? false;

  /// Show confirmation dialog before navigation.
  static Future<bool> confirmNavigation({
    required String title,
    required String message,
    String confirmText = 'Continue',
    String cancelText = 'Cancel',
  }) async {
    final ctx = context;
    if (ctx == null) return false;

    final result = await ThemedDialogs.confirm(
      ctx,
      title: title,
      message: message,
      confirmText: confirmText,
      cancelText: cancelText,
      barrierDismissible: false,
    );

    return result;
  }

  static Future<void> navigateToChat() => navigateTo(Routes.chat);
  static Future<void> navigateToLogin() => navigateTo(Routes.serverConnection);
  static Future<void> navigateToProfile() => navigateTo(Routes.profile);
  static Future<void> navigateToServerConnection() =>
      navigateTo(Routes.serverConnection);

  /// Clear navigation history. With GoRouter this becomes a simple go call.
  static void clearNavigationStack() {
    final router = _router;
    if (router == null) return;
    router.go(Routes.serverConnection);
  }
}

/// Route path definitions used across the app.
class Routes {
  static const String splash = '/splash';
  static const String chat = '/chat';
  static const String login = '/login';
  static const String serverConnection = '/server-connection';
  static const String connectionIssue = '/connection-issue';
  static const String authentication = '/authentication';
  static const String profile = '/profile';
  static const String appCustomization = '/profile/customization';
}

/// Friendly names for GoRouter routes to support context.pushNamed.
class RouteNames {
  static const String splash = 'splash';
  static const String chat = 'chat';
  static const String login = 'login';
  static const String serverConnection = 'server-connection';
  static const String connectionIssue = 'connection-issue';
  static const String authentication = 'authentication';
  static const String profile = 'profile';
  static const String appCustomization = 'app-customization';
}
