import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile/src/localization/app_strings.dart';
import 'package:mobile/src/models/screening_model.dart';
import 'package:mobile/src/theme/app_theme.dart';
import 'package:mobile/src/screens/demographics_screen.dart';
import 'package:mobile/src/screens/history_queue_screen.dart';
import 'package:mobile/src/screens/referral_pass_sheet.dart';
import 'package:mobile/src/screens/surveillance_screen.dart';

/// Custom Painter for the signature Interexy ECG pulse waveform
class EcgWavePainter extends CustomPainter {
  final Color color;
  final double strokeWidth;

  const EcgWavePainter({this.color = Colors.white, this.strokeWidth = 2.2});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final path = Path();
    final h = size.height;
    final w = size.width;

    path.moveTo(0, h * 0.65);
    path.lineTo(w * 0.15, h * 0.65);
    path.lineTo(w * 0.22, h * 0.58);
    path.lineTo(w * 0.28, h * 0.65);
    path.lineTo(w * 0.40, h * 0.65);
    // P-wave
    path.lineTo(w * 0.45, h * 0.52);
    path.lineTo(w * 0.49, h * 0.65);
    // Q-R-S complex (acoustic peak)
    path.lineTo(w * 0.53, h * 0.72);
    path.lineTo(w * 0.60, h * 0.12);
    path.lineTo(w * 0.67, h * 0.90);
    path.lineTo(w * 0.72, h * 0.65);
    // T-wave
    path.lineTo(w * 0.79, h * 0.48);
    path.lineTo(w * 0.85, h * 0.65);
    path.lineTo(w, h * 0.65);

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class ResultScreen extends StatelessWidget {
  final ScreeningResult result;
  final Map<String, dynamic> workerInfo;

  const ResultScreen({
    super.key,
    required this.result,
    required this.workerInfo,
  });

  void _showReferralPass(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => FractionallySizedBox(
        heightFactor: 0.9,
        child: ReferralPassSheet(result: result, workerInfo: workerInfo),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tierColor = AppTheme.getTierColor(result.tier);

    return Scaffold(
      backgroundColor: AppTheme.backgroundSlate,
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundSlate,
        elevation: 0,
        centerTitle: true,
        title: Text(
          AppStrings.get('result_title'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.textDark),
        ),
        automaticallyImplyLeading: false,
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
              onPressed: () {
                Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => DemographicsScreen(workerInfo: workerInfo)),
                );
              },
            ),
          ),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 6.0),
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
                icon: const Icon(Icons.radar, size: 20, color: AppTheme.obsidianNavy),
                tooltip: "District Surveillance",
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const SurveillanceScreen()),
                  );
                },
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
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
                icon: const Icon(Icons.history, size: 20, color: AppTheme.obsidianNavy),
                tooltip: AppStrings.get('view_history_btn'),
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const HistoryQueueScreen()),
                  );
                },
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // INTEREXY PATIENT IDENTIFIER PILL BAR
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppTheme.pastelBlue,
                    borderRadius: BorderRadius.circular(30),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        "${AppStrings.get('patient_code_label')}: ",
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.obsidianNavy),
                      ),
                      Text(
                        result.patientCode,
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.obsidianNavy),
                      ),
                      const SizedBox(width: 8),
                      GestureDetector(
                        onTap: () {
                          Clipboard.setData(ClipboardData(text: result.patientCode));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text("Patient code copied to clipboard"), duration: Duration(seconds: 1)),
                          );
                        },
                        child: const Icon(Icons.copy_rounded, size: 14, color: AppTheme.obsidianNavy),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                // Sync status chip
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: result.isSynced ? AppTheme.pastelMint : AppTheme.pastelPeach,
                    borderRadius: BorderRadius.circular(30),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        result.isSynced ? Icons.cloud_done : Icons.cloud_off,
                        size: 14,
                        color: result.isSynced ? const Color(0xFF15803D) : const Color(0xFFB45309),
                      ),
                      const SizedBox(width: 5),
                      Text(
                        result.isSynced ? "Synced" : "Offline",
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: result.isSynced ? const Color(0xFF15803D) : const Color(0xFFB45309),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // PATIENT TITLE
            Center(
              child: Text(
                "Patient Assessment • ${result.patientCode.split('-').last}",
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.obsidianNavy,
                  letterSpacing: -0.5,
                ),
              ),
            ),
            const SizedBox(height: 16),

            // INTEREXY FLANKING STATS & CENTER AVATAR
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                // Left Stat
                Column(
                  children: [
                    Text(
                      "${result.clinicalScore} pts",
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.obsidianNavy,
                      ),
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      "WHO Score",
                      style: TextStyle(fontSize: 11, color: AppTheme.textMuted, fontWeight: FontWeight.w500),
                    ),
                  ],
                ),

                // Center Circular Medical Avatar with ring
                Container(
                  width: 82,
                  height: 82,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                    border: Border.all(color: AppTheme.pastelAqua, width: 4),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.08),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Center(
                    child: Container(
                      width: 66,
                      height: 66,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.pastelBlue,
                      ),
                      child: const Icon(
                        Icons.medical_services_rounded,
                        color: AppTheme.obsidianNavy,
                        size: 32,
                      ),
                    ),
                  ),
                ),

                // Right Stat
                Column(
                  children: [
                    Text(
                      "${(result.audioCalibratedScore * 100).toInt()}%",
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.obsidianNavy,
                      ),
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      "Acoustic AI",
                      style: TextStyle(fontSize: 11, color: AppTheme.textMuted, fontWeight: FontWeight.w500),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 18),

            // INTEREXY ACTION PILL ROW
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Refresh / Re-test circular button
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.06),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.refresh_rounded, size: 20, color: AppTheme.obsidianNavy),
                    tooltip: "Re-screen",
                    onPressed: () {
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(builder: (_) => DemographicsScreen(workerInfo: workerInfo)),
                      );
                    },
                  ),
                ),
                const SizedBox(width: 14),

                // Obsidian Capsule Button: Issue NTEP Referral Pass
                GestureDetector(
                  onTap: () => _showReferralPass(context),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                    decoration: BoxDecoration(
                      color: AppTheme.obsidianNavy,
                      borderRadius: BorderRadius.circular(30),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.obsidianNavy.withValues(alpha: 0.25),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.qr_code_2_rounded, color: Colors.amberAccent, size: 20),
                        SizedBox(width: 8),
                        Text(
                          "NTEP Referral Pass",
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                            letterSpacing: 0.2,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 14),

                // District radar circular button
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.06),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.chevron_right_rounded, size: 24, color: AppTheme.obsidianNavy),
                    tooltip: "View Queue",
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const HistoryQueueScreen()),
                      );
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // SIGNATURE INTEREXY METRICS GRID
            // Left: Obsidian Navy Card with live ECG Waveform
            // Right: 2 Stacked Pastel Cards (WHO Score & Referral Tier)
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Left Column: Obsidian Navy Card
                Expanded(
                  flex: 5,
                  child: Container(
                    height: 200,
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      color: AppTheme.obsidianNavy,
                      borderRadius: BorderRadius.circular(26),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.obsidianNavy.withValues(alpha: 0.3),
                          blurRadius: 16,
                          offset: const Offset(0, 6),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          "Acoustic AI",
                          style: TextStyle(
                            color: Colors.white70,
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.baseline,
                          textBaseline: TextBaseline.alphabetic,
                          children: [
                            Text(
                              "${(result.audioCalibratedScore * 100).toInt()}",
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 36,
                                fontWeight: FontWeight.w900,
                                height: 1.0,
                              ),
                            ),
                            const SizedBox(width: 4),
                            const Text(
                              "% risk",
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                        const Spacer(),
                        // Interexy signature white ECG pulse waveform
                        SizedBox(
                          height: 52,
                          width: double.infinity,
                          child: CustomPaint(
                            painter: const EcgWavePainter(color: Colors.white, strokeWidth: 2.2),
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          "Calibrated Cough Proxy",
                          style: TextStyle(color: Colors.white54, fontSize: 10),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 14),

                // Right Column: Two Stacked Pastel Cards
                Expanded(
                  flex: 5,
                  child: SizedBox(
                    height: 200,
                    child: Column(
                      children: [
                        // Top Card: Pastel Mint (WHO Score)
                        Expanded(
                          child: Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                            decoration: BoxDecoration(
                              color: AppTheme.pastelMint,
                              borderRadius: BorderRadius.circular(22),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Text(
                                  "Clinical Score",
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFF1E3A1E),
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  "${result.clinicalScore} / ${result.questionnaireMax}",
                                  style: const TextStyle(
                                    fontSize: 22,
                                    fontWeight: FontWeight.w900,
                                    color: AppTheme.obsidianNavy,
                                    letterSpacing: -0.5,
                                  ),
                                ),
                                const Text(
                                  "WHO Symptom Count",
                                  style: TextStyle(fontSize: 10, color: Color(0xFF3F623F)),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),

                        // Bottom Card: Pastel Sky Blue (Referral Tier)
                        Expanded(
                          child: Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                            decoration: BoxDecoration(
                              color: AppTheme.pastelAqua,
                              borderRadius: BorderRadius.circular(22),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Text(
                                  "Referral Tier",
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFF0F3652),
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Row(
                                  children: [
                                    Container(
                                      width: 8,
                                      height: 8,
                                      decoration: BoxDecoration(
                                        color: tierColor,
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    Expanded(
                                      child: Text(
                                        result.tier,
                                        style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w900,
                                          color: tierColor,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                Text(
                                  result.redFlagDetected ? "Red Flag Active" : "Triage Directive",
                                  style: TextStyle(
                                    fontSize: 10,
                                    color: result.redFlagDetected ? Colors.red.shade900 : const Color(0xFF265476),
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),

            // RED FLAG BANNER (IF DETECTED)
            if (result.redFlagDetected) ...[
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: Colors.red.shade300, width: 1.5),
                ),
                child: Row(
                  children: [
                    Icon(Icons.warning_amber_rounded, size: 22, color: Colors.red.shade800),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Text(
                        "Safety Override: Hemoptysis (coughing blood) mandates immediate emergency escalation.",
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.red),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // RECOMMENDED PATHWAY CARD (Clean White Squircle)
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ],
                border: Border.all(color: AppTheme.cardBorderColor, width: 1.2),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: tierColor.withValues(alpha: 0.15),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(Icons.alt_route_rounded, color: tierColor, size: 18),
                      ),
                      const SizedBox(width: 10),
                      const Text(
                        "Clinical Action Protocol",
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.obsidianNavy,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    result.recommendedPathway,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textDark,
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // CENTERED GRAD-CAM SPECTROGRAM CARD
            if (result.gradcamImage != null && result.gradcamImage!.startsWith("data:image")) ...[
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.04),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ],
                  border: Border.all(color: AppTheme.pastelAqua, width: 1.5),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.palette_outlined, color: Color(0xFF2563EB), size: 18),
                        const SizedBox(width: 8),
                        Text(
                          AppStrings.get('gradcam_title'),
                          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.obsidianNavy),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Center(
                      child: Container(
                        constraints: const BoxConstraints(maxHeight: 250),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F172A), // Dark slate frame
                          borderRadius: BorderRadius.circular(16),
                        ),
                        padding: const EdgeInsets.all(8),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Image.memory(
                            base64Decode(result.gradcamImage!.split(',').last),
                            fit: BoxFit.contain,
                            alignment: Alignment.center,
                            errorBuilder: (ctx, err, stack) => const Padding(
                              padding: EdgeInsets.all(20),
                              child: Text(
                                "Grad-CAM visualization unavailable",
                                style: TextStyle(color: Colors.white70),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      AppStrings.get('gradcam_caption'),
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 12, color: AppTheme.textMuted, height: 1.4),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
            ],

            // STATUTORY DISCLAIMER (Pastel Card)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.verified_user_outlined, size: 16, color: Colors.grey.shade700),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      AppStrings.get('disclaimer_text'),
                      style: TextStyle(fontSize: 11, height: 1.4, color: Colors.grey.shade700),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 22),

            // INTEREXY CAPSULE ACTIONS
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.obsidianNavy,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
              ),
              onPressed: () {
                Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(
                    builder: (_) => DemographicsScreen(workerInfo: workerInfo),
                  ),
                );
              },
              child: Text(
                AppStrings.get('new_screening_btn'),
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              style: OutlinedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: AppTheme.obsidianNavy,
                padding: const EdgeInsets.symmetric(vertical: 15),
                side: const BorderSide(color: Color(0xFFCBD5E1), width: 1.5),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
              ),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const HistoryQueueScreen()),
                );
              },
              child: Text(
                AppStrings.get('view_history_btn'),
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

