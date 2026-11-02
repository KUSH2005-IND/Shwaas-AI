"""
Complete test suite for ShwaasAI Extended Server (Phase 1).
Tests auth, screening pipeline, database queries, referral tracking, and stats.
"""

import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from server.main import app
from server.auth import create_access_token

def worker_headers(): return {"Authorization": "Bearer "+create_access_token({"sub":"asha_rani"})}
def doctor_headers(): return {"Authorization": "Bearer "+create_access_token({"sub":"test_doctor"})}

AUDIO_DIR = Path(__file__).parent.parent.parent / "fixtures" / "audio"

@pytest.fixture
def valid_wav_bytes():
    wav_path = AUDIO_DIR / "sample_cough_01.wav"
    with open(wav_path, "rb") as f:
        return f.read()

@pytest.fixture
def silence_wav_bytes():
    wav_path = AUDIO_DIR / "error_silence.wav"
    with open(wav_path, "rb") as f:
        return f.read()

@pytest.fixture
def clipping_wav_bytes():
    wav_path = AUDIO_DIR / "error_clipping.wav"
    with open(wav_path, "rb") as f:
        return f.read()

@pytest.mark.asyncio
async def test_health_and_version():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

        res_v = await client.get("/version")
        assert res_v.status_code == 200
        assert res_v.json()["version"] == "1.1.0"

@pytest.mark.asyncio
async def test_auth_login_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        res = await client.post("/auth/login", json={"username": "asha_rani", "password": "asha123"})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "asha_rani"
        assert data["role"] == "worker"

