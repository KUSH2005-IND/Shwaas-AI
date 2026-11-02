import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile/src/localization/app_strings.dart';
import 'package:mobile/src/services/prescription_ocr_engine.dart';
import 'package:mobile/src/theme/app_theme.dart';
import 'package:mobile/src/screens/questionnaire_screen.dart';

class OcrScannerScreen extends StatefulWidget {
  final Map<String, dynamic> workerInfo;
  final int age;
  final String sex;
  final String village;

  const OcrScannerScreen({
    super.key,
    required this.workerInfo,
    required this.age,
    required this.sex,
    required this.village,
  });

  @override
  State<OcrScannerScreen> createState() => _OcrScannerScreenState();
}

class _OcrScannerScreenState extends State<OcrScannerScreen> with SingleTickerProviderStateMixin {
  final ImagePicker _picker = ImagePicker();
  File? _imageFile;
  bool _isProcessing = false;
  OcrExtractionResult? _ocrResult;
  late AnimationController _scanAnimController;

  @override
  void initState() {
    super.initState();
    _scanAnimController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _scanAnimController.dispose();
    super.dispose();
  }

  void _skipToManualSurvey() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => QuestionnaireScreen(
          workerInfo: widget.workerInfo,
          age: widget.age,
          sex: widget.sex,
          village: widget.village,
          initialAnswers: null, // Start with clean defaults
        ),
      ),
    );
  }

  void _continueWithExtractedAnswers() {
    final answers = _ocrResult?.answers;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => QuestionnaireScreen(
          workerInfo: widget.workerInfo,
          age: widget.age,
          sex: widget.sex,
          village: widget.village,
          initialAnswers: answers,
        ),
      ),
    );
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(source: source, imageQuality: 85);
      if (picked != null) {
        final file = File(picked.path);
        setState(() {
          _imageFile = file;
          _isProcessing = true;
          _ocrResult = null;
        });

        // Perform real on-device and server OCR recognition on captured image
        final result = await PrescriptionOcrEngine.scanImage(file);

        if (!mounted) return;
        setState(() {
          _isProcessing = false;
          _ocrResult = result;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _isProcessing = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Camera/Gallery access error: $e")),
      );
    }
  }

  void _loadDemoPrescription(Map<String, String> demo) {
    setState(() {
      _isProcessing = true;
      _imageFile = null;
      _ocrResult = null;
    });

    Future.delayed(const Duration(milliseconds: 800), () {
      final result = PrescriptionOcrEngine.processText(demo["text"]!);
      setState(() {
        _isProcessing = false;
        _ocrResult = result;
      });
    });
  }

  void _showDemoPrescriptionPicker() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              "Select Sample Medical Document",
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const SizedBox(height: 12),
            ...PrescriptionOcrEngine.demoPrescriptions.map((demo) {
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: const Icon(Icons.description, color: AppTheme.primaryTeal),
                  title: Text(demo["title"]!, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  subtitle: Text(demo["hospital"]!, style: const TextStyle(fontSize: 11)),
                  onTap: () {
                    Navigator.pop(ctx);
                    _loadDemoPrescription(demo);
                  },
                ),
              );
            }),
          ],
        ),
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
          AppStrings.get('ocr_title'),
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
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.05),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: TextButton(
                onPressed: _skipToManualSurvey,
                child: const Text(
                  "Skip",
                  style: TextStyle(color: AppTheme.obsidianNavy, fontWeight: FontWeight.bold, fontSize: 13),
                ),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Optional Step Badge & Explanation
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.blue.shade300),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline, size: 14, color: Colors.blue.shade800),
                      const SizedBox(width: 6),
                      Text(
                        AppStrings.get('ocr_optional_badge'),
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.blue.shade800),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            Text(
              AppStrings.get('ocr_desc'),
              style: const TextStyle(fontSize: 13, height: 1.4, color: AppTheme.textDark),
            ),
            const SizedBox(height: 20),

            // Scan Viewfinder Card
            Container(
              height: 180,
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.primaryTeal, width: 2),
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  if (_imageFile != null)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: Image.file(_imageFile!, width: double.infinity, height: double.infinity, fit: BoxFit.cover),
                    )
                  else
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.document_scanner, size: 48, color: Colors.teal.shade300),
                        const SizedBox(height: 8),
                        const Text(
                          "Align OPD Prescription or Lab Report",
                          style: TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                      ],
                    ),

                  // Animated Scanning Laser Line
                  if (_isProcessing)
                    AnimatedBuilder(
                      animation: _scanAnimController,
                      builder: (context, child) {
                        return Positioned(
                          top: 10 + (_scanAnimController.value * 150),
                          left: 16,
                          right: 16,
                          child: Container(
                            height: 3,
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                colors: [Colors.transparent, Colors.cyanAccent, Colors.transparent],
                              ),
                              boxShadow: [
                                BoxShadow(color: Colors.cyanAccent.withValues(alpha: 0.8), blurRadius: 8),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // Scanner Action Buttons
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    icon: const Icon(Icons.camera_alt, size: 18),
                    label: Text(AppStrings.get('ocr_camera_btn'), style: const TextStyle(fontSize: 12)),
                    onPressed: _isProcessing ? null : () => _pickImage(ImageSource.camera),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    icon: const Icon(Icons.photo_library, size: 18),
                    label: Text(AppStrings.get('ocr_gallery_btn'), style: const TextStyle(fontSize: 12)),
                    onPressed: _isProcessing ? null : () => _pickImage(ImageSource.gallery),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            // Demo Hospital Slip Quick Loader
            TextButton.icon(
              icon: const Icon(Icons.science, size: 18, color: AppTheme.primaryTeal),
              label: Text(AppStrings.get('ocr_sample_btn'), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
              onPressed: _isProcessing ? null : _showDemoPrescriptionPicker,
            ),

            if (_isProcessing) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: Colors.teal.shade50, borderRadius: BorderRadius.circular(12)),
                child: Row(
                  children: [
                    const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        AppStrings.get('ocr_analyzing'),
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.teal.shade900),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Extracted OCR Results Card
            if (_ocrResult != null) ...[
              const SizedBox(height: 20),
              if (_ocrResult!.entities.isEmpty)
                Card(
                  margin: EdgeInsets.zero,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                    side: BorderSide(color: Colors.amber.shade400, width: 1.5),
                  ),
                  color: Colors.amber.shade50.withValues(alpha: 0.5),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.warning_amber_rounded, color: Colors.amber.shade900, size: 24),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                "No Medical Symptoms Detected",
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                  color: Colors.amber.shade900,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          "No readable medical text or clinical symptoms were detected in this image. "
                          "Please take a clear photo of an OPD prescription or slip, or tap below to proceed manually.",
                          style: TextStyle(fontSize: 12, height: 1.4, color: Colors.brown.shade800),
                        ),
                        const SizedBox(height: 14),
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryTeal,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                          icon: const Icon(Icons.edit_note, color: Colors.white),
                          label: const Text("Fill Survey Manually", style: TextStyle(color: Colors.white)),
                          onPressed: _skipToManualSurvey,
                        ),
                      ],
                    ),
                  ),
                )
              else
                Card(
                  margin: EdgeInsets.zero,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                    side: BorderSide(color: AppTheme.primaryTeal.withValues(alpha: 0.5), width: 1.5),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              AppStrings.get('ocr_detected_heading'),
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(color: Colors.green.shade100, borderRadius: BorderRadius.circular(12)),
                              child: Text(
                                "${_ocrResult!.entities.length} Detected",
                                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.green.shade900),
                              ),
                            ),
                          ],
                        ),
                        const Divider(height: 20),

                        if (_ocrResult!.redFlagDetected)
                          Container(
                            margin: const EdgeInsets.only(bottom: 12),
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(8)),
                            child: const Row(
                              children: [
                                Icon(Icons.warning, color: Colors.red, size: 18),
                                SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    "EMERGENCY RED FLAG: Hemoptysis (blood in cough) detected in slip!",
                                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.red),
                                  ),
                                ),
                              ],
                            ),
                          ),

                        ..._ocrResult!.entities.map((entity) {
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                Icon(
                                  entity.isRedFlag ? Icons.flag : Icons.check_circle,
                                  size: 18,
                                  color: entity.isRedFlag ? Colors.red : Colors.green.shade700,
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    entity.symptomTitle,
                                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                                  ),
                                ),
                                Text(
                                  "‘${entity.matchedKeyword}’",
                                  style: const TextStyle(fontSize: 11, color: Colors.black54, fontStyle: FontStyle.italic),
                                ),
                              ],
                            ),
                          );
                        }),
                        const SizedBox(height: 16),

                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.green.shade700,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                          icon: const Icon(Icons.assignment_turned_in, color: Colors.white),
                          label: Text(AppStrings.get('ocr_apply_btn')),
                          onPressed: _continueWithExtractedAnswers,
                        ),
                      ],
                    ),
                  ),
                ),
            ],

            const SizedBox(height: 24),

            // Secondary Bottom Skip Button
            OutlinedButton(
              onPressed: _skipToManualSurvey,
              child: Text(AppStrings.get('ocr_skip_btn')),
            ),
          ],
        ),
      ),
    );
  }
}
