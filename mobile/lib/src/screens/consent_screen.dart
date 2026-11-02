import 'package:flutter/material.dart';
import 'package:mobile/src/localization/app_strings.dart';
import 'package:mobile/src/theme/app_theme.dart';
import 'package:mobile/src/screens/demographics_screen.dart';

class ConsentScreen extends StatefulWidget {
  final Map<String, dynamic> workerInfo;

  const ConsentScreen({super.key, required this.workerInfo});

  @override
  State<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends State<ConsentScreen> {
  bool _hasConsent = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundSlate,
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundSlate,
        elevation: 0,
        centerTitle: true,
        title: Text(
          AppStrings.get('consent_title'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.textDark),
        ),
        leading: Padding(
          padding: const EdgeInsets.all(8.0),
          child: Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.05),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: IconButton(
              icon: const Icon(Icons.arrow_back_ios_new, size: 16, color: AppTheme.obsidianNavy),
              onPressed: () => Navigator.pop(context),
            ),
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Worker Badge in Pastel Blue Pill
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              decoration: BoxDecoration(
                color: AppTheme.pastelBlue,
                borderRadius: BorderRadius.circular(22),
                border: Border.all(color: Colors.white, width: 2),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.verified_user, color: AppTheme.accentBlue, size: 20),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.workerInfo['full_name'] ?? "ASHA Worker",
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.textDark),
                        ),
                        Text(
                          widget.workerInfo['phc_center'] ?? "Primary Health Center",
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Plain-Language Consent Card
            Card(
              margin: EdgeInsets.zero,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(26),
                side: const BorderSide(color: AppTheme.cardBorderColor, width: 1.2),
              ),
              child: Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      AppStrings.get('consent_desc'),
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textDark,
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 18),
                    _buildClause(Icons.warning_amber_rounded, AppStrings.get('consent_clause_1'), Colors.orange.shade700),
                    const SizedBox(height: 14),
                    _buildClause(Icons.privacy_tip_outlined, AppStrings.get('consent_clause_2'), AppTheme.accentBlue),
                    const SizedBox(height: 14),
                    _buildClause(Icons.local_hospital_outlined, AppStrings.get('consent_clause_3'), Colors.indigo.shade600),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Mandatory Checkbox
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: _hasConsent ? AppTheme.obsidianNavy : AppTheme.cardBorderColor,
                  width: 1.5,
                ),
              ),
              child: CheckboxListTile(
                value: _hasConsent,
                onChanged: (val) => setState(() => _hasConsent = val ?? false),
                title: Text(
                  AppStrings.get('consent_checkbox'),
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                ),
                activeColor: AppTheme.obsidianNavy,
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
              ),
            ),
            const SizedBox(height: 28),

            ElevatedButton(
              onPressed: _hasConsent
                  ? () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => DemographicsScreen(workerInfo: widget.workerInfo),
                        ),
                      );
                    }
                  : null,
              child: Text(AppStrings.get('continue_btn')),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildClause(IconData icon, String text, Color color) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: color),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(fontSize: 13, height: 1.4, color: AppTheme.textDark),
          ),
        ),
      ],
    );
  }
}
