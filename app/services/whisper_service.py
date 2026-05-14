from __future__ import annotations

import whisper
import asyncio
from app.config import WHISPER_MODEL
from app.services.diarization_service import diarize_segments, format_diarized_transcript

_model = None


def load_model(size: str | None = None):
    global _model
    model_size = size or WHISPER_MODEL
    print(f"Loading Whisper model '{model_size}'... (this may download the model on first run)")
    _model = whisper.load_model(model_size)
    print(f"Whisper model '{model_size}' loaded successfully.")


def _transcribe_sync(file_path: str, diarize: bool = False) -> dict:
    if _model is None:
        load_model()
    result = _model.transcribe(file_path)

    if diarize and result.get("segments"):
        segments = [
            {"start": s["start"], "end": s["end"], "text": s["text"]}
            for s in result["segments"]
        ]
        diarized = diarize_segments(file_path, segments, num_speakers=2)
        transcript = format_diarized_transcript(diarized)
    else:
        transcript = result["text"].strip()

    return {
        "text": transcript,
        "language": result.get("language", "unknown"),
    }


async def transcribe_file(file_path: str, diarize: bool = False) -> dict:
    return await asyncio.to_thread(_transcribe_sync, file_path, diarize)