@pytest.mark.asyncio
async def test_auth_login_failure():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        res = await client.post("/auth/login", json={"username": "asha_rani", "password": "wrongpassword"})
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_pediatric_gate(valid_wav_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        res = await client.post(
            "/screenings",
            files={"file": ("cough.wav", valid_wav_bytes, "audio/wav")},
            data={"consent_given": "true", "age": 16, "village": "Sundarpur"}
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error_code"] == "PEDIATRIC_PATIENT"
        assert data["action"] == "route_to_pediatric_protocol"

@pytest.mark.asyncio
async def test_quality_gates(silence_wav_bytes, clipping_wav_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        # Silence
        res_sil = await client.post(
            "/screenings",
            files={"file": ("cough.wav", silence_wav_bytes, "audio/wav")},
            data={"consent_given": "true", "age": 30}
        )
        assert res_sil.status_code == 400
        assert res_sil.json()["error_code"] == "AUDIO_QUALITY_REJECTED"

        # Clipping
        res_clip = await client.post(
            "/screenings",
            files={"file": ("cough.wav", clipping_wav_bytes, "audio/wav")},
            data={"consent_given": "true", "age": 30}
        )
        assert res_clip.status_code == 400
        assert res_clip.json()["error_code"] == "AUDIO_QUALITY_REJECTED"

@pytest.mark.asyncio
async def test_create_screening_success_and_persist(valid_wav_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        # 1. Post a new screening
        res = await client.post(
            "/screenings",
            files={"file": ("cough.wav", valid_wav_bytes, "audio/wav")},
            data={"consent_given": "true",
                "age": 42,
                "sex": "female",
                "village": "Belagavi",
                "cough_duration": 2,
                "fever": 2,
                "night_sweats": 1  # Unsure
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        session_id = data["session_id"]
        assert session_id is not None
        assert data["patient_code"].startswith("PAT-BEL-")
        assert data["questionnaire_score"] == 4  # 2 + 2 = 4
        assert "night_sweats" in data["uncertain_symptoms"]
        assert data["fusion"]["tier"] in ["LOW", "MODERATE", "HIGH"]

        # 2. Verify record exists via GET /screenings/{id}
        res_get = await client.get(f"/screenings/{session_id}")
        assert res_get.status_code == 200
        detail = res_get.json()
        assert detail["id"] == session_id
        assert detail["referral"]["status"] == "pending"

@pytest.mark.asyncio
async def test_urgent_hemoptysis_override(valid_wav_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        res = await client.post(
            "/screenings",
            files={"file": ("cough.wav", valid_wav_bytes, "audio/wav")},
            data={"consent_given": "true", "age": 50, "hemoptysis": 2}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["red_flag_detected"] is True
        assert data["fusion"]["tier"] == "URGENT"
        assert data["pathway_code"] == "IMMEDIATE_TRIAGE"

@pytest.mark.asyncio
async def test_gradcam_generation(valid_wav_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        res = await client.post(
            "/screenings?include_gradcam=true",
            files={"file": ("cough.wav", valid_wav_bytes, "audio/wav")},
            data={"consent_given": "true", "age": 35}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["gradcam_image"] is not None
        assert data["gradcam_image"].startswith("data:image/jpeg;base64,")

@pytest.mark.asyncio
async def test_list_screenings_and_filters():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        # Default list
        res = await client.get("/screenings?limit=10")
        assert res.status_code == 200
        items = res.json()
        assert len(items) <= 10

        # Filter by tier
        res_urgent = await client.get("/screenings?tier=URGENT")
        assert res_urgent.status_code == 200
        for item in res_urgent.json():
            assert item["tier"] == "URGENT"

        # Filter by village
        res_vil = await client.get("/screenings?village=Rampur")
        assert res_vil.status_code == 200
        for item in res_vil.json():
            assert "Rampur" in item["village"]

@pytest.mark.asyncio
async def test_patch_referral_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        # Fetch one screening
        res_list = await client.get("/screenings?limit=1")
        items = res_list.json()
        assert len(items) > 0
        screening_id = items[0]["id"]

        # Update referral
        patch_res = await client.patch(
            f"/screenings/{screening_id}/referral",
            headers=doctor_headers(),
            json={"status": "tested", "notes": "CBNAAT confirmed positive; DOTS treatment initiated."}
        )
        assert patch_res.status_code == 200
        data = patch_res.json()
        assert data["status"] == "tested"
        assert "DOTS" in data["notes"]

        # Verify update
        get_res = await client.get(f"/screenings/{screening_id}")
        assert get_res.json()["referral"]["status"] == "tested"

@pytest.mark.asyncio
async def test_stats_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        res = await client.get("/stats")
        assert res.status_code == 200
        stats = res.json()
        assert stats["total_screenings"] >= 30
        assert "URGENT" in stats["tier_counts"]
        assert "tested" in stats["referral_counts"]
        assert isinstance(stats["referral_completion_rate"], float)
        assert "Rampur" in stats["screenings_by_village"]

@pytest.mark.asyncio
async def test_ocr_blank_and_text_image():
    import io
    from PIL import Image, ImageDraw

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=worker_headers()) as client:
        # 1. Blank/black image must return empty text
        blank_img = Image.new("RGB", (200, 100), color="black")
        blank_bytes = io.BytesIO()
        blank_img.save(blank_bytes, format="PNG")
        blank_bytes.seek(0)

        res_blank = await client.post(
            "/ocr/scan",
            files={"image": ("blank.png", blank_bytes.getvalue(), "image/png")}
        )
        assert res_blank.status_code == 200
        data_blank = res_blank.json()
        assert data_blank["text"] == ""
        assert data_blank["length"] == 0

        # 2. Image with medical text
        text_img = Image.new("RGB", (400, 100), color="white")
        draw = ImageDraw.Draw(text_img)
        draw.text((10, 10), "Chronic cough fever", fill="black")
        text_bytes = io.BytesIO()
        text_img.save(text_bytes, format="PNG")
        text_bytes.seek(0)

        res_text = await client.post(
            "/ocr/scan",
            files={"image": ("prescription.png", text_bytes.getvalue(), "image/png")}
        )
        assert res_text.status_code == 200
        data_text = res_text.json()
        assert "cough" in data_text["text"].lower() or "fever" in data_text["text"].lower()

