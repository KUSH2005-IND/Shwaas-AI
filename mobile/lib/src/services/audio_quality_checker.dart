import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

class AudioQualityResult {
  final bool isValid;
  final String message;
  final double peak;
  final double rms;

  AudioQualityResult({
    required this.isValid,
    this.message = "Audio quality passed",
    this.peak = 0.0,
    this.rms = 0.0,
  });
}

class AudioQualityChecker {
  static const double maxAmplitudeThreshold = 0.99;
  static const double minRmsThreshold = 0.005;

  static Future<AudioQualityResult> verifyWav(String filePath) async {
    final file = File(filePath);
    if (!await file.exists()) {
      return AudioQualityResult(isValid: false, message: "Audio file not found on device.");
    }

    final bytes = await file.readAsBytes();
    if (bytes.length < 44) {
      return AudioQualityResult(isValid: false, message: "Audio file is corrupt or too short.");
    }

    // Skip 44-byte WAV header and read 16-bit signed PCM samples
    final pcmBytes = bytes.sublist(44);
    final sampleCount = pcmBytes.length ~/ 2;
    if (sampleCount < 16000) { // Less than 1 second at 16kHz
      return AudioQualityResult(isValid: false, message: "Recording is too short. Please cough for full 3 seconds.");
    }

    final byteData = ByteData.sublistView(pcmBytes);
    double maxAmp = 0.0;
    double sumSquares = 0.0;

    for (int i = 0; i < sampleCount; i++) {
      final sample = byteData.getInt16(i * 2, Endian.little);
      final normalized = sample.abs() / 32768.0;
      if (normalized > maxAmp) {
        maxAmp = normalized;
      }
      sumSquares += (sample / 32768.0) * (sample / 32768.0);
    }

    final rms = sqrt(sumSquares / sampleCount);

    if (maxAmp >= maxAmplitudeThreshold) {
      return AudioQualityResult(
        isValid: false,
        message: "Audio is clipping (distorted). Please move the microphone further away (~15 cm).",
        peak: maxAmp,
        rms: rms,
      );
    }

    if (rms < minRmsThreshold) {
      return AudioQualityResult(
        isValid: false,
        message: "Audio is too quiet. Please cough forcefully into the microphone.",
        peak: maxAmp,
        rms: rms,
      );
    }

    return AudioQualityResult(isValid: true, peak: maxAmp, rms: rms);
  }
}
