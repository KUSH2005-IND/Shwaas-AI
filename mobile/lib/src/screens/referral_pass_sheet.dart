import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:mobile/src/models/screening_model.dart';
import 'package:mobile/src/theme/app_theme.dart';


class ReferralPassSheet extends StatelessWidget {
  final ScreeningResult result;
  final Map<String, dynamic> workerInfo;

  const ReferralPassSheet({
    super.key,
    required this.result,
    required this.workerInfo,
  });

  @override
  Widget build(BuildContext context) {
    final tierColor = AppTheme.getTierColor(result.tier);
    final qrData = "https://shwaas.ai/verify?id=${result.sessionId}&patient=${result.patientCode}&tier=${result.tier}";

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.all(24),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Drag handle
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Official Govt / NTEP Header Banner
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E3A8A), // Indian National Navy Blue
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Row(
                children: [
                  Icon(Icons.local_hospital, color: Colors.white, size: 28),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "NATIONAL TB ELIMINATION PROGRAMME",
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                        Text(
                          "OFFICIAL DIGITAL REFERRAL PASS",
                          style: TextStyle(
                            color: Colors.amberAccent,
                            fontSize: 13,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Patient Identity & Pass Details Box
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.grey.shade50,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey.shade300),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("PATIENT CODE", style: TextStyle(fontSize: 11, color: Colors.black54)),
                          Text(
                            result.patientCode,
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: tierColor,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          result.tier,
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 20),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _buildMetaCol("VILLAGE / SECTOR", result.village),
                      _buildMetaCol("AGE / SEX", "${result.age}y • ${result.sex.toUpperCase()}"),
                      _buildMetaCol("SCORE", "${result.clinicalScore}/18"),
                    ],
                  ),
                  const SizedBox(height: 12),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _buildMetaCol("REFERRING ASHA", workerInfo['full_name'] ?? "ASHA Rani"),
                      _buildMetaCol("PRIMARY HEALTH CENTRE", workerInfo['phc_center'] ?? "Rampur PHC"),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Scannable QR Code Box
            Center(
              child: Column(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 10, spreadRadius: 2),
                      ],
                    ),
                    child: QrImageView(
                      data: qrData,
                      version: QrVersions.auto,
                      size: 160.0,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    "Scan with any PHC Laboratory scanner for instant CBNAAT enrollment",
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 11, color: Colors.black54),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Mandated Referral Action Directive
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: tierColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: tierColor),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.directions_walk, color: tierColor, size: 24),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text("MANDATED CLINICAL PATHWAY", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 2),
                        Text(
                          result.recommendedPathway,
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: tierColor),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Action Buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.share),
                    label: const Text("Share WhatsApp"),
                    onPressed: () {
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text("Digital Pass for ${result.patientCode} prepared for WhatsApp dispatch!"),
                          backgroundColor: Colors.green.shade800,
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    icon: const Icon(Icons.print),
                    label: const Text("Print Slip"),
                    onPressed: () {
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text("Sending pass to Bluetooth portable field printer...")),
                      );
                    },
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetaCol(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: Colors.black54, fontWeight: FontWeight.w600)),
        const SizedBox(height: 2),
        Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
