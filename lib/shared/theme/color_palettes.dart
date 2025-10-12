import 'package:flutter/material.dart';

@immutable
class AppPaletteTone {
  const AppPaletteTone({
    required this.primary,
    required this.secondary,
    required this.accent,
  });

  final Color primary;
  final Color secondary;
  final Color accent;
}

@immutable
class AppColorPalette {
  const AppColorPalette({
    required this.id,
    required this.label,
    required this.description,
    required this.light,
    required this.dark,
    this.preview,
  });

  final String id;
  final String label;
  final String description;
  final AppPaletteTone light;
  final AppPaletteTone dark;
  final List<Color>? preview;
}

@immutable
class AppPaletteThemeExtension
    extends ThemeExtension<AppPaletteThemeExtension> {
  const AppPaletteThemeExtension({required this.palette});

  final AppColorPalette palette;

  @override
  AppPaletteThemeExtension copyWith({AppColorPalette? palette}) {
    return AppPaletteThemeExtension(palette: palette ?? this.palette);
  }

  @override
  AppPaletteThemeExtension lerp(
    covariant ThemeExtension<AppPaletteThemeExtension>? other,
    double t,
  ) {
    if (other is! AppPaletteThemeExtension) return this;
    return t < 0.5 ? this : other;
  }
}

class AppColorPalettes {
  static const String defaultPaletteId = 'inner_fire';

  static const AppColorPalette innerFire = AppColorPalette(
    id: defaultPaletteId,
    label: 'Inner Fire',
    description: 'Radiant reds symbolizing the spark of divine intelligence.',
    light: AppPaletteTone(
      primary: Color(0xFFFF3131),
      secondary: Color(0xFFFF5252),
      accent: Color(0xFFFFA3A3),
    ),
    dark: AppPaletteTone(
      primary: Color(0xFFFF4C4C),
      secondary: Color(0xFFFF6B6B),
      accent: Color(0xFFFFB3B3),
    ),
    preview: [Color(0xFFFF3131), Color(0xFFFF5252), Color(0xFFFFA3A3)],
  );

  static const AppColorPalette emeraldRush = AppColorPalette(
    id: 'emerald_rush',
    label: 'Emerald Rush',
    description: 'High-contrast greens with calm highlights.',
    light: AppPaletteTone(
      primary: Color(0xFF0C7F48),
      secondary: Color(0xFF26A164),
      accent: Color(0xFF6DE0A4),
    ),
    dark: AppPaletteTone(
      primary: Color(0xFF40DD7F),
      secondary: Color(0xFF26A164),
      accent: Color(0xFF6DE0A4),
    ),
    preview: [Color(0xFF0C7F48), Color(0xFF26A164), Color(0xFF40DD7F)],
  );

  static const AppColorPalette azurePulse = AppColorPalette(
    id: 'azure_pulse',
    label: 'Azure Pulse',
    description: 'Electric blues with crisp highlights.',
    light: AppPaletteTone(
      primary: Color(0xFF1B64DA),
      secondary: Color(0xFF2E7AF0),
      accent: Color(0xFF6DA6FF),
    ),
    dark: AppPaletteTone(
      primary: Color(0xFF37C7FF),
      secondary: Color(0xFF2E7AF0),
      accent: Color(0xFF6DA6FF),
    ),
    preview: [Color(0xFF1B64DA), Color(0xFF2E7AF0), Color(0xFF37C7FF)],
  );

  static const AppColorPalette sunsetGlow = AppColorPalette(
    id: 'sunset_glow',
    label: 'Sunset Glow',
    description: 'Warm oranges for energetic interfaces.',
    light: AppPaletteTone(
      primary: Color(0xFFB83200),
      secondary: Color(0xFFE65100),
      accent: Color(0xFFFFA05B),
    ),
    dark: AppPaletteTone(
      primary: Color(0xFFFF8A00),
      secondary: Color(0xFFE65100),
      accent: Color(0xFFFFA05B),
    ),
    preview: [Color(0xFFB83200), Color(0xFFE65100), Color(0xFFFF8A00)],
  );

  static const List<AppColorPalette> all = [
    innerFire,
    emeraldRush,
    azurePulse,
    sunsetGlow,
  ];

  static AppColorPalette byId(String? id) {
    return all.firstWhere(
      (palette) => palette.id == id,
      orElse: () => innerFire,
    );
  }
}

extension AppColorPaletteX on AppColorPalette {
  AppPaletteTone toneFor(Brightness brightness) {
    return brightness == Brightness.dark ? dark : light;
  }

  Color primaryFor(Brightness brightness) {
    return toneFor(brightness).primary;
  }

  Color secondaryFor(Brightness brightness) {
    return toneFor(brightness).secondary;
  }

  Color accentFor(Brightness brightness) {
    return toneFor(brightness).accent;
  }
}
