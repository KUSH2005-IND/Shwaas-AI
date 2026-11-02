import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:mobile/src/models/question_model.dart';

class ExtractedClinicalEntity {
  final String questionKey;
  final String matchedKeyword;
  final String symptomTitle;
  final bool isRedFlag;
  final bool isHighRisk;

  ExtractedClinicalEntity({
    required this.questionKey,
    required this.matchedKeyword,
    required this.symptomTitle,
    this.isRedFlag = false,
    this.isHighRisk = false,
  });
}

class OcrExtractionResult {
  final String rawText;
  final Map<String, int> answers;
  final List<ExtractedClinicalEntity> entities;
  final bool redFlagDetected;

  OcrExtractionResult({
    required this.rawText,
    required this.answers,
    required this.entities,
    required this.redFlagDetected,
  });
}

class PrescriptionOcrEngine {
  // Clinical NLP keyword matching patterns
  static final Map<String, List<String>> _symptomKeywords = {
    'cough_duration': [
      'cough', 'khansi', 'chronic cough', 'cough > 2', 'cough > 3', 'coughing', 
      'expectoration', 'productive cough', 'persistent cough', 'tussis', '2 weeks'
    ],
    'fever': [
      'fever', 'pyrexia', 'bukhar', 'evening rise', 'chills', 'febrile', 'temp >', 'hyperthermia'
    ],
    'night_sweats': [
      'night sweat', 'night sweats', 'diaphoresis', 'drenching sweat', 'pasina'
    ],
    'weight_loss': [
      'weight loss', 'wt loss', 'loss of weight', 'loss of appetite', 'anorexia', 'wasting', 'cachexia'
    ],
    'hemoptysis': [
      'hemoptysis', 'haemoptysis', 'blood in sputum', 'blood in cough', 'streaks of blood', 'khoon'
    ],
    'tb_contact': [
      'tb contact', 'contact with tb', 'household tb', 'nikshay', 'pulmonary tb contact', 'tb family'
    ],
    'diabetes': [
      'diabetes', 'diabetic', 'dm2', 't2dm', 'type 2 diabetes', 'metformin', 'glycomet', 'hba1c', 'sugar'
    ],
    'hiv': [
      'hiv', 'hiv positive', 'antiretroviral', 'art therapy', 'elisa positive'
    ],
    'immunosuppression': [
      'steroid', 'prednisolone', 'dexamethasone', 'chemotherapy', 'corticosteroid', 'immunosuppressive'
    ],
    'silica_exposure': [
      'silicosis', 'silica', 'mining', 'stone crusher', 'pottery worker', 'quarry', 'dust exposure'
    ],
  };

  static OcrExtractionResult processText(String rawText) {
    final lower = rawText.toLowerCase();
    final Map<String, int> answers = {};
    final List<ExtractedClinicalEntity> detectedEntities = [];
    bool redFlag = false;

    // Default all 10 to 0
    for (var q in allQuestions) {
      answers[q.key] = 0;
    }

    _symptomKeywords.forEach((key, keywords) {
      for (var kw in keywords) {
        if (lower.contains(kw)) {
          answers[key] = 2; // Yes

          final qMeta = allQuestions.firstWhere((q) => q.key == key, orElse: () => allQuestions.first);
          if (qMeta.isRedFlag) redFlag = true;

          detectedEntities.add(
            ExtractedClinicalEntity(
              questionKey: key,
              matchedKeyword: kw,
              symptomTitle: qMeta.titleEn,
              isRedFlag: qMeta.isRedFlag,
              isHighRisk: qMeta.isHighRisk,
            ),
          );
          break; // Stop after first match for this question
        }
      }
    });

    return OcrExtractionResult(
      rawText: rawText,
      answers: answers,
      entities: detectedEntities,
      redFlagDetected: redFlag,
    );
  }

