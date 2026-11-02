#!/usr/bin/env python3
"""
Executes all triage branches against src.api:app, measures latency & payload sizes,
and saves the canonical JSON fixtures for Phase 0 and the mock server.
"""

import asyncio
import json
import time
from pathlib import Path
from httpx import AsyncClient, ASGITransport

PROJECT_ROOT = Path(__file__).parent.parent
SHWAAS_AI_DIR = PROJECT_ROOT if (PROJECT_ROOT / "src").exists() else (PROJECT_ROOT / "Shwaas-AI")
FIXTURES_DIR = PROJECT_ROOT / "fixtures"
AUDIO_DIR = FIXTURES_DIR / "audio"
RESPONSES_DIR = FIXTURES_DIR / "responses"
RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(SHWAAS_AI_DIR))
from src.api import app

async def run_benchmark():
    transport = ASGITransport(app=app)
    results = {}
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("=" * 70)
        print("🎯 RUNNING SHWAASAI ENDPOINT BENCHMARK & BRANCH CAPTURE")
        print("=" * 70)
        
        valid_wav_path = AUDIO_DIR / "sample_cough_01.wav"
        with open(valid_wav_path, "rb") as f:
            valid_bytes = f.read()

        # 1. Normal Success: LOW Risk (Clinical Score 0, Audio Model Low)
        t0 = time.perf_counter()
        res = await client.post(
            "/predict",
            files={"file": ("cough.wav", valid_bytes, "audio/wav")},
            data={"age": 28, "sex": "male", "cough_duration": 0, "fever": 0, "night_sweats": 0}
        )
        t_low = (time.perf_counter() - t0) * 1000
        results["branch_01_low_risk"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_low, 2),
            "response": res.json()
        }
        print(f"✅ [Branch 1: LOW Risk] Status: {res.status_code} | Latency: {t_low:.2f}ms")

        # 2. URGENT (Red flag: hemoptysis == 2)
        t0 = time.perf_counter()
        res = await client.post(
            "/predict",
            files={"file": ("cough.wav", valid_bytes, "audio/wav")},
            data={"age": 45, "sex": "female", "hemoptysis": 2, "cough_duration": 2}
        )
        t_urgent = (time.perf_counter() - t0) * 1000
        results["branch_02_urgent_red_flag"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_urgent, 2),
            "response": res.json()
        }
        print(f"🚨 [Branch 2: URGENT Red Flag] Status: {res.status_code} | Latency: {t_urgent:.2f}ms")

        # 3. HIGH_RISK_SCREENING (high_risk=True, clinical_score <= 3)
        t0 = time.perf_counter()
        res = await client.post(
            "/predict",
            files={"file": ("cough.wav", valid_bytes, "audio/wav")},
            data={"age": 34, "sex": "female", "hiv": 2, "cough_duration": 1}
        )
        t_high_risk = (time.perf_counter() - t0) * 1000
        results["branch_03_high_risk_screening"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_high_risk, 2),
            "response": res.json()
        }
        print(f"⚠️ [Branch 3: HIGH_RISK_SCREENING] Status: {res.status_code} | Latency: {t_high_risk:.2f}ms")

        # 4. MODERATE Risk (Clinical score 4-8)
        t0 = time.perf_counter()
        res = await client.post(
            "/predict",
            files={"file": ("cough.wav", valid_bytes, "audio/wav")},
            data={"age": 52, "sex": "male", "cough_duration": 2, "fever": 1, "night_sweats": 1, "weight_loss": 1}
        )
        t_mod = (time.perf_counter() - t0) * 1000
        results["branch_04_moderate_risk"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_mod, 2),
            "response": res.json()
        }
        print(f"🔶 [Branch 4: MODERATE Risk] Status: {res.status_code} | Latency: {t_mod:.2f}ms")

        # 5. HIGH Risk (Clinical score > 8)
        t0 = time.perf_counter()
        res = await client.post(
            "/predict",
            files={"file": ("cough.wav", valid_bytes, "audio/wav")},
            data={
                "age": 60, "sex": "male",
                "cough_duration": 2, "fever": 2, "night_sweats": 2, "weight_loss": 2,
                "diabetes": 1, "silica_exposure": 1
            }
        )
        t_high = (time.perf_counter() - t0) * 1000
        results["branch_05_high_risk"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_high, 2),
            "response": res.json()
        }
        print(f"🔴 [Branch 5: HIGH Risk] Status: {res.status_code} | Latency: {t_high:.2f}ms")

        # 6. WITH GRAD-CAM (include_gradcam=True)
        t0 = time.perf_counter()
        res = await client.post(
            "/predict?include_gradcam=true",
            files={"file": ("cough.wav", valid_bytes, "audio/wav")},
            data={"age": 30, "sex": "female", "cough_duration": 1}
        )
        t_gradcam = (time.perf_counter() - t0) * 1000
        json_data = res.json()
        gradcam_img = json_data.get("gradcam_image", "")
        img_bytes = len(gradcam_img.encode('utf-8'))
        results["branch_06_with_gradcam"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_gradcam, 2),
            "gradcam_payload_bytes": img_bytes,
            "gradcam_payload_kb": round(img_bytes / 1024, 2),
            "response": json_data
        }
        print(f"🎨 [Branch 6: With Grad-CAM] Status: {res.status_code} | Latency: {t_gradcam:.2f}ms | Payload: {img_bytes / 1024:.2f} KB")

        # 7. 400 Age Error (Age < 18)
        t0 = time.perf_counter()
        res = await client.post(
            "/predict",
            files={"file": ("cough.wav", valid_bytes, "audio/wav")},
            data={"age": 14, "sex": "female"}
        )
        t_age = (time.perf_counter() - t0) * 1000
        results["branch_07_error_pediatric_age"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_age, 2),
            "response": res.json()
        }
        print(f"👶 [Branch 7: 400 Pediatric Gate] Status: {res.status_code} | Latency: {t_age:.2f}ms")

        # 8. 400 Audio Clipping Error
        clip_path = AUDIO_DIR / "error_clipping.wav"
        with open(clip_path, "rb") as f:
            clip_bytes = f.read()
        t0 = time.perf_counter()
        res = await client.post(
            "/predict",
            files={"file": ("clipping.wav", clip_bytes, "audio/wav")},
            data={"age": 25}
        )
        t_clip = (time.perf_counter() - t0) * 1000
        results["branch_08_error_clipping"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_clip, 2),
            "response": res.json()
        }
        print(f"🔊 [Branch 8: 400 Clipping Error] Status: {res.status_code} | Latency: {t_clip:.2f}ms")

        # 9. 400 Audio Silence Error
        silence_path = AUDIO_DIR / "error_silence.wav"
        with open(silence_path, "rb") as f:
            silence_bytes = f.read()
        t0 = time.perf_counter()
        res = await client.post(
            "/predict",
            files={"file": ("silence.wav", silence_bytes, "audio/wav")},
            data={"age": 25}
        )
        t_silence = (time.perf_counter() - t0) * 1000
        results["branch_09_error_silence"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_silence, 2),
            "response": res.json()
        }
        print(f"🔇 [Branch 9: 400 Silence Error] Status: {res.status_code} | Latency: {t_silence:.2f}ms")

        # 10. 500 Internal Server Error (e.g. corrupt / non-audio data)
        t0 = time.perf_counter()
        res = await client.post(
            "/predict",
            files={"file": ("corrupt.wav", b"INVALID_CORRUPT_AUDIO_BYTES_HEADER", "audio/wav")},
            data={"age": 25}
        )
        t_500 = (time.perf_counter() - t0) * 1000
        results["branch_10_error_500"] = {
            "status_code": res.status_code,
            "latency_ms": round(t_500, 2),
            "response": res.json()
        }
        print(f"💥 [Branch 10: 500 Server Error] Status: {res.status_code} | Latency: {t_500:.2f}ms")

    # Save individual JSON files and benchmark summary
    for branch_name, data in results.items():
        with open(RESPONSES_DIR / f"{branch_name}.json", "w") as f:
            json.dump(data, f, indent=2)

    summary_file = FIXTURES_DIR / "benchmark_summary.json"
    with open(summary_file, "w") as f:
        json.dump(results, f, indent=2)

    print("=" * 70)
    print(f"💾 Saved {len(results)} branch fixtures to: {RESPONSES_DIR}")
    print(f"📊 Saved benchmark summary to: {summary_file}")
    
    # Latency comparison:
    gradcam_overhead = t_gradcam - t_low
    print("\n📈 LATENCY & PAYLOAD METRICS:")
    print(f"  • Baseline Inference (no Grad-CAM): {t_low:.1f} ms")
    print(f"  • Inference with Grad-CAM:          {t_gradcam:.1f} ms")
    print(f"  • Grad-CAM Computation Overhead:    +{gradcam_overhead:.1f} ms")
    print(f"  • Grad-CAM Base64 Payload Size:     {img_bytes / 1024:.2f} KB ({img_bytes} bytes)")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
