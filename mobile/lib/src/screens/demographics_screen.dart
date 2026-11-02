import 'package:flutter/material.dart';
import 'package:mobile/src/localization/app_strings.dart';
import 'package:mobile/src/screens/ocr_scanner_screen.dart';
import 'package:mobile/src/theme/app_theme.dart';


class DemographicsScreen extends StatefulWidget {
  final Map<String, dynamic> workerInfo;

  const DemographicsScreen({super.key, required this.workerInfo});

  @override
  State<DemographicsScreen> createState() => _DemographicsScreenState();
}

class _DemographicsScreenState extends State<DemographicsScreen> {
  final _ageController = TextEditingController(text: "35");
  String _selectedSex = "male";
  String _selectedVillage = "Rampur";

  final List<String> _villages = [
    "Rampur",
    "Sundarpur",
    "Belagavi",
    "Kalyan",
    "Other Sector"
  ];

  void _validateAndProceed() {
    final age = int.tryParse(_ageController.text.trim());

    if (age == null || age <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please enter a valid age.")),
      );
      return;
    }

    // Pediatric Protocol Check (<18)
    if (age < 18) {
      _showPediatricDialog();
      return;
    }

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => OcrScannerScreen(
          workerInfo: widget.workerInfo,
          age: age,
          sex: _selectedSex,
          village: _selectedVillage,
        ),
      ),
    );
  }

  void _showPediatricDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            Icon(Icons.child_care, color: Colors.orange.shade800),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                AppStrings.get('pediatric_warning_title'),
                style: const TextStyle(fontSize: 18),
              ),
            ),
          ],
        ),
        content: Text(
          AppStrings.get('pediatric_warning_desc'),
          style: const TextStyle(fontSize: 14, height: 1.4),
        ),
        actions: [
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.orange.shade800),
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Acknowledge Protocol"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundSlate,
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundSlate,
        elevation: 0,
        centerTitle: true,
        title: Text(
          AppStrings.get('demographics_title'),
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
            Card(
              margin: EdgeInsets.zero,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(28),
                side: const BorderSide(color: AppTheme.cardBorderColor, width: 1.2),
              ),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Age Input
                    Text(
                      AppStrings.get('age_label'),
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textDark),
                    ),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _ageController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        hintText: "e.g. 35",
                        suffixText: "years",
                        prefixIcon: Icon(Icons.cake_outlined, color: AppTheme.accentBlue),
                      ),
                    ),
                    const SizedBox(height: 22),

                    // Sex Selector
                    Text(
                      AppStrings.get('sex_label'),
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textDark),
                    ),
                    const SizedBox(height: 8),
                    SegmentedButton<String>(
                      segments: [
                        ButtonSegment(value: 'male', label: Text(AppStrings.get('sex_male'))),
                        ButtonSegment(value: 'female', label: Text(AppStrings.get('sex_female'))),
                        ButtonSegment(value: 'other', label: Text(AppStrings.get('sex_other'))),
                      ],
                      selected: {_selectedSex},
                      style: ButtonStyle(
                        backgroundColor: WidgetStateProperty.resolveWith((states) {
                          if (states.contains(WidgetState.selected)) {
                            return AppTheme.obsidianNavy;
                          }
                          return Colors.white;
                        }),
                        foregroundColor: WidgetStateProperty.resolveWith((states) {
                          if (states.contains(WidgetState.selected)) {
                            return Colors.white;
                          }
                          return AppTheme.obsidianNavy;
                        }),
                        shape: WidgetStateProperty.all(
                          RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                        ),
                      ),
                      onSelectionChanged: (val) {
                        setState(() => _selectedSex = val.first);
                      },
                    ),
                    const SizedBox(height: 22),

                    // Village / PHC Sector Selector
                    Text(
                      AppStrings.get('village_label'),
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textDark),
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      initialValue: _selectedVillage,
                      decoration: const InputDecoration(
                        prefixIcon: Icon(Icons.location_on_outlined, color: AppTheme.accentBlue),
                      ),
                      items: _villages.map((v) {
                        return DropdownMenuItem(value: v, child: Text(v));
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) setState(() => _selectedVillage = val);
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 32),

            ElevatedButton(
              onPressed: _validateAndProceed,
              child: Text(AppStrings.get('continue_btn')),
            ),
          ],
        ),
      ),
    );
  }
}
