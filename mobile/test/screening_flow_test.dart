import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/src/models/question_model.dart';
import 'package:mobile/src/models/screening_model.dart';
import 'package:mobile/src/services/audio_quality_checker.dart';
import 'package:mobile/src/services/prescription_ocr_engine.dart';

void main() {
  group('Clinical Questionnaire & Rules Tests', () {
    test('All 10 clinical symptoms defined with translations and weights', () {
      expect(allQuestions.length, 10);
      
      int totalMaxWeight = 0;
      for (var q in allQuestions) {
        expect(q.key.isNotEmpty, true);
        expect(q.titleEn.isNotEmpty, true);
        expect(q.titleHi.isNotEmpty, true);
        totalMaxWeight += q.weight;
      }
      
      // WHO aligned max score must be exactly 18 points
      expect(totalMaxWeight, 18);
    });

    test('Hemoptysis is correctly identified as emergency red flag', () {
      final hemoptysisQ = allQuestions.firstWhere((q) => q.key == 'hemoptysis');
      expect(hemoptysisQ.isRedFlag, true);
      expect(hemoptysisQ.weight, 2);
    });

    test('High-risk factors correctly identified', () {
      final hivQ = allQuestions.firstWhere((q) => q.key == 'hiv');
      final contactQ = allQuestions.firstWhere((q) => q.key == 'tb_contact');
      final immunoQ = allQuestions.firstWhere((q) => q.key == 'immunosuppression');

      expect(hivQ.isHighRisk, true);
      expect(contactQ.isHighRisk, true);
      expect(immunoQ.isHighRisk, true);
    });
  });

  group('Screening Result Serialization Tests', () {
    test('ScreeningResult serializes and deserializes cleanly without data loss', () {
      final now = DateTime.now();
      final original = ScreeningResult(
        sessionId: "test-session-uuid",
        patientCode: "PAT-RAM-1001",
        age: 45,
        sex: "female",
        village: "Rampur",
        clinicalScore: 8,
        questionnaireMax: 18,
        redFlagDetected: false,
        highRiskFactorsPresent: true,
        uncertainSymptoms: ["night_sweats"],
        audioRawScore: 0.72,
        audioCalibratedScore: 0.81,
        tier: "HIGH",
        pathwayCode: "CBNAAT_REFERRAL",
        recommendedPathway: "Urgent referral for CBNAAT testing recommended.",
        gradcamImage: "data:image/jpeg;base64,samplebase64",
        createdAt: now,
        isSynced: false,
      );

      final json = original.toJson();
      final restored = ScreeningResult.fromJson(json);

      expect(restored.sessionId, original.sessionId);
      expect(restored.patientCode, original.patientCode);
      expect(restored.clinicalScore, 8);
      expect(restored.tier, "HIGH");
      expect(restored.isSynced, false);
      expect(restored.uncertainSymptoms, ["night_sweats"]);
    });
  });

  group('Audio Quality Checker Verification', () {
    test('Rejects non-existent audio file', () async {
      final result = await AudioQualityChecker.verifyWav("non_existent_path.wav");
      expect(result.isValid, false);
      expect(result.message.contains("not found"), true);
    });

    test('Rejects corrupt or empty audio file', () async {
      final tempFile = File('/tmp/test_corrupt.wav');
      await tempFile.writeAsBytes([1, 2, 3]); // Less than 44 bytes

      final result = await AudioQualityChecker.verifyWav(tempFile.path);
      expect(result.isValid, false);
      expect(result.message.contains("corrupt"), true);

      if (await tempFile.exists()) await tempFile.delete();
    });
  });

  group('Prescription & Document OCR Engine Tests', () {
    test('Correctly extracts clinical entities from sample OPD slip', () {
      final sample = PrescriptionOcrEngine.demoPrescriptions[0]["text"]!;
      final result = PrescriptionOcrEngine.processText(sample);

      expect(result.answers['cough_duration'], 2);
      expect(result.answers['fever'], 2);
      expect(result.answers['weight_loss'], 2);
      expect(result.answers['diabetes'], 2);
      expect(result.answers['tb_contact'], 2);
      expect(result.redFlagDetected, false);
      expect(result.entities.length >= 4, true);
    });

    test('Correctly triggers red flag alert when hemoptysis is present in prescription', () {
      final redFlagSample = PrescriptionOcrEngine.demoPrescriptions[1]["text"]!;
      final result = PrescriptionOcrEngine.processText(redFlagSample);

      expect(result.redFlagDetected, true);
      expect(result.answers['hemoptysis'], 2);
    });

    test('Unrelated non-respiratory text returns zero prefilled symptoms', () {
      const benignText = "Patient visited for sprained ankle. Prescribed ibuprofen 400mg. Follow-up in 1 week.";
      final result = PrescriptionOcrEngine.processText(benignText);

      expect(result.redFlagDetected, false);
      expect(result.entities.isEmpty, true);
      for (var val in result.answers.values) {
        expect(val, 0);
      }
    });
  });
}