  /// Scans an image file using on-device Google ML Kit with backend Tesseract fallback.
  /// If the image is a blank/dark/random non-document photo, it extracts no text and returns 0 entities.
  static Future<OcrExtractionResult> scanImage(File imageFile, {String? serverUrl}) async {
    String extractedText = "";

    // 1. Try On-Device Google ML Kit Text Recognition
    try {
      final inputImage = InputImage.fromFilePath(imageFile.path);
      final textRecognizer = TextRecognizer(script: TextRecognitionScript.latin);
      final RecognizedText recognizedText = await textRecognizer.processImage(inputImage);
      extractedText = recognizedText.text.trim();
      await textRecognizer.close();
    } catch (e) {
      debugPrint("On-device Google ML Kit recognition: $e");
    }

    // 2. Fallback to Server Tesseract OCR endpoint if on-device extracted nothing
    if (extractedText.isEmpty) {
      try {
        final targetUrl = serverUrl ?? "http://127.0.0.1:8000";
        final uri = Uri.parse("$targetUrl/ocr/scan");
        final request = http.MultipartRequest("POST", uri);
        request.files.add(await http.MultipartFile.fromPath("image", imageFile.path));
        final streamed = await request.send().timeout(const Duration(seconds: 5));
        if (streamed.statusCode == 200) {
          final body = await streamed.stream.bytesToString();
          final data = jsonDecode(body);
          if (data is Map && data["text"] != null) {
            extractedText = (data["text"] as String).trim();
          }
        }
      } catch (e) {
        debugPrint("Server OCR fallback: $e");
      }
    }

    // 3. Process recognized text with clinical rules (empty text -> 0 entities)
    return processText(extractedText);
  }

  // Preloaded sample hospital prescriptions for offline demo presentation
  static const List<Map<String, String>> demoPrescriptions = [
    {
      "title": "District Hospital OPD Slip (Chronic Cough & Diabetes)",
      "hospital": "Rampur District Civil Hospital • Outpatient Dept",
      "text": """RAMPUR DISTRICT CIVIL HOSPITAL - OPD SLIP
Date: 28/10/2026 | Dept: Pulmonary Medicine
Patient: Ramesh Kumar (Age: 46 / Male)
Chief Complaints:
- Chronic productive cough > 3 weeks, yellow expectoration.
- Recurrent evening pyrexia and fever with chills.
- Unintended weight loss of 4 kg over past month.
- Known Type 2 Diabetes Mellitus (T2DM) on Tab Metformin 500mg.
- Household TB contact: Brother treated for active pulmonary TB in 2024.
Advised:
1. Sputum CBNAAT / GeneXpert sample collection.
2. Chest X-Ray PA view."""
    },
    {
      "title": "Emergency Triage Note (Hemoptysis Red Flag)",
      "hospital": "Sub-District Hospital • Emergency Unit",
      "text": """SUB-DISTRICT HOSPITAL EMERGENCY CASUALTY NOTE
Patient: Sita Devi (Age: 38 / Female)
Presenting Condition:
- Acute episode of hemoptysis (fresh blood in cough / sputum).
- Drenching night sweats and high-grade fever for 10 days.
- Severe fatigue and loss of appetite.
- No history of silica mining or smoking.
Impression: High suspicion presumptive pulmonary TB with hemoptysis.
Plan: Immediate emergency triage, cross-match, urgent molecular testing."""
    },
    {
      "title": "PHC Routine Health Check (Routine Bronchitis)",
      "hospital": "Sundarpur Primary Health Centre",
      "text": """SUNDARPUR PRIMARY HEALTH CENTRE (PHC)
Patient: Manoj Verma (Age: 29 / Male)
Symptoms:
- Dry throat irritation and seasonal cough for 4 days.
- No fever, no weight loss, no night sweats.
- No TB contact in household. Non-diabetic.
Diagnosis: Seasonal acute viral bronchitis.
Advised: Steam inhalation, warm hydration, paracetamol SOS."""
    },
  ];
}
