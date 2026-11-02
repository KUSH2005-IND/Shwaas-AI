import 'package:flutter/material.dart';
import 'package:mobile/src/localization/app_strings.dart';
import 'package:mobile/src/models/screening_model.dart';
import 'package:mobile/src/services/offline_storage.dart';
import 'package:mobile/src/theme/app_theme.dart';
import 'package:mobile/src/screens/result_screen.dart';

class HistoryQueueScreen extends StatefulWidget {
  const HistoryQueueScreen({super.key});

  @override
  State<HistoryQueueScreen> createState() => _HistoryQueueScreenState();
}

class _HistoryQueueScreenState extends State<HistoryQueueScreen> {
  List<ScreeningResult> _history = [];
  bool _isLoading = true;
  bool _isSyncing = false;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => _isLoading = true);
    final items = await OfflineStorage.getHistory();
    setState(() {
      _history = items;
      _isLoading = false;
    });
  }

  Future<void> _syncPending() async {
    setState(() => _isSyncing = true);
    final count = await OfflineStorage.syncPendingScreenings();
    await _loadHistory();
    setState(() => _isSyncing = false);

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text("Synced $count offline screenings to server.")),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pendingCount = _history.where((s) => !s.isSynced).length;

    return Scaffold(
      backgroundColor: AppTheme.backgroundSlate,
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundSlate,
        elevation: 0,
        centerTitle: true,
        title: Text(
          AppStrings.get('history_title'),
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
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                if (pendingCount > 0)
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: AppTheme.pastelPeach,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.cloud_upload_rounded, color: Color(0xFFB45309)),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            "$pendingCount screenings pending sync",
                            style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFFB45309), fontSize: 13),
                          ),
                        ),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.obsidianNavy,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                          ),
                          onPressed: _isSyncing ? null : _syncPending,
                          child: _isSyncing
                              ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                              : const Text("Sync Now", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
                        ),
                      ],
                    ),
                  ),

                Expanded(
                  child: _history.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.folder_open_rounded, size: 64, color: Colors.grey.shade400),
                              const SizedBox(height: 12),
                              Text(AppStrings.get('no_records'), style: const TextStyle(color: AppTheme.textMuted)),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          itemCount: _history.length,
                          itemBuilder: (ctx, idx) {
                            final item = _history[idx];
                            final tierColor = AppTheme.getTierColor(item.tier);

                            // Interexy appointment pastel cards
                            Color cardBg;
                            switch (item.tier.toUpperCase()) {
                              case 'LOW':
                                cardBg = AppTheme.pastelMint;
                                break;
                              case 'MODERATE':
                                cardBg = AppTheme.pastelPeach;
                                break;
                              default:
                                cardBg = AppTheme.pastelBlue;
                            }

                            return Container(
                              margin: const EdgeInsets.only(bottom: 14),
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: cardBg,
                                borderRadius: BorderRadius.circular(24),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withValues(alpha: 0.04),
                                    blurRadius: 8,
                                    offset: const Offset(0, 2),
                                  ),
                                ],
                              ),
                              child: Row(
                                children: [
                                  // Patient Circular Avatar
                                  Container(
                                    width: 48,
                                    height: 48,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: Colors.white,
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black.withValues(alpha: 0.06),
                                          blurRadius: 6,
                                        ),
                                      ],
                                    ),
                                    child: Center(
                                      child: Icon(Icons.person_rounded, color: tierColor, size: 26),
                                    ),
                                  ),
                                  const SizedBox(width: 14),

                                  // Patient Metadata
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          item.patientCode,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w800,
                                            fontSize: 15,
                                            color: AppTheme.obsidianNavy,
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          "Village: ${item.village} • ${item.age} yrs",
                                          style: const TextStyle(fontSize: 12, color: Color(0xFF334155), fontWeight: FontWeight.w500),
                                        ),
                                        const SizedBox(height: 8),
                                        // Interexy-style clock / score pill
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                          decoration: BoxDecoration(
                                            color: Colors.white.withValues(alpha: 0.8),
                                            borderRadius: BorderRadius.circular(14),
                                          ),
                                          child: Row(
                                            mainAxisSize: MainAxisSize.min,
                                            children: [
                                              Icon(Icons.query_stats_rounded, size: 12, color: tierColor),
                                              const SizedBox(width: 4),
                                              Text(
                                                "${item.tier} • ${(item.audioCalibratedScore * 100).toInt()}% AI",
                                                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: tierColor),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),

                                  // Interexy Obsidian Capsule "Consult" / "View" Button
                                  GestureDetector(
                                    onTap: () {
                                      Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (_) => ResultScreen(
                                            result: item,
                                            workerInfo: const {"full_name": "Local Viewer", "phc_center": "Stored Record"},
                                          ),
                                        ),
                                      );
                                    },
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 22),
                                      decoration: BoxDecoration(
                                        color: AppTheme.obsidianNavy,
                                        borderRadius: BorderRadius.circular(20),
                                      ),
                                      child: const Text(
                                        "View",
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13,
                                          letterSpacing: 0.3,
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }
}
