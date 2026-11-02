import 'package:flutter/material.dart';

class AppTheme {
  // Brand & Aesthetic Palette (2025 Modern Healthcare Interexy Theme)
  static const Color obsidianNavy = Color(0xFF101524);     // Deep midnight black/navy from reference UI
  static const Color accentBlue = Color(0xFF2563EB);       // Modern vibrant medical blue
  static const Color primaryTeal = Color(0xFF101524);      // Default primary action color (Obsidian)
  static const Color primaryDark = Color(0xFF090D16);
  static const Color primaryLight = Color(0xFFD6E8FE);     // Soft pastel sky blue
  static const Color backgroundSlate = Color(0xFFEBF4FE);  // Airy soft baby-blue canvas
  static const Color cardSurface = Colors.white;
  static const Color textDark = Color(0xFF101524);
  static const Color textMuted = Color(0xFF64748B);

  // Interexy 2025 Signature Pastel Accents
  static const Color pastelBlue = Color(0xFFD6E8FE);      // Soft sky blue card/pill
  static const Color pastelMint = Color(0xFFE2F7D8);      // Soft pistachio mint card/pill
  static const Color pastelPeach = Color(0xFFFEF0D6);     // Soft buttercup peach card/pill
  static const Color pastelAqua = Color(0xFFBAE0FD);      // Soft aqua card/pill
  static const Color cardBorderColor = Color(0xFFE2EDFB);

  // Triage Tier Colors (Harmonized with modern pastel theme)
  static const Color tierLow = Color(0xFF10B981);       // Emerald Green
  static const Color tierModerate = Color(0xFFF59E0B);  // Amber Gold
  static const Color tierHigh = Color(0xFFEA580C);      // Vivid Orange
  static const Color tierUrgent = Color(0xFFDC2626);    // Crimson Red
  static const Color tierHighRisk = Color(0xFF7C3AED);  // Deep Violet

  static Color getTierColor(String tier) {
    switch (tier.toUpperCase()) {
      case 'URGENT':
        return tierUrgent;
      case 'HIGH':
        return tierHigh;
      case 'HIGH_RISK_SCREENING':
        return tierHighRisk;
      case 'MODERATE':
        return tierModerate;
      case 'LOW':
      default:
        return tierLow;
    }
  }

  static ThemeData lightTheme = ThemeData(
    useMaterial3: true,
    fontFamily: 'Roboto',
    colorScheme: ColorScheme.fromSeed(
      seedColor: accentBlue,
      primary: obsidianNavy,
      secondary: accentBlue,
      surface: cardSurface,
    ),
    scaffoldBackgroundColor: backgroundSlate,
    appBarTheme: const AppBarTheme(
      backgroundColor: backgroundSlate,
      foregroundColor: textDark,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: true,
      iconTheme: IconThemeData(color: textDark),
      titleTextStyle: TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.bold,
        color: textDark,
        letterSpacing: 0.2,
      ),
    ),
    cardTheme: CardThemeData(
      color: cardSurface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
        side: const BorderSide(color: cardBorderColor, width: 1.2),
      ),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: obsidianNavy,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(30), // Sleek pill/capsule
        ),
        textStyle: const TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.bold,
          letterSpacing: 0.3,
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: obsidianNavy,
        side: const BorderSide(color: Color(0xFFCBD5E1), width: 1.5),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 15),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(30),
        ),
        textStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: cardBorderColor),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: cardBorderColor),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: accentBlue, width: 2),
      ),
    ),
  );
}
