import 'package:flutter/material.dart';
import 'package:mobile/src/localization/app_strings.dart';
import 'package:mobile/src/services/api_client.dart';
import 'package:mobile/src/theme/app_theme.dart';
import 'package:mobile/src/screens/consent_screen.dart';
import 'package:mobile/src/screens/settings_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController(text: "asha_rani");
  final _passwordController = TextEditingController(text: "asha123");
  bool _isLoading = false;
  String? _errorMessage;

  void _toggleLanguage() {
    setState(() {
      AppStrings.currentLanguage = (AppStrings.currentLanguage == AppLanguage.en)
          ? AppLanguage.hi
          : AppLanguage.en;
    });
  }

  Future<void> _handleLogin() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final user = await ApiClient.login(
        _usernameController.text.trim(),
        _passwordController.text.trim(),
      );

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => ConsentScreen(workerInfo: user)),
      );
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceAll("Exception: ", "");
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final lang = AppStrings.currentLanguage;

    return Scaffold(
      appBar: AppBar(
        title: Text(AppStrings.get('app_title')),
        actions: [
          Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              color: AppTheme.pastelBlue,
              borderRadius: BorderRadius.circular(20),
            ),
            child: TextButton(
              onPressed: _toggleLanguage,
              child: Text(
                lang == AppLanguage.en ? "हिन्दी" : "English",
                style: const TextStyle(color: AppTheme.obsidianNavy, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            margin: const EdgeInsets.only(right: 14),
            decoration: BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.05),
                  blurRadius: 10,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: IconButton(
              icon: const Icon(Icons.settings, color: AppTheme.obsidianNavy, size: 20),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const SettingsScreen()),
                );
              },
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Brand Logo & Subtitle
            Center(
              child: Container(
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  color: AppTheme.pastelBlue,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 4),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.accentBlue.withValues(alpha: 0.15),
                      blurRadius: 20,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.health_and_safety_rounded,
                  size: 52,
                  color: AppTheme.accentBlue,
                ),
              ),
            ),
            const SizedBox(height: 16),
            Center(
              child: Text(
                AppStrings.get('app_title'),
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textDark,
                  letterSpacing: -0.5,
                ),
              ),
            ),
            const SizedBox(height: 4),
            Center(
              child: Text(
                AppStrings.get('app_subtitle'),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 14,
                  color: AppTheme.textMuted,
                  height: 1.4,
                ),
              ),
            ),
            const SizedBox(height: 28),

            // Login Card
            Card(
              margin: EdgeInsets.zero,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(28),
                side: const BorderSide(color: AppTheme.cardBorderColor, width: 1.2),
              ),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      AppStrings.get('login_title'),
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.obsidianNavy,
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _usernameController,
                      decoration: InputDecoration(
                        labelText: AppStrings.get('username'),
                        prefixIcon: const Icon(Icons.person_outline),
                        border: const OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _passwordController,
                      obscureText: true,
                      decoration: InputDecoration(
                        labelText: AppStrings.get('password'),
                        prefixIcon: const Icon(Icons.lock_outline),
                        border: const OutlineInputBorder(),
                      ),
                    ),
                    if (_errorMessage != null) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.red.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.red.shade200),
                        ),
                        child: Text(
                          _errorMessage!,
                          style: TextStyle(color: Colors.red.shade800, fontSize: 13),
                        ),
                      ),
                    ],
                    const SizedBox(height: 20),
                    ElevatedButton(
                      onPressed: _isLoading ? null : _handleLogin,
                      child: _isLoading
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                            )
                          : Text(AppStrings.get('login_btn')),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),
            // Quick-fill credentials for judges & testing
            Center(
              child: Wrap(
                spacing: 8,
                children: [
                  ActionChip(
                    avatar: const Icon(Icons.badge, size: 16),
                    label: const Text("ASHA Rani"),
                    onPressed: () {
                      _usernameController.text = "asha_rani";
                      _passwordController.text = "asha123";
                    },
                  ),
                  ActionChip(
                    avatar: const Icon(Icons.admin_panel_settings, size: 16),
                    label: const Text("Admin"),
                    onPressed: () {
                      _usernameController.text = "admin";
                      _passwordController.text = "admin123";
                    },
                  ),
                ],
              ),
            ),

            const SizedBox(height: 40),
            Center(
              child: Text(
                "INNOTECH 2026 • Team KARTAVYA\nOffline-First TB Triage Architecture",
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
