#!/usr/bin/env python3
"""
Generates 16kHz, 16-bit mono WAV test fixtures for ShwaasAI triage testing:
1. Valid cough bouts that pass audio_quality_gate (RMS > 0.005, Peak < 0.99)
2. Quiet audio that triggers the silence gate (< 0.005 RMS)
3. Clipped audio that triggers the distortion gate (Peak >= 0.99)
"""

import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "audio"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

SR = 16000
DURATION = 3.0  # seconds
TOTAL_SAMPLES = int(SR * DURATION)

def synthesize_cough(seed=42, intensity=0.7, n_bursts=2):
    np.random.seed(seed)
    t = np.linspace(0, DURATION, TOTAL_SAMPLES, endpoint=False)
    audio = np.zeros(TOTAL_SAMPLES)
    
    # Generate cough bursts
    burst_times = [0.4, 0.9] if n_bursts == 2 else [0.3, 0.7, 1.2]
    
    for bt in burst_times:
        burst_dur = 0.25 + np.random.uniform(0.05, 0.15)
        burst_env = np.exp(-((t - bt) ** 2) / (2 * (burst_dur / 3) ** 2))
        
        # Acoustic content: bandpass filtered noise + resonant harmonics (400 - 2500 Hz)
        noise = np.random.normal(0, 1, TOTAL_SAMPLES)
        formants = (
            np.sin(2 * np.pi * 500 * t) * 0.4 +
            np.sin(2 * np.pi * 900 * t) * 0.3 +
            np.sin(2 * np.pi * 1400 * t) * 0.2
        )
        burst = (noise * 0.7 + formants * 0.3) * burst_env
        audio += burst
        
    # Bandpass filter (300 - 4000 Hz)
    nyq = 0.5 * SR
    b, a = signal.butter(4, [300.0 / nyq, 4000.0 / nyq], btype='band')
    audio = signal.filtfilt(b, a, audio)
    
    # Scale peak to target intensity
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = (audio / max_val) * intensity
        
    # Add subtle background noise (well within safe RMS floor)
    ambient = np.random.normal(0, 0.008, TOTAL_SAMPLES)
    audio += ambient
    
    # Clamp below clipping
    audio = np.clip(audio, -0.85, 0.85)
    return audio

def save_wav(filename, audio_float):
    # Convert float [-1.0, 1.0] to int16
    int16_audio = (audio_float * 32767).astype(np.int16)
    out_path = FIXTURES_DIR / filename
    wav.write(str(out_path), SR, int16_audio)
    rms = np.sqrt(np.mean(audio_float ** 2))
    peak = np.max(np.abs(audio_float))
    print(f"Generated {filename:22} | RMS: {rms:.4f} | Peak: {peak:.4f} | Samples: {len(audio_float)}")

def main():
    print("🔊 Synthesizing 16kHz mono audio test fixtures...")
    
    # 1. Five diverse valid cough samples
    for i in range(1, 6):
        cough = synthesize_cough(seed=100 + i, intensity=0.65 + i * 0.03, n_bursts=(2 if i % 2 == 0 else 3))
        save_wav(f"sample_cough_{i:02d}.wav", cough)
        
    # 2. Silence fixture (RMS < 0.005)
    silence = np.random.normal(0, 0.001, TOTAL_SAMPLES)
    save_wav("error_silence.wav", silence)
    
    # 3. Clipping fixture (Peak >= 0.99)
    cough = synthesize_cough(seed=999, intensity=0.9)
    clipped = np.clip(cough * 2.0, -1.0, 1.0)
    save_wav("error_clipping.wav", clipped)
    
    # 4. Short fixture (1.0 second)
    short_audio = synthesize_cough(seed=101, intensity=0.7)[:SR]
    int16_short = (short_audio * 32767).astype(np.int16)
    wav.write(str(FIXTURES_DIR / "error_short.wav"), SR, int16_short)
    print(f"Generated error_short.wav        | Samples: {len(short_audio)} (1.0s)")

if __name__ == "__main__":
    main()
