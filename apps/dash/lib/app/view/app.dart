import 'package:dash_support/chat/chat.dart';
import 'package:chat_repository/chat_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// Very Good Ventures' primary brand color.
const vgvBlue = Color(0xFF2A48DE);

/// Very Good Ventures' white, for text on dark, clean backgrounds.
const vgvWhite = Color(0xFFFFFFFF);

/// Very Good Ventures' navy, for dark backgrounds and gradient anchors.
const vgvNavy = Color(0xFF0A1530);

/// Very Good Ventures' black, for body text.
const vgvBlack = Color(0xFF232326);

class App extends StatelessWidget {
  const App({required this.chatRepository, super.key});

  final ChatRepository chatRepository;

  @override
  Widget build(BuildContext context) {
    return RepositoryProvider.value(
      value: chatRepository,
      child: MaterialApp(
        title: 'Dash support',
        theme: _buildTheme(Brightness.light),
        darkTheme: _buildTheme(Brightness.dark),
        home: const ChatPage(),
      ),
    );
  }
}

ThemeData _buildTheme(Brightness brightness) {
  final isDark = brightness == Brightness.dark;
  final colorScheme = ColorScheme.fromSeed(
    seedColor: vgvBlue,
    brightness: brightness,
  ).copyWith(
    primary: vgvBlue,
    onPrimary: vgvWhite,
    surface: isDark ? vgvNavy : vgvWhite,
    onSurface: isDark ? vgvWhite : vgvBlack,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: isDark ? vgvNavy : vgvWhite,
    appBarTheme: AppBarTheme(
      backgroundColor: isDark ? vgvNavy : vgvWhite,
      foregroundColor: colorScheme.onSurface,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(
        color: colorScheme.onSurface,
        fontSize: 20,
        fontWeight: FontWeight.w700,
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: isDark ? const Color(0xFF141B3D) : const Color(0xFFF2F3FA),
      contentPadding: const EdgeInsets.symmetric(
        horizontal: 20,
        vertical: 14,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(28),
        borderSide: BorderSide.none,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(28),
        borderSide: BorderSide.none,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(28),
        borderSide: const BorderSide(color: vgvBlue, width: 1.5),
      ),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(
        backgroundColor: vgvBlue,
        foregroundColor: vgvWhite,
        disabledBackgroundColor:
            isDark ? const Color(0xFF232B4D) : const Color(0xFFE0E0E0),
        disabledForegroundColor:
            isDark ? const Color(0xFF6B7280) : const Color(0xFFAAAAAA),
        shape: const CircleBorder(),
        padding: const EdgeInsets.all(12),
      ),
    ),
  );
}
