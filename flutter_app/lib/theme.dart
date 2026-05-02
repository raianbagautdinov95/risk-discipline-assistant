import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  static const bg = Color(0xFF0A0B12);
  static const bgAlt = Color(0xFF0E1018);
  static const surface = Color(0xFF14171F);
  static const surfaceAlt = Color(0xFF1C2030);
  static const border = Color(0xFF252A3A);
  static const borderStrong = Color(0xFF353B52);

  static const textPrimary = Color(0xFFEAECEF);
  static const textSecondary = Color(0xFF9BA1B5);
  static const textMuted = Color(0xFF6A7088);

  static const primary = Color(0xFF7B7BFF);
  static const primaryDeep = Color(0xFF5B5BFF);
  static const success = Color(0xFF22C55E);
  static const successDim = Color(0xFF14532D);
  static const danger = Color(0xFFEF4444);
  static const dangerDim = Color(0xFF7F1D1D);
  static const warn = Color(0xFFF59E0B);
  static const warnDim = Color(0xFF78350F);
  static const info = Color(0xFF38BDF8);

  static const lBg = Color(0xFFF8F9FB);
  static const lSurface = Color(0xFFFFFFFF);
  static const lSurfaceAlt = Color(0xFFF1F3F7);
  static const lBorder = Color(0xFFE4E6EE);
  static const lTextPrimary = Color(0xFF111327);
  static const lTextSecondary = Color(0xFF565A75);
  static const lTextMuted = Color(0xFF8F94A8);
}

TextTheme _interTextTheme(TextTheme base) {
  return GoogleFonts.interTextTheme(base).copyWith(
    displayLarge:
        GoogleFonts.inter(fontWeight: FontWeight.w800, letterSpacing: -0.6),
    displayMedium:
        GoogleFonts.inter(fontWeight: FontWeight.w800, letterSpacing: -0.5),
    displaySmall:
        GoogleFonts.inter(fontWeight: FontWeight.w700, letterSpacing: -0.4),
    headlineLarge:
        GoogleFonts.inter(fontWeight: FontWeight.w700, letterSpacing: -0.3),
    headlineMedium:
        GoogleFonts.inter(fontWeight: FontWeight.w700, letterSpacing: -0.2),
    headlineSmall: GoogleFonts.inter(fontWeight: FontWeight.w700),
    titleLarge: GoogleFonts.inter(fontWeight: FontWeight.w700),
    titleMedium: GoogleFonts.inter(fontWeight: FontWeight.w600),
    titleSmall: GoogleFonts.inter(fontWeight: FontWeight.w500),
    labelLarge: GoogleFonts.inter(fontWeight: FontWeight.w600),
    bodyLarge: GoogleFonts.inter(fontWeight: FontWeight.w400, height: 1.5),
    bodyMedium: GoogleFonts.inter(fontWeight: FontWeight.w400, height: 1.5),
    bodySmall: GoogleFonts.inter(fontWeight: FontWeight.w400),
  );
}

ThemeData buildAppTheme({Brightness brightness = Brightness.dark}) {
  final isDark = brightness == Brightness.dark;
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    brightness: brightness,
    primary: AppColors.primary,
    surface: isDark ? AppColors.surface : AppColors.lSurface,
    error: AppColors.danger,
    onPrimary: Colors.white,
    onSurface: isDark ? AppColors.textPrimary : AppColors.lTextPrimary,
  );

  final base = ThemeData(brightness: brightness, useMaterial3: true);
  final textTheme = _interTextTheme(base.textTheme).apply(
    bodyColor: isDark ? AppColors.textPrimary : AppColors.lTextPrimary,
    displayColor: isDark ? AppColors.textPrimary : AppColors.lTextPrimary,
  );

  final bg = isDark ? AppColors.bg : AppColors.lBg;
  final surface = isDark ? AppColors.surface : AppColors.lSurface;
  final border = isDark ? AppColors.border : AppColors.lBorder;
  final textSecondary =
      isDark ? AppColors.textSecondary : AppColors.lTextSecondary;
  final textMuted = isDark ? AppColors.textMuted : AppColors.lTextMuted;

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: bg,
    textTheme: textTheme,

    appBarTheme: AppBarTheme(
      backgroundColor: bg.withValues(alpha: 0.6),
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: textTheme.titleMedium?.copyWith(
        fontSize: 16,
        letterSpacing: -0.1,
      ),
      iconTheme: IconThemeData(
        color: isDark ? AppColors.textPrimary : AppColors.lTextPrimary,
      ),
    ),

    cardTheme: CardThemeData(
      color: surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: border, width: 1),
        borderRadius: BorderRadius.circular(14),
      ),
    ),

    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: surface,
      hintStyle: TextStyle(color: textMuted),
      labelStyle: TextStyle(color: textSecondary),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
    ),

    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle:
            textTheme.labelLarge?.copyWith(fontSize: 14, letterSpacing: 0.1),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: AppColors.primary),
    ),

    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: AppColors.primary,
      foregroundColor: Colors.white,
    ),

    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: surface.withValues(alpha: 0.85),
      surfaceTintColor: Colors.transparent,
      indicatorColor: AppColors.primary.withValues(alpha: 0.18),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return textTheme.labelSmall?.copyWith(
          fontSize: 11,
          fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
          color: selected ? AppColors.primary : textSecondary,
        );
      }),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return IconThemeData(
          color: selected ? AppColors.primary : textSecondary,
          size: 22,
        );
      }),
      height: 72,
    ),

    snackBarTheme: SnackBarThemeData(
      backgroundColor: isDark ? AppColors.surfaceAlt : AppColors.lSurface,
      contentTextStyle: TextStyle(
        color: isDark ? AppColors.textPrimary : AppColors.lTextPrimary,
      ),
      behavior: SnackBarBehavior.floating,
    ),

    dividerTheme: DividerThemeData(color: border, thickness: 1),
    iconTheme: IconThemeData(color: textSecondary),
  );
}
