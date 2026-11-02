import 'package:mobile/src/localization/app_strings.dart';

class ClinicalQuestion {
  final String key;
  final String titleEn;
  final String titleHi;
  final String descEn;
  final String descHi;
  final int weight;
  final bool isRedFlag;
  final bool isHighRisk;

  const ClinicalQuestion({
    required this.key,
    required this.titleEn,
    required this.titleHi,
    required this.descEn,
    required this.descHi,
    this.weight = 2,
    this.isRedFlag = false,
    this.isHighRisk = false,
  });

  String get title => AppStrings.currentLanguage == AppLanguage.hi ? titleHi : titleEn;
  String get description => AppStrings.currentLanguage == AppLanguage.hi ? descHi : descEn;
}

final List<ClinicalQuestion> allQuestions = [
  const ClinicalQuestion(
    key: 'cough_duration',
    titleEn: 'Cough for 2 weeks or more?',
    titleHi: 'क्या खांसी 2 सप्ताह या उससे अधिक समय से है?',
    descEn: 'Persistent, ongoing cough is the cardinal entry symptom for presumptive TB.',
    descHi: 'लगातार खांसी टीबी की प्राथमिक पहचान का प्रमुख लक्षण है।',
    weight: 2,
  ),
  const ClinicalQuestion(
    key: 'fever',
    titleEn: 'Recurrent or evening fever?',
    titleHi: 'क्या शाम को हल्का बुखार या बार-बार बुखार आता है?',
    descEn: 'Low-grade fever, often spiking in the evening or night.',
    descHi: 'हल्का बुखार जो अक्सर शाम या रात में बढ़ जाता है।',
    weight: 2,
  ),
  const ClinicalQuestion(
    key: 'night_sweats',
    titleEn: 'Drenching night sweats?',
    titleHi: 'क्या रात में अत्यधिक पसीना आता है?',
    descEn: 'Waking up with soaked nightclothes or sheets without physical exertion.',
    descHi: 'बिना किसी मेहनत के रात में कपड़े या चादर भीगने जितना पसीना आना।',
    weight: 2,
  ),
  const ClinicalQuestion(
    key: 'weight_loss',
    titleEn: 'Unintended weight loss?',
    titleHi: 'क्या बिना किसी कारण के वजन कम हुआ है?',
    descEn: 'Noticeable drop in body weight or loose-fitting clothing over the past month.',
    descHi: 'पिछले एक महीने में शरीर का वजन तेजी से घटना या कपड़े ढीले होना।',
    weight: 2,
  ),
  const ClinicalQuestion(
    key: 'hemoptysis',
    titleEn: 'Coughing up blood (Hemoptysis)?',
    titleHi: 'क्या खांसी या बलगम में खून आया है?',
    descEn: 'CRITICAL RED FLAG: Fresh blood or streaks of blood in sputum warrants immediate hospital assessment.',
    descHi: 'अति महत्वपूर्ण चेतावनी: बलगम में खून आना गंभीर स्थिति का संकेत है, तत्काल अस्पताल जाएं।',
    weight: 2,
    isRedFlag: true,
  ),
  const ClinicalQuestion(
    key: 'tb_contact',
    titleEn: 'Close household TB contact?',
    titleHi: 'क्या परिवार में किसी को पहले टीबी की बीमारी रही है?',
    descEn: 'Living with or caring for a confirmed active pulmonary TB patient in the past 2 years.',
    descHi: 'पिछले 2 वर्षों में घर या करीबी संपर्क में किसी टीबी मरीज के साथ रहना।',
    weight: 2,
    isHighRisk: true,
  ),
  const ClinicalQuestion(
    key: 'diabetes',
    titleEn: 'Known history of Diabetes Mellitus?',
    titleHi: 'क्या रोगी को मधुमेह (शुगर/डायबिटीज) है?',
    descEn: 'Elevated blood sugar impairs cellular immunity, tripling active TB reactivation risk.',
    descHi: 'शुगर होने पर रोग प्रतिरोधक क्षमता कमजोर होती है और टीबी का खतरा 3 गुना बढ़ जाता है।',
    weight: 2,
  ),
  const ClinicalQuestion(
    key: 'hiv',
    titleEn: 'HIV positive status / known exposure?',
    titleHi: 'क्या एचआईवी पॉजिटिव होने की जानकारी है?',
    descEn: 'High-risk immunocompromised profile requiring immediate priority screening pathway.',
    descHi: 'एचआईवी की स्थिति में टीबी की जांच तुरंत प्राथमिकता के आधार पर की जानी चाहिए।',
    weight: 2,
    isHighRisk: true,
  ),
  const ClinicalQuestion(
    key: 'immunosuppression',
    titleEn: 'Immunosuppressive condition / steroids?',
    titleHi: 'क्या रोगी लंबे समय से स्टेरॉयड या गंभीर दवाएं ले रहा है?',
    descEn: 'Prolonged corticosteroid use, cancer therapy, or organ transplant.',
    descHi: 'कैंसर, अंग प्रत्यारोपण या लंबे समय तक स्टेरॉयड दवाओं का सेवन।',
    weight: 1,
    isHighRisk: true,
  ),
  const ClinicalQuestion(
    key: 'silica_exposure',
    titleEn: 'Occupational silica/dust exposure?',
    titleHi: 'क्या पत्थर खदान, धूल या सिलिका में काम करने का अनुभव है?',
    descEn: 'Work history in stone crushing, silica mills, mining, or pottery factories.',
    descHi: 'पत्थर तोड़ने, खदानों, रेत या सीमेंट कारखानों में काम करने का इतिहास।',
    weight: 1,
  ),
];
