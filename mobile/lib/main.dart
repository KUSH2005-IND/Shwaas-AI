import 'package:flutter/material.dart';
import 'package:mobile/src/theme/app_theme.dart';
import 'package:mobile/src/screens/login_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ShwaasAIApp());
}

class ShwaasAIApp extends StatelessWidget {
  const ShwaasAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ShwaasAI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const LoginScreen(),
    );
  }
}
