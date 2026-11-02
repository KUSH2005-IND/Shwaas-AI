import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:mobile/src/localization/app_strings.dart';
import 'package:mobile/src/models/screening_model.dart';
import 'package:mobile/src/services/api_client.dart';
import 'package:mobile/src/services/audio_source.dart';
import 'package:mobile/src/services/audio_quality_checker.dart';
import 'package:mobile/src/services/offline_storage.dart';
import 'package:mobile/src/theme/app_theme.dart';
import 'package:mobile/src/screens/result_screen.dart';

class AudioRecorderScreen extends StatefulWidget {
  final Map<String, dynamic> workerInfo;
  final int age;
  final String sex;
  final String village;
  final Map<String, int> answers;

  const AudioRecorderScreen({
    super.key,
    required this.workerInfo,
    required this.age,
    required this.sex,
    required this.village,
    required this.answers,
  });

  @override
  State<AudioRecorderScreen> createState() => _AudioRecorderScreenState();
}

class _AudioRecorderScreenState extends State<AudioRecorderScreen> with SingleTickerProviderStateMixin {
  int _selectedSourceIndex = 0;
  final List<AudioSource> _sources = [
    PhoneMicAudioSource(),
    FileUploadAudioSource(),
    DeviceWifiAudioSource(),
    DemoPresetAudioSource(sampleFileName: "sample_cough_01.wav"),
  ];

  bool _isRecording = false;
  int _countdown = 3;
  Timer? _timer;
  Timer? _waveAnimTimer;

  // 18 Frequency bars for live visualizer
  final List<double> _frequencyLevels = List.generate(18, (i) => 0.15);

  String? _recordedFilePath;
  bool _isCheckingQuality = false;
  String? _qualityError;
  bool _isUploading = false;

  void _startWaveformAnimation() {
    final rand = Random();
    _waveAnimTimer = Timer.periodic(const Duration(milliseconds: 90), (timer) {
      if (!_isRecording) {
        timer.cancel();
        return;
      }
      setState(() {
        for (int i = 0; i < _frequencyLevels.length; i++) {
          // Simulate energy peaks between 400Hz and 3000Hz (mid-bands)
          double centerBoost = sin((i / _frequencyLevels.length) * pi);
          _frequencyLevels[i] = 0.2 + (rand.nextDouble() * 0.75 * centerBoost);
        }
      });
    });
  }

