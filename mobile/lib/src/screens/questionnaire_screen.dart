import 'package:flutter/material.dart';
import 'package:mobile/src/localization/app_strings.dart';
import 'package:mobile/src/models/question_model.dart';
import 'package:mobile/src/theme/app_theme.dart';
import 'package:mobile/src/screens/audio_recorder_screen.dart';

class QuestionnaireScreen extends StatefulWidget {
  final Map<String, dynamic> workerInfo;
  final int age;
  final String sex;
  final String village;
  final Map<String, int>? initialAnswers;

  const QuestionnaireScreen({
    super.key,
    required this.workerInfo,
    required this.age,
    required this.sex,
    required this.village,
    this.initialAnswers,
  });

  @override
  State<QuestionnaireScreen> createState() => _QuestionnaireScreenState();
}

class _QuestionnaireScreenState extends State<QuestionnaireScreen> {
  int _currentIndex = 0;
  final Map<String, int> _answers = {};

  @override
  void initState() {
    super.initState();
    // Do NOT default to 0 (No). Questions must start unselected / empty by default.
    // Only pre-fill questions that were affirmatively detected by OCR (value == 2).
    if (widget.initialAnswers != null) {
      widget.initialAnswers!.forEach((key, val) {
        if (val == 2) {
          _answers[key] = 2;
        }
      });
    }
  }

  void _recordAnswerAndAdvance(int value) {
    final currentQ = allQuestions[_currentIndex];
    setState(() {
      _answers[currentQ.key] = value;
    });

    // Provide a brief 200ms feedback pause so the user sees their selection before transition
    Future.delayed(const Duration(milliseconds: 200), () {
      if (!mounted) return;
      if (_currentIndex < allQuestions.length - 1) {
        setState(() {
          _currentIndex++;
        });
      } else {
        _proceedToAudioScreen();
      }
    });
  }

