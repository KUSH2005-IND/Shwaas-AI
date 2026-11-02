import 'package:flutter/material.dart';
import 'package:mobile/src/localization/app_strings.dart';
import 'package:mobile/src/services/api_client.dart';
import 'package:mobile/src/theme/app_theme.dart';
import 'package:mobile/src/screens/login_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _serverUrlController = TextEditingController();
  bool _isDemoMode = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final url = await ApiClient.getBaseUrl();
    final demo = await ApiClient.isDemoMode();
    setState(() {
      _serverUrlController.text = url;
      _isDemoMode = demo;
      _isLoading = false;
    });
  }

  Future<void> _saveSettings() async {
    await ApiClient.setBaseUrl(_serverUrlController.text.trim());
    await ApiClient.setDemoMode(_isDemoMode);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Settings saved successfully")),
    );
  }

  Future<void> _logout() async {
    await ApiClient.clearToken();
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text("Settings & Preferences"),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Language Selection Card
            Card(
              margin: EdgeInsets.zero,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Language / भाषा", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                    const SizedBox(height: 12),
                    SegmentedButton<AppLanguage>(
                      segments: const [
                        ButtonSegment(value: AppLanguage.en, label: Text("English")),
                        ButtonSegment(value: AppLanguage.hi, label: Text("हिन्दी (Hindi)")),
                      ],
                      selected: {AppStrings.currentLanguage},
                      onSelectionChanged: (val) {
                        setState(() {
                          AppStrings.currentLanguage = val.first;
                        });
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Server & Network Card
            Card(
              margin: EdgeInsets.zero,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Server Connection", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _serverUrlController,
                      decoration: const InputDecoration(
                        labelText: "API Server Base URL",
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.cloud_outlined),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      children: [
                        ActionChip(
                          label: const Text("Localhost:8000"),
                          onPressed: () => _serverUrlController.text = "http://127.0.0.1:8000",
                        ),
                        ActionChip(
                          label: const Text("Mock:8001"),
                          onPressed: () => _serverUrlController.text = "http://127.0.0.1:8001",
                        ),
                        ActionChip(
                          label: const Text("Android (10.0.2.2)"),
                          onPressed: () => _serverUrlController.text = "http://10.0.2.2:8000",
                        ),
                      ],
                    ),
                    const Divider(height: 28),

                    // Demo Mode Switch
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(AppStrings.get('demo_mode'), style: const TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: Text(AppStrings.get('demo_mode_desc'), style: const TextStyle(fontSize: 12)),
                      value: _isDemoMode,
                      activeThumbColor: AppTheme.primaryTeal,
                      onChanged: (val) {
                        setState(() => _isDemoMode = val);
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            ElevatedButton(
              onPressed: _saveSettings,
              child: const Text("Save Preferences"),
            ),
            const SizedBox(height: 24),

            // Logout Button
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.red,
                side: const BorderSide(color: Colors.red),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              icon: const Icon(Icons.logout),
              label: const Text("Logout"),
              onPressed: _logout,
            ),
            const SizedBox(height: 40),

            Center(
              child: Text(
                "ShwaasAI v1.1.0 • INNOTECH 2026\nDesigned for Rural Frontline Healthcare",
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
