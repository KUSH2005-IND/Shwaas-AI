class ScreeningInput {

  final int age;
  final String sex;
  final String village;
  final Map<String, int> answers;
  final String audioPath;
  final String audioSource; // "phone_mic", "device_wifi", "sample_audio"
  final bool includeGradcam;

  ScreeningInput({
    required this.age,
    required this.sex,
    required this.village,
    required this.answers,
    required this.audioPath,
    this.audioSource = "phone_mic",
    this.includeGradcam = true,
  });

  Map<String, dynamic> toJson() => {
    'age': age,
    'sex': sex,
    'village': village,
    'answers': answers,
    'audioPath': audioPath,
    'audioSource': audioSource,
    'includeGradcam': includeGradcam,
  };

  factory ScreeningInput.fromJson(Map<String, dynamic> json) => ScreeningInput(
    age: json['age'] ?? 18,
    sex: json['sex'] ?? 'prefer_not_to_say',
    village: json['village'] ?? 'Unknown',
    answers: Map<String, int>.from(json['answers'] ?? {}),
    audioPath: json['audioPath'] ?? '',
    audioSource: json['audioSource'] ?? 'phone_mic',
    includeGradcam: json['includeGradcam'] ?? true,
  );
}

class ScreeningResult {
  final String sessionId;
  final String patientCode;
  final int age;
  final String sex;
  final String village;
  final int clinicalScore;
  final int questionnaireMax;
  final bool redFlagDetected;
  final bool highRiskFactorsPresent;
  final List<String> uncertainSymptoms;
  final double audioRawScore;
  final double audioCalibratedScore;
  final String tier; // LOW, MODERATE, HIGH, URGENT, HIGH_RISK_SCREENING
  final String pathwayCode;
  final String recommendedPathway;
  final String? gradcamImage; // base64 data URI
  final DateTime createdAt;
  final bool isSynced;

  ScreeningResult({
    required this.sessionId,
    required this.patientCode,
    required this.age,
    required this.sex,
    required this.village,
    required this.clinicalScore,
    this.questionnaireMax = 18,
    required this.redFlagDetected,
    required this.highRiskFactorsPresent,
    required this.uncertainSymptoms,
    required this.audioRawScore,
    required this.audioCalibratedScore,
    required this.tier,
    required this.pathwayCode,
    required this.recommendedPathway,
    this.gradcamImage,
    required this.createdAt,
    this.isSynced = true,
  });

  Map<String, dynamic> toJson() => {
    'sessionId': sessionId,
    'patientCode': patientCode,
    'age': age,
    'sex': sex,
    'village': village,
    'clinicalScore': clinicalScore,
    'questionnaireMax': questionnaireMax,
    'redFlagDetected': redFlagDetected,
    'highRiskFactorsPresent': highRiskFactorsPresent,
    'uncertainSymptoms': uncertainSymptoms,
    'audioRawScore': audioRawScore,
    'audioCalibratedScore': audioCalibratedScore,
    'tier': tier,
    'pathwayCode': pathwayCode,
    'recommendedPathway': recommendedPathway,
    'gradcamImage': gradcamImage,
    'createdAt': createdAt.toIso8601String(),
    'isSynced': isSynced,
  };

  factory ScreeningResult.fromJson(Map<String, dynamic> json) => ScreeningResult(
    sessionId: json['session_id'] ?? json['sessionId'] ?? '',
    patientCode: json['patient_code'] ?? json['patientCode'] ?? 'PAT-UNKNOWN',
    age: json['patient_demographics']?['age'] ?? json['age'] ?? 18,
    sex: json['patient_demographics']?['sex'] ?? json['sex'] ?? 'prefer_not_to_say',
    village: json['patient_demographics']?['village'] ?? json['village'] ?? 'Unknown',
    clinicalScore: json['questionnaire_score'] ?? json['clinicalScore'] ?? 0,
    questionnaireMax: json['questionnaire_max'] ?? json['questionnaireMax'] ?? 18,
    redFlagDetected: json['red_flag_detected'] ?? json['redFlagDetected'] ?? false,
    highRiskFactorsPresent: json['high_risk_factors_present'] ?? json['highRiskFactorsPresent'] ?? false,
    uncertainSymptoms: List<String>.from(json['uncertain_symptoms'] ?? json['uncertainSymptoms'] ?? []),
    audioRawScore: (json['audio_model']?['raw_score'] ?? json['audioRawScore'] ?? 0.0).toDouble(),
    audioCalibratedScore: (json['audio_model']?['calibrated_score'] ?? json['audioCalibratedScore'] ?? 0.0).toDouble(),
    tier: json['fusion']?['tier'] ?? json['tier'] ?? 'LOW',
    pathwayCode: json['pathway_code'] ?? json['pathwayCode'] ?? 'STANDARD_HYGIENE',
    recommendedPathway: json['recommended_pathway'] ?? json['recommendedPathway'] ?? '',
    gradcamImage: json['gradcam_image'] ?? json['gradcamImage'],
    createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : (json['createdAt'] != null ? DateTime.parse(json['createdAt']) : DateTime.now()),
    isSynced: json['isSynced'] ?? true,
  );
}