  void _onNextPressed() {
    final currentQ = allQuestions[_currentIndex];
    if (!_answers.containsKey(currentQ.key)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Please select Yes, No, or Unsure before proceeding."),
          duration: Duration(seconds: 2),
        ),
      );
      return;
    }

    if (_currentIndex < allQuestions.length - 1) {
      setState(() => _currentIndex++);
    } else {
      _proceedToAudioScreen();
    }
  }

  void _proceedToAudioScreen() {
    // Ensure all 10 questions have an answer (safeguard against any missing)
    final finalAnswers = <String, int>{};
    for (var q in allQuestions) {
      finalAnswers[q.key] = _answers[q.key] ?? 0;
    }

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AudioRecorderScreen(
          workerInfo: widget.workerInfo,
          age: widget.age,
          sex: widget.sex,
          village: widget.village,
          answers: finalAnswers,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final question = allQuestions[_currentIndex];
    final progress = (_currentIndex + 1) / allQuestions.length;
    final selectedValue = _answers[question.key];

    return Scaffold(
      appBar: AppBar(
        title: Text(AppStrings.get('quiz_title')),
      ),
      body: Column(
        children: [
          // Linear Progress Indicator
          LinearProgressIndicator(
            value: progress,
            backgroundColor: AppTheme.pastelBlue,
            valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.accentBlue),
            minHeight: 6,
          ),

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  "Question ${_currentIndex + 1} of ${allQuestions.length}",
                  style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textMuted),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.pastelBlue,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Text(
                    "${(progress * 100).toInt()}% Done",
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppTheme.obsidianNavy),
                  ),
                ),
              ],
            ),
          ),

          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Red Flag Alert Badge if Hemoptysis
                  if (question.isRedFlag)
                    Container(
                      margin: const EdgeInsets.only(bottom: 16),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: Colors.red.shade50,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: Colors.red.shade200),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.report_problem, color: Colors.red),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              AppStrings.get('red_flag_alert'),
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: Colors.red.shade900,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                  // Question Card in 28px rounded Interexy style
                  Card(
                    margin: EdgeInsets.zero,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(28),
                      side: const BorderSide(color: AppTheme.cardBorderColor, width: 1.2),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                width: 34,
                                height: 34,
                                decoration: const BoxDecoration(
                                  color: AppTheme.pastelBlue,
                                  shape: BoxShape.circle,
                                ),
                                child: Center(
                                  child: Text(
                                    "${_currentIndex + 1}",
                                    style: const TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.obsidianNavy,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              if (question.isHighRisk)
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: AppTheme.pastelPeach,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: const Text(
                                    "High Risk Factor",
                                    style: TextStyle(fontSize: 11, color: AppTheme.obsidianNavy, fontWeight: FontWeight.bold),
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 18),
                          Text(
                            question.title,
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              height: 1.3,
                              color: AppTheme.textDark,
                              letterSpacing: -0.3,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            question.description,
                            style: const TextStyle(
                              fontSize: 14,
                              color: AppTheme.textMuted,
                              height: 1.4,
                            ),
                          ),
                          if (widget.initialAnswers != null && widget.initialAnswers![question.key] == 2) ...[
                            const SizedBox(height: 14),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              decoration: BoxDecoration(
                                color: AppTheme.pastelMint,
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: Colors.green.shade200),
                              ),
                              child: Row(
                                children: [
                                  Icon(Icons.auto_awesome, size: 16, color: Colors.green.shade900),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      "Pre-filled from medical document OCR (Verified: Yes)",
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                        color: Colors.green.shade900,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Three Large Action Buttons: YES (2), NO (0), UNSURE (1)
                  _buildOptionButton(
                    label: AppStrings.get('btn_yes'),
                    value: 2,
                    isSelected: selectedValue == 2,
                    activeBackgroundColor: AppTheme.pastelMint,
                    activeAccentColor: const Color(0xFF059669),
                    icon: Icons.check_circle_outline,
                  ),
                  const SizedBox(height: 12),
                  _buildOptionButton(
                    label: AppStrings.get('btn_no'),
                    value: 0,
                    isSelected: selectedValue == 0,
                    activeBackgroundColor: const Color(0xFFF1F5F9),
                    activeAccentColor: const Color(0xFF475569),
                    icon: Icons.cancel_outlined,
                  ),
                  const SizedBox(height: 12),
                  _buildOptionButton(
                    label: AppStrings.get('btn_unsure'),
                    value: 1,
                    isSelected: selectedValue == 1,
                    activeBackgroundColor: AppTheme.pastelPeach,
                    activeAccentColor: const Color(0xFFD97706),
                    icon: Icons.help_outline,
                  ),
                ],
              ),
            ),
          ),

          // Bottom Back / Next Floating Capsule Controls
          Container(
            margin: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppTheme.cardBorderColor, width: 1.2),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.05),
                  blurRadius: 15,
                  offset: const Offset(0, 5),
                ),
              ],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                TextButton.icon(
                  onPressed: _currentIndex > 0 ? () => setState(() => _currentIndex--) : null,
                  icon: const Icon(Icons.arrow_back, size: 18),
                  label: const Text("Previous", style: TextStyle(fontWeight: FontWeight.bold)),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.obsidianNavy,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                  onPressed: _onNextPressed,
                  iconAlignment: IconAlignment.end,
                  icon: const Icon(Icons.arrow_forward, size: 18, color: Colors.white),
                  label: Text(
                    _currentIndex == allQuestions.length - 1 ? "Audio Step" : "Next",
                    style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOptionButton({
    required String label,
    required int value,
    required bool isSelected,
    required Color activeBackgroundColor,
    required Color activeAccentColor,
    required IconData icon,
  }) {
    return InkWell(
      onTap: () => _recordAnswerAndAdvance(value),
      borderRadius: BorderRadius.circular(22),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        decoration: BoxDecoration(
          color: isSelected ? activeBackgroundColor : Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: isSelected ? AppTheme.obsidianNavy : AppTheme.cardBorderColor,
            width: isSelected ? 2.2 : 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: isSelected ? 0.06 : 0.02),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Icon(icon, color: isSelected ? activeAccentColor : Colors.grey.shade400, size: 24),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                  color: isSelected ? AppTheme.obsidianNavy : AppTheme.textDark,
                ),
              ),
            ),
            if (isSelected)
              Container(
                padding: const EdgeInsets.all(4),
                decoration: const BoxDecoration(
                  color: AppTheme.obsidianNavy,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.check, color: Colors.white, size: 14),
              ),
          ],
        ),
      ),
    );
  }
}
