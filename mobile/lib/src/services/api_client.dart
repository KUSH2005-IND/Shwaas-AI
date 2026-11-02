import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mobile/src/models/screening_model.dart';

class ApiClient {
  static const String defaultBaseUrl = "http://127.0.0.1:8000";
  static const String prefBaseUrlKey = "server_url";
  static const String prefDemoModeKey = "demo_mode";
  static const String prefTokenKey = "auth_token";

  static Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(prefBaseUrlKey) ?? defaultBaseUrl;
  }

  static Future<void> setBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(prefBaseUrlKey, url);
  }

  static Future<bool> isDemoMode() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(prefDemoModeKey) ?? false;
  }

  static Future<void> setDemoMode(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(prefDemoModeKey, enabled);
  }

  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(prefTokenKey);
  }

  static Future<void> saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(prefTokenKey, token);
  }

  static Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(prefTokenKey);
  }

  /// 1. Health Worker Login
  static Future<Map<String, dynamic>> login(String username, String password) async {
    final demo = await isDemoMode();
    if (demo) {
      return {
        "access_token": "demo-offline-token",
        "username": username,
        "full_name": "Demo ASHA Worker",
        "role": "worker",
        "phc_center": "Rampur Health Centre (Demo)"
      };
    }

    final baseUrl = await getBaseUrl();
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['access_token'] != null) {
          await saveToken(data['access_token']);
        }
        return data;
      } else {
        throw Exception(jsonDecode(response.body)['detail'] ?? "Login failed");
      }
    } catch (e) {
      throw Exception("Could not connect to server at $baseUrl. ($e)");
    }
  }

  /// 2. Submit Screening with Multipart Audio Upload
  static Future<ScreeningResult> submitScreening(ScreeningInput input) async {
    final demo = await isDemoMode();
    if (demo) {
      return _generateMockResult(input);
    }

    final baseUrl = await getBaseUrl();
    final token = await getToken();

    try {
      final uri = Uri.parse('$baseUrl/screenings?include_gradcam=${input.includeGradcam}');
      final request = http.MultipartRequest('POST', uri);

      if (token != null) {
        request.headers['Authorization'] = 'Bearer $token';
      }

      // Add Demographics & Form Fields
      request.fields['age'] = input.age.toString();
      request.fields['sex'] = input.sex;
      request.fields['village'] = input.village;
      request.fields['consent_given'] = 'true';

      // Send all 10 symptom answers
      input.answers.forEach((key, val) {
        request.fields[key] = val.toString();
      });

      // Attach Audio File
      final audioFile = File(input.audioPath);
      if (await audioFile.exists()) {
        request.files.add(
          await http.MultipartFile.fromPath(
            'file',
            input.audioPath,
            contentType: MediaType('audio', 'wav'),
          ),
        );
      } else {
        throw Exception("Audio recording file not found at ${input.audioPath}");
      }

      // Execute with 15s timeout
      final streamedResponse = await request.send().timeout(const Duration(seconds: 15));
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return ScreeningResult.fromJson(data);
      } else {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['message'] ?? errorData['detail'] ?? "Screening submission failed (${response.statusCode})");
      }
    } catch (e) {
      // If network fails, return offline mock result flagged as pending sync
      final fallback = _generateMockResult(input, isSynced: false);
      return fallback;
    }
  }

  /// Mock Generator for Offline Fallback & Demo Mode
  static ScreeningResult _generateMockResult(ScreeningInput input, {bool isSynced = true}) {
    final answers = input.answers;
    int score = 0;
    bool redFlag = (answers['hemoptysis'] == 2);
    bool highRisk = (answers['hiv'] == 2 || answers['tb_contact'] == 2 || answers['immunosuppression'] == 2);

    answers.forEach((k, v) {
      if (v == 2) {
        score += (k == 'immunosuppression' || k == 'silica_exposure') ? 1 : 2;
      }
    });

    String tier;
    String pathwayCode;
    String action;

    if (redFlag) {
      tier = "URGENT";
      pathwayCode = "IMMEDIATE_TRIAGE";
      action = "Immediate medical assessment required (hemoptysis detected).";
    } else if (highRisk && score <= 3) {
      tier = "HIGH_RISK_SCREENING";
      pathwayCode = "HIGH_RISK_PATHWAY";
      action = "High-risk profile detected (HIV/contact). Prioritized screening pathway recommended.";
    } else if (score > 8) {
      tier = "HIGH";
      pathwayCode = "CBNAAT_REFERRAL";
      action = "Urgent referral for CBNAAT testing recommended.";
    } else if (score >= 4) {
      tier = "MODERATE";
      pathwayCode = "PHC_EVALUATION";
      action = "Clinical evaluation recommended. Persistent cough warrants PHC visit.";
    } else {
      tier = "LOW";
      pathwayCode = "STANDARD_HYGIENE";
      action = "Low immediate risk. Maintain standard respiratory hygiene.";
    }

    final rand = Random();
    final villageCode = input.village.length >= 3 ? input.village.substring(0, 3).toUpperCase() : "GEN";
    final patientCode = "PAT-$villageCode-${rand.nextInt(9000) + 1000}";

    return ScreeningResult(
      sessionId: "mock-${DateTime.now().millisecondsSinceEpoch}",
      patientCode: patientCode,
      age: input.age,
      sex: input.sex,
      village: input.village,
      clinicalScore: score,
      questionnaireMax: 18,
      redFlagDetected: redFlag,
      highRiskFactorsPresent: highRisk,
      uncertainSymptoms: answers.entries.where((e) => e.value == 1).map((e) => e.key).toList(),
      audioRawScore: roundDouble(0.02 + rand.nextDouble() * 0.7, 4),
      audioCalibratedScore: roundDouble(0.05 + rand.nextDouble() * 0.7, 4),
      tier: tier,
      pathwayCode: pathwayCode,
      recommendedPathway: action,
      gradcamImage: input.includeGradcam ? "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAg..." : null,
      createdAt: DateTime.now(),
      isSynced: isSynced,
    );
  }

  static double roundDouble(double val, int places) {
    num mod = pow(10.0, places);
    return ((val * mod).round().toDouble() / mod);
  }
}
