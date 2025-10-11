import 'package:flutter/material.dart';
import '../../../shared/theme/theme_extensions.dart';

class SplashLauncherPage extends StatelessWidget {
  const SplashLauncherPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.jyotigptTheme.surfaceBackground,
      body: Center(
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(
              context.jyotigptTheme.loadingIndicator,
            ),
          ),
        ),
      ),
    );
  }
}
