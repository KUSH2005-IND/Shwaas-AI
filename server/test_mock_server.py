import pytest
from httpx import AsyncClient, ASGITransport
from server.mock_server import app

@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["mode"] == "static_fixtures"

@pytest.mark.asyncio
async def test_pediatric_gate():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/predict", data={"age": 15})
        assert res.status_code == 400
        data = res.json()
        assert data["action"] == "route_to_pediatric_protocol"

@pytest.mark.asyncio
async def test_urgent_branch():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/predict", data={"age": 30, "hemoptysis": 2})
        assert res.status_code == 200
        data = res.json()
        assert data["fusion"]["tier"] == "URGENT"
        assert data["red_flag_detected"] is True
        assert "session_id" in data

@pytest.mark.asyncio
async def test_gradcam_flag():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/predict?include_gradcam=true", data={"age": 30})
        assert res.status_code == 200
        data = res.json()
        assert "gradcam_image" in data
        assert data["gradcam_image"].startswith("data:image/jpeg;base64,")

@pytest.mark.asyncio
async def test_quality_gates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Silence simulation
        res_silence = await client.post(
            "/predict",
            files={"file": ("cough_silence.wav", b"fakebytes", "audio/wav")},
            data={"age": 25}
        )
        assert res_silence.status_code == 400
        assert res_silence.json()["action"] == "request_new_recording"

        # Clipping simulation
        res_clip = await client.post(
            "/predict",
            files={"file": ("cough_clipping.wav", b"fakebytes", "audio/wav")},
            data={"age": 25}
        )
        assert res_clip.status_code == 400
        assert "clipping" in res_clip.json()["message"].lower()
