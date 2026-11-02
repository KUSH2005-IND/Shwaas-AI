from io import BytesIO
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
from src.api import create_app
from src.rules import Questionnaire, route

def test_bad_or_missing_audio_cannot_block_reported_red_flag(tmp_path):
    with TestClient(create_app(tmp_path / "missing")) as client:
        assert client.get("/health").status_code == 200
        assert not client.get("/health").json()["audio_bundle_loaded"]
        for files in (None, {"file": ("bad.wav", b"invalid", "audio/wav")}):
            response = client.post("/screen", data={"questionnaire": '{"hemoptysis":true}'}, files=files)
            assert response.status_code == 200
            assert response.json()["priority"] == "URGENT"
            assert response.json()["audio_model"]["score"] is None

def test_unknown_is_not_no_and_invalid_questionnaires_are_rejected(tmp_path):
    with TestClient(create_app(tmp_path / "missing")) as client:
        result = client.post("/predict").json()
        assert result["priority"] == "COMPLETE_QUESTIONNAIRE"
        assert "hiv" in result["unknown_answers"]
        for questionnaire in ('{"fever":1}', '{"age":-1}', '{"made_up_weight":100}', "broken"):
            assert client.post("/screen", data={"questionnaire": questionnaire}).status_code == 422
        legacy = client.post("/predict", data={"age": 35, "fever": 2})
        assert legacy.status_code == 422
        assert "questionnaire JSON" in legacy.json()["detail"]

def test_valid_audio_with_missing_model_retains_questionnaire_result(tmp_path):
    stream = BytesIO()
    sf.write(stream, np.sin(np.arange(48000) * .1) * .1, 16000, format="WAV")
    with TestClient(create_app(tmp_path / "missing")) as client:
        result = client.post("/screen", data={"questionnaire": '{"tb_contact":true}'},
                             files={"file": ("sample.wav", stream.getvalue(), "audio/wav")}).json()
        assert result["audio_model"]["status"] == "model_unavailable"
        assert result["priority"] == "CLINICAL_REVIEW"

def test_loaded_bundle_api_scores_audio(dataset, bundle):
    _, _, frame = dataset
    with TestClient(create_app(bundle[0])) as client:
        with open(frame.audio_path.iloc[0], "rb") as handle:
            response = client.post("/screen", files={"file": ("sample.wav", handle, "audio/wav")})
        assert response.status_code == 200
        assert response.json()["audio_model"]["status"] == "available"
        assert 0 <= response.json()["audio_model"]["score"] <= 1

def test_acoustic_score_cannot_cancel_clinical_trigger():
    decision = route(Questionnaire(cough_duration_days=30, tb_contact=True), False)
    assert decision["priority"] == "CLINICAL_REVIEW"
    assert decision["channels_disagree"] is True
