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
  static const String defaultPaletteId = 'aurora_violet';

  static const AppColorPalette auroraViolet = AppColorPalette(
    id: defaultPaletteId,
    label: 'Aurora Violet',
    description: 'Bold purples inspired by aurora skies.',
    light: AppPaletteTone(
      primary: Color(0xFFA420FF),
      secondary: Color(0xFFB058FF),
      accent: Color(0xFFD9A5FF),
    ),
    dark: AppPaletteTone(
      primary: Color(0xFF9500FF),
      secondary: Color(0xFFC773FF),
      accent: Color(0xFFE3BDFF),
    ),
    preview: [Color(0xFF9500FF), Color(0xFFA420FF), Color(0xFFB058FF)],
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
    auroraViolet,
    emeraldRush,
    azurePulse,
    sunsetGlow,
  ];

  static AppColorPalette byId(String? id) {
    return all.firstWhere(
      (palette) => palette.id == id,
      orElse: () => auroraViolet,
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
