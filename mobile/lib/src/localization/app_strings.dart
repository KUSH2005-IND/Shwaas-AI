enum AppLanguage { en, hi }


class AppStrings {
  static AppLanguage currentLanguage = AppLanguage.en;

  static final Map<String, Map<AppLanguage, String>> _localizedValues = {
    // App Header & Brand
    'app_title': {
      AppLanguage.en: 'ShwaasAI',
      AppLanguage.hi: 'श्वास एआई',
    },
    'app_subtitle': {
      AppLanguage.en: 'Two-Channel Tuberculosis Triage System',
      AppLanguage.hi: 'दो-स्तरीय क्षयरोग (टीबी) स्क्रीनिंग प्रणाली',
    },
    'tagline': {
      AppLanguage.en: 'Frontline ASHA Screening Assistant',
      AppLanguage.hi: 'आशा कार्यकर्ता स्क्रीनिंग सहायक',
    },

    // Login & Auth
    'login_title': {
      AppLanguage.en: 'Health Worker Login',
      AppLanguage.hi: 'स्वास्थ्य कार्यकर्ता लॉगिन',
    },
    'username': {
      AppLanguage.en: 'Worker ID / Username',
      AppLanguage.hi: 'कार्यकर्ता आईडी / उपयोगकर्ता नाम',
    },
    'password': {
      AppLanguage.en: 'PIN / Password',
      AppLanguage.hi: 'पिन / पासवर्ड',
    },
    'login_btn': {
      AppLanguage.en: 'Login to Start Screening',
      AppLanguage.hi: 'स्क्रीनिंग शुरू करने के लिए लॉगिन करें',
    },
    'server_url': {
      AppLanguage.en: 'Server URL',
      AppLanguage.hi: 'सर्वर यूआरएल',
    },
    'demo_mode': {
      AppLanguage.en: 'Offline Demo Mode',
      AppLanguage.hi: 'ऑफलाइन डेमो मोड',
    },
    'demo_mode_desc': {
      AppLanguage.en: 'Uses local mock engine for testing without live server',
      AppLanguage.hi: 'बिना लाइव सर्वर के परीक्षण हेतु स्थानीय मॉक का उपयोग करें',
    },

    // Consent Screen
    'consent_title': {
      AppLanguage.en: 'Informed Patient Consent',
      AppLanguage.hi: 'रोगी की सूचित सहमति',
    },
    'consent_desc': {
      AppLanguage.en: 'Before proceeding, read the following statement to the patient in their primary language and ensure understanding:',
      AppLanguage.hi: 'आगे बढ़ने से पहले, रोगी को उनकी प्राथमिक भाषा में निम्नलिखित पढ़कर सुनाएं और समझ सुनिश्चित करें:',
    },
    'consent_clause_1': {
      AppLanguage.en: 'This tool is a screening assistant for frontline prioritization, NOT a final medical diagnosis.',
      AppLanguage.hi: 'यह टूल प्राथमिक स्वास्थ्य जांच और प्राथमिकता तय करने का सहायक है, अंतिम चिकित्सीय निदान नहीं।',
    },
    'consent_clause_2': {
      AppLanguage.en: 'Your 3-second cough audio will be analyzed for acoustic patterns and deleted immediately. No raw voice recordings are stored.',
      AppLanguage.hi: 'आपकी 3 सेकंड की खांसी की आवाज का विश्लेषण किया जाएगा और तुरंत हटा दिया जाएगा। कोई आवाज रिकॉर्डिंग सुरक्षित नहीं रखी जाएगी।',
    },
    'consent_clause_3': {
      AppLanguage.en: 'High-risk results require confirmatory CBNAAT/sputum testing at the nearest Primary Health Center (PHC).',
      AppLanguage.hi: 'उच्च जोखिम परिणामों के लिए निकटतम प्राथमिक स्वास्थ्य केंद्र (PHC) में सीबीएनएएटी/बलगम जांच आवश्यक होगी।',
    },
    'consent_checkbox': {
      AppLanguage.en: 'Patient understands and has granted verbal/written consent.',
      AppLanguage.hi: 'रोगी ने समझ लिया है और मौखिक/लिखित सहमति दी है।',
    },
    'continue_btn': {
      AppLanguage.en: 'Continue to Intake',
      AppLanguage.hi: 'आगे बढ़ें',
    },

    // Demographics
    'demographics_title': {
      AppLanguage.en: 'Patient Intake',
      AppLanguage.hi: 'रोगी की प्रारंभिक जानकारी',
    },
    'age_label': {
      AppLanguage.en: 'Patient Age (Years)',
      AppLanguage.hi: 'रोगी की आयु (वर्ष)',
    },
    'sex_label': {
      AppLanguage.en: 'Biological Sex',
      AppLanguage.hi: 'लिंग',
    },
    'sex_male': {
      AppLanguage.en: 'Male',
      AppLanguage.hi: 'पुरुष',
    },
    'sex_female': {
      AppLanguage.en: 'Female',
      AppLanguage.hi: 'महिला',
    },
    'sex_other': {
      AppLanguage.en: 'Other / Prefer not to say',
      AppLanguage.hi: 'अन्य / बताना नहीं चाहते',
    },
    'village_label': {
      AppLanguage.en: 'Village / Sector',
      AppLanguage.hi: 'गांव / क्षेत्र',
    },
    'pediatric_warning_title': {
      AppLanguage.en: 'Pediatric Patient Detected',
      AppLanguage.hi: 'बाल रोगी (18 वर्ष से कम)',
    },
    'pediatric_warning_desc': {
      AppLanguage.en: 'Patient is under 18 years. WHO guidelines mandate routing pediatric patients directly to the specialized Pediatric TB Clinical Protocol.',
      AppLanguage.hi: 'रोगी 18 वर्ष से कम उम्र का है। डब्लूएचओ दिशानिर्देशों के अनुसार बाल रोगियों को सीधे बाल चिकित्सा टीबी प्रोटोकॉल में भेजा जाना आवश्यक है।',
    },

    // Medical Document & Prescription OCR Scanner (Optional)
    'ocr_title': {
      AppLanguage.en: 'Medical Document & Slip OCR',
      AppLanguage.hi: 'चिकित्सा पर्ची एवं रिपोर्ट स्कैनर',
    },
    'ocr_optional_badge': {
      AppLanguage.en: 'Optional Step',
      AppLanguage.hi: 'वैकल्पिक चरण',
    },
    'ocr_desc': {
      AppLanguage.en: 'If the patient has a previous OPD slip, lab report, or Nikshay card, capture it to auto-extract symptoms and clinical history:',
      AppLanguage.hi: 'यदि रोगी के पास पूर्व ओपीडी पर्ची, लैब रिपोर्ट या निक्षय कार्ड है, तो लक्षण स्वतः प्राप्त करने हेतु फोटो खींचें:',
    },
    'ocr_skip_btn': {
      AppLanguage.en: 'Skip & Enter Survey Manually',
      AppLanguage.hi: 'छोड़ें और मैन्युअल प्रश्नावली भरें',
    },
    'ocr_camera_btn': {
      AppLanguage.en: 'Scan with Camera',
      AppLanguage.hi: 'कैमरे से फोटो लें',
    },
    'ocr_gallery_btn': {
      AppLanguage.en: 'Pick from Gallery',
      AppLanguage.hi: 'गैलरी से चुनें',
    },
    'ocr_sample_btn': {
      AppLanguage.en: 'Try Sample OPD Prescription (Demo)',
      AppLanguage.hi: 'नमूना ओपीडी पर्ची लोड करें (डेमो)',
    },
    'ocr_analyzing': {
      AppLanguage.en: 'Running Optical Character Recognition & Clinical Entity Extraction...',
      AppLanguage.hi: 'ऑप्टिकल कैरेक्टर रिकॉग्निशन एवं लक्षण निष्कर्षण जारी है...',
    },
    'ocr_detected_heading': {
      AppLanguage.en: 'Extracted Clinical Symptoms & Comorbidities',
      AppLanguage.hi: 'पहचाने गए चिकित्सीय लक्षण एवं स्थितियां',
    },
    'ocr_apply_btn': {
      AppLanguage.en: 'Apply Extracted Answers & Review (Survey)',
      AppLanguage.hi: 'पहचाने गए उत्तर लागू करें और प्रश्नावली में समीक्षा करें',
    },

    // Questionnaire
    'quiz_title': {

      AppLanguage.en: 'WHO Clinical Symptom Questionnaire',
      AppLanguage.hi: 'डब्लूएचओ लक्षण प्रश्नावली',
    },
    'question_counter': {
      AppLanguage.en: 'Question {current} of {total}',
      AppLanguage.hi: 'प्रश्न {current} / {total}',
    },
    'btn_yes': {
      AppLanguage.en: 'Yes (हाँ)',
      AppLanguage.hi: 'हाँ (Yes)',
    },
    'btn_no': {
      AppLanguage.en: 'No (नहीं)',
      AppLanguage.hi: 'नहीं (No)',
    },
    'btn_unsure': {
      AppLanguage.en: 'Unsure (अस्पष्ट)',
      AppLanguage.hi: 'अस्पष्ट (Unsure)',
    },
    'red_flag_alert': {
      AppLanguage.en: 'Urgent Red Flag: Coughing blood warrants immediate clinical evaluation.',
      AppLanguage.hi: 'आपातकालीन चेतावनी: खून की खांसी होने पर तत्काल अस्पताल जाने की आवश्यकता है।',
    },

    // Audio Recorder
    'recorder_title': {
      AppLanguage.en: 'Acoustic Cough Capture',
      AppLanguage.hi: 'खांसी ध्वनि रिकॉर्डिंग',
    },
    'audio_source_label': {
      AppLanguage.en: 'Audio Source',
      AppLanguage.hi: 'ऑडियो स्रोत',
    },
    'source_phone_mic': {
      AppLanguage.en: 'Phone Microphone',
      AppLanguage.hi: 'फोन माइक्रोफोन',
    },
    'source_device_wifi': {
      AppLanguage.en: 'ESP32 Device (Wi-Fi)',
      AppLanguage.hi: 'ईएसपी32 यंत्र (वाई-फाई)',
    },
    'source_sample_audio': {
      AppLanguage.en: 'Demo Sample Cough',
      AppLanguage.hi: 'डेमो नमूना खांसी',
    },
    'record_instructions': {
      AppLanguage.en: 'Ask the patient to cough forcefully 2–3 times into the microphone (distance ~15 cm).',
      AppLanguage.hi: 'रोगी से कहें कि वे माइक से 15 सेमी की दूरी पर 2-3 बार तेज खांसी करें।',
    },
    'tap_to_record': {
      AppLanguage.en: 'Tap to Record (3s)',
      AppLanguage.hi: 'रिकॉर्ड करने के लिए दबाएं (3 सेकंड)',
    },
    'recording_in_progress': {
      AppLanguage.en: 'Recording cough acoustics... Please cough now!',
      AppLanguage.hi: 'रिकॉर्डिंग जारी है... कृपया अब खांसें!',
    },
    'playback_review': {
      AppLanguage.en: 'Listen to Cough Audio',
      AppLanguage.hi: 'रिकॉर्ड की गई आवाज सुनें',
    },
    'rerecord_btn': {
      AppLanguage.en: 'Re-record',
      AppLanguage.hi: 'फिर से रिकॉर्ड करें',
    },
    'submit_screening_btn': {
      AppLanguage.en: 'Submit for Two-Channel Triage',
      AppLanguage.hi: 'स्क्रीनिंग हेतु सबमिट करें',
    },
    'clipping_error': {
      AppLanguage.en: 'Audio distortion / clipping detected. Please hold the phone slightly further away.',
      AppLanguage.hi: 'आवाज में विकृति/क्लिपिंग पाई गई। कृपया फोन को थोड़ा दूर रखकर पुनः रिकॉर्ड करें।',
    },
    'silence_error': {
      AppLanguage.en: 'Audio was too quiet or silence detected. Please hold the phone closer (~15 cm).',
      AppLanguage.hi: 'आवाज बहुत धीमी पाई गई। कृपया फोन को मुंह के करीब (~15 सेमी) रखें।',
    },

    // Results Screen
    'result_title': {
      AppLanguage.en: 'Triage & Referral Result',
      AppLanguage.hi: 'स्क्रीनिंग एवं रेफरल परिणाम',
    },
    'patient_code_label': {
      AppLanguage.en: 'Patient Anonymous Code',
      AppLanguage.hi: 'रोगी पहचान कोड',
    },
    'tier_low': {
      AppLanguage.en: 'LOW RISK',
      AppLanguage.hi: 'कम जोखिम (LOW)',
    },
    'tier_moderate': {
      AppLanguage.en: 'MODERATE RISK',
      AppLanguage.hi: 'मध्यम जोखिम (MODERATE)',
    },
    'tier_high': {
      AppLanguage.en: 'HIGH RISK',
      AppLanguage.hi: 'उच्च जोखिम (HIGH)',
    },
    'tier_urgent': {
      AppLanguage.en: 'URGENT RED FLAG',
      AppLanguage.hi: 'आपातकालीन चेतावनी (URGENT)',
    },
    'tier_high_risk_screening': {
      AppLanguage.en: 'HIGH-RISK SCREENING',
      AppLanguage.hi: 'प्राथमिकता जांच (HIGH RISK)',
    },
    'clinical_score_label': {
      AppLanguage.en: 'Clinical Symptom Score',
      AppLanguage.hi: 'लक्षण स्कोर',
    },
    'audio_score_label': {
      AppLanguage.en: 'Acoustic Abnormality Proxy',
      AppLanguage.hi: 'खांसी ध्वनि असामान्यता सूचकांक',
    },
    'gradcam_title': {
      AppLanguage.en: 'Grad-CAM Spectrogram Heatmap',
      AppLanguage.hi: 'ग्रैड-कैम स्पेक्ट्रोग्राम हीटमैप',
    },
    'gradcam_caption': {
      AppLanguage.en: 'Red and orange regions show acoustic frequencies triggering AI model attention.',
      AppLanguage.hi: 'लाल और नारंगी क्षेत्र मॉडल द्वारा पहचानी गई असामान्य ध्वनियों को दर्शाते हैं।',
    },
    'disclaimer_text': {
      AppLanguage.en: 'Screening support tool, not a diagnostic confirmation. Final medical decision requires clinical sputum/CBNAAT testing.',
      AppLanguage.hi: 'यह स्क्रीनिंग सहायता टूल है, चिकित्सीय निदान नहीं। अंतिम पुष्टि हेतु बलगम/सीबीएनएएटी जांच अनिवार्य है।',
    },
    'new_screening_btn': {
      AppLanguage.en: 'Start New Screening',
      AppLanguage.hi: 'नई स्क्रीनिंग शुरू करें',
    },
    'view_history_btn': {
      AppLanguage.en: 'View Offline History & Sync',
      AppLanguage.hi: 'इतिहास और सिंक देखें',
    },

    // History & Sync
    'history_title': {
      AppLanguage.en: 'Screening History & Offline Queue',
      AppLanguage.hi: 'स्क्रीनिंग इतिहास एवं ऑफलाइन कतार',
    },
    'sync_all_btn': {
      AppLanguage.en: 'Sync All Pending Items',
      AppLanguage.hi: 'सभी लंबित रिकॉर्ड सिंक करें',
    },
    'status_synced': {
      AppLanguage.en: 'Synced',
      AppLanguage.hi: 'सिंक हो गया',
    },
    'status_pending': {
      AppLanguage.en: 'Pending Sync',
      AppLanguage.hi: 'सिंक होना बाकी',
    },
    'no_records': {
      AppLanguage.en: 'No screening records yet.',
      AppLanguage.hi: 'अभी तक कोई स्क्रीनिंग रिकॉर्ड नहीं है।',
    },
  };

  static String get(String key) {
    final entry = _localizedValues[key];
    if (entry == null) return key;
    return entry[currentLanguage] ?? entry[AppLanguage.en] ?? key;
  }
}