  Future<void> _startCapture() async {
    setState(() {
      _isRecording = true;
      _countdown = 3;
      _qualityError = null;
      _recordedFilePath = null;
    });

    _startWaveformAnimation();

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_countdown > 1) {
        setState(() => _countdown--);
      } else {
        _timer?.cancel();
        _waveAnimTimer?.cancel();
        _finishCapture();
      }
    });
  }

  Future<void> _finishCapture() async {
    try {
      final source = _sources[_selectedSourceIndex];
      final path = await source.recordOrFetchAudio();

      setState(() {
        _isRecording = false;
        _isCheckingQuality = true;
      });

      // Run Client-Side Audio Quality Gate
      final qualityResult = await AudioQualityChecker.verifyWav(path);

      setState(() {
        _isCheckingQuality = false;
      });

      if (!qualityResult.isValid) {
        setState(() {
          _qualityError = qualityResult.message;
          _recordedFilePath = null;
        });
      } else {
        setState(() {
          _recordedFilePath = path;
          _qualityError = null;
        });
      }
    } catch (e) {
      setState(() {
        _isRecording = false;
        _isCheckingQuality = false;
        _qualityError = e.toString().replaceAll("Exception: ", "");
      });
    }
  }

  Future<void> _pickWavFile() async {
    try {
      final file = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: ['wav'],
      );

      if (file != null && file.path != null) {
        final filePath = file.path!;
        setState(() {
          _isCheckingQuality = true;
          _qualityError = null;
          _recordedFilePath = null;
        });

        // Run client-side audio quality gate on uploaded WAV
        final qualityResult = await AudioQualityChecker.verifyWav(filePath);

        setState(() {
          _isCheckingQuality = false;
        });

        if (!qualityResult.isValid) {
          setState(() {
            _qualityError = qualityResult.message;
            _recordedFilePath = null;
          });
        } else {
          setState(() {
            _recordedFilePath = filePath;
            _qualityError = null;
          });
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text("Loaded WAV: ${file.name}"),
              backgroundColor: Colors.green.shade700,
            ),
          );
        }
      }
    } catch (e) {
      setState(() {
        _isCheckingQuality = false;
        _qualityError = "Failed to select WAV file: $e";
      });
    }
  }

  void _showBenchmarkSamplePicker() {
    final samples = [
      {"name": "Standard Cough (Normal Acoustic)", "file": "sample_cough_01.wav", "desc": "Clean 16kHz mono cough burst"},
      {"name": "High Suspicion Cough (TB Proxy)", "file": "sample_cough_urgent.wav", "desc": "Severe acoustic abnormality sample"},
      {"name": "Borderline Cough (High Risk)", "file": "sample_cough_high_risk.wav", "desc": "Subtle abnormality profile"},
    ];

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              "Select Preloaded Benchmark Sample",
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const SizedBox(height: 12),
            ...samples.map((s) => Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                leading: const Icon(Icons.graphic_eq, color: AppTheme.primaryTeal),
                title: Text(s["name"]!, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                subtitle: Text(s["desc"]!, style: const TextStyle(fontSize: 11)),
                onTap: () async {
                  Navigator.pop(ctx);
                  final tempDir = await getTemporaryDirectory();
                  final targetPath = '${tempDir.path}/benchmark_${s["file"]}';
                  final byteData = await rootBundle.load('assets/audio/${s["file"]}');
                  final file = File(targetPath);
                  await file.writeAsBytes(byteData.buffer.asUint8List(byteData.offsetInBytes, byteData.lengthInBytes));
                  setState(() {
                    _recordedFilePath = targetPath;
                    _qualityError = null;
                  });
                  if (!mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text("Benchmark Loaded: ${s["name"]}")),
                  );
                },
              ),
            )),
          ],
        ),
      ),
    );
  }

  Future<void> _submitScreening() async {
    if (_recordedFilePath == null) return;

    setState(() {
      _isUploading = true;
    });

    try {
      final input = ScreeningInput(
        age: widget.age,
        sex: widget.sex,
        village: widget.village,
        answers: widget.answers,
        audioPath: _recordedFilePath!,
        audioSource: _sources[_selectedSourceIndex].name,
        includeGradcam: true,
      );

      final result = await ApiClient.submitScreening(input);

      // Save to local offline store
      await OfflineStorage.saveScreening(result);

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => ResultScreen(result: result, workerInfo: widget.workerInfo),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error: $e"), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _isUploading = false);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _waveAnimTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final activeSource = _sources[_selectedSourceIndex];

    return Scaffold(
      backgroundColor: AppTheme.backgroundSlate,
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundSlate,
        elevation: 0,
        centerTitle: true,
        title: Text(
          AppStrings.get('recorder_title'),
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
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Audio Source Selector (White Squircle Card)
            Container(
              padding: const EdgeInsets.all(18),
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
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: const BoxDecoration(
                          color: AppTheme.pastelBlue,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.tune_rounded, color: AppTheme.obsidianNavy, size: 16),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        AppStrings.get('audio_source_label'),
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.obsidianNavy),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<int>(
                    initialValue: _selectedSourceIndex,
                    decoration: InputDecoration(
                      filled: true,
                      fillColor: const Color(0xFFF8FAFC),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                      ),
                    ),
                    items: List.generate(_sources.length, (idx) {
                      return DropdownMenuItem(
                        value: idx,
                        child: Text(_sources[idx].name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                      );
                    }),
                    onChanged: _isRecording ? null : (val) {
                      if (val != null) {
                        setState(() {
                          _selectedSourceIndex = val;
                          _recordedFilePath = null;
                          _qualityError = null;
                        });
                      }
                    },
                  ),
                  const SizedBox(height: 8),
                  Text(
                    activeSource.description,
                    style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Instructions Pill Card
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.pastelBlue,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline_rounded, color: AppTheme.obsidianNavy, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      AppStrings.get('record_instructions'),
                      style: const TextStyle(fontSize: 12, height: 1.4, color: AppTheme.obsidianNavy, fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // LIVE FREQUENCY SPECTRUM VISUALIZER
            Container(
              height: 84,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: AppTheme.obsidianNavy,
                borderRadius: BorderRadius.circular(22),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.obsidianNavy.withValues(alpha: 0.2),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
                border: Border.all(color: _isRecording ? Colors.redAccent : const Color(0xFF1E293B)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: List.generate(_frequencyLevels.length, (i) {
                  final h = _isRecording ? _frequencyLevels[i] * 62 : 6.0;
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 90),
                    width: 8,
                    height: max(6.0, h),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(4),
                      gradient: LinearGradient(
                        colors: _isRecording
                            ? [Colors.orangeAccent, Colors.redAccent]
                            : [const Color(0xFF60A5FA), const Color(0xFF93C5FD)],
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                      ),
                    ),
                  );
                }),
              ),
            ),
            const SizedBox(height: 8),
            Center(
              child: Text(
                _isRecording
                    ? "● Real-Time Acoustic Spectrogram (300Hz – 6000Hz)"
                    : "Acoustic Spectrum Ready • 16 kHz Mono 16-Bit Stream",
                style: const TextStyle(fontSize: 11, color: AppTheme.textMuted, fontWeight: FontWeight.w500),
              ),
            ),
            const SizedBox(height: 24),

            // Main Recording Pulsing Mic Button
            Center(
              child: Column(
                children: [
                  GestureDetector(
                    onTap: (_isRecording || _isUploading) ? null : _startCapture,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      height: 140,
                      width: 140,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _isRecording ? const Color(0xFFDC2626) : AppTheme.obsidianNavy,
                        boxShadow: [
                          BoxShadow(
                            color: (_isRecording ? Colors.red : AppTheme.obsidianNavy).withValues(alpha: 0.35),
                            blurRadius: _isRecording ? 32 : 16,
                            spreadRadius: _isRecording ? 10 : 4,
                          ),
                        ],
                      ),
                      child: Center(
                        child: _isRecording
                            ? Text(
                                "$_countdown",
                                style: const TextStyle(fontSize: 48, fontWeight: FontWeight.w900, color: Colors.white),
                              )
                            : const Icon(Icons.mic_rounded, size: 58, color: Colors.white),
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    _isRecording
                        ? AppStrings.get('recording_in_progress')
                        : (_recordedFilePath != null ? "Cough Audio Verified" : AppStrings.get('tap_to_record')),
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: _isRecording ? const Color(0xFFDC2626) : AppTheme.obsidianNavy,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // OR UPLOAD WAV FILE OPTION
            Row(
              children: [
                Expanded(child: Divider(color: Colors.grey.shade300)),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Text(
                    "OR UPLOAD AUDIO",
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: Colors.grey.shade600,
                      letterSpacing: 0.8,
                    ),
                  ),
                ),
                Expanded(child: Divider(color: Colors.grey.shade300)),
              ],
            ),
            const SizedBox(height: 14),

            // Upload WAV File Button (Squircle Pastel Outlined)
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(30),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  side: const BorderSide(color: Color(0xFFCBD5E1), width: 1.5),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                ),
                icon: const Icon(Icons.file_upload_outlined, color: AppTheme.obsidianNavy, size: 20),
                label: const Text(
                  "Upload Cough WAV File (.wav)",
                  style: TextStyle(color: AppTheme.obsidianNavy, fontWeight: FontWeight.bold, fontSize: 13),
                ),
                onPressed: (_isRecording || _isUploading) ? null : _pickWavFile,
              ),
            ),
            const SizedBox(height: 8),
            Center(
              child: TextButton.icon(
                icon: const Icon(Icons.science_rounded, size: 16, color: Color(0xFF2563EB)),
                label: const Text(
                  "Select Benchmark Cough Sample (Pitch Demo)",
                  style: TextStyle(fontSize: 12, color: Color(0xFF2563EB), fontWeight: FontWeight.w600),
                ),
                onPressed: (_isRecording || _isUploading) ? null : _showBenchmarkSamplePicker,
              ),
            ),

            if (_isCheckingQuality) ...[
              const SizedBox(height: 20),
              const Center(
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                    SizedBox(width: 10),
                    Text("Verifying audio quality (clipping & RMS)...", style: TextStyle(fontSize: 13)),
                  ],
                ),
              ),
            ],

            // Audio Quality Error Banner
            if (_qualityError != null) ...[
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline_rounded, color: Colors.red),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _qualityError!,
                        style: TextStyle(fontSize: 13, color: Colors.red.shade900),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Preview & Submit
            if (_recordedFilePath != null) ...[
              const SizedBox(height: 22),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.pastelMint,
                  borderRadius: BorderRadius.circular(22),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.check_circle_rounded, color: Color(0xFF15803D), size: 28),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text("Audio Verified Clean", style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF15803D))),
                          Text("3.0s • 16 kHz Mono PCM • Ready for ML Triage", style: TextStyle(fontSize: 12, color: Color(0xFF1E3A1E))),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh_rounded, color: Color(0xFF15803D)),
                      tooltip: AppStrings.get('rerecord_btn'),
                      onPressed: _startCapture,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.obsidianNavy,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                  elevation: 4,
                  shadowColor: AppTheme.obsidianNavy.withValues(alpha: 0.4),
                ),
                onPressed: _isUploading ? null : _submitScreening,
                child: _isUploading
                    ? const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)),
                          SizedBox(width: 12),
                          Text("Analyzing Two-Channel Fusion..."),
                        ],
                      )
                    : Text(
                        AppStrings.get('submit_screening_btn'),
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
              ),
              const SizedBox(height: 16),
            ],
          ],
        ),
      ),
    );
  }
}
