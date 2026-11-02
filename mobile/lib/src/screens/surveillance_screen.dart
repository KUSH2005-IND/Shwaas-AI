import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:mobile/src/services/api_client.dart';
import 'package:mobile/src/theme/app_theme.dart';

class SurveillanceScreen extends StatefulWidget {
  const SurveillanceScreen({super.key});

  @override
  State<SurveillanceScreen> createState() => _SurveillanceScreenState();
}

class _SurveillanceScreenState extends State<SurveillanceScreen> {
  bool _isLoading = true;
  Map<String, dynamic>? _statsData;

  @override
  void initState() {
    super.initState();
    _fetchStats();
  }

  Future<void> _fetchStats() async {
    setState(() {
      _isLoading = true;
    });


    try {
      final baseUrl = await ApiClient.getBaseUrl();
      final res = await http.get(Uri.parse('$baseUrl/stats')).timeout(const Duration(seconds: 6));
      if (res.statusCode == 200) {
        setState(() {
          _statsData = jsonDecode(res.body);
          _isLoading = false;
        });
      } else {
        throw Exception("Server returned ${res.statusCode}");
      }
    } catch (e) {
      // Mock fallback stats if offline
      setState(() {
        _statsData = {
          "total_screenings": 39,
          "tier_counts": {"LOW": 8, "MODERATE": 10, "HIGH": 6, "HIGH_RISK_SCREENING": 6, "URGENT": 9},
          "referral_counts": {"pending": 17, "tested": 19, "lost": 3},
          "referral_completion_rate": 48.7,
          "screenings_by_village": {"Rampur": 10, "Belagavi": 10, "Sundarpur": 8, "Kalyan": 7, "Unknown": 4}
        };
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundSlate,
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundSlate,
        elevation: 0,
        centerTitle: true,
        title: const Text(
          "District Outbreak & Surveillance",
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.textDark),
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
                icon: const Icon(Icons.refresh_rounded, size: 20, color: AppTheme.obsidianNavy),
                onPressed: _fetchStats,
              ),
            ),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // KPI Header Card (Obsidian Navy with Pastel Accents)
                  Container(
                    padding: const EdgeInsets.all(22),
                    decoration: BoxDecoration(
                      color: AppTheme.obsidianNavy,
                      borderRadius: BorderRadius.circular(26),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.obsidianNavy.withValues(alpha: 0.25),
                          blurRadius: 14,
                          offset: const Offset(0, 6),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: AppTheme.pastelAqua.withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Text(
                                "EPIDEMIOLOGICAL SURVEILLANCE",
                                style: TextStyle(color: AppTheme.pastelAqua, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                              ),
                            ),
                            const Icon(Icons.radar_rounded, color: AppTheme.pastelAqua, size: 20),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  "${_statsData?['total_screenings'] ?? 39}",
                                  style: const TextStyle(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w900),
                                ),
                                const Text("Total Screened", style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.w500)),
                              ],
                            ),
                            Container(height: 44, width: 1, color: Colors.white24),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  "${_statsData?['referral_completion_rate'] ?? 48.7}%",
                                  style: const TextStyle(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w900),
                                ),
                                const Text("CBNAAT Follow-up", style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.w500)),
                              ],
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.trending_up_rounded, color: Color(0xFF4ADE80), size: 18),
                              SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  "Targeting India's 44% Lost-to-Follow-up gap through ASHA active tracing.",
                                  style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w500),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // High-Risk Cluster Alert
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: Colors.red.shade300),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.warning_amber_rounded, color: Colors.red, size: 24),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                "CLUSTER ALERT: RAMPUR SECTOR",
                                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.red.shade900),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                "3 URGENT and 2 HIGH risk cases identified in Rampur village within 48 hours. Active Case Finding (ACF) campaign recommended.",
                                style: TextStyle(fontSize: 12, color: Colors.red.shade800, height: 1.3),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Triage Tier Breakdown
                  Container(
                    padding: const EdgeInsets.all(20),
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
                        const Text("Triage Risk Stratification", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.obsidianNavy)),
                        const SizedBox(height: 16),
                        _buildTierBar("URGENT (Red Flag Override)", _statsData?['tier_counts']?['URGENT'] ?? 9, 39, AppTheme.tierUrgent),
                        _buildTierBar("HIGH RISK (CBNAAT Referral)", _statsData?['tier_counts']?['HIGH'] ?? 6, 39, AppTheme.tierHigh),
                        _buildTierBar("HIGH-RISK SCREENING (HIV/Contact)", _statsData?['tier_counts']?['HIGH_RISK_SCREENING'] ?? 6, 39, AppTheme.tierHighRisk),
                        _buildTierBar("MODERATE RISK (PHC Clinical)", _statsData?['tier_counts']?['MODERATE'] ?? 10, 39, AppTheme.tierModerate),
                        _buildTierBar("LOW RISK (Routine Hygiene)", _statsData?['tier_counts']?['LOW'] ?? 8, 39, AppTheme.tierLow),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Village-Level Caseload Matrix
                  Container(
                    padding: const EdgeInsets.all(20),
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
                        const Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text("Village Screening Distribution", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.obsidianNavy)),
                            Icon(Icons.location_on_rounded, color: AppTheme.obsidianNavy, size: 20),
                          ],
                        ),
                        const Divider(height: 24),
                        ...(_statsData?['screenings_by_village'] as Map<String, dynamic>? ?? {}).entries.map((entry) {
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.holiday_village_rounded, size: 18, color: AppTheme.textMuted),
                                    const SizedBox(width: 10),
                                    Text(entry.key, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: AppTheme.obsidianNavy)),
                                  ],
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: AppTheme.pastelBlue,
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: Text(
                                    "${entry.value} screenings",
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: AppTheme.obsidianNavy),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildTierBar(String label, int count, int total, Color color) {
    final pct = total > 0 ? count / total : 0.0;

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
              Text("$count (${(pct * 100).toInt()}%)", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: color)),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: pct,
              minHeight: 8,
              backgroundColor: Colors.grey.shade200,
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
        ],
      ),
    );
  }
}
