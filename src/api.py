"""Questionnaire-first screening API. No network calls or weights at import time."""
from __future__ import annotations
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from src.audio import AudioError, assess_quality, load_audio
from src.common import ROOT
from src.inference import Predictor
from src.rules import Questionnaire, route

LOGGER = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

def create_app(model_dir: str | Path | None = None) -> FastAPI:
    directory = Path(model_dir or os.environ.get("SHWAAS_MODEL_DIR", str(ROOT / "artifacts/mel")))

    @asynccontextmanager
    async def lifespan(app):
        app.state.predictor = None
        app.state.model_status = "unavailable"
        try:
            app.state.predictor = await run_in_threadpool(Predictor, directory)
            app.state.model_status = "bundle_loaded"
        except Exception as error:
            LOGGER.warning("Audio bundle unavailable: %s. Questionnaire routing remains active.", error)
        yield
        app.state.predictor = None

    app = FastAPI(title="ShwaasAI Screening Prototype", version="0.2.0", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "questionnaire_available": True,
                "audio_bundle_loaded": getattr(app.state, "predictor", None) is not None,
                "model_status": getattr(app.state, "model_status", "unavailable")}

    @app.post("/screen")
    @app.post("/predict")
    async def screen(request: Request, questionnaire: str = Form("{}"), file: UploadFile | None = File(None)):
        unexpected = set(await request.form()) - {"questionnaire", "file"}
        if unexpected:
            raise HTTPException(422, detail="Send raw answers in the questionnaire JSON form field; "
                                "unsupported form fields: " + ", ".join(sorted(unexpected)))
        try:
            answers = Questionnaire.model_validate_json(questionnaire)
        except ValidationError as error:
            raise HTTPException(422, detail=error.errors(include_url=False, include_context=False)) from error
        # Routing is independent of audio success. Never exit early on a bad recording.
        audio = {"status": "not_provided", "score": None, "acoustic_flag": None}
        quality = None
        if file is not None:
            try:
                contents = await file.read(MAX_UPLOAD_BYTES + 1)
                if len(contents) > MAX_UPLOAD_BYTES:
                    raise AudioError("Recording exceeds the 10 MB upload limit.")
                y = await run_in_threadpool(load_audio, contents)
                quality = assess_quality(y).to_dict()
                if not quality["usable"]:
                    raise AudioError("Please record again: " + ", ".join(quality["reasons"]))
                predictor = getattr(app.state, "predictor", None)
                if predictor is None:
                    audio["status"] = "model_unavailable"
                else:
                    audio = await run_in_threadpool(predictor.score_waveform, y)
            except AudioError as error:
                audio = {"status": "record_again", "score": None, "acoustic_flag": None, "message": str(error)}
            except Exception:
                LOGGER.exception("Audio inference failed; retaining questionnaire routing.")
                audio = {"status": "model_unavailable", "score": None, "acoustic_flag": None}
            finally:
                await file.close()
        decision = route(answers, audio.get("acoustic_flag"))
        return {
            "status": "success" if audio["status"] == "available" else "partial",
            "audio_model": audio, "audio_quality": quality,
            "questionnaire": answers.model_dump(),
            **decision,
            "fusion": {"tier": decision["priority"], "status": "versioned_rules"},
        }

    return app

app = create_app()
