import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mobile/src/models/screening_model.dart';

class OfflineStorage {
  static const String prefHistoryKey = "screening_history";

  static Future<void> saveScreening(ScreeningResult result) async {
    final prefs = await SharedPreferences.getInstance();
    final historyJson = prefs.getStringList(prefHistoryKey) ?? [];
    
    // Add new screening at the beginning
    historyJson.insert(0, jsonEncode(result.toJson()));
    
    // Keep last 100 screenings locally
    if (historyJson.length > 100) {
      historyJson.removeLast();
    }
    
    await prefs.setStringList(prefHistoryKey, historyJson);
  }

  static Future<List<ScreeningResult>> getHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final historyJson = prefs.getStringList(prefHistoryKey) ?? [];
    
    return historyJson.map((item) {
      try {
        final map = jsonDecode(item);
        return ScreeningResult.fromJson(map);
      } catch (e) {
        return null;
      }
    }).whereType<ScreeningResult>().toList();
  }

  static Future<int> getPendingSyncCount() async {
    final history = await getHistory();
    return history.where((s) => !s.isSynced).length;
  }

  static Future<int> syncPendingScreenings() async {
    final prefs = await SharedPreferences.getInstance();
    final history = await getHistory();
    int syncedCount = 0;

    final updatedHistory = <ScreeningResult>[];

    for (var screening in history) {
      if (!screening.isSynced) {
        // Mark as synced locally
        final syncedScreening = ScreeningResult(
          sessionId: screening.sessionId,
          patientCode: screening.patientCode,
          age: screening.age,
          sex: screening.sex,
          village: screening.village,
          clinicalScore: screening.clinicalScore,
          questionnaireMax: screening.questionnaireMax,
          redFlagDetected: screening.redFlagDetected,
          highRiskFactorsPresent: screening.highRiskFactorsPresent,
          uncertainSymptoms: screening.uncertainSymptoms,
          audioRawScore: screening.audioRawScore,
          audioCalibratedScore: screening.audioCalibratedScore,
          tier: screening.tier,
          pathwayCode: screening.pathwayCode,
          recommendedPathway: screening.recommendedPathway,
          gradcamImage: screening.gradcamImage,
          createdAt: screening.createdAt,
          isSynced: true,
        );
        updatedHistory.add(syncedScreening);
        syncedCount++;
      } else {
        updatedHistory.add(screening);
      }
    }

    final rawJsonList = updatedHistory.map((s) => jsonEncode(s.toJson())).toList();
    await prefs.setStringList(prefHistoryKey, rawJsonList);
    return syncedCount;
  }
}
